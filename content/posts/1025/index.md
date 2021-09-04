---
aliases:
- /archives/1025
categories:
- Linux
date: 2020-02-21 04:51:47+00:00
draft: false
title: 手搓zabbix
---



## 前言

按照官方文档使用CentOS8的源安装失败，原因是缺少合适的libssh2依赖，无奈只能手搓了。

## 过程

官方文档： <https: current="" documentation="" install="" installation="" manual="" www.zabbix.com=""> 

我就不解释了直接贴关键命令了



```

./configure --prefix=/usr/local/zabbix  --enable-server --enable-agent --with-mysql=/usr/local/mariadb/bin/mysql_config --with-libcurl --with-libxml2

make 

groupadd --system zabbix
useradd --system -g zabbix -d /usr/local/zabbix/lib -s /sbin/nologin -c "Zabbix Monitoring System" zabbix

make install

```



**两个service**



```

# cat /etc/systemd/system/zabbix-server.service
[Unit]
Description=Zabbix Server
After=syslog.target network.target mariadb.service nginx.service httpd.service

[Service]
Type=simple
ExecStart=/usr/local/zabbix/sbin/zabbix_server -c /usr/local/zabbix/etc/zabbix_server.conf
ExecReload=/usr/local/zabbix/sbin/zabbix_server -R config_cache_reload
RemainAfterExit=yes
Restart=on-failure
RestartSec=20

[Install]
WantedBy=multi-user.target

```




```

# cat /etc/systemd/system/zabbix-agentd.service
[Unit]
Description=Zabbix Agentd
After=syslog.target network.target mariadb.service nginx.service httpd.service zabbix-server.service

[Service]
Type=simple
ExecStart=/usr/local/zabbix/sbin/zabbix_agentd -c /usr/local/zabbix/etc/zabbix_agentd.conf
RemainAfterExit=yes
Restart=on-failure
RestartSec=20


[Install]
WantedBy=multi-user.target

```



怎么用就不多说了，相信搞运维的都会的

配置文件也不多说了，按着配置文件上的英文提示改就行了。</https:>