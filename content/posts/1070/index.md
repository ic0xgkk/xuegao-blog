---
aliases:
- /archives/1070
categories:
- Linux
date: 2020-02-26 07:37:11+00:00
draft: false
title: WordPress全站优化指南（续）
---

上次的指南对CDN提及不多，本次文章侧重从CDN角度进行优化，并且辅以一些安全策略。

## CDN选择

由于我常用的CDN服务商只有三家，分别是阿里云、又拍云和Cloudflare。本篇文章就对比这三个服务商说好了，还有其他不错的服务商推荐的可以私我

我不会一上来就说这个CDN服务商不行怎么怎么滴，各个服务商产品设计面向的需求都不一样，因此找到最需要的就好了，不满足需求的pass就好了

### 阿里云CDN和全站加速

作为一个阿里云的老用户，说实话，我并不非常推荐使用阿里云CDN和全站加速服务。阿里云的CDN和全站加速在国内的优化还不错，节点很多，并且回源是就近回源，如果你源站的服务器在国内，那么选择阿里云的普通CDN即可，或许会是你的最佳选择。但是，如果你的源站在海外，并且静态元素没有在国内部署镜像，那么请不要选择阿里云，尽管阿里云的全站加速能够优化路由，但是这个是分动静态的，只有动态资源才能通过最佳路由回源，静态资源仍然是就近回源，延迟会很高，并且动态资源无法被边缘缓存。这逻辑简直就是个bug

并且，阿里云的CDN经常出现掉缓存的情况，我连续两次遇到这种情况：打开页面，响应头里MISS，刷新页面，还MISS。这元素我明明加了缓存的。这情况是抽风时的情况，并不是常态，但是本来静态回源不走最佳路由，缓存一掉基本网站就打不开了...

### Cloudflare

简称CF。这家的CDN是我见过的最牛逼的。虽然Free版限制挺多的，但是基础用户够用了，赠送的3个Page Rules也很好用，可以根据多种条件设置缓存或响应，实实在在的软件定义，灵活性非常强，普通玩家上手可能需要一段时间，但是玩熟了会发现这东西简直tm是神器。

再一点是，CF的节点主要在海外，国内的我没测试过节点有没有，不过参考AWS的，以及再看CF的非免费版本的套餐中有个启用中国节点选项，我就感觉国内应该是没有节点的。CF反代Websocket也可以免费，所以被国内很多fq的玩坏了...然而阿里和又拍的WS反代流量价钱贵的吓死人，想了解的可以去查查看

如果你的源站在海外，并且面向的用户群体也在海外，或者你觉得你的用户群体能忍受国内访问海外节点的质量的情况下，或者你的预算不足的情况下，选择CF不会错。很香

### 又拍云

这也是我目前再用的CDN服务商，国内访问质量没有阿里云的好，不论是命中缓存和最佳路由回源的。最佳路由回源的延迟比阿里云的动态回源高接近一倍（200ms~367ms），边缘缓存分发延迟也是将近一倍（24ms~50ms），从延迟上说确实不如阿里。但是，我的源站在海外并且国内没有静态资源的镜像，所以这家CDN反而成了最合适的选择。

又拍云的CDN在设置全站加速的情况下，回源全局走最优路由，所以即便是没有命中缓存回源了，延迟也不会像阿里云那样那么恐怖。而且又拍云的动态资源也可以缓存，这在阿里云里是完全不可能的。而且个人觉得，又拍云的缓存规则设置上，比阿里云的好用，并且SSL证书可以使用Let’s Encrypt的免费证书，自动续签，不像阿里云一样还非要让你用云盾里的证书，虽然也免费，每年都还要去续签一次，没留意续签免费不免费，反正用完了就得掏钱。同时，又拍云的CDN支持webp图，也支持像CF那样的边缘规则（虽然是个入门版吧），灵活性会高很多。

于是我选择迁移所有的站点到了又拍云。

## 安全策略

建议不要使用默认的nginx配置套httpd，存在安全隐患。nginx配置的动静态分离建议只允许js、css、png等纯静态资源直接访问，并且要确保这些文件没可能带上敏感信息，其他的建议一律转发到httpd处理，WP有防火墙插件，配合使用才能保障安全。



```nginx
        location ~ /.well-known {
            allow all;
            try_files $uri =404;
        }

        location ~ /\.
        {
            deny all;
        }

        location ~ .*\.(mp3|wma|flv|mp4||ico|swf|bmp|gif|jpeg|jpg|png|svg|tiff|woff2)$
        {
            expires      30d;
            try_files $uri =404;
        }

        location ~ .*\.(js|css)?$
        {
            expires      3d;
            try_files $uri =404;
        }

        location /
        {
            if ($request_uri !~ (/wp-admin/|/wp-json/))
            {
                more_clear_input_headers 'Cookie';
            }
            proxy_pass http://php_backend;
            proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
            include proxy.conf;
        }
```



需要特别注意的是，`$uri`不等同于`$request_uri`。 `$request_uri` 是原始的URI，包含了一些参数，并且并没有被解码，而`$uri`遵循如下三点：

  * Removal of the `?` and query string 移除了?和查询字符串
  * Consecutive `/` characters are replace by a single `/` 替换了重复的/
  * URL encoded characters are decoded URL被重新编码过

## 回源安全

想了个办法，CDN回源的时候带上一个头，源站去验证这个头，如果请求中存在，则正常响应，如果不存在，则跳转到CDN域名。

也就一个.htaccess的重写规则

```xml
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteBase /
RewriteCond %{HTTP:<自定义的HTTP头>} !<验证字段>
RewriteRule ^(.*)$ https://<跳转到的目标域名>/$1 [L,R=301]
</IfModule>
```

自定义的HTTP头不建议使用任何符号，可能会有一些问题。
