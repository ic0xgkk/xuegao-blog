---
title: 使用Linux内核的ftrace跟踪eBPF问题
date: 2022-02-15T22:56:11+08:00
draft: false
categories:
  - 网络基础
  - Linux
---

好久没写文章了，最近忙于各种事情，再加上过年~~放假~~学习，计划文章队列排的老长了。在此，新年第一篇文章，就先祝一下大家新年快乐哈~

eBPF香是香，但是竟然还有内核不支持？博主最近遇到了这么个情况，eBPF程序死活无法加载，始终报出Invalid argument的错误，为了解决这个问题，博主我花了好多天时间排查，跟踪了Linux内核的调用链，最后发现，问题竟然是...（实在想不到好的开头了）

## 背景

博主我写了个eBPF的程序，其中需要用到eBPF的XDP，在测试环境中加载eBPF程序时，始终出现这么个错误：

```bash
FATA[0030] load ebpf objects failed: field XskRedirector: program xsk_redirector: map xsk_map: map create without BTF: invalid argument
```

一时间陷入了沉思...用的cilium官方提供的loader，参数是参考cilium官方的写法写的，这怎么还能有错误？

在翻来覆去无脑改代码改了一下午之后，头昏脑涨毫无进展，决定还是利用科学的办法解决科学的问题——跟踪内核执行这部分系统调用的代码，来确定到底是哪里出现了问题。

## 注意

本文使用Linux内核级别的跟踪工具ftrace来跟踪调用链，在使用它之前，你得知道：

* 它可能并不能完整跟踪调用链，由于跟踪工具本身也会带来性能开销，因此在某些情况下，可能会丢失事件，至于怎么显式避免我也没有明确的答案，只能通过过滤手段缓解一些
* 在跟踪前，建议重启一下系统，因为实际环境确实遇到了开机时间太长（有一周多了），ftrace竟然dead了，重启之后才恢复
* 绝大多数函数在编译时都会被内联编译，如果你是学习需要，可以手工重新编译内核禁用掉内联（编译器设置），但是这会损失相当多的性能，**生产环境请不要这么做**。保持内联的话，则需要对每个调用的函数进行检查，检查其是否会被内联到上一级函数中
* 不一定所有的内核都有编译ftrace，请自行检查你使用的内核的config是否有编译对其的支持
* 请注意路径。本文所有的路径均使用了绝对路径，就我自己而言，一开始使用相对路径，结果就经常在窗口间切来切去，就忘记了路径的差异，最后导致配置没有设置上，跟踪没有成功。因此，建议保持使用绝对路径，以便方便、可靠地进行tracing

## 打开ftrace

由于它存在开销，因此默认操作系统是关闭了ftrace，需要通过sysctl手工打开。

```bash
sysctl -w kernel.ftrace_enabled=1
```

## 设置ftrace

▼ 首先，得把它挂载上

```bash
mount -t tracefs nodev /sys/kernel/tracing
```

▼ 其次，设置跟踪的调用的深度。假如你要跟踪一个系统调用，如果保持此值不变（默认为0）的话，则只会显示出来系统调用的根调用，不会显示到系统调用的函数中又执行了哪些函数。此处，我直接设置了1000，确保跟踪到尽可能多的调用情况。

但是，设置跟踪深度大时，造成的事件丢失也会增加，因此如果你只需要跟踪根函数，那么保持默认的0即可~

```bash
echo 1000 > /sys/kernel/tracing/max_graph_depth
```

▼ 有的操作系统上默认可能已经开启了ftrace，此时，我们需要先把它关掉，并清空和设置缓冲区

```bash
echo 0 > /sys/kernel/tracing/tracing_on
echo 10240 > /sys/kernel/tracing/buffer_size_kb
echo 1 >/sys/kernel/tracing/free_buffer
```

▼ 设置跟踪的系统调用。默认都是关闭的，如果你需要跟踪特定的系统调用，则需要对`/sys/kernel/tracing/events/syscalls`下相关的`enable`置`1`，此处，我只需要跟踪`sys_bpf`的系统调用，因此就只开启了下边这两个

```bash
echo 1 > /sys/kernel/tracing/events/syscalls/sys_enter_bpf/enable
echo 1 > /sys/kernel/tracing/events/syscalls/sys_exit_bpf/enable
```

▼ 设置跟踪器模式，此处我使用的`function_graph`来跟踪，会更加直观一些。可以通过`cat /sys/kernel/tracing/available_tracers`查看你的内核支持的模式，如果仅有`nop`，那么需要检查内核是否编译了相关的模块

```bash
echo function_graph > /sys/kernel/tracing/current_tracer
```

▼ 设置过滤的函数，注意其只会保留该函数的子调用和其本身。上文提到，会存在事件丢失，如果事件丢失非常严重影响到了问题排查，或者信息太多造成了扰乱，可以使用如下的方式设置过滤，只过滤保留特定的函数本身及其子调用。此处我仅需要跟踪`sys_bpf`的系统调用，因此也就只设置了这一个

```bash
echo "__x64_sys_bpf" > /sys/kernel/tracing/set_graph_function
```

## 开始跟踪

在开始跟踪你的程序之前，需要你对程序做出一些修改。当然可能也有更好的办法，欢迎评论告诉我哈~

▼ 为了不带上更多无关的信息，需要设置只对你需要跟踪的进程进行跟踪，即使用下边的方式设置进程的PID，即可通过PID进行事件过滤。由于大多数程序执行都是很快就结束了，因此这样的话可能不利于我们对问题进行跟踪。因此，你可能需要对程序进行一定的修改，使其在执行系统调用前，打印出PID并进行一个短暂的休眠，借此留足时间设置跟踪参数，以便于进行跟踪

```bash
echo 3433 > /sys/kernel/tracing/set_ftrace_pid
```

▼ 打开一个新的窗口（或者使用`tmux`等这样的工具），挂起执行下方命令，将管道的内容重定向到文件中。当然，你也可以使用buffer模式，但是由于其是RingBuffer，因此当缓冲区写满后，事件会出现丢失，因此此处也不再讲述它的用法

```bash
cat /sys/kernel/tracing/trace_pipe > /root/trace.log
```

▼ 开始跟踪

```bash
echo 1 > /sys/kernel/tracing/tracing_on
```

在跟踪期间，不建议进行其他有负载操作，也不推荐使用`tail`查看文件内容，因为实测这样会导致丢失更多的事件......也可能是我的测试机器太拉胯了。

▼ 当跟踪结束后（好比程序报错退出，或者系统调用部分已经结束等），即可停止跟踪。**然后，停掉刚刚`cat`的重定向即可。**

```bash
echo 0 > /sys/kernel/tracing/tracing_on
```

然后，即可在`/root/`下看到跟踪文件`trace.log`。

## 解读跟踪记录

一开始我使用了常见的Linux发行版进行测试（Rocky Linux），由于其是使用glibc库，编译机（Fedora）也是glibc库，因此运行十分良好。换到Alpine的操作系统上，始终无法执行，怀疑这个操作系统使用的C库是不是有些差别，看了一下发现还真的是musl。因此，如果你也使用的Alpine进行测试，你可能需要在编译机上启动一个Alpine的容器进行构建，以确保二进制文件能够正常在musl-based的系统中运行。

### 正常的执行流程

```bash
 0)               |  /* sys_bpf(cmd: 0, uattr: c00009d080, size: 40) */
 0)               |  __x64_sys_bpf() {
 0)               |    __sys_bpf() {
 0)               |      capable() {
 0)               |        security_capable() {
 0)   0.445 us    |          cap_capable();
 0)   1.332 us    |        }
 0)   2.080 us    |      }
 0)   0.720 us    |      bpf_check_uarg_tail_zero();
 0)               |      __check_object_size() {
 0)   0.320 us    |        check_stack_object();
 0)   0.945 us    |      }
 0)   0.433 us    |      security_bpf();
 0)   0.763 us    |      array_map_alloc_check();
 0)               |      array_map_alloc() {
 0)               |        capable() {
 0)               |          security_capable() {
 0)   0.315 us    |            cap_capable();
 0)   0.953 us    |          }
 0)   1.577 us    |        }
 0)               |        bpf_map_area_alloc() {
 0)               |          __bpf_map_area_alloc() {
 0)               |            __kmalloc_node() {
 0)   0.445 us    |              kmalloc_slab();
 0)               |              __cond_resched() {
 0)               |                rcu_note_context_switch() {
 0)   0.385 us    |                  rcu_qs();
 0)   1.105 us    |                }
 0)               |                raw_spin_rq_lock_nested() {
 0)   0.330 us    |                  _raw_spin_lock();
 0)   0.948 us    |                }
 0)   0.320 us    |                update_rq_clock();
 0)               |                pick_next_task_fair() {
 0)   0.325 us    |                  update_curr();
 0)   0.370 us    |                  pick_next_entity();
 0)   0.338 us    |                  pick_next_entity();
 ...
```

### 有问题的执行流程（保留了问题代码）

细心的朋友可能会发现，此处的`uattr`有些不太一样，因此原本到此处的事件都被丢失掉了，因此无法最好还原它了，比较遗憾。但是好在，bpf的系统调用是一个统一的入口，在分支之前所有的代码都是公共的，因此对于定位问题来说，换用其他阶段的调用也是能够解决问题的。

```bash
 0)               |  /* sys_bpf(cmd: 0, uattr: c000097058, size: 40) */
 0)               |  __x64_sys_bpf() {
 0)   0.239 us    |    bpf_check_uarg_tail_zero();
 0)               |    __check_object_size() {
 0)   0.186 us    |      check_stack_object();
 0)   0.602 us    |    } /* __check_object_size */
 0)   0.191 us    |    __might_fault();
 0) + 42.100 us   |  }
 0)               |  /* sys_bpf -> 0xffffffffffffffea */
```

### 有问题的执行流程（删掉了问题代码）

```bash
 0)               |  /* sys_bpf(cmd: 0, uattr: c000097080, size: 40) */
 0)               |  __x64_sys_bpf() {
 0)   1.115 us    |    bpf_check_uarg_tail_zero();
 0)               |    __check_object_size() {
 0)   0.425 us    |      check_stack_object();
 0)   1.989 us    |    }
 0)   0.355 us    |    __might_fault();
 0)   1.070 us    |    array_map_alloc_check();
 0)               |    array_map_alloc() {
 0)               |      capable() {
 0)               |        ns_capable_common() {
 0)   0.477 us    |          cap_capable();
 0)   1.390 us    |        }
 0)   2.115 us    |      }
 0)               |      bpf_map_charge_init() {
 0)   0.948 us    |        bpf_charge_memlock();
 0)   7.492 us    |      }
 0)               |      bpf_map_area_alloc() {
 0)               |        __kmalloc() {
 0)   0.357 us    |          kmalloc_slab();
 0)               |          fs_reclaim_acquire() {
 0)   0.350 us    |            __need_fs_reclaim();
 0)   0.840 us    |            fs_reclaim_acquire.part.0();
 0)   2.355 us    |          }
 0)               |          fs_reclaim_release() {
 0)   0.390 us    |            __need_fs_reclaim();
 0)   0.570 us    |            fs_reclaim_release.part.0();
 0)   2.163 us    |          }
 0)   0.370 us    |          should_failslab();
 0)               |          rcu_read_lock_sched_held() {
 0)               |            rcu_read_lock_held_common() {
 0)   0.385 us    |              rcu_lockdep_current_cpu_online();
 0)   1.147 us    |            }
 0)   1.965 us    |          }
 0) + 10.017 us   |        }
 0) + 10.790 us   |      }
 0)   0.368 us    |      bpf_map_init_from_attr();
 0)   0.345 us    |      bpf_map_charge_move();
 0) + 29.234 us   |    }
 0)   0.425 us    |    bpf_obj_name_cpy();
 0)               |    _raw_spin_lock_bh() {
 0)   0.443 us    |      __local_bh_disable_ip();
 0)   0.962 us    |      do_raw_spin_lock();
 0)   8.790 us    |    }
 ...
```

### 对比和定位

在对比之前，我想补充一下，如果你也需要这样对比了解的话，可以先让程序能够正常运行起来，最好的办法是有问题的和正常的都能运行到相同的代码，以先确定调用链上是否有什么不同。一开始我在跟踪时，遇错误就停，跟踪日志也只显示到了`check_stack_object()`，以至于我一度以为是`check_stack_object()`后边到`security_bpf()`之间的内容出现了问题，后边经过删掉问题代码重新运行之后，发现`security_bpf()`是被条件编译成了内联函数，因此问题根本就不在`security_bpf()`之前，反而在其之后。

▼ 那段被内联的代码，就长这样：

```c
#ifdef CONFIG_SECURITY
extern int security_bpf(int cmd, union bpf_attr *attr, unsigned int size);
extern int security_bpf_map(struct bpf_map *map, fmode_t fmode);
extern int security_bpf_prog(struct bpf_prog *prog);
extern int security_bpf_map_alloc(struct bpf_map *map);
extern void security_bpf_map_free(struct bpf_map *map);
extern int security_bpf_prog_alloc(struct bpf_prog_aux *aux);
extern void security_bpf_prog_free(struct bpf_prog_aux *aux);
#else
static inline int security_bpf(int cmd, union bpf_attr *attr,
					     unsigned int size)
{
	return 0;
}

static inline int security_bpf_map(struct bpf_map *map, fmode_t fmode)
{
	return 0;
}

static inline int security_bpf_prog(struct bpf_prog *prog)
{
	return 0;
}

static inline int security_bpf_map_alloc(struct bpf_map *map)
{
	return 0;
}

static inline void security_bpf_map_free(struct bpf_map *map)
{ }

static inline int security_bpf_prog_alloc(struct bpf_prog_aux *aux)
{
	return 0;
}

static inline void security_bpf_prog_free(struct bpf_prog_aux *aux)
{ }
#endif /* CONFIG_SECURITY */
```

当配置中没有设置`CONFIG_SECURITY`时，`security_bpf`函数就不会被导出，反而是直接条件编译直接内联到父函数里去了，因此在ftrace的记录中，也不会看到这个函数的调用过程。

▼ 我们来看内核对于此系统调用的实现，在排除了`bpf_check_uarg_tail_zero`执行没有问题之后，又排除了内联的`security_bpf`。

```c
SYSCALL_DEFINE3(bpf, int, cmd, union bpf_attr __user *, uattr, unsigned int, size)
{
	union bpf_attr attr;
	int err;

	if (sysctl_unprivileged_bpf_disabled && !capable(CAP_SYS_ADMIN))
		return -EPERM;

	err = bpf_check_uarg_tail_zero(uattr, sizeof(attr), size);
	if (err)
		return err;
	size = min_t(u32, size, sizeof(attr));

	/* copy attributes from user space, may be less than sizeof(bpf_attr) */
	memset(&attr, 0, sizeof(attr));
	if (copy_from_user(&attr, uattr, size) != 0)
		return -EFAULT;

	err = security_bpf(cmd, &attr, size);
	if (err < 0)
		return err;

	switch (cmd) {
	case BPF_MAPREATE:
		err = map_create(&attr);
		break;
	case BPF_MAP_LOOKUP_ELEM:
		err = map_lookup_elem(&attr);
		break;
	case BPF_MAP_UPDATE_ELEM:
		err = map_update_elem(&attr);
		break;
...
```

▼  这样一来，问题即可确定到是分支代码部分，大概就是下边这一块。

```c
...
    switch (cmd) {
	case BPF_MAPREATE:
		err = map_create(&attr);
		break;
	case BPF_MAP_LOOKUP_ELEM:
		err = map_lookup_elem(&attr);
		break;
	case BPF_MAP_UPDATE_ELEM:
		err = map_update_elem(&attr);
		break;
...
```

此处，由于`map_create`函数的定义是个内联函数，因此ftrace的记录上也不会显示它，我们需要进一步去查看。

由于最初的错误还没有到`array_map_alloc_check`函数，因此可以进一步确定问题在这个函数的调用之前。由于我还不怎么熟悉使用喷射大脑的CLion，因此很多函数的调用CLion并没有成功索引到，只能手工一个一个搜索。搜索不到`array_map_alloc_check`就只能继续搜索后边的其他函数，当搜索`bpf_map_area_alloc`函数时，定位到了`xskmap.c`文件中的`xsk_map_alloc`函数，可以看到该函数是静态内联的，而且其内同时存在`capable`、`bpf_map_charge_init`、`bpf_map_area_alloc`，基本可以确定是上文调用链的后续，还是比较符合的，因此接下来就倒着从它往上找。

▼  通过对该函数搜索引用，可以定位到`const struct bpf_map_ops xsk_map_ops`，通过对该常量再搜索，可以定位到`BPF_MAP_TYPE(BPF_MAP_TYPE_XSKMAP, xsk_map_ops)`，紧接着，一个非常鲜亮的条件编译展现了出来

```c
#if defined(CONFIG_XDP_SOCKETS)
BPF_MAP_TYPE(BPF_MAP_TYPE_XSKMAP, xsk_map_ops)
#endif
```

看到这里，相信很多朋友已经知道是什么问题了——没有启用这个条件编译，说白了就是少点了这么个参数。虽然还没有翻看上游的代码，但是此时我去对比了一下两个内核的config，确认了确实存在这个差异。

▼  起初，我以为eBPF可能对LPM Trie支持欠佳，直到看了下边的代码，发现它其实反而是被支持最好的...因为内核编译时不存在条件编译，默认启用了它，推测可能是直接复用了fib的数据结构吧

```c
...
#endif
BPF_MAP_TYPE(BPF_MAP_TYPE_HASH, htab_map_ops)
BPF_MAP_TYPE(BPF_MAP_TYPE_PERCPU_HASH, htab_percpu_map_ops)
BPF_MAP_TYPE(BPF_MAP_TYPE_LRU_HASH, htab_lru_map_ops)
BPF_MAP_TYPE(BPF_MAP_TYPE_LRU_PERCPU_HASH, htab_lru_percpu_map_ops)
BPF_MAP_TYPE(BPF_MAP_TYPE_LPM_TRIE, trie_map_ops)
#ifdef CONFIG_PERF_EVENTS
...
```

## 结论与验证

没有增加`CONFIG_XDP_SOCKETS`的内核配置。

▼  我添加上了这个参数，并重新编译了内核，这一次，它终于运行起来了

```bash
# ./ebpf_attach_test_musl -interface ens192
INFO[0000] current pid: 3396
INFO[0000] OK, go to sleeping...
^C
# ip link 
...
    prog/xdp id 1 tag 4fd8d07df9e801bb jited 
...
```

完结撒花。

## 总结

第一次跟踪内核的调用链，上手起来还是略有些困难，问题不断，好在还是硬抗了下来，最终也把问题定位出来了。

虽然难搞，但是针对这类问题，开辟了出了一条新的道路，以后再也不用在外围盲查问题了。

