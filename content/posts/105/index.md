---
aliases:
- /archives/105
categories:
- Linux
date: 2019-02-16 10:46:27+00:00
draft: false
title: libgcc和protobuf编译过程中的问题
---



# libgcc

这阵子在做IceBox的系统时意外遇到一个bug，工具链在交叉编译GCC 5.4.0时报错如下问题


```bash
In file included from ../.././libgcc/unwind-dw2.c:401:0:
./md-unwind-support.h: In function 'x86_64_fallback_frame_state':
./md-unwind-support.h:65:47: error: dereferencing pointer to incomplete type 'struct ucontext'
       sc = (struct sigcontext *) (void *) &uc_->uc_mcontext;
                                               ^~
../.././libgcc/shared-object.mk:14: recipe for target 'unwind-dw2.o' failed
make[6]: *** [unwind-dw2.o] Error 1
make[6]: Leaving directory '/home/xuegao/data/openwrt/18061/build_dir/target-x86_64_glibc/gcc-5.4.0/x86_64-openwrt-linux-gnu/libgcc'
```


百度查了查没有找到什么有用的东西，倒是Google上找到了glibc的wiki上有人开过issue应该，官方在wiki上留下了解决方案

> Removal of ‘struct ucontext’ The ucontext_t type has a tag struct ucontext. As with previous such issues for siginfo_t and stack_t, this tag is not permitted by POSIX (is not in a reserved namespace), and so namespace conformance means breaking C++ name mangling for this type. In this case, the type does need to have some tag rather than just a typedef name, because it includes a pointer to itself. We use a struct ucontext_t as the new tag, so the type is mangled as ucontext_t (the POSIX *_t reservation applies in all namespaces, not just the namespace of ordinary identifiers). Another reserved name such as struct __ucontext could of course be used. Packagers need to watch out for cases where application and library code uses struct ucontext and change such references to the POSIX reserved ucontext_t. 

可见链接[^1]

[^1]: https://sourceware.org/glibc/wiki/Release/2.26#Removal_of_.27struct_ucontext.27

具体的解决办法如下：

进入**编译目录/build_dir/target-x86_64-glibc/gcc-5.4.0/x86_64-openwrt-linux-gnu/libgcc**，找到**md-unwind-support.h**这个文件，按照如上编译的报错信息在65行附近找到 `struct ucontext XXX;` 这句，按照官方的说法，将其指向POSIX保留的ucontext_t即可，即将**struct ucontext**改成**ucontext_t**即可，同样下面第141行也存在这个错误的声明，改一下就好了 

# protobuf

编译ocserv(openConnect服务端)时需要该依赖，出错误，Google了一下

> Google Protocol Buffer( 简称 Protobuf) 是 Google 公司内部的混合语言数据标准，目前已经正在使用的有超过 48,162 种报文格式定义和超过 12,183 个 .proto 文件。他们用于 RPC 系统和持续数据存储系统。
> 
> Protocol Buffers 是一种轻便高效的结构化数据存储格式，可以用于结构化数据串行化，或者说序列化。它很适合做数据存储或 RPC 数据交换格式。可用于通讯协议、数据存储等领域的语言无关、平台无关、可扩展的序列化结构数据格式。目前提供了 C++、Java、Python 三种语言的 API


整理这个文章有点晚了，忘了是什么样的错误了，报错是在下面的代码附近：


```c
#if __cplusplus >= 201103L
#include <cmath>
#define ISINF isinf
#define ISNAN isnan
#else
#include <cmath>
#define ISINF isinf
#define ISNAN isnan
#endif
```


上述代码是修正后的，原本代码中指定了isnan是std这个命名空间中的变量，然后编译提示std中没有这个东西，网上没有查到相关解决办法，参照另外一部分预编译的代码，将**math.h**改成后，再改成上边那样就行了

该bug在文件**mathlimits.h**中，问题代码在232行左右

 [1]: https://sourceware.org/glibc/wiki/Release/2.26#Removal_of_.27struct_ucontext.27</https:>