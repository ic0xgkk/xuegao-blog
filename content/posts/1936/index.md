---
title: 贴贴地气——解决Go语言没有原生RCU一致性原语的问题
date: 2021-12-12T15:23:13+08:00
draft: false
categories:
  - 网络基础
  - 语言
---

众所周知，Go语言里没有原生的RCU一致性原语，这在一些特定场景下，会造成蛮大的性能问题。为了解决这个问题，我们来贴贴地气，在符合适用场景需要的条件下，使用简单粗暴的手段解决问题。

## 前言

之所以需要RCU，其实是来自于Bridge中FDB（Forwarding Database）场景的一个需要。

Linux的Bridge会维护一个FDB表，用于存放MAC地址与端口等信息的映射关系，通过MAC Learning的方式更新FDB，以供后续转发时查表选择出端口和行为（好比Flood）。与之相似的动态VxLAN（也即VTEP），也是通过自己维护的FDB表中记录的VTEP IP等信息，决定封装的VxLAN的外层报文目标IP。[^1]可以说，FDB为二层转发提供了相当多样性的选择。

[^1]: Scaling bridge forwarding database. http://vger.kernel.org/lpc_net2018_talks/scaling_bridge_fdb_database_slidesV3.pdf

那么，FDB这么个数据结构一定就必须是无锁了。引入锁会带来锁竞争，势必会带来不必要的转发延迟和抖动。想想看，如果你在玩游戏时，忽然一个10ms，又忽然一个100ms，这样可以吗？所以，FDB的实现，一定不能引入锁，各种锁都不能引入。在看了Linux内核的源代码之后，终于找到了最佳解决办法——RCU。

```c
static void fdb_rcu_free(struct rcu_head *head)
{
	struct net_bridge_fdb_entry *ent
		= container_of(head, struct net_bridge_fdb_entry, rcu);
	kmem_cache_free(br_fdb_cache, ent);
}
```

## 题外话

我一直提倡开发者通过解决自己的实际问题这一过程，理解和实践产品、开发（技术）的真正奥义，这个过程，也就是所谓的**需求驱动**。毕竟，我们学习、工作，哪怕是研究，也都是为了解决实质性问题，而不是为了刷题而刷题，为了算法而算法，浪费时间在内卷。博主我写过蛮多技术文章，都是源于实际场景，在写开源项目时为了解决实际遇到的问题而留下的笔记，这样一个模式长期下来不仅解决了我众多实际需要，还衍生出来了很多可以商业化的解决方案，同时也大大增强了对产品和技术的理解。

如果你刚好也感兴趣，并且也期望在实际实践中感受一番，欢迎一起来书写开源参与项目~[^2]也欢迎加我微信交个朋友~[^3]目前，项目的TechSpec和Brief还没有更新上去，感兴趣的话可以先来找我要大概的~

[^2]: https://github.com/XUEGAONET/starOcean
[^3]: https://blog.xuegaogg.com/about/

## 注意

本文中的代码，截止至本文推送时，还未同步到GitHub。如有需要，麻烦下方评论告诉我，或者可以自行留意GitHub的Commit~

## 什么是RCU？

RCU全称为Read-copy update，也是一种同步机制。一开始看到这玩意的思路，就立马想到了BTRFS的COW（当然还有其他很多地方都在用，不仅仅是BTRFS），都是提供了一个“幻像”用于程序后续的读和写，实际上程序操作的内存中的内容已经不是原本的那一个了，有点类似偷梁换柱。

RCU的思路就是，对内存中的数据只读，如果需要修改，那么先读再复制，在复制的新的数据中进行修改，然后替换指针，等待原始值不再被使用时释放掉即可。在这个过程中，对引用（即指针）的操作必须是原子操作，以确保获取到的值（即指针指向的内存空间）始终是正确的、可用的，因此就需要使用到Go语言的原生的原子操作。但是，问题来了，什么时候释放呢？

## 什么时候释放？

在C语言中，我们可以自行实现RCU，按照本文的思路，可以通过引用计数、内存屏障等方式实现。需要释放时，可以手工释放内存空间，毕竟C语言中，你可以任意管理内存，没有垃圾回收机制。

但是，这是Go语言。当你对一个值进行修改后，需要将其地址通过原子操作覆盖到指针上，然而在Go语言中，可计数指针（好比`uintptr`）均为“不安全”的，因为垃圾回收器无法知道这么个内存地址的数值究竟对应的是哪个值，即便你保存了这个内存地址，但是它实际的内存空间可能已经被GC掉了。

所以，至少在Go语言中，**我们没办法界定声明过的变量的内存空间在什么时候被释放**。

我来举个例子：

```go
ptr := atomic.LoadUintptr(&r.instancePtr)
fdb := *(*map[uint64]*FDBEntry)(unsafe.Pointer(ptr))
```

▲ `ptr`为我通过原子操作得到的一个内存地址。假设原本有个变量`a`，`ptr`为变量`a`的内存地址。如果我在第二行使用内存地址还原成对应数据结构的指针时，变量`a`下文没有再被使用，同时GC触发过了一次，那么这个变量`a`的内存中的数据实际上已经被回收掉了。当下文有在使用时，那么转成对应数据结构的指针时，才能得到预期的内容。

当内存地址指向的空间被回收掉了，然后后续又对其进行访问，这个操作会被拒绝，从而就产生了`Segmentation Fault`错误，程序就gg了。

## 接接地气？

这里的接接地气，其实就是更贴近实际场景去思考。因为FDB查表是一次性的，因此当一次查找操作完成后，就只剩下了对Value的引用，就不存在对FDB这个Map的引用了。在尝试了多种思路解决后，找到了一种最简单粗暴的解决办法——临时关闭GC。

这种操作只适合于小程序，大点规模的程序建议不要使用。原因是，大点规模的程序可能存在比较多的情况会发生值逃逸（逃逸到堆上），临时关闭GC会造成这中间的时间段内内存膨胀（因为没有回收），中间GC关闭时间太长就会消耗非常多内存，容易触发OOM导致被kill。好在本文的程序不是大型程序，因此使用这种简单粗暴的方式是没有问题的。

```go
func (r *RCUFDB) updateLoop(waitTime time.Duration) {
	defaultGCPercent := debug.SetGCPercent(-1)
	debug.SetGCPercent(defaultGCPercent)

	changed := make([]*rcuFDBRequest, TableSize)

	for {
		// 如果已经关闭了，就直接退出
		select {
		case <-r.closeChan:
			return
		default:
		}

		// 固定使用已经初始化过的changed的内存空间
		changed = changed[:0]
		changed = append(changed, <-r.updateChan)
		l := len(r.updateChan)
		for i := 0; i < l; i++ {
			changed = append(changed, <-r.updateChan)
		}
        // 复制一个副本出来
		cloned := cloneFDB(r.instance)
        // 对副本进行修改
		patchFDB(changed, cloned)

		// 关闭GC
		debug.SetGCPercent(-1)
        // 修改引用，确保后边启用GC后副本不会被回收。此时因为GC已经临时关闭了，因此先前的内容也不会被回收
		r.instance = cloned
        // 原子操作替换为副本的指针指向的地址
		atomic.StoreUintptr(&r.instancePtr, uintptr(unsafe.Pointer(cloned)))
        // 等待可能还在使用中的先前的内容，由于是一个Map，因此只需要等待非常短时间（好比一秒）即可，或者出于保险，也可以加大
		time.Sleep(waitTime)
        // 重新启用GC
		debug.SetGCPercent(defaultGCPercent)
	}
}
```

那么总结一下，这个临时关闭GC的主要目的就是——防止先前的值的内存空间被GC回收。在临时关闭GC后，即便替换掉原本的值，造成了原本的值的引用丢失，由于此时GC关闭了，因此内存空间也不会被回收（仅限逃逸到堆上），先前还在使用这处内存空间的操作可以正常继续。此时我再通过原子操作换掉指针，后续的操作就会使用新的副本，然后最后只需要等待差不多时候原始的内存空间不会再使用了，重新打开GC，等待回收即可~

## 来点数据说话

写了两个Benchmark，一个是通过RCU实现的，一个是在RCU的基础之上额外加了个锁（读写锁）。我也就不再使用互斥锁了，毕竟这个场景压根就不能使用互斥。

▼ 纯RCU实现

```go
func BenchmarkRCUFDB_Edit(b *testing.B) {
	gcWait := time.Second * 1
	fdb := NewFDB(gcWait)
	defer fdb.Close()

	for i := uint16(0); i < 4000; i++ {
		fdb.Override(generateKV(i))
	}
	time.Sleep(gcWait)
	time.Sleep(gcWait)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		key, _ := generateKV(uint16(i % 4000))
		entry := fdb.Get(key)
		if entry == nil {
			panic("nil pointer")
		}
	}
}
```

▼ 在RCU基础上增加了个读写锁

```go
func BenchmarkFDBMutex(b *testing.B) {
	gcWait := time.Second * 1
	fdb := NewFDB(gcWait)
	defer fdb.Close()

	for i := uint16(0); i < 4000; i++ {
		fdb.Override(generateKV(i))
	}
	time.Sleep(gcWait)
	time.Sleep(gcWait)

	var lock sync.RWMutex

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		key, _ := generateKV(uint16(i % 4000))
		lock.RLock()
		entry := fdb.Get(key)
		lock.RUnlock()
		if entry == nil {
			panic("nil pointer")
		}
	}
}
```

▼ 测试结果

```bash
[xuegao@CD-OFFICE-DT bd]$ go test -bench='BenchmarkRCUFDB_Edit' -benchtime=100000000x -benchmem .
goos: linux
goarch: amd64
pkg: starOcean/bd
cpu: Intel(R) Core(TM) i5-10210U CPU @ 1.60GHz
BenchmarkRCUFDB_Edit-2          100000000               34.64 ns/op            0 B/op          0 allocs/op
PASS
ok      starOcean/bd    20.480s

[xuegao@CD-OFFICE-DT bd]$ go test -bench='BenchmarkFDBMutex' -benchtime=100000000x -benchmem .
goos: linux
goarch: amd64
pkg: starOcean/bd
cpu: Intel(R) Core(TM) i5-10210U CPU @ 1.60GHz
BenchmarkFDBMutex-2     100000000               45.11 ns/op            0 B/op          0 allocs/op
PASS
ok      starOcean/bd    21.531s

```

可以看到，在仅仅一个读写锁的变量因素下，每个操作的延迟从原本的`34.64ns`到了`45.11ns`，直接上升了30%的延迟。更何况，这还是非常理想情况下、完全串行、无并发测试的，如果换到并发操作的场景下，读写锁难免还要进行换锁操作，写操作抢到锁之后读就只能等待。

单单这么一个数据，已经很有说服力了，更别提完全无锁和有锁在并发时的差异了，完全没有可比性了。出于时间关系，并发的操作延迟我此处就不测试了，如果后边有时间了再补充，可以留意博客的文章（公众号的推送后只能改几个字）内容~

## 总结

可以看到，正是通过RCU这么个方式，使得读可以完全无锁，通过牺牲写操作的速度换取读的性能。毕竟在FDB的场景下，FDB表可以延迟更新，更何况还是分布式场景，但是对于转发的阻塞，一定是绝对无法接受的。牺牲写速度来换取稳定、超低的读速度，对Bridge的性能来说会有非常大帮助。

虽然Go语言中没有原生的RCU原语，但是折中一下换一个实现方式，也能得到一样的效果~

