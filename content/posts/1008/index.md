---
aliases:
- /archives/1008
categories:
- Linux
date: 2020-02-21 01:54:32+00:00
draft: false
title: nginx和httpd强迫症配置
---

## Nginx

首先注意一下nginx匹配location的顺序（优先级从上到下）：

  1. location = **（即精确匹配）**
  2. location ^~  **（即前缀匹配）**
  3. **按配置文件中顺序**
  4. location /uri **（即不带任何正则的路径）**
  5. location / **（即全局）**

### conf/base.conf

基本的安全策略，要确保所有隐藏目录（在Linux里隐藏目录文件名前都有个.）不能被访问



```nginx
location ~ /.well-known {
            allow all;
        }
        location ~ /\.
        {
            deny all;
        }
```



### conf/expires.conf

根据实际需要再改吧。

此处的过期是在文件时间上进行缓存（即判断文件是否修改），并不是缓存文件（作用不等于CDN）。



```nginx
        location ~ .*\.(mp3|wma|flv|mp4|wmv|ogg|avi|doc|docx|xls|xlsx|ppt|pptx|txt|pdf|zip|exe|tat|ico|swf|bmp|gif|jpeg|jpg|png|svg|tiff|woff2)$
        {
            expires      30d;
        }
        location ~ .*\.(js|css)?$
        {
            expires      3d;
        }
```



### conf/proxy-pass-php.conf

这个文件是拿军哥的改的，增加了负载均衡和故障切换（其实在这里是重试的作用，具体有没有效果我也不知道，参考文章：https://hashnode.com/post/how-to-configure-nginx-to-hold-the-connections-and-retry-if-the-proxied-server-returns-502-cilngkof700iteq53ratetsry）。



```nginx
        location /
        {
            try_files $uri @apache;
        }
        location @apache
        {
            internal;
            proxy_pass http://php_backend;
            proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
            include proxy.conf;
        }
        location ~ [^/]\.php(/|$)
        {
            proxy_pass http://php_backend;
            proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
            include proxy.conf;
        }
```



### conf/logger.conf

改了下日志格式，加上了CDN带上的客户端地址。这个要配合根配置文件中的logger一起修改使用。



```nginx
        if ($time_iso8601 ~ "^(\d{4})-(\d{2})-(\d{2})")
        {
            set $year $1;
            set $month $2;
            set $day $3;
        }
        access_log  /home/wwwlogs/nginx/$host.$year-$month-$day.log logger;
```



### conf/proxy.conf

反向代理的配置文件。我加长了发送和读取延迟，因为有时候POST请求会在服务端阻塞较长时间，超时时间设置太短可能会导致请求还没有处理完超时直接返回502，这个超时建议设置成和php的最大脚本执行时间限制相同吧。

其次是改了`X-Forwarded-For`，由于我套了一层CDN，按照原来的add的操作，`X-Forwarded-For`会有两个IP，有些统计插件解析时可能会无法解析。因此直接改成这样就好了：`proxy_set_header   X-Forwarded-For $http_x_forwarded_for;`。



```nginx
proxy_connect_timeout 300s;
proxy_send_timeout   300s;
proxy_read_timeout   300s;
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
proxy_set_header   X-Forwarded-For $http_x_forwarded_for;
proxy_set_header   X-Forwarded-Proto $scheme;
```



### conf/nginx.conf

我在网关打开了全局的日志，httpd把日志全部关了

内存不多，核心不多，因此就调成了单进程模式。



```nginx
user  www www;
worker_processes 1;
worker_cpu_affinity auto;
error_log  /home/wwwlogs/nginx/error.log  crit;
pid        /usr/local/nginx/logs/nginx.pid;
#Specifies the value for maximum file descriptors that can be opened by this process.
worker_rlimit_nofile 51200;
events
    {
        use epoll;
        worker_connections 1000;
        multi_accept on;
        accept_mutex on;
    }
http
    {
        log_format logger       '$remote_addr - '
                                '$http_x_forwarded_for - '
                                '$remote_user, '
                                '[$time_local], '
                                '"$request" $status $body_bytes_sent '
                                '"$http_referer" "$http_user_agent" "$gzip_ratio"';
        include       mime.types;
        default_type  application/octet-stream;
        server_names_hash_bucket_size 128;
        client_header_buffer_size 32k;
        large_client_header_buffers 4 32k;
        client_max_body_size 128m;
        sendfile on;
        sendfile_max_chunk 512k;
        tcp_nopush on;
        keepalive_timeout 60;
        tcp_nodelay on;
        fastcgi_connect_timeout 300;
        fastcgi_send_timeout 300;
        fastcgi_read_timeout 300;
        fastcgi_buffer_size 64k;
        fastcgi_buffers 4 64k;
        fastcgi_busy_buffers_size 128k;
        fastcgi_temp_file_write_size 256k;
        gzip on;
        gzip_min_length  1k;
        gzip_buffers     4 16k;
        gzip_http_version 1.1;
        gzip_comp_level 2;
        gzip_types     text/plain application/javascript application/x-javascript text/javascript text/css application/xml application/xml+rss;
        gzip_vary on;
        gzip_proxied   expired no-cache no-store private auth;
        gzip_disable   "MSIE [1-6]\.";
        #limit_conn_zone $binary_remote_addr zone=perip:10m;
        ##If enable limit_conn_zone,add "limit_conn perip 10;" to server section.
        server_tokens off;
        access_log off;
        upstream php_backend {
            server 127.0.0.1:88;
            server 127.0.0.1:88 backup;
            server 127.0.0.1:88 backup;
        }
server
    {
        listen 80 default_server reuseport;
        #listen [::]:80 default_server ipv6only=on;
        server_name _;
        index index.html index.htm index.php;
        root  /home/wwwroot/default;
        #error_page   404   /404.html;
        # Deny access to PHP files in specific directory
        #location ~ /(wp-content|uploads|wp-includes|images)/.*\.php$ { deny all; }
        include base.conf;
        if ($time_iso8601 ~ "^(\d{4})-(\d{2})-(\d{2})")
        {
            set $year $1;
            set $month $2;
            set $day $3;
        }
        access_log  /home/wwwlogs/nginx/root.$year-$month-$day.log logger;
    }
include vhost/*.conf;
}

```



### conf/vhost/example1.conf


```nginx
server
    {
        listen 443 ssl http2;
        server_name example1.com ;
        index index.html index.htm index.php default.html default.htm default.php;
        root  /home/wwwroot/example1.com;
        ssl_certificate /ssl/example1.com/crt;
        ssl_certificate_key /ssl/example1.com/key;
        ssl_session_timeout 5m;
        ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;
        ssl_ciphers "TLS13-AES-256-GCM-SHA384:TLS13-CHACHA20-POLY1305-SHA256:TLS13-AES-128-GCM-SHA256:TLS13-AES-128-CCM-8-SHA256:TLS13-AES-128-CCM-SHA256:EECDH+CHACHA20:EECDH+CHACHA20-draft:EECDH+AES128:RSA+AES128:EECDH+AES256:RSA+AES256:EECDH+3DES:RSA+3DES:!MD5";
        ssl_session_cache builtin:1000 shared:SSL:10m;
        ssl_dhparam /ssl/dhparam.pem;
        # Client cert verify
        ssl_verify_client on;
        ssl_client_certificate /ssl/ca.crt;
        ssl_crl /ssl/ca.crl;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        include base.conf;
        include proxy-pass-php.conf;
        location ~ {
            autoindex on;
            autoindex_localtime on;
            autoindex_exact_size off;
        }
        include logger.conf;
    }

```



### conf/vhost/example2.conf


```nginx
server
    {
        listen 80;
        server_name example2.com ;
        index index.html index.htm index.php;
        root  /home/wwwroot/example2.com;
        include base.conf;
        include expires.conf;
        include proxy-pass-php.conf;
        include logger.conf;
    }
```



## Apache httpd

我觉得能不要用httpd还是不要用了…觉得不如nginx好用，搭配php7存在内存泄露的情况（没有做对比测试），官方的文档和相关社区并未找到能用的信息。也不排除是我配置错了，但是能把1G RAM+2G SWAP用满还不主动释放只能等系统触发强制回收业务中断才算完，我也是服。这个问题检查了将近一周了，各种trace显示内存使用集中在匿名页上，并且即便是请求量很小，内存使用也不断猛增。

无奈只好使用prefork模式解决，还要确保进程定期一定要能够被回收，否则就会持续溢出，boom。经过一周的观察测试，虽然worker和event模式的**单个进程最大连接数**设置合理的情况下能够避免内存泄露问题，但是偏偏就是很奇葩：频繁报502。经过短期跟踪发现，httpd对于多线程模式下并没有机制确保所有任务执行完后再结束进程，反而是管你还有多少线程在活跃状态只要连接够了直接关，然后一大堆502。晚点有空再研究下代码

为了这一个httpd搞腾了一周。醉了，建议不要轻易下坑

### conf/httpd.conf

vhost配置中不要配置日志，因为我把模块禁用了所以如果还写日志配置了会报错。

我把用不上的模块全部禁用了，有实际需要的可以自行查看编译选项自行恢复。



```apache
#
ServerRoot "/usr/local/apache"
Listen 127.0.0.1:88
LoadModule authn_file_module modules/mod_authn_file.so
LoadModule authn_core_module modules/mod_authn_core.so
LoadModule authz_host_module modules/mod_authz_host.so
LoadModule authz_groupfile_module modules/mod_authz_groupfile.so
LoadModule authz_user_module modules/mod_authz_user.so
LoadModule authz_core_module modules/mod_authz_core.so
LoadModule access_compat_module modules/mod_access_compat.so
LoadModule auth_basic_module modules/mod_auth_basic.so
LoadModule reqtimeout_module modules/mod_reqtimeout.so
LoadModule filter_module modules/mod_filter.so
LoadModule deflate_module modules/mod_deflate.so
LoadModule mime_module modules/mod_mime.so
LoadModule env_module modules/mod_env.so
LoadModule expires_module modules/mod_expires.so
LoadModule headers_module modules/mod_headers.so
LoadModule setenvif_module modules/mod_setenvif.so
LoadModule version_module modules/mod_version.so
LoadModule remoteip_module modules/mod_remoteip.so
LoadModule mpm_prefork_module modules/mod_mpm_prefork.so
LoadModule unixd_module modules/mod_unixd.so
LoadModule status_module modules/mod_status.so
LoadModule autoindex_module modules/mod_autoindex.so
LoadModule dir_module modules/mod_dir.so
LoadModule alias_module modules/mod_alias.so
LoadModule rewrite_module modules/mod_rewrite.so
LoadModule php7_module        modules/libphp7.so
<IfModule unixd_module>
User www
Group www
</IfModule>
ServerAdmin i@xuegaogg.com
ServerName 127.0.0.1:88
<Directory />
    AllowOverride All
    Require all granted
</Directory>
DocumentRoot "/home/wwwroot/default"
<Directory "/home/wwwroot/default">
    Options FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
<IfModule dir_module>
    DirectoryIndex index.html index.htm index.php
</IfModule>
<Files ".ht*">
    Require all denied
</Files>
ErrorLog "/home/wwwlogs/httpd/error.log"
LogLevel crit
<IfModule alias_module>
    ScriptAlias /cgi-bin/ "/usr/local/apache/cgi-bin/"
</IfModule>
<IfModule cgid_module>
</IfModule>
<Directory "/usr/local/apache/cgi-bin">
    AllowOverride All
    Options None
    Require all granted
</Directory>
<IfModule mime_module>
    TypesConfig conf/mime.types
    AddType application/x-compress .Z
    AddType application/x-gzip .gz .tgz
    AddType application/x-httpd-php .php
    AddType application/x-httpd-php-source .phps
</IfModule>
Include conf/extra/mod_remoteip.conf
# Server-pool management (MPM specific)
Include conf/extra/httpd-mpm.conf
# Virtual hosts
Include conf/extra/httpd-vhosts.conf
# Various default settings
Include conf/extra/httpd-default.conf
<IfModule proxy_html_module>
Include conf/extra/proxy-html.conf
</IfModule>
<IfModule ssl_module>
SSLRandomSeed startup builtin
SSLRandomSeed connect builtin
</IfModule>
SetEnvIf X-Forwarded-Proto https HTTPS=on
IncludeOptional conf/vhost/*.conf
```



### conf/extra/httpd-vhost.conf

默认的virtual host



```apache
<VirtualHost *:88>
ServerAdmin i@xuegaogg.com
DocumentRoot "/home/wwwroot/default"
ServerName _
<Directory "/home/wwwroot/default">
    SetOutputFilter DEFLATE
    Options FollowSymLinks
    AllowOverride All
    Order allow,deny
    Allow from all
    DirectoryIndex index.html
</Directory>
</VirtualHost>
```



### conf/extra/httpd-mpm.conf

根据实际情况调整



```apache
<IfModule mpm_prefork_module>
    StartServers             3
    MinSpareServers          5
    MaxSpareServers          10
    MaxRequestWorkers        200
    MaxClients               200
    ServerLimit              200
    MaxConnectionsPerChild   500
</IfModule>
```



## 关于php的内存泄漏问题

该段于2020年4月8日补充

无意中发现上传的图片在处理时把内存全部耗尽了，检查进程发现和之前出的内存泄漏的问题的症状一模一样，怀疑是Imagick导致的，关闭相应的php扩展后还真缓解了很多

~~之前所发现的出502的问题也是由于imagick导致的，关闭该扩展后，调小MaxConnectionsPerChild终于不会出502了。这样一来，终于可以摆脱prefork了，页面的渲染速度会有进一步的改善。~~
~~实际使用还是会有概率出502，不过内存泄漏问题确实得到了改善。~~

由于Imagick实在是不可或缺，gd库对于一些功能无法支持，所以还是得重新打开，开回prefork模式了。


```apache
# 这里可以不用看了
# worker MPM
# StartServers: initial number of server processes to start
# MinSpareThreads: minimum number of worker threads which are kept spare
# MaxSpareThreads: maximum number of worker threads which are kept spare
# ThreadsPerChild: constant number of worker threads in each server process
# MaxRequestWorkers: maximum number of worker threads
# MaxConnectionsPerChild: maximum number of connections a server process serves
#                         before terminating
<IfModule mpm_worker_module>
    StartServers             2
    MinSpareThreads          5
    MaxSpareThreads         10
    ThreadsPerChild         10
    MaxRequestWorkers       20
    MaxConnectionsPerChild  50
    ThreadLimit 20
</IfModule>
```

~~之所以要调这么小，是为了避免并发的线程数太多导致内存开销太高，避免内存持续占用着出现回收延迟。毕竟是小内存的机器，调小线程数有助于爱与和平（笑~~

所以这就告诉我们，不论怎么整，你还得折腾回去。