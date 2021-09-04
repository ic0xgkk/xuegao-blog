---
aliases:
- /archives/404
categories:
- Linux
date: 2019-09-20 12:56:18+00:00
draft: false
title: Docker自制镜像-CentOS-systemd
---

自制docker镜像，centos-systemd

抓下来centos官方的systemd docker镜像

之所以使用官方的镜像，是因为systemd启动时会竞争1 PID，如果直接使用官方的docker image，会直接造成systemd无法使用，因此建议如果要使用systemd一定要使用官方的修改版


> 这是因为dbus-daemon没能启动。
> 
> 其实 systemctl 并不是不可以使用。将CMD或者entrypoint设置为 /usr/sbin/init 即可。会自动将dbus等服务启动起来。 然后就可以使用 systemctl 了。
> 
> docker中使用systemd管理服务  - CSDN https://blog.csdn.net/m0_37886429/article/details/80350659

网上也看到有人有上述的办法，然而官方给出的说法是systemd会抢占PID，因此要使用官方提供的修改版的image。

我是用如下命令来抓取官方的镜像并进行封装，具体做出的修改在后面


```bash
docker run -it -d --privileged -v /sys/fs/cgroup:/sys/fs/cgroup:ro --name centos centos/systemd:latest 
docker commit --change='CMD ["/usr/sbin/sshd", "-D"]' -c "EXPOSE 22" centos centos-systemd:[忘了这里用不用加latest了]
docker tag centos-systemd:latest a980883231/centos-systemd:latest
docker exec -it test /bin/zsh
# 一堆操作，在下面
docker commit centos a980883231/centos-systemd
docker push a980883231/centos-systemd
```


做出的修改，默认密码为123456，有需要的可以去我的docker hub抓


```bash
df -h
cd /etc/dnf/
vi /etc/yum.repos.d/fedora.repo
vi /etc/yum.repos.d/fedora-updates.repo
vi /etc/yum.repos.d/fedora-modular.repo
vi /etc/yum.repos.d/fedora-updates-modular.repo
sudo dnf makecache
dnf install vim screen wget net-tools NetworkManager-tui lrzsz openssh-server
netstat -antp
netstat -antp
netstat -antp
systemctl enable sshd.service
systemctl start sshd.service
service sshd start
mkdir /var/run/sshd
vim /auto_sshd.sh
chmod a+x auto_sshd.sh 
passwd
chpasswd 
echo "root:123456" | chpasswd 
ssh-keygen -t dsa -f /etc/ssh/ssh_host_dsa_key
ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key
history 
```
