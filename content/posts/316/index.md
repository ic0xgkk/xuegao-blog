---
aliases:
- /archives/316
categories:
- Linux
date: 2019-08-25 09:55:40+00:00
draft: false
title: 双系统Win10更新1903后grub无法进入
---

此文仅限于双系统（Windows10 + Linux Ubuntu）。更新Windows 10 1903后，grub开机报`error: unknown filesystem`，讲真一路Windows 10升级过来，从来没有遇到任何一次完美升级的，大大小小问题频出。微软在更新方面还是任重道远

当更新Windows 10 1903版本后，原本正常显示的grub启动时直接显示未知文件系统，同时已经自动进入救援模式，解决方法：

  1. `ls`查看硬盘序号和分区序号，此处我的Linux在hd1的gpt6号分区
  2. 设置根目录 `set root=(hd1,gpt6)`
  3. 设置grub目录 `set prefix=(hd1,gpt6)/boot/grub`
  4. 加载grub配置 `insmod normal`
  5. 进入grub界面 `normal`

方括号内的内容为命令。同时，这个配置并不会被保存，还需要手工重新安装grub，假设将efi分区挂载到**/tmp/efi**目录中了，使用如下命令：

```bash
grub-install –efi-directory=/tmp/efi /dev/nvme0
```

其中，/dev/nvme0指系统所在硬盘的设备文件描述符，安装后再使用如下命令重新生成配置即可
```bash
grub-mkconfig -o /boot/grub/grub.cfg
```
重启即可