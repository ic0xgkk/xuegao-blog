---
aliases:
- /archives/1307
categories:
- 语言
date: 2020-03-20 16:18:21+00:00
draft: false
title: Go LRU缓存算法
---

其实我本来不打算写这篇文章的，直到提交完代码后发现...**在所有 Go 提交中击败了99.42%的用户**...这就有点意思了，所以还是写一篇吧刚好总结一下。

## 前言

古人云，搬砖5分钟，修bug两小时。还真是。

本以为LRU能半个小时征服，结果不停出bug。不知道是下午太困了还是怎么回事，双向链表做交换时愣是把头节点和头节点后边的节点做了个交叉..晚饭后出去散步回来，怎么看感觉怎么不对劲，稍微一改就可以了...补这个窟窿下午花了两个多钟还愣是没看到..

**这也得出了一个总结**：能把重复操作单独封装成一个函数的，就单独封装起来，这样一出问题故障会明显很多（因为你只要调用这里就都有问题），而不至于像我最开始的写法，节点交换都是独立的，以至于出问题就很不容易看出来。

## 什么是LRU
> LRU是Least Recently Used的缩写，即最近最少使用，是一种常用的页面置换算法，选择最近最久未使用的页面予以淘汰。该算法赋予每个页面一个访问字段，用来记录一个页面自上次被访问以来所经历的时间 t，当须淘汰一个页面时，选择现有页面中其 t 值最大的，即最近最少使用的页面予以淘汰。
> 
> LRU – 百度百科

## 思路

**哈希表 + 双向链表**

### 为什么要用哈希表

如果你用数组的话，当你需要从中查找某个元素的话，那么这个查找性能可能会是个问题。那哈希表有什么优势呢，哈希表通过一个key和自定义的散列函数（这个看哈希表起初如何设计，个人觉得这个哈希表的设计和维护也要看场景来选择）来直接计算内存访问地址，就相当于人家还在遍历查找它想要的东西在哪里，哈希表已经直接通过key把地址给算出来了（暂且先不考虑冲突），那么这个速度差距可想而知。

晚点再单独写一遍纯手工哈希表的，到时候再详细说哈希表，本篇先不提及太多。

### 为什么要用双向链表

正如上边所说，哈希表的查找速度非常快，无冲突的情况下压根就不用查找直接就能得到key对应的value。那么问题来了，只有哈希表的情况下，我们如何实现缓存的前移？这个时候或许会有数组这个选项出现，但是有一个问题，缓存可能存在于数组的中间，位置几乎是不定的，那么即便我们能很快得到它的位置，但是如果要移动到头部，几乎要动整个数组，这个开销觉得并不划算，不如链表来的实在。

由于牵扯到缓存过期问题，因此会有一个操作是清除尾部（即多余的）的缓存（如果你不清就成内存泄漏了），这个时候需要来回在头部和尾部进行操作，这个场景下，双向链表最为合适。

## 代码

```go
package main

import "fmt"

/*
LRU大结构体
 */
type LRUCache struct {
	cacheMap map[int]*Instance
	Header *Instance // 变量名称为Header，实际是来回变的
	Length int // 哈希表的大小
	Size int // 已存入的缓存的数量
}

/*
每个KV的实体（双向链表）
 */
type Instance struct {
	Last *Instance
	key int
	value int
	Next *Instance
}

/*
LRU初始化函数
 */
func Constructor(capacity int) LRUCache {
	c := LRUCache{}
	c.cacheMap = make(map[int]*Instance, capacity)
	c.Length = capacity
	return c
}

/*
Get元素方法
此操作会将元素（若有）移到链表顶端
 */
func (this *LRUCache) Get(key int) int {
	// 先从哈希表中找到位置
	cache, ok := this.cacheMap[key]
	if ok == false {
		return -1
	}

	// 在链表头部，不需要操作
	if cache.Last == nil {
		return cache.value
	}

	// 在链表尾部，需要放到开始
	if cache.Next == nil {
		// 清理倒数第二个Next
		cache.Last.Next = nil

		// 放到前边
		this.transToHeader(cache)

		return cache.value
	}

	// 不在两边的
	// 链接前后两个节点
	cache.Last.Next = cache.Next
	cache.Next.Last = cache.Last

	// 移到前边
	this.transToHeader(cache)

	return cache.value
}

/*
Put函数
当覆盖写入时会隐式执行一次Get（前移使用）
当插入时会放在链表前端
 */
func (this *LRUCache) Put(key int, value int)  {
	cache, ok := this.cacheMap[key]
	if ok {
		cache.value = value
		_ = this.Get(key)
		return
	}

	// 当链表还是空的时候
	if this.Header == nil {
		this.Header = &Instance{
			Last:  nil,
			key:   key,
			value: value,
			Next:  nil,
		}
		this.cacheMap[key] = this.Header
		this.Size++
		return
	}

	// 当链表已经满了的时候
	if this.Size == this.Length {
		// 如果只有一个元素
		if this.Length == 1 {
			delete(this.cacheMap, this.Header.key)
			this.Header = &Instance{
				key:   key,
				value: value,
			}
			this.cacheMap[key] = this.Header
			return
		}

		// 移除末尾的
		// 把指针移到尾部
		this.goFooter()

		needDelete := this.Header
		this.Header = this.Header.Last
		this.Header.Next = nil
		delete(this.cacheMap, needDelete.key)

		// 新增到前边的
		ins := &Instance{
			key:  key,
			value: value,
		}
		this.transToHeader(ins)
		this.cacheMap[key] = ins

		return
	} else
	// 当链表还没满但是已经有头的时候，增加到前边
	{
		ins := &Instance{
			key:   key,
			value: value,
		}
		this.transToHeader(ins)
		this.cacheMap[key] = ins
		this.Size++
		return
	}
}

func (this *LRUCache) goHeader()  {
	for {
		if this.Header.Last == nil {
			break
		}
		this.Header = this.Header.Last
	}
}

func (this *LRUCache) goFooter()  {
	for {
		if this.Header.Next == nil {
			break
		}
		this.Header = this.Header.Next
	}
}

func (this *LRUCache) transToHeader(needTrans *Instance) {
	this.goHeader()
	oldHeader := this.Header
	this.Header = needTrans
	this.Header.Last = nil
	this.Header.Next = oldHeader
	oldHeader.Last = this.Header
}

/**
 * Your LRUCache object will be instantiated and called as such:
 * obj := Constructor(capacity);
 * param_1 := obj.Get(key);
 * obj.Put(key,value);
 */

func main() {
	var g int
	lru := Constructor(2)
	g = lru.Get(2)
	lru.Put(2, 6)
	g = lru.Get(1)
	lru.Put(1, 5)
	lru.Put(1, 2)
	g = lru.Get(1)
	g = lru.Get(2)
	fmt.Println(g)
}
```


特别需要留意的是，删除缓存和新增缓存时一定要更新哈希表...不然会比较尴尬

## 结果

![图片](./image-2.png)

可以看到，执行用时慢到爆表了..我大概感觉有的地方还是能优化的，只不过现在太晚了而且后边还有其他东西要学，暂且先挖个坑在这里把，等晚点有空再回来填

不过内存消耗还是挺满意的，也只能说，这个代码的空间复杂度挺不错的（至少我这么觉得），时间复杂度还是太高，晚点有空再来填坑吧