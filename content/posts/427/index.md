---
aliases:
- /archives/427
categories:
- Linux
date: 2019-09-28 08:44:35+00:00
draft: false
title: nginx处理url路由和反向代理
---

此文讲述nginx处理url路由和反向代理，同时还有websocket反向代理



反向代理：


```nginx
location /api
{
    proxy_pass http://192.168.21.241:8080/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $http_host;

    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forward-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forward-Proto http;
    proxy_set_header X-Nginx-Proxy true;
    proxy_redirect off;
}

```


URL路由：


```nginx
location /api
{
    proxy_pass http://192.168.21.241:8080/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $http_host;

    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forward-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forward-Proto http;
    proxy_set_header X-Nginx-Proxy true;
    proxy_redirect off;
}

location / {
}
```


路由规则逐个向下匹配

该反向代理规则可以直接用，已经支持websocket