---
aliases:
- /archives/1027
categories:
- Linux
date: 2020-02-21 06:52:08+00:00
draft: false
title: zabbix监控mariadb
---



坑有点多...

由于我是自己手动编译的zabbix，因此很多配置不能按照官方文档来，要进行一定修改

首先我的zabbix的路径为/usr/local/zabbix

按照官方给的文档的说法：https://www.zabbix.com/integrations/mysql，我需要把`template_db_mysql.conf`复制到`zabbix_agentd.d`目录中去，需要特别注意的是，配置文件默认是不引用这个目录中的配置文件的，要手动打开引用。

其次我试了大半天也没试出来`.my.cnf`正确的路径，看到网上（ https://www.zabbix.com/forum/zabbix-troubleshooting-and-problems/34520-newbie-question-why-won-t-zabbix-see-the-my-cnf-file ）有人直接把密码写进去了，试了试发现可以

### template_db_mysql.conf 

注意`-u -p` 一定要紧挨用户名和密码，否则报错



```
#template_db_mysql.conf created by Zabbix for "Template DB MySQL" and Zabbix 4.2
#For OS Linux: You need create .my.cnf in zabbix-agent home directory (/var/lib/zabbix by default)
#For OS Windows: You need add PATH to mysql and mysqladmin and create my.cnf in %WINDIR%\my.cnf,C:\my.cnf,BASEDIR\my.cnf https://dev.mysql.com/doc/refman/5.7/en/option-files.html
#The file must have three strings:
#
#
UserParameter=mysql.ping[*], /usr/local/mariadb/bin/mysqladmin -h"$1" -P"$2" ping

UserParameter=mysql.get_status_variables[*], /usr/local/mariadb/bin/mysql -h"$1" -P"$2" -u<Username> -p<Password> -sNX -e "show global status"

UserParameter=mysql.version[*], /usr/local/mariadb/bin/mysqladmin -s -h"$1" -P"$2" version

UserParameter=mysql.db.discovery[*], /usr/local/mariadb/bin/mysql -h"$1" -P"$2" -sN -u<Username> -p<Password> -e "show databases"

UserParameter=mysql.dbsize[*], /usr/local/mariadb/bin/mysql -h"$1" -P"$2" -u<Username> -p<Password> -sN -e "SELECT SUM(DATA_LENGTH + INDEX_LENGTH) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='$3'"

UserParameter=mysql.replication.discovery[*], /usr/local/mariadb/bin/mysql -h"$1" -P"$2" -u<Username> -p<Password> -sNX -e "show slave status"

UserParameter=mysql.slave_status[*], /usr/local/mariadb/bin/mysql -h"$1" -P"$2" -u<Username> -p<Password> -sNX -e "show slave status"
```

以及，由于访问数据库默认使用的localhost而不是我指定宏的127.0.0.1，因此建议新建用户时也将主机域设置为全局%