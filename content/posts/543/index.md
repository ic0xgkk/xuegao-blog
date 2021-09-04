---
aliases:
- /archives/543
categories:
- Linux
date: 2019-12-07 09:08:32+00:00
draft: false
title: CentOS8万金油脚本
---

万金油脚本~



老规矩~先贴一张女神~

![图片](./1570172952036-1.png)


一键替换国内源并且安装EPEL、关闭SELinux、禁用firewalld、 配置默认的防火墙规则并启用iptables service、安装常用的软件包

**注意：仅适用于CentOS8，并且建议对新装的系统使用，已经有过操作记录的不建议使用，避免配置被覆盖**



```bash
cat > /tmp/install.sh << EOFEND
#!/bin/bash

# 替换源
cd /etc/yum.repos.d
cp CentOS-Base.repo CentOS-Base.repo.bak
cp CentOS-AppStream.repo CentOS-AppStream.repo.bak
cp CentOS-Extras.repo CentOS-Extras.repo.bak
# 问题未知，注释掉这个无法同步缓存
# sed -i 's/mirrorlist=/#mirrorlist=/g' CentOS-Base.repo CentOS-AppStream.repo CentOS-Extras.repo
sed -i 's/#baseurl=/baseurl=/g' CentOS-Base.repo CentOS-AppStream.repo CentOS-Extras.repo
sed -i 's/http:\/\/mirror.centos.org/https:\/\/mirrors.aliyun.com/g' CentOS-Base.repo CentOS-AppStream.repo CentOS-Extras.repo

# 安装epel并重建缓存
dnf update -y
dnf install epel-release -y
dnf makecache -y

# 安装常用包
dnf install -y vim wget net-tools iproute lrzsz nano iftop bind-utils traceroute git zsh openssh-server screen NetworkManager-tui bash-completion procps passwd cronie chkconfig iputils util-linux-user tree sysstat iotop tmux

# 关闭SELinux
cat > /etc/selinux/config << EOF
# This file controls the state of SELinux on the system.
# SELINUX= can take one of these three values:
#     enforcing - SELinux security policy is enforced.
#     permissive - SELinux prints warnings instead of enforcing.
#     disabled - No SELinux policy is loaded.
SELINUX=disabled
# SELINUXTYPE= can take one of these three values:
#     targeted - Targeted processes are protected,
#     minimum - Modification of targeted policy. Only selected processes are protected.
#     mls - Multi Level Security protection.
SELINUXTYPE=targeted
EOF

# 禁用firewalld
systemctl disable --now firewalld.service

# 安装iptables service
dnf install iptables-services -y
cat > /etc/sysconfig/iptables << EOF
# sample configuration for iptables service
# you can edit this manually or use system-config-firewall
# please do not ask us to add additional ports/services to this default configuration
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -p tcp -m state --state NEW -m tcp --dport 22 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -j REJECT --reject-with icmp-host-prohibited
COMMIT
EOF
systemctl enable --now iptables.service

EOFEND
chmod a+x /tmp/install.sh
/tmp/install.sh
```



执行完成后记得重启系统让SELinux生效~