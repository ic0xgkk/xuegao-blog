---
aliases:
- /archives/93
categories:
- Linux
date: 2019-01-15 10:27:55+00:00
draft: false
title: 利用Pcap_dnsproxy搭建牛逼的DNS服务
---

为了方便开发使用，近期在给实验室布网，用一些别人集成好的方案，发现效果也太差了，或者是各种不稳定，果然还是自己做的最好。自己动手，丰衣足食。

很早以前就留意到了Pcap_dnsproxy这个东西，只不过最开始用时可能还有些bug，以至于性能和稳定性都不算很好。直到今天，在因为DNS污染问题实在是搞得我已经烦了甚至想自己开发DNS服务框架的时候，又再去试了试Pcap_dnsproxy，发现现在的功能已经比之前完美了很多，而且，也稳定了很多，最重要的，文档也比之前全了很多，再三考虑后，上车试了试，没翻车而且很爽，写篇文章纪念下好了。

官方的介绍：

```text
Pcap_DNSProxy is a tool based on WinPcap/LibPcap which can filter DNS poisoning. It provides a convenient and powerful way to change Hosts via regular expressions, DNSCurve/DNSCrypt protocol support, as well as parallel request and TCP request support. Multiple servers parallel request can improve the reliability of domain name resolution in a bad network:

  * IPv4/IPv6 dual stack support, custom the multiple listening addresses, port and protocols.
  * Provides DNS service for other devices with custom limiting requests.
  * CNAME Hosts and Local DNS servers resolution support, which can improve DNS service quality.
  * Main/Alternate servers support and servers parallel requests with multiple times support, which can improve DNS service reliability.
  * Built-in DNS cache, also EDNS tag, DNSSEC and DNSCurve/DNSCrypt protocol support.
  * SOCKS version 4/4a/5 and HTTP CONNECT tunnel protocol including TLS/SSL handshake support.
  * Lots of options and powerful error reporting.
  * ASCII, UTF-8(/BOM), UTF-16(LE/BE) and UTF-32(LE/BE) encoding including Unicode standard requirements support.
```

大意是介绍了这个工具很牛逼（确实牛逼），支持正则表达式、DNSCurve/DNSCrypt协议和TCP，而且支持多服务器并行请求，内置的SOCK支持也实在是很好用，在开启了缓存之后多少对于局域网内有一定的DNS加速作用。

项目主页目前已经被删除了，可能要多找找才找得到


# 相关项目

首先在此之前，需要知道的几个项目：

  * china_ip_list  
    项目地址：[^1]  
    个人比较喜欢这个，路由表相对比较全一些 
  * dnsmasq-china-list  
    项目地址[^2]
    收录了大多数使用国内服务器（包含CDN）的域名，其中accelerated-domains.china.conf文件包含了所有NS服务器在大陆的域名和使用国内DNS解析出的IP为大陆的域名，防止解析到国外去 

[^1]: https://github.com/LisonFan/china_ip_list
[^2]: https://github.com/felixonmars/dnsmasq-china-list

# 操作

此处，我使用的Windows Server 2012 R2 x64作为DNS服务器的操作系统，至于为什么不用Linux，是因为cmake编译一直报错，懒得解决了，省点功夫写代码吧（截至到更新为止，已经换成Linux了，Windows Server用起来感觉很不舒服）

  1. 下载安装Pcap_dnsproxy  
    在Releases中找到发布版本，建议不想折腾还是老老实实不要用预发布版本了，此处我使用的0.4.9.9版本。

其中根目录下的Config.ini为配置文件，Routing为路由表，WhiteList为白名单，Hosts中可以配置请求转发

  1. 此处，我将china_ip_list的内容全部复制到Routing.txt中，同时将上述的dnsmasq-china-list中的accelerated-domains.china.conf列表除去学校域名后（因为学校某些域名使用学校DNS解析到内网快很多）除去转发的IP后，粘贴进WhiteList.txt，格式如下： `[Local Hosts] ......... Server=/baidu.com/ Server=/taobao.com/ .........` 我删除了Server=/zhbit.com/这一条，因为默认使用了114DNS，接下来我要把学校域名的DNS请求全部转发到学校的DNS去，在Hosts.txt中添加下面 一条： `[Local Hosts] Server=/:.*\bzhbit\.com:/10.0.10.10#53` 其中使用了正则表达式，测试正则表达式可以到一些在线网站上测试。上述规则中的两个冒号间为正则表达式，把所有学 校域名的解析请求转发到了10.0.10.10的53端口，实现了定向解析。 
  2. 配置文件如下， 官方提供了足够详尽的文档，具体可以去项目页面查看 


```ini
[Base]
Version = 0.45
File Refresh Time = 15
Large Buffer Size = 4096
Additional Path = 
Hosts File Name = Hosts.ini|Hosts.conf|Hosts.txt|WhiteList.txt
IPFilter File Name = IPFilter.ini|IPFilter.conf|IPFilter.dat|Routing.txt|chnroute.txt

[Log]
Print Log Level = 3
Log Maximum Size = 8MB

[Listen]
Process Unique = 1
Pcap Capture = 0
Pcap Devices Blacklist = AnyConnect|Host|Hyper|ISATAP|IKE|L2TP|Only|Oracle|PPTP|Pseudo|Teredo|Tunnel|Virtual|VMNet|VMware|VPN|any|gif|lo|nflog|nfqueue|stf|tunl|utun
Pcap Reading Timeout = 250
Listen Protocol = IPv4 + UDP
Listen Port = 53
Operation Mode = Private
IPFilter Type = Deny
IPFilter Level &lt; 0
Accept Type = 

[DNS]
Outgoing Protocol = IPv4 + UDP
Direct Request = IPv4
Cache Type = Timer + Queue
Cache Parameter = 10240
Cache Single IPv4 Address Prefix = 0
Cache Single IPv6 Address Prefix = 0
Default TTL = 3600

[Local DNS]
Local Protocol = IPv4 + UDP
Local Hosts = 1
Local Routing = 1
Local Force Request = 1

[Addresses]
IPv4 Listen Address = 0.0.0.0:53
IPv4 EDNS Client Subnet Address = 
IPv4 Main DNS Address = 1.1.1.1:53
IPv4 Alternate DNS Address = 
IPv4 Local Main DNS Address = 114.114.114.114:53|10.0.10.10:53
IPv4 Local Alternate DNS Address = 223.6.6.6:53
IPv6 Listen Address = 
IPv6 EDNS Client Subnet Address = 
IPv6 Main DNS Address = [2001:4860:4860::8844]:53
IPv6 Alternate DNS Address = [2606:4700:4700::1001]:53|[2620:FE::FE]:53|[2620:0:CCD::2]:5353
IPv6 Local Main DNS Address = [240C::6644]:53
IPv6 Local Alternate DNS Address = [240C::6666]:53

[Values]
Thread Pool Base Number = 3
Thread Pool Maximum Number = 512
Thread Pool Reset Time = 25
Queue Limits Reset Time = 0
EDNS Payload Size = 1220
IPv4 Packet TTL = 72 - 255
IPv4 Main DNS TTL = 0
IPv4 Alternate DNS TTL = 0
IPv6 Packet Hop Limits = 72 - 255
IPv6 Main DNS Hop Limits = 0
IPv6 Alternate DNS Hop Limits = 0
Hop Limits Fluctuation = 2
Reliable Once Socket Timeout = 3000
Reliable Serial Socket Timeout = 1500
Unreliable Once Socket Timeout = 550
Unreliable Serial Socket Timeout = 1000
TCP Fast Open = 0
Receive Waiting = 0
ICMP Test = 900
Domain Test = 900
Alternate Times = 10
Alternate Time Range = 60
Alternate Reset Time = 300
Multiple Request Times = 2

[Switches]
Domain Case Conversion = 1
Compression Pointer Mutation = 0
EDNS Label = 0
EDNS Client Subnet Relay = 0
DNSSEC Request = 0
DNSSEC Force Record = 0
Alternate Multiple Request = 0
IPv4 Do Not Fragment = 0
TCP Data Filter = 1
DNS Data Filter = 1
Blacklist Filter = 1
Resource Record Set TTL Filter = 0

[Data]
ICMP ID = 
ICMP Sequence = 
ICMP PaddingData = 
Domain Test Protocol = TCP + UDP
Domain Test ID = 
Domain Test Data = 
Local Machine Server Name = dns.ihc.servers.xuegaogg.com

[Proxy]
SOCKS Proxy = 0
SOCKS Version = 5
SOCKS Protocol = IPv4 + TCP
SOCKS UDP No Handshake = 1
SOCKS Proxy Only = 0
SOCKS IPv4 Address = 127.0.0.1:1080
SOCKS IPv6 Address = [::1]:1080
SOCKS Target Server = 8.8.4.4:53
SOCKS Username = 
SOCKS Password = 
HTTP CONNECT Proxy = 0
HTTP CONNECT Protocol = IPv4
HTTP CONNECT Proxy Only = 0
HTTP CONNECT IPv4 Address = 127.0.0.1:1080
HTTP CONNECT IPv6 Address = [::1]:1080
HTTP CONNECT Target Server = 8.8.4.4:53
HTTP CONNECT TLS Handshake = 0
HTTP CONNECT TLS Version = 0
HTTP CONNECT TLS Validation = 1
HTTP CONNECT TLS Server Name Indication = 
HTTP CONNECT TLS ALPN = 0
HTTP CONNECT Version = 1.1
HTTP CONNECT Header Field = User-Agent: Pcap_DNSProxy/0.5.0.0
HTTP CONNECT Header Field = Accept: */*
HTTP CONNECT Header Field = Cache-Control: no-cache
HTTP CONNECT Header Field = Pragma: no-cache
HTTP CONNECT Proxy Authorization = 

[DNSCurve]
DNSCurve = 0
DNSCurve Protocol = IPv4 + UDP
DNSCurve Payload Size = 512
DNSCurve Reliable Socket Timeout = 3000
DNSCurve Unreliable Socket Timeout = 2000
DNSCurve Encryption = 1
DNSCurve Encryption Only = 0
DNSCurve Client Ephemeral Key = 0
DNSCurve Key Recheck Time = 1800

[DNSCurve Database]
DNSCurve Database Name = dnscrypt-resolvers.csv
DNSCurve Database IPv4 Main DNS = cisco
DNSCurve Database IPv4 Alternate DNS = 
DNSCurve Database IPv6 Main DNS = cisco-ipv6
DNSCurve Database IPv6 Alternate DNS = 

[DNSCurve Addresses]
DNSCurve IPv4 Main DNS Address = 208.67.220.220:443
DNSCurve IPv4 Alternate DNS Address = 
DNSCurve IPv6 Main DNS Address = [2620:0:CCC::2]:443
DNSCurve IPv6 Alternate DNS Address = 
DNSCurve IPv4 Main Provider Name = 2.dnscrypt-cert.opendns.com
DNSCurve IPv4 Alternate Provider Name = 
DNSCurve IPv6 Main Provider Name = 2.dnscrypt-cert.opendns.com
DNSCurve IPv6 Alternate Provider Name = 

[DNSCurve Keys]
DNSCurve Client Public Key = 
DNSCurve Client Secret Key = 
DNSCurve IPv4 Main DNS Public Key = B735:1140:206F:225D:3E2B:D822:D7FD:691E:A1C3:3CC8:D666:8D0C:BE04:BFAB:CA43:FB79
DNSCurve IPv4 Alternate DNS Public Key = 
DNSCurve IPv6 Main DNS Public Key = B735:1140:206F:225D:3E2B:D822:D7FD:691E:A1C3:3CC8:D666:8D0C:BE04:BFAB:CA43:FB79
DNSCurve IPv6 Alternate DNS Public Key = 
DNSCurve IPv4 Main DNS Fingerprint = 
DNSCurve IPv4 Alternate DNS Fingerprint = 
DNSCurve IPv6 Main DNS Fingerprint = 
DNSCurve IPv6 Alternate DNS Fingerprint = 

[DNSCurve Magic Number]
DNSCurve IPv4 Main Receive Magic Number = 
DNSCurve IPv4 Alternate Receive Magic Number = 
DNSCurve IPv6 Main Receive Magic Number = 
DNSCurve IPv6 Alternate Receive Magic Number = 
DNSCurve IPv4 Main DNS Magic Number = 
DNSCurve IPv4 Alternate DNS Magic Number = 
DNSCurve IPv6 Main DNS Magic Number = 
DNSCurve IPv6 Alternate DNS Magic Number = 
```


# 效果

可以看到：


```powershell
PS C:\Users\IceCream> nslookup baidu.com 192.168.12.3
服务器:  dns.ihc.servers.xuegaogg.com
Address:  192.168.12.3

非权威应答:
名称:    baidu.com
Addresses:  123.125.115.110
          220.181.57.216

PS C:\Users\IceCream> nslookup e.zhbit.com 192.168.12.3
服务器:  dns.ihc.servers.xuegaogg.com
Address:  192.168.12.3

非权威应答:
名称:    e.Zhbit.cOm
Address:  10.0.12.171

PS C:\Users\IceCream> nslookup google.com 192.168.12.3
服务器:  dns.ihc.servers.xuegaogg.com
Address:  192.168.12.3

非权威应答:
名称:    GOoGLe.cOM
Addresses:  2404:6800:4005:809::200e
          172.217.31.238
```


# 调参建议

  * 在使用TCP查询DNS并且运行系统为Linux时，强烈建议将TCP的连接回收时间减短至5秒左右，CentOS7默认对TCP的超时连接回收时间太长了，此处由于我们主要是用于DNS TCP查询，查询请求过高时太长的TCP回收时间会导致端口浪费严重甚至直接端口不够用（亲身经历，连接回收时间为默认，导致运行一个多小时后netstat查看端口占用一大堆TIMEOUT，并且此时查询速度已经非常慢）。至于为什么设置在5秒，是因为即便是走SOCK查询，5秒的回收周期也是足够了的，直连TCP查询5秒了还没回来的话，估计你也觉得卡的难受干脆把查询请求也扔进SOCK了。具体修改内核参数的方法自行Google
  * 建议缓存队列不要设置太长。我没有看代码，不知道作者有没有对大量的缓存的查询做优化，如果局域网内设备实在是太多而且查询请求量非常大，正巧你缓存队列又设置得非常长，设备性能又跟不上，可能查询缓存的时间比直接请求都慢……
  * 建议关闭Pcap捕获，实在不行建议使用iptables对所有非该DNS服务器的目标端口为53的请求进行重定向
  * 局域网内使用建议使用Private模式，以确保只有RFC1918中规定的私网地址能够使用，避免恶意请求
  * TTL缓存时间不要加太长，见过有人加一周的你这不是逗我吗……建议跟随网内客户端数量和请求情况来决定TTL缓存时间，经验来讲，不太建议缓存时间超过半天
  * 线程池根据持久观察的局域网内请求数量来定，开大浪费开小不够

