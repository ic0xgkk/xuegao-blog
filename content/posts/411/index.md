---
aliases:
- /archives/411
categories:
- Linux
date: 2019-09-22 05:48:33+00:00
draft: false
title: Docker自制镜像-CentOS7
---

Docker自制镜像-CentOS7



源镜像：https://github.com/CentOS/sig-cloud-instance-images/blob/2cd93d6632e5476306240ce66a7a1ff929a6997f/docker/Dockerfile

改动：


```bash
docker run -it -d --privileged --name centos_t1 centos:latest
docker commit --change='CMD ["/usr/sbin/init"]' centos_t1 centos7_cv1
docker run -it -d --privileged --name centos_t2 centos7_cv1
docker exec -it centos_t2 /bin/bash
```


```bash
yum update
yum install -y vim wget epel-release net-tools iproute lrzsz nano iftop bind-utils traceroute git zsh openssh-server screen NetworkManager-tui
yum group install "Development Tools"
systemctl daemon-reload
vim /etc/ssh/sshd_config 
systemctl start sshd.service
systemctl enable sshd.service

yum install iptables-services
vim /etc/sysconfig/iptables
systemctl restart iptables.service
systemctl enable iptables.service

passwd
vim /etc/profile

```


在特权模式下，亲测systemd可用。

原来之前systemd无法执行只是dbus没有启动而已，难怪官方的dockerfile不能用，但是报错提示PID 1被抢占也一直引导我没有去尝试换一个方式，直到今天才算解决。

对于生产环境，建议重新生成SSH的私钥和公钥，具体命令如下：


```bash
  ssh-keygen -t dsa -f /etc/ssh/ssh_host_dsa_key
  ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key
```
