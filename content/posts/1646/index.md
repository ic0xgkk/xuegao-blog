---
aliases:
- /archives/1646
categories:
- Linux
date: 2020-12-29 06:51:19+00:00
draft: false
title: 安装Magisk后无法使用部分APP解决方法
---

某些APP软件在近期更新后不能在装有Magisk等root过的机器上运行，同时即便是Magisk Hide已经打开，但是仍然没有效果。大家都知道国产毒瘤APP什么尿性，没有root再加上是原生的Android，怕是根本镇不住这些流氓软件，不root是不考虑的，那么此时此刻如何解决这个问题呢？





## 设备

设备：一加8

系统：OxygenOS 欧洲版（Android 11）

## 写在开始

今天一个手贱更新了下交通银行的APP，然后发现再也进不去了（提示设备环境有问题不给登录账户）。这就尴尬了。

还是想说一下，如果你刷的Magisk及其一些组件，是来源于百度搜到的网站或者百度网盘等渠道，而不是来源于开源社区（GitHub、GitLab和XDA等），请不要执行如下操作，该操作存在风险。我确实有见到过网上非正常渠道来的插件，安装之后使得系统上多了一大堆奇奇怪怪的广告，而且由于植入在系统层面，又无法轻易清除，如果这样的插件存在监听密码等行为，将会造成钱财损失。

因此，请勿在无法确保插件绝对可信的情况下，贸然安装或者按照下文屏蔽APP检测。

## 思路

隐藏Manager+Magisk Hide+屏蔽检测服务。

Magisk Hide从软件层面完成了root隐藏，但是，最好确认一下SafetyNet是否能通过，今天无意中在Google上看到说SafetyNet是Google从硬件层面引入的安全检测，应用程序能够直接检测到Bootloader状态和系统是否root。SafetyNet完全通过的情况下，应该能确保最大程度上隐藏。当然该段话的内容来源于互联网，我也不是很确定，暂时还没有查证

屏蔽检测服务即通过MyAndroidTools等应用，禁用APP的奇奇怪怪的服务。一般正常的服务名称都会看起来比较正常，检测服务的服务名称就会略有些“突兀”，禁用即可。



经过这样一个操作之后，就没有APP提示环境问题不给打开了。