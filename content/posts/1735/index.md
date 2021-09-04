---
aliases:
- /archives/1735
categories:
- 未分类
date: -001-11-30T00:00:00+00:00
draft: true
title: 数据结构五大常用算法
---

在前几天，有幸被字节跳动基础架构部发起面试，看起来工作内容也挺对口，一面非常无压力就过了，二面栽在了一个很简单的DP上……本来还打算借助工作时候再自顶向下学算法，现在看起来还是先花时间学吧，不然下一个机会可能又失之交臂了…



~~事实证明，即便是网络研发，数据结构基础还是得要有的…~~事实证明，这样的刷题脱离实际需求的学习方法太不适合我了，一道题往往能抠一天，好花时间，本着时间最大化利用原则，还是以眼前的有价值的需求为主好了…我还是先去写毕设的DPDK的路由表查表好了，吐了吐了

讲个笑话，数据结构基础非常好（偏重），可以去BAT，计算机网络基础非常好（偏重），可以去做甲方。

以我目前所接触到的，我把算法归类为这几大类：

  * DP，也就是动态规划。说真的这个思想不难，但是似乎我天生对所有的DP+字符串不感冒？
  * 回溯
  * 分治
  * 贪心
  * 分支界定

这些算法似乎看起来都不难，但是当它们+字符串的时候，GG？难道是我天生不感冒？？？

## 回溯

个人感觉其实就是DFS+剪枝，深搜一直在搜索符合条件的结果（不符合条件的进行剪枝），在每次搜索时完成一级搜索后向上返回，因此也叫回溯。在这个过程中，主要会使用递归来解决层级搜索问题

此处贴出来LeetCode 46，执行用时击败100%内存消耗击败64%，我拿这个细说回溯。

题目也很简单：给定一个** 没有重复** 数字的序列，返回其所有可能的全排列。那么输入[1, 2, 3]，你就会得到他的全排列[1,2,3], [1,3,2], [2,1,3], [2,3,1], [3,1,2], [3,2,1]


```
func permute(nums []int) [][]int {

        // 定义返回的全排列集合
	ret := [][]int{}

        // 定义标记位，其实就一个哈希表，不过优化一下的话容量可以直接设定为nums的大小。不过我测试了一下，没有肉眼可见的提升，可能是因为case的量都不大吧
	flags := map[int]bool{}

        // 遍历nums并且对应每个元素初始化其flag（用于后边判定是否重复）
	for i, _ := range nums {
		flags[nums[i]] = false
	}

        // 定义有名函数，不能使用:=，否则下方递归会提示无定义
	backtrack := func(path []int) {}
	backtrack = func(path []int) {

                // 当长度相等时说明符合并且返回
		if len(path) == len(nums) {

                        // Go中的slice底层其实是指针，因此要make一个新的并copy原本的path进去，否则后续对path的操作会影响原有的path中的数据
			p := make([]int, len(path))
			copy(p, path)
			ret = append(ret, p)
			return
		}

                // 挨个判断，重复则继续
		for i:=0; i<len(nums); <="" backtrack([]int{})="" backtrack(path)="" code="" flags[nums[i]]="false" i++="" if="" nums[i])="" path="path[:len(path)-1]" ret="" return="" {="" }="" 不重复则设置该数值flag，并且追加进path中="" 回溯，重置当前flag和path最后一位=""></len(nums);>
```


正好刚又做了一个题，LeetCode 82，也就一个递归思想，正好也放进来好了：


```
/**
 * Definition for singly-linked list.
 * type ListNode struct {
 *     Val int
 *     Next *ListNode
 * }
 */
func deleteDuplicates(head *ListNode) *ListNode {
    if head == nil {
        return nil
    }

    dup := map[int]int{}

    var past *ListNode = nil
    back := func(current *ListNode) {}
    back = func(current *ListNode) {
        _, ok := dup[current.Val]
        if !ok {
            dup[current.Val] = 1
        } else {
            dup[current.Val]++
        }

        if current.Next != nil {
            back(current.Next)
        } 

        if dup[current.Val] &gt; 1 {
            return
        } else {
            current.Next = past
            past = current
        }
    }

    back(head)

    return past
}
```


## DP动态规划

LeetCode 63


```
func uniquePathsWithObstacles(obstacleGrid [][]int) int {
	rowLen := len(obstacleGrid)
	if rowLen &lt; 1 {
		return 0
	}
	columLen := len(obstacleGrid[0])
	if columLen &lt; 1 {
		return 0
	}
	if obstacleGrid[0][0] == 1 {
		return 0
	}

	dp := make([][]int, rowLen)
	for i:=0; i<rowlen; &&="" +="" <="" code="" columlen)="" dp[i-1][j]="" dp[i]="make([]int," dp[i][j]="dp[i][j-1]" dp[rowlen-1][columlen-1]="" else="" for="" i="0" i!="0" i++="" if="" j="0" j!="0" j++="" j:="0;" j<columlen;="" obstaclegrid[i][j]="0" return="" {="" }=""></rowlen;>
```
