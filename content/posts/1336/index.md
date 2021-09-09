---
aliases:
- /archives/1336
categories:
- Linux
date: 2020-03-29 04:31:01+00:00
draft: false
title: Open vSwitch和DPDK在CentOS8的部署
---

最近在学DPDK，借助DPDK的优化，转发平面的包转发性能提升了将近10倍，这一指标实在是太香了。刚好同时担任助教在讲相关方面的课程，趁此机会顺便封装一个最小环境，顺便尝试部署一下OVS，一边为课程提供一个实验环境一边为后边落地提供一个保障。


## 前言

在本文开始写时，部署工作已经进行了一半了，前边的可能就没办法详细写了。

本文所部署的环境只是一个最小实验环境，包含如下程序：

  * docker，测试OVS是否畅通
  * openvswitch，打算借此作为SDN的实践平台
  * dpdk，提高ovs的性能

系统为CentOS Linux release 8.1.1911 (Core)

## 提醒

不要使用CentOS的源中的ovs，版本太老了。本文使用源码编译，同时DPDK也是手动编译引入OVS做静态链接。

DPDK的版本和OVS的一定要对应，这个可以看文档，亲测版本号如果与文档的不一致会造成configure失败（找不到DPDK）

## 建议阅读

前置任务。建议在开始部署之前先阅读这些内容

* http://docs.openvswitch.org/en/latest/intro/install/general/ 【官方的安装指南】
* http://docs.openvswitch.org/en/latest/faq/openflow/ 【官方的OpenFlow使用指南】
* http://docs.openvswitch.org/en/latest/intro/install/dpdk/ 【官方的DPDK集成指南】
* https://core.dpdk.org/download/ 【DPDK官方下载页】
* https://medium.com/@lhamthomas45/dpdk-19-11-is-out-why-you-should-update-and-how-to-do-so-7395810f71e 【DPDK 19.11 编译时出错误的解决办法】
* https://docs.pica8.com/display/picos2102cg/Configure+OVS+for+RYU+OpenFlow+Controller 【OVS配置OpenFlow控制器】

## 部署思路

  1. 安装系统，最简安装，安装常用软件和编译环境，替换源等
  2. 准备OVS和DPDK源码，版本要对应
  3. 编译安装DPDK
  4. 配置引入DPDK到OVS并编译安装
  5. 配置环境变量
  6. 安装docker并关闭默认没卵用的功能
  7. 配置OVS的systemd服务和依赖服务

## 步骤

### 环境准备

```bash
dnf update
cd /etc/yum.repos.d/
mkdir backup
mv CentOS-Base.repo backup/
curl -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-8.repo
mv CentOS-AppStream.repo CentOS-Extras.repo CentOS-PowerTools.repo CentOS-centosplus.repo backup/
dnf clean all
dnf makecache
dnf install epel-release
dnf update
sed -i 's|^#baseurl=https://download.fedoraproject.org/pub|baseurl=https://mirrors.aliyun.com|' /etc/yum.repos.d/epel*
sed -i 's|^metalink|#metalink|' /etc/yum.repos.d/epel*
dnf makecache
dnf install -y vim wget net-tools iproute lrzsz nano iftop bind-utils traceroute git zsh openssh-server screen NetworkManager-tui bash-completion procps passwd cronie chkconfig iputils util-linux-user tree sysstat iotop tmux
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
dnf install iptables-services -y
dnf remove firewalld --noautoremove
iptables -t filter -F
iptables -t filter -X
iptables -t filter -A INPUT -j ACCEPT 
iptables-save > /etc/sysconfig/iptables
systemctl enable iptables.service 
systemctl start iptables.service 
```


然后重启一下

### 编译DPDK

我使用的OVS是2.12.0版本，按照文档所说，只能使用DPDK 19.11版本。


```bash
cd /usr/src/
wget https://fast.dpdk.org/rel/dpdk-19.11.tar.xz
tar xvf dpdk-19.11.tar.xz 
cd dpdk-19.11/
export DPDK_DIR=/usr/src/dpdk-19.11
export DPDK_TARGET=x86_64-native-linuxapp-gcc
export DPDK_BUILD=$DPDK_DIR/$DPDK_TARGET
make install T=$DPDK_TARGET DESTDIR=install -j2
```


### 编译OVS

我手动指定了OVS的安装位置，便于管理。


```bash
wget https://www.openvswitch.org/releases/openvswitch-2.12.0.tar.gz
tar xvf openvswitch-2.12.0.tar.gz 
cd openvswitch-2.12.0/
./boot.sh 
./configure --prefix=/usr/local/ovs --with-dpdk=$DPDK_BUILD
# 这里报了个错误，要python2或3，补一个动态链接库就好了
dnf install python36-devel
./configure --prefix=/usr/local/ovs --with-dpdk=$DPDK_BUILD
make -j2
make 
# 这里报了个错误，具体什么错误可以看前置阅读中的那篇文章
sed -i "s/ ETHER_/ RTE_ETHER_/" lib/netdev-dpdk.c                    
sed -i "s/(ETHER_/(RTE_ETHER_/" lib/netdev-dpdk.c                       
sed -i "s/ ETHER_/ RTE_ETHER_/" lib/netdev-dpdk.c                       
sed -i "s/ e_RTE_METER_/ RTE_COLOR_/" lib/netdev-dpdk.c                       
sed -i "s/struct ether_addr/struct rte_ether_addr/" lib/netdev-dpdk.c                       
sed -i "s/struct ether_hdr/struct rte_ether_hdr/" lib/netdev-dpdk.c
make 
make install
```


### 配置环境变量

这就简单东西了，就不细说了，直接放个`/etc/profile`自己看吧，这行在尾部


```bash
export PATH="/usr/local/ovs/sbin:/usr/local/ovs/bin:/usr/local/ovs/share/openvswitch/scripts:$PATH"
```


### 安装docker

```bash
dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
dnf install docker-ce --nobest -y
```


由于docker默认会开一个bridge和一堆iptables规则出来，所以要把这些没卵用的东西关掉。在`/etc/docker`中新建一个daemon.json文件，然后把如下内容放进去就好。如果没有这个目录手动建一个就行


```json
{
    "iptables": false,
    "bridge": "none"
}
```


要额外安装一个ovs-docker，方法网上都有，自己Google吧，此处就不多说了

### 安装OVS的依赖和服务

service文件在源码的`rhel/systemd`目录中，建议根据实际路径更改后再拿去用

同时，要从这个目录中复制一个ovs-systemd-reload到ovs下的`share/openvswitch/scripts`目录中去，并且给a+x权限

service太多了懒得改了，所以我直接创建符号链接好了，把`/usr/local/ovs/share/openvswitch`链接到`/usr/share/openvswitch`，其他有必要改的再改

总共需要3个服务，第一个是主服务，剩余两个是静态服务（一个是ovsdb，一个是ovs daemon）并构成到主服务中去。只有主服务才可以被enable，静态服务要跟随主服务需要启动，不能被enable。目前所需要的最小构成就这三个，其他的暂且用不上

#### openvswitch.service

```ini
[Unit]
Description=Open vSwitch
Before=network.target network.service
After=network-pre.target ovsdb-server.service ovs-vswitchd.service
PartOf=network.target
Requires=ovsdb-server.service
Requires=ovs-vswitchd.service

[Service]
Type=oneshot
ExecStart=/bin/true
ExecReload=/usr/share/openvswitch/scripts/ovs-systemd-reload
ExecStop=/bin/true
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```


#### ovsdb-server.service

注意改PID文件的位置，否则可能会start后卡死（检测不到PID文件导致）


```ini
[Unit]
Description=Open vSwitch Database Unit
After=syslog.target network-pre.target
Before=network.target network.service
PartOf=openvswitch.service

[Service]
Type=forking
PIDFile=/usr/local/ovs/var/run/openvswitch/ovsdb-server.pid
Restart=on-failure
ExecStart=/usr/share/openvswitch/scripts/ovs-ctl --no-ovs-vswitchd --no-monitor --system-id=random start
ExecStop=/usr/share/openvswitch/scripts/ovs-ctl --no-ovs-vswitchd stop
ExecReload=/usr/share/openvswitch/scripts/ovs-ctl --no-ovs-vswitchd --no-monitor restart
```


#### ovs-vswitchd.service

同样要注意PID和套接字文件，不存在的依赖要删掉

有编译DPDK的下边的DPDK预加载部分要留着，没有编译DPDK的可以删除


```ini
[Unit]
Description=Open vSwitch Forwarding Unit
After=ovsdb-server.service network-pre.target systemd-udev-settle.service
Before=network.target network.service
Requires=ovsdb-server.service
ReloadPropagatedFrom=ovsdb-server.service
AssertPathIsReadWrite=/usr/local/ovs/var/run/openvswitch/db.sock
PartOf=openvswitch.service

[Service]
Type=forking
PIDFile=/usr/local/ovs/var/run/openvswitch/ovs-vswitchd.pid
Restart=on-failure
LimitSTACK=2M
#@begin_dpdk@
ExecStartPre=-/bin/sh -c '/usr/bin/chown :$${OVS_USER_ID##*:} /dev/hugepages'
ExecStartPre=-/usr/bin/chmod 0775 /dev/hugepages
#@end_dpdk@
ExecStart=/usr/share/openvswitch/scripts/ovs-ctl \
          --no-ovsdb-server --no-monitor --system-id=random \
          start
ExecStop=/usr/share/openvswitch/scripts/ovs-ctl --no-ovsdb-server stop
ExecReload=/usr/share/openvswitch/scripts/ovs-ctl --no-ovsdb-server \
          --no-monitor --system-id=random \
          restart
TimeoutSec=300

```


## 推荐额外阅读

也算是参考资料

* https://software.intel.com/en-us/articles/open-vswitch-with-dpdk-overview 【强烈推荐看一看】
* https://developer.ibm.com/recipes/tutorials/using-ovs-bridge-for-docker-networking/ 【如何让docker使用ovs桥】