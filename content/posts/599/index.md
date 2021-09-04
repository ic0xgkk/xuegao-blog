---
aliases:
- /archives/599
categories:
- Linux
date: 2020-01-01 03:41:48+00:00
draft: false
title: 曲线救国——使用反向代理解决Splunk Free认证问题
---

使用Splunk作为日志分析平台，当Enterprise授权到期后将会没有用户管理功能，页面打开将会直接进入控制台，这无疑是比较操蛋的一个问题。针对这个问题，可以使用nginx进行反向代理加上验证解决



本文只讨论基础认证（用户名和密码），并且没有部署ssl证书，如有想用ssl证书做客户端验证，还请看我早一段时间发的文章

首先需要将splunk free原本服务的端口通过防火墙关掉（默认端口8000）

然后配置反向代理



```nginx
server
    {
        listen 8001;
        server_name _ ;
        index index.html index.htm;
        root  /data/splunk;

        auth_basic           "Splunk";
        auth_basic_user_file /usr/local/nginx/conf/.htpasswd;

        location ~
        {
            try_files $uri @splunk;
        }

        location @splunk
        {
            internal;
            proxy_pass http://127.0.0.1:8000;
            include proxy.conf;
        }
        access_log off;
    }

```

/usr/local/nginx/conf/.htpasswd 该验证文件可以通过 apache2-utils (Debian, Ubuntu) or httpd-tools (RHEL/CentOS/Oracle Linux) 生成

使用命令 htpasswd -c .htpasswd <username> 即可

proxy.conf文件内容如下

```nginx
proxy_connect_timeout 300s;
proxy_send_timeout   900;
proxy_read_timeout   900;
proxy_buffer_size    32k;
proxy_buffers     4 32k;
proxy_busy_buffers_size 64k;
proxy_redirect     off;
proxy_hide_header  Vary;
proxy_set_header   Accept-Encoding '';
proxy_set_header   Host   $http_host;
proxy_set_header   Referer $http_referer;
proxy_set_header   Cookie $http_cookie;
proxy_set_header   X-Real-IP  $remote_addr;
proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header   X-Forwarded-Proto $scheme;
```

配置完成后重新加载nginx即可打开