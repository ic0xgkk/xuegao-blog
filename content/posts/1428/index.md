---
aliases:
- /archives/1428
categories:
- Linux
date: 2020-04-13 02:43:49+00:00
draft: false
title: OVSOF环境使用指南
---

OVSOF全称Open vSwitch & OpenFlow Environment，即是一个封装好的Open vSwitch（含OpenFlow支持）、同时集成了DPDK、集成了Docker OVS组件。该环境可以直接导入到VMware Workstation中，然后免部署了解和学习OpenFlow等SDN和容器相关内容。

## 版本状态

**当前版本号：** v1.0

**最后更新：** 2020年3月29日

Changelog在末尾

## 下载方式

**Sourceforge：** https://sourceforge.net/projects/xuegao-ovsof/files/

由于OVSOF环境体积较大，单独提供CDN分发成本太高，因此后续更新会全部托管于Sourceforge。由于这家服务器基本都在海外，如遇无法打开或者速度缓慢等问题，请自备梯子（不提供相关内容的解答）

## 集成组件

**Open vSwitch：** 2.12.0

**DPDK：** 19.11

**OpenFlow Support：** 1.0 – 1.5 with full support

**Docker：** 19.03.8

**基础镜像：** CentOS Linux release 8.1.1911 (Core)

## 默认登录

**用户名：** root

**密码：** 1111

## 注意

  * 确保VMware Workstation版本在12.0或者更高，否则会出现虚拟机不兼容而无法导入的情况
  * 最好不要修改语言和地区，不建议这么做
  * 主接口已经开启了DHCP，因此导入后不论是NAT模式还是Bridge模式，虚拟机均可通过DHCP获取地址
  * 不要打开HugePage，这可能会导致刚启动就触发OOM错误
  * 默认已经关闭了docker的iptables规则，并关闭了默认的bridge
  * 接口中的br0为Open vSwicth的bridge

## 使用方法

### 下载

前往上边的链接进行下载，你会得到`OVSOF-*.ova`这样一个文件

### 导入

如果你的电脑有安装VMware Workstation，那么正常情况下直接双击ova文件即可提示导入。如果没有安装，请先安装

### 虚拟机配置

敲黑板

编辑虚拟机配置，我们此处重点放在**内存**、**磁盘**和**网络**三部分

#### 内存

我建议内存最好不要小于2GB，否则可能会出现各种无法启动之类的问题。如果你使用途中出现莫名其妙的问题，请先尝试调大内存观察

#### 磁盘

由于存储使用了精简置备，因此你的虚拟机的存储使用是**动态增加**的！请确保你的虚拟机在持续使用中时磁盘有足够的存储空间，否则可能会导致你的操作系统和虚拟机都出现问题或者无法启动

#### 网络

网络建议使用NAT模式

每次打开虚拟机后，虚拟机的IP地址可能会跟随VMware DHCP服务变化而产生变动，通过控制台直接登录并使用`ifconfig`命令查看接口IP即可。

获得接口IP之后，便可以使用MobaXterm或者Xshell等SSH软件连接上并进行操作。

## 推荐阅读

并不推荐参考CSDN、简书之类中文社区的资料，这些中文社区的内容普遍存在一些问题就是——权威性不高、缺胳膊少腿、年代久远。参考这些社区的资料可能会误导你操作并产生一系列无法挽回的错误

无论任何时候，都推荐阅读官方的文档，获得第一手的资料，会使你学习效率大大提升并且规避掉很多坑。官方资料多为英文，不过语法和词汇都是一些常用词，慢慢看习惯就好了，更何况当今机器智能翻译这么发达，即便有些表达看不懂，借助这些翻译也可以很好的理解

**Open vSwicth文档（含DPDK、OF使用指南）：** http://docs.openvswitch.org/en/latest/

**Ryu文档（开源SDN控制器）：** https://ryu.readthedocs.io/en/latest/index.html

**Docker文档：** https://docs.docker.com/

不得不说docker的文档是我目前看的所有里边觉得最好的，非常直观。对于普通用户来说想熟练使用docker的话，完整阅读其文档非常有必要
