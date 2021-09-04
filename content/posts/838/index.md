---
aliases:
- /archives/838
categories:
- Linux
date: 2020-02-11 02:31:25+00:00
draft: false
title: 为PHP安装Imagick
---





## 前言

该图形库需要分为两部分安装，一部分是操作系统的二进制文件和动态链接库（ImageMagick），一部分是php的扩展（imagick），这两部分需要分别使用不同的源码进行编译和安装。

建议安装版本都为最新的稳定版（Stable）

## 安装系统二进制文件和动态链接库

本部分即安装ImageMagick

找到官网： <https: imagemagick.org="" install-source.php="" script=""> ，从中我们可以得到源码包的下载链接：<https: download="" imagemagick.org="" imagemagick.tar.gz="">

下载解压的方式就不说了

安装使用参数：./configure –prefix=/usr/local/imagemagick 指定路径，等下便于php扩展去查找

然后make并install即可

## 安装PHP扩展

源码包我们可以在这里找到： <https: imagick="" package="" pecl.php.net=""> 

下载解压方式就不说了

解压后进入源码根目录，执行：/usr/local/php/bin/phpize 进而生成configure

然后执行 ./configure –with-php-config=/usr/local/php/bin/php-config –with-imagick=/usr/local/imagemagick 

然后make并install

最后我们在php.ini中新增一行 extension = imagick.so 即可

## 额外问题

我的apache在启动后php加载magick时就直接报段错误然后退出了，导致网页访问全部成了502网关错误。查找日志错误如下：


```
PHP Warning:  PHP Startup: Unable to load dynamic library 'imagick.so' (tried: /usr/local/php/lib/php/extensions/no-debug-zts-20180731/imagick.so (/usr/lib64/libfontconfig.so.1: undefined symbol: FT_Done_MM_Var), /usr/local/php/lib/php/extensions/no-debug-zts-20180731/imagick.so.so (/usr/local/php/lib/php/extensions/
no-debug-zts-20180731/imagick.so.so: cannot open shared object file: No such file or directory)) in Unknown on line 0 
```


查找文档发现是因为Linux版本较新导致的，具体问题的原因并没有做出详细说明，只是提出删除 _libfreetype.so.6_ 就好了，亲测可行（参考资料： [https://kb.tecplot.com/2019/09/11/undefined-symbol-ft_done_mm_var/][1] ）

**注意**

在我重启或者执行ldconfig后，发现问题重新又出现了。

ld的主要作用是管理动态链接库，那么当我删除了libfreetype.so.6后就可以了，意味着程序再查找动态链接时可能是使用的这个文件，当删除后即可正常使用，那么可能是同时存在的两个版本导致冲突了。

查看了一下/etc/ld.so.conf发现还真的是冲突了，其实也就是顺序问题而已，应该让系统自带的freetype 库最先被找到，因此调整一下顺序并重新执行ldconfig 即可。

参考文档： <http: ldconfig.8.html="" linux="" man-pages="" man7.org="" man8="">

 [1]: https://kb.tecplot.com/2019/09/11/undefined-symbol-ft_done_mm_var/</http:></https:></https:></https:>