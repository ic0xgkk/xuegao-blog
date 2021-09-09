---
categories:
- Linux
date: -001-11-30T00:00:00+00:00
draft: true
title: Ocserv和daloRadius集成
---

众所周知，Cisco的AnyConnect还是蛮好用的，但是ASA、vASA的授权实在是顶天，折中一下只能用Ocserv做服务端了，体验也不会特别差，只是少了些高级功能。本文记录一下在自有的IDC和POP点中部署服务的过程。

# 写在开始

由于本文是在自有的IDC和POP点中部署，并且当前只是使用了原生的daloRadius和ocserv，并无修改，因此支持的功能属实少一些。同时，自有的IDC中节点是散开部署的，radius服务是在IDC中，ocserv位于各地域的POP点，因此结构上可能与传统的部署方式略有差别。

按照习惯，我仍然是只记录了重要的内容（比如配置），请参考本文末尾的参考资料进一步确认是否符合自身需要~

## 操作逻辑

此处我使用了podman部署MySQL和PMA，由于已经启动了实例，因此仅简单记录一下启动命令，详细需要自行前往Docker Hub查看


```bash
podman run --restart=always --name xuegao-mysql5 -v /data/mysql-data:/var/lib/mysql \
    -e MYSQL_ROOT_PASSWORD="<数据库root密码>" --network dbr0-core --ip=<分配的IP地址> -v /data/mysql-config:/etc/mysql \
    -d mysql:5 \
    --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

podman run --restart=always --name xuegao-pma -it -d -e PMA_HOST=<MySQL的IP地址> --network dbr0-core --ip=<分配的IP地址> phpmyadmin
```


上述容器启动命令中，我使用了联合挂载把配置文件和数据目录挂载了出来，配置文件需要预先置入挂入的目录中，否则可能会无法正常启动MySQL。

接下来在数据库中创建radius库并且分配用户，这个步骤就不多说了，直接看daloRadius的安装~此处我仍然使用容器（podman）部署daloRadius服务，原本仓库的位置见参考资料[^1]，由于这个仓库的构建逻辑稍微有一些问题，因此我建议在我提交的Commit没有合并之前，先使用我构建的镜像[^2]。我构建的镜像里相对原版改动了这些内容：

  * 原本构建没有完整安装依赖，暂时没遇到问题，不过保险起见还是全装上了
  * 修改了原本的访问路径到/
  * 增加了crontab task（借助Supervisor）实现定期清理挂死的Session
  * 修正了原版中初始化数据库时sed没有完全注释的问题，导致FreeRadius默认使用TLS连接数据库从而被强制关闭的问题（当然如果你有TLS连接的需要的话可以手工挂出配置并且修改）
  * 移动了FreeRadius的数据库初始化到Dockerfile中，确保sed失败直接不构建，避免引入问题到容器运行时
  * 新增了自动检查数据库是否为空，更新时将会自动跳过不为空的库

## 参考资料

[^1]: Frauhottelmann. Daloradius in Docker, Docker Hub. https://hub.docker.com/r/frauhottelmann/daloradius-docker
[^2]: Harris. Daloradius in Docker, Docker Hub. https://hub.docker.com/r/a980883231/daloradius-docker