---
aliases:
- /archives/1053
categories:
- Linux
date: 2020-02-25 16:33:31+00:00
draft: false
title: Nginx部署请求头修改并解决WP缓存一致性问题
---

此处的“缓存一致性”我定义为在WordPress套有CDN的情况下，不论管理员是否登录，访问文章页时都不会出现上方的黑色的bar和页面中的编辑按钮等管理用元素，确保CDN缓存下的页面中不存在敏感信息。

## 前言

WordPress为MVC的架构，这是众所周知的，好处是做伪静态后对页面上缓存比较方便，坏处是如果页面发生变动时缓存需要同步更新，否则就会出现延迟。这也就存在了一个比较大的问题是，WP登录管理员后，默认会显示黑色的bar，并在每个文章后显示编辑按钮，显示编辑按钮还好，但是黑色的bar上带有用户名，如果带bar的页面被CDN缓存上，所有的访客都能直接看到这些内容，无疑这是存在安全隐患的。

本站全站也做了伪静态，同时也不熟了CDN用于加速这些伪静态的内容。为了应付上边所提到的问题，博主我是这样思考的：其实逻辑也很简单，只允许访问控制台时带上Cookie这个请求头就好了，其他的请求全部把Cookie剥离掉即可。这样一来，即便管理员登录，访问非控制台页面（好比文章页时）即可自动剥离Cookie，相当于普通用户在浏览，这样CDN缓存时缓存的页面始终是一致的，就能较好得解决上边这个问题。

## 再前言

我在实际部署过程中遇到了点小插曲，差点导致我丢数据，温馨提示，能不要看中文社区的资料就不要看中文社区的东西，此处尤其是CSDN和cnblog等这种公共博客上的内容，最好不要看。这些平台里的文章大多都是不知道N多手的信息，信息传递下去越来越多的东西被删减，很容易掉坑。去看官方的文档不仅会比较完整，而且由于官方文档不断在更新，时效性和可靠性也更强，对于英文文档基本有个四级和专英水平就够了，看不懂的多背背单词或者用翻译就好了。

## 你需要

Nginx

## 步骤

### 为nginx安装模块

为了实现这个操作，需要对入站的请求进行匹配，而nginx自带的**ngx_http_headers_module**模块并不支持这一操作，其只支持响应头添加，因此我们需要手动引入新模块——**headers-more-nginx-module**。这是一个非官方的模块，其GitHub地址在[这里](https://github.com/openresty/headers-more-nginx-module#more_set_input_headers)。

暂且说不来nginx为什么不支持引入动态链接，httpd对这方面支持挺好的，nginx没有做过相关研究，暂且不发表见解，看到网上说可以引入动态编译的链接库即可，编译完结果把我nginx覆盖了….才发现nginx即便是编译模块的动态链接库，nginx主程序也要重新编译…我不知道是我没细看官方文档还是真的只能这样…我还真的有点迷…所以还不如直接重新编译了得了。

开始操作之前建议备份下nginx的目录，避免翻车



```bash
./configure --user=www --group=www --prefix=/usr/local/nginx --with-http_stub_status_module --with-http_ssl_module --with-http_v2_module --with-http_gzip_static_module --with-http_sub_module --with-stream --with-stream_ssl_module --with-openssl=<你openssl的源码的路径> --with-openssl-opt='enable-weak-ssl-ciphers' --with-ld-opt='-ljemalloc' --add-module=<你headers-more-nginx-module模块源码的路径>
```



上边的配置中，prefix可以根据需要改安装位置，启用的模块也可以自己进行修改，需要特别注意的是我安装了Jemalloc，因此要多一个`--with-ld-opt='-ljemalloc'`，没有的可以删掉这一个。

然后make并且make install即可。

安装完成后`nginx -t`检查一下配置文件能不能用，来确定一下你有没有漏编译模块…没问题的话就可以开始下边的内容了

### 配置请求头删除

特别注意：外围一定要配置拦截访问隐藏文件（包括.htaccess等的高危文件）的规则，避免数据泄露

由于我是httpd+nginx，因此有个反向代理存在，配置如下



```nginx
        location /
        {
            try_files $uri @apache;
        }

        location @apache
        {
            internal;
            if ($request_uri !~ (/wp-admin/|/wp-json/))
            {
                more_clear_input_headers 'Cookie';
            }
            proxy_pass http://php_backend;
            proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
            include proxy.conf;
        }

        location ~ [^/]\.php(/|$)
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



注意不要把`if`那一块写进`location /`里去，如果写进去（就是和`try_files`并存的话）会出现问题，博主我出的问题是莫名其妙404。去Google查了查，把try_files和if写在一起出问题的大有人在，具体什么原理就先不说了，现在凌晨了晚点再研究。所以一定要把if写在反向代理这部分，亲测无故障完美运行。

需要特别注意的是，只需要关注`if {}`这一块即可，其他地方不用关注，修改请求头这块真正生效的只有`if {}`这块。

我也亲自测试了将if写在server里去，然后测试时发现more_clear_input_headers不允许在server等级…所以只能写在location内了，暂且还没想到更好的解决办法。关于上边的配置，即便是有if块，但是由于并没有content handler（想知道这是什么继续向下看），因此后续的反代操作将会被继承，感觉应该没什么问题。

目前暂且只发现如下这些目录不能屏蔽cookie，否则会导致问题：

  * /wp-admin 你管理用的，这个肯定不能剥离cookie
  * /wp-json 提交文章用的，亲测如果剥离cookie会无法保存和提交文章
  * /xmlrpc.php 移动端发布文章用的，应该需要cookie（没测试），有需要用app的哥们可以测试一下

## 一些坑

### location相关

起初我想通过location解决，即反向代理时传递Cookie时传递个空就好了，就是要设置很多组location，实测不行。



```nginx
        location /
        {
            try_files $uri @apache;
        }

        location @apache
        {
            internal;
            proxy_pass http://127.0.0.1:88;
            include proxy.conf;
        }

#        location ~ [^/]\.php(/|$)
#        {
#            proxy_pass http://127.0.0.1:88;
#            include proxy.conf;
#        }
```



上边这个配置是军哥一键包里默认的，此处我在测试机上装个lnmpa的环境测一下，不直接操作生产平台免得出事。

当我注释了下边匹配php文件的正则后，所有访问.php的请求直接全部变成了下载。注意！这非常危险，尤其是你站点有配置文件的情况下，很容易导致密码等数据外泄！

查了下文档，找到这么段话

> Checks the existence of files in the specified order and uses the first found file for request processing; the processing is performed in the current context. The path to a file is constructed from the file parameter according to the root and alias directives. It is possible to check directory’s existence by specifying a slash at the end of a name, e.g. “$uri/”. If none of the files were found, an internal redirect to the uri specified in the last parameter is made.
> 
> Module ngx_http_core_module – Nginx.org

这段话的意思是，try_files会去检查访问的URI的文件是否存在，如果存在会使用第一个找到的这个文件响应，否则会重定向到后边的的URI去。这就意味着，在我还没改配置的时候（上边那个配置文件里php那块没有注释的情况下），所有请求会先匹配是否后缀是php，是的话就反代到httpd去，否则走全局的location，所以在我注释掉了上边的内容后就挂了…因为注释掉后nginx比httpd先查找，发现文件存在因此就直接返回了php文件，然后危险由此而来。

对于配置了htaccess的情况下，由于不存在这个文件，所以nginx会把请求交由httpd处理，所以这样一来URL重写的部分就能正常使用了。

所以，我如果想直接拿location分uri做反代的情况下去剥离/保留Cookie，URI部分需要尽可能让它满足足够长的匹配，否则按照nginx的匹配逻辑，可能会命中最后全局的.php规则。所以我选择使用if去判断。

上边的情况，如果想保障安全，也可以使用全局反向代理，即把`proxy_pass`相关的直接写进`location /`即可，不要使用try_files，这样就好了，这样一来下面那个.php的就可以去掉了。但是这样的话似乎nginx就好像没有它存在的意义了…

### if和try_file的故事

上边我说到了，try_files如果和if一块使用，会出问题（好比404）。刚刚我们对try_files的逻辑进行了梳理，那么理论上来说是不会有问题的，但是实际上就是有问题了，所以看文档把。

好了，我看到官方有一篇文章题目叫做**If Is Evil**，我觉得我现在也是不幸的了，自从看了中文社区后。这又警告我们，能不要看中文社区就不要看中文社区….内容残缺太多…

> Directive if has problems when used in location context, in some cases it doesn’t do what you expect but something completely different instead. In some cases it even segfaults. It’s generally a good idea to avoid it if possible.
> 
> Introduction – If Is Evil

这段话大意是，如果你把if用在location里，他可能会出一些问题，问题不仅仅是和你的意愿完全相反，甚至可能直接段错误然后你没了…最好的办法就是，别用。

文档非常肯定得说只有下边两种是安全的，其他的都不能保证绝对可靠：

  * return ...;
  * rewrite ... last;

至于解决的办法，也不是没有，官方建议最好把if写在server块里去，这样就不会出问题了。在文档中也列举了这几种作死行为：


```nginx
# only second header will be present in response
# not really bug, just how it works

location /only-one-if {
    set $true 1;

    if ($true) {
        add_header X-First 1;
    }

    if ($true) {
        add_header X-Second 2;
    }

    return 204;
}
```



上边这个配置会使得只有第二个Header在响应头中添加成功，并且强调这不是bug，只是由于其工作机制导致了会出这样的问题。



```nginx
# request will be sent to backend without uri changed
# to '/' due to if

location /proxy-pass-uri {
    proxy_pass http://127.0.0.1:8080/;

    set $true 1;

    if ($true) {
        # nothing
    }
}
```



上边这个配置将会导致URI不被修改为/直接发到后端去。



```nginx
# try_files wont work due to if

location /if-try-files {
     try_files  /file  @fallback;

     set $true 1;

     if ($true) {
         # nothing
     }
}
```



上边这个配置会导致try_files不工作。所以这就是为什么直接把if写进`location /`去频繁出404的原因了，还好没动php那块….不然可能会泄露配置数据…



```nginx
# nginx will SIGSEGV

location /crash {

    set $true 1;

    if ($true) {
        # fastcgi_pass here
        fastcgi_pass  127.0.0.1:9000;
    }

    if ($true) {
        # no handler here
    }
}
```



上边这个会直接出段错误。



```nginx
# alias with captures isn't correcly inherited into implicit nested
# location created by if

location ~* ^/if-and-alias/(?<file>.*) {
    alias /tmp/$file;

    set $true 1;

    if ($true) {
        # nothing
    }
}
```



上边这个配置会导致带有捕获的alias（应该是指$file吧）无法正确继承。

## if的工作原理
> In short, Nginx’s “if” block effectively creates a (nested) location block and once the “if” condition matches, only the content handler of the inner location block (i.e., the “if” block) will be executed.
> 
> How nginx “location if” works

上边这段话的意思是，if的实现是嵌套的location声明实现的，一旦匹配到，只有内部的location块（即if里的）的content handler会被执行。

### 示例一


```nginx
  location /proxy {
      set $a 32;
      if ($a = 32) {
          set $a 56;
      }
      set $a 76;
      proxy_pass http://127.0.0.1:$server_port/$a;
  }

  location ~ /(\d+) {
      echo $1;
  }
```


> Calling /proxy gives 76 because it works in the following steps:
> 
> 1. Nginx runs all the rewrite phase directives in the order that they’re in the config file, i.e., set $a 32;<br/> if ($a = 32) {<br/> set $a 56;<br/> }<br/> set $a 76; and $a gets the final value of 76.
> 1. Nginx traps into the “if” inner block because its condition $a = 32 was met in step 1.
> 1. The inner block does not has any content handler, ngx_proxy inherits the content handler (that of ngx_proxy) in the outer scope (see src/http/modules/ngx_http_proxy_module.c:2025).
> 1. Also the config specified by proxy_pass also gets inherited by the inner “if” block (see src/http/modules/ngx_http_proxy_module.c:2015)
> 1. Request terminates (and the control flow never goes outside of the “if” block).
> 
> That is, the proxy_pass directive in the outer scope will never run in this example. It is “if” inner block that actually serves you.
> 
> How nginx “location if” works

在上边这个配置中，匹配到/proxy时会执行这些步骤：

  1. 按照顺序重写配置，所以a最后是76
  2. 陷入内嵌的if块中，因为在最开始它能匹配到$a=32
  3. 这个内嵌的块中没有content handler，ngx_proxy将会继承外部的内容成为为content handler
  4. proxy_pass被内嵌的if块继承
  5. 请求终止

按照这个逻辑，这个过程中的proxy_pass压根就没有在外部的location中执行，而是在内嵌的if中完成了继承和处理。

### 示例二


```nginx
  location /proxy {
      set $a 32;
      if ($a = 32) {
          set $a 56;
          echo "a = $a";
      }
      set $a 76;
      proxy_pass http://127.0.0.1:$server_port/$a;
  }

  location ~ /(\d+) {
      echo $1;
  }
```



在上边这个location /proxy中，执行顺序是这样的：

  1. 按照顺序重写配置
  2. 陷入（$a=32）
  3. 由于内嵌中存在了content handler（即echo），所以客户端可以看到内容为`a = 76`
  4. 请求终止

上边这个过程可以看到，nginx对于请求的处理会终止到content handler，我把这个词理解为内容句柄，内容句柄只会执行一次，相当于return，然后这个业务流将会结束。由于按照配置重写后，a最终是等于76，所以客户端看到的a为76，但是由于在if处是匹配的，所以会正常陷入if。

### 示例三


```nginx
 location /proxy {
      set $a 32;
      if ($a = 32) {
          set $a 56;
          break;

          echo "a = $a";
      }
      set $a 76;
      proxy_pass http://127.0.0.1:$server_port/$a;
  }

  location ~ /(\d+) {
      echo $1;
  }
```



在上边这个location /proxy中，执行顺序是这样的：

  1. 按照顺序重写配置，由于if内有个break，所以剩下的ngx_rewrite操作将会停止，因此a等于56
  2. 陷入if
  3. 存在content handler，执行
  4. 终止

### 示例四


```nginx
  location /proxy {
      set $a 32;
      if ($a = 32) {
          return 404;
      }
      set $a 76;
      proxy_pass http://127.0.0.1:$server_port/$a;
      more_set_headers "X-Foo: $a";
  }

  location ~ /(\d+) {
      echo $1;
  }
```



在上边这个location /proxy中，由于if会被陷入执行，并且return已经相当于content handler，因此proxy_pass将不会被执行，其下边的more_set_headers反而会被继承到if块中去，最后的效果是这样的：



```bash
  $ curl localhost/proxy
  HTTP/1.1 404 Not Found
  Server: nginx/0.8.54 (without pool)
  Date: Mon, 14 Feb 2011 05:24:00 GMT
  Content-Type: text/html
  Content-Length: 184
  Connection: keep-alive
  X-Foo: 32
```



是不是觉得眼前一亮…..?

## 参考资料

* http://nginx.org/en/docs/http/ngx_http_core_module.html#location
* http://nginx.org/en/docs/http/ngx_http_core_module.html#try_files
* https://www.nginx.com/resources/wiki/start/topics/depth/ifisevil/
* https://agentzh.blogspot.com/2011/03/how-nginx-location-if-works.html
