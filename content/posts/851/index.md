---
aliases:
- /archives/851
categories:
- Linux
date: 2020-02-12 03:58:42+00:00
draft: false
title: PHP环境优化
---

众所周知，php被成为“世界上最美好的语言”，它的性能也实在是令人堪忧。大多数的php应用都是以MVC的方式存在，因此整体上不如前后分离的那么舒服，因此如果需要php达到令人较为舒服的境界，需要多处进行优化。





## 前言

这也是本博客使用的优化策略，旨在尽可能确保内存开销小的情况下提高CPU使用率（因为内存不够用而CPU单核却还是听够用的）。

## 优化策略

### Zend OPcache

注意：该配置可能在conf.d目录中而并不在php.ini中，因此需要特别留意你所修改的文件。



```

[Zend Opcache]
zend_extension="opcache.so"
opcache.memory_consumption=200
opcache.interned_strings_buffer=8
opcache.max_accelerated_files=1000000
opcache.validate_timestamps=1
opcache.revalidate_freq=7200
opcache.fast_shutdown=1
opcache.enable_cli=0

```



opcache.enable_cli=0 表示关闭cli显示，一般调试使用

opcache.memory_consumption=200 最大缓存使用（MB）。服务器只有1G内存，还是省着点用吧

opcache.interned_strings_buffer=8 兴趣字符驻留（MB）。当有重复内容时，会通过指针形式做指向进而节省内存

opcache.max_accelerated_files=1000000 最大可以缓存的文件数量，个人觉得开到最大就行

opcache.validate_timestamps=1 是否自动检测php更新。如果设置为0，**当php文件更新时，需要手动刷缓存，否则可能会因为命中缓存导致无法预料的问题**，此时下方的文件变动检测周期无效；当设置为1时，会自动检测文件是否变化，下方的变动周期有效

opcache.revalidate_freq=7200 自动检测php是否更新的周期（s），考虑到文件变化不是很频繁，因此设置较长，更新后手动刷一下缓存即可。

### 加大数据库查询缓存

综合实际考虑，修改数据并不是非常频繁，主要以读为主，因此可以稍微加大查询缓存。



```

[mysqld]
query_cache_limit = 4M
query_cache_size = 32M

```



只需要修改my.cnf，试其中如上两个值改动即可。第一个query_cache_limit表示单个查询结果的大小限制（小于4M都可以被缓存），第二个query_cache_size表示查询缓存的大小。

### Nginx优化

因为我的VPS是单核机，并且主频高，我不是很了解nginx内部的运行机制，但是大概知道nginx是以事件为驱动的，master负载管理信号，worker是工作进程。线程资源共享，进程不共享，所以进程会占用稍微多点的内存。本来服务器的内存就不大，所以需要尽量缩减内存消耗，但是线程资源共享会存在安全问题，由于对nginx的线程安全的管理方式不是很了解，所以先尽可能在不影响太多性能的情况下吧内存开销压下去，腾出来更多的内存给更有必要的应用使用，如果有问题再调整，同时也留出点时间去了解一下原理

同时，鉴于访问量不大，再加上已经尽可能将进程下调，因此 accept_mutex 可以打开，尤其在还有其他worker的情况下，这个还是要关闭。对于性能不佳的硬件，个人觉得开着没什么必要，多个worker再加上 accept_mutex 关闭的情况下，会有一定的惊群效应，毕竟是单核心，惊群难免引起额外的上下文切换，不如保持打开来确保请求串行处理划算。当然在并发比较高的情况下就别这样玩了

再其次，由于进程被下调，multi_accept觉得需要打开，否则一个worker同时只能接受一个请求，worker对于请求的生命周期的定义还不是很清楚，暂且先打开看一看。至于连接数的话，此处nginx作为入口，连接数应当稍微放大一些，结合实际情况觉得调整到1000就差不多了（其实已经撑死了）。



```

worker_processes 1;

events
    {
        use epoll;
        worker_connections 1000;
        multi_accept on;
        accept_mutex on;
    }

```



### Apache优化

由于此处我只是使用apache的mod_php，因此实际连接数会比nginx要少很多。

注意：mpm模块**同时只能被启用一个**。所以如果发现修改了conf/extra/httpd-mpm.conf并没有作用后，记得检查httpd.conf中是否启用了这个模块，如果没有需要注释掉其他模块切换到这个模块上去。

<p class="has-background has-medium-gray-background-color">
~~StartServers: 启动时的进程数，由于我要节省内存开销，所以直接设置为1~~
</p>
<p class="has-background has-medium-gray-background-color">
~~MinSpareThreads: 最小的备用线程，觉得50够用~~
</p>
<p class="has-background has-medium-gray-background-color">
~~MaxSpareThreads: 最大的备用线程，觉得100足矣。需要特别注意的是，这里的值如果超出下边的 ThreadsPerChild 的话，进程数会增加，最小备用线程数同理。~~
</p>
<p class="has-background has-medium-gray-background-color">
~~ThreadsPerChild: 每个进程的最大线程数。当线程可以容纳全局最大线程之和时，那么就确定了worker只会存在一个。~~
</p>
<p class="has-background has-medium-gray-background-color">
~~MaxRequestWorkers: 所有worker的最大线程之和。我按照600计算，够用了~~
</p>
<p class="has-background has-medium-gray-background-color">
~~MaxConnectionsPerChild: 一个进程在终止之前被允许的接受过的连接数之和。说白了就是，这个进程接够多少个连接后就需要强制终止。不建议开启，有概率出502~~
</p>

在`/etc/sysctl.conf`中新增一行`vm.swappiness = 3`然后执行`sysctl -p`即可。此处我建议将swappiness的值设置在3-5左右比较好，之所以不建议设置为0，是由于Linux会侦测并kill掉内存使用率到100%的进程（表述可能不是很严谨），swappiness设为0的情况下有概率导致程序由于OOM被杀。

~~关于实际情况还会再跟进做一下观察，晚点再更新~~
<p class="has-text-color has-background" style="background-color:#ff0004;color:#eaff00">
  更新内容：
</p>
<p class="has-text-color has-background" style="background-color:#ff0004;color:#eaff00">
  不建议使用httpd。可以看新文章：<a aria-label="链接（在新窗口打开）" href="https://blog.xuegaogg.com/archives/1008.html#Apache_httpd" rel="noreferrer noopener" target="_blank">链接</a>
</p>

### 关闭THP

看这篇文章：<https: 528.html#thp="" archives="" blog.xuegaogg.com=""></https:>