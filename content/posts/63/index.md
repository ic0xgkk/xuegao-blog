---
aliases:
- /archives/63
categories:
- 生产力
date: 2018-08-22 09:36:00+00:00
draft: false
title: 攒一台黑群晖
summary: 群晖的DSM真的好用，性能也不错，扩展性也很好，但是官方也限制了只能运行在自家的硬件上。不过好在，可以通过黑来解决（笑
---

估计很多人都用过群晖的DSM（DiskStation Manager）吧，不得不说的是，群晖的DSM NAS系统相当不错，不管是安装还是调试、维护，都很方便，而且管理选项很细致好用，性能也相当不错，扩展性也很好，唯独坑爹的一点是DSM只能运行在自家的硬件上，无法在非官方的硬件使用完整的功能，而且目前已经无法完全洗白了。不过某宝似乎有卖SN/MAC，可以半洗白或者全洗

## 黑群晖or白群晖?

黑群晖有官方的DSM系统，但是无法享受官方的增值服务和技术支持（好比QuickConnect）；白群晖可以享受到所有增值服务，不过买不起就是了～～

## 黑群晖硬件要求

博主我攒了一块D525的小板+1G DDR3内存跑DSM，1Gbps的网卡，亲测局域网能到110M/s，CPU几乎无负载。  
额外的设备，需要准备一个做引导盘(SATA或者U盘随意)，如果用U盘的话可以在synoboot配置中将U盘在DSM中隐藏（grub.cfg中配置PID VID参数），满足强迫症，除此之外还要准备一块硬盘，群晖不允许被安装在移动设备上，系统将会被安装在这块硬盘上（可以和存储空间共用）

## 需要

1. synoboot或者XPEnology（用于引导、安装、维护DSM系统），可以在这里下载 https://xpenology.club/downloads/
2. PAT文件（DSM的系统包），可以在这里下载 https://www.synology.com/en-global/support/download
3. SN生成工具，以便转码。百度找找这个文件serial_generator_new.html 
4. ChipGenius（U盘查看PID VID） 
5. osfmount（用于在Windows上挂载多分区的img镜像） 
6. starwindconverter（把img镜像转换为vmdk虚拟磁盘文件，虚拟机专用，非必需） 
7. synology-assistant（DSM管理工具，推荐安装） 
8. 得到SN算MAC工具。百度找下这个文件 Synology-mod-new.xlsm 是一个Excel表 
9. img写入U盘工具-rufus，可以在这里下载 http://rufus.akeo.ie

## 步骤

1. 使用 serial_generator_new.html 网页，打开后选设备3615xs，然后点击Generate生成序列号 
2. 目前你已经得到了一个SN序列号，下载文件库的第8个文件，用Excel打开，找到 Serial number 下边的红色字体，是这个表格生成的随机序列号，确认下Select model是DS3615xs，如果不是把其改成DS3615xs后再进行接下来操作！确认无误后，将我们刚刚生成的SN填入Serial number下边的框中，点击空白处后将会在 MAC 表中算出MAC，千万注意，不要再选择设备!否则SN会被重置 
3. 好了，目前已经得到了SN和MAC，接下来我们需要把SN和MAC填入synoboot镜像中，那么接下来下载安装文件库中的5，然后下载文件库1，确保文件名和路径中没有中文！！！否则会无法挂载！！！打开软件，选择 Mount new ，选择刚刚下载的img文件，弹出窗口中选择 Partition 0 – 15.0MB 这个分区，取消下边的 Read-only drive复选框，然后OK即可 
4. 定位到刚刚挂载的设备中的grub下的grub.cfg文件，编辑器打开，定位到以下内容 。然后把刚刚得到的SN ，MAC分别填入其中，如果是U盘做启动盘，需要下载文件库4，查看U盘的PID VID填入，然后保存文件后，osfmount中右键 dismount 即可 
```bash
set vid=0781
set pid=5590
set sn=1130L2N413557
set mac1=001233D50AD3
```
5. 现在的synoboot的img文件是我们编辑过的了，可以用rufus直接写入U盘，也可以用starwindconverter转换成虚拟机磁盘文件（VMware ESX和VMware Workstation的镜像不同，跟QEMU的也不同） 
6. 上机启动，把NAS主板连接网络，自己准备台电脑，安装文件库7，并下载2，安装7后打开，会自动搜索群晖设备，再按照提示安装就好啦
