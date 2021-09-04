---
aliases:
- /archives/466
categories:
- Linux
date: 2019-10-15 06:57:37+00:00
draft: false
title: CentOS8自动安装
---

部署集群环境，使用ks自动安装



首先先完成一台CentOS8安装，得到root目录下的一个anaconda-ks.cfg文件，文件内容如下


```bash
#version=RHEL8
ignoredisk --only-use=sda,sdb
# System bootloader configuration
bootloader --location=mbr --boot-drive=sda
# Partition clearing information
clearpart --none --initlabel
# Use graphical install
graphical
repo --name="AppStream" --baseurl=file:///run/install/repo/AppStream
# Use CDROM installation media
cdrom
# Keyboard layouts
keyboard --vckeymap=cn --xlayouts='cn'
# System language
lang en_HK.UTF-8 --addsupport=en_GB.UTF-8,en_US.UTF-8,zh_CN.UTF-8

# Network information
network  --bootproto=static --device=ens192 --gateway=192.168.100.1 --ip=192.168.100.x --nameserver=192.168.18.2 --netmask=255.255.255.0 --noipv6 --activate
# 此处x自己修改IP地址
network  --hostname=HOSTNAME
# 此处自行修改主机名

# Root password
rootpw --iscrypted PASSWD
# 此处自行设置密码（加密处理的）

# Run the Setup Agent on first boot
firstboot --enable
# Do not configure the X Window System
skipx
# System services
services --enabled="chronyd"
# System timezone
timezone Asia/Hong_Kong --isUtc
# Disk partitioning information
part pv.2933 --fstype="lvmpv" --ondisk=sdb --size=262142
part swap --fstype="swap" --ondisk=sda --size=10240
part /boot/efi --fstype="efi" --ondisk=sda --size=488 --fsoptions="umask=0077,shortname=winnt"
part / --fstype="xfs" --ondisk=sda --size=40470
volgroup cl_bs-data-vg --pesize=4096 pv.2933
logvol /var --fstype="xfs" --size=262140 --name=data --vgname=cl_bs-data-vg

%packages
@^minimal-environment

%end

%addon com_redhat_kdump --disable --reserve-mb='auto'

%end

%anaconda
pwpolicy root --minlen=6 --minquality=1 --notstrict --nochanges --notempty
pwpolicy user --minlen=6 --minquality=1 --notstrict --nochanges --emptyok
pwpolicy luks --minlen=6 --minquality=1 --notstrict --nochanges --notempty
%end

```


文件已脱敏。部分内容需要自己修改

紧接着，启动新安装，在grub页面时，选中install直接按e

找到启动设置的第二行（结尾是quiet），后边补充一句如下内容（同一行尾部补充即可，不要换行）


```
ks=http://192.168.18.7/ks2.cfg
```


当然，这个文件我已经提前上传到服务器了，当加完后按下Ctrl+X

默默等待安装即可~