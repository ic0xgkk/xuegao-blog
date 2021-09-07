---
aliases:
- /archives/528
categories:
- Linux
date: 2019-12-06 05:52:08+00:00
draft: false
title: MongoDB集群部署
---

研发需要，部署MongoDB的一主一副一仲裁集群，用于解锁对事务的支持，顺带提供高可用。同时，还会一同部署一备份节点和一内存缓存节点，备份节点为数据提供冷备，使用LUN快照，保障数据异常时还有机会进行回滚；内存节点用于加速查询速度。



老规矩~

![图片](./1570173123846.png)


接下来开始正题~



## 环境

CentOS 8 x86_64

## 前置工作

### 准备目录


```bash
mkdir /data/etc -p
mkdir /data/db -p
mkdir /data/log -p
```



如上，分别新建了几个目录，其中：

  * etc目录用于存放配置文件
  * db用于存放数据库文件
  * log用于存放所有的日志（不含数据库的操作日志）

### 优化

#### THP优化

按照官方的说法，Linux Kernel默认开启了内存透明大页（THP）支持。透明大页面是一种Linux内存管理系统，通过使用更大的内存页面，可以减少具有大量内存的计算机上的Translation Lookaside Buffer（TLB）查找的开销。但是由于数据库对内存的访问模式往往是稀疏而不是连续的，因此透明大页一定程度上会影响数据库的性能，所以要关掉。

命令直接贴出来了



```bash
mkdir /etc/tuned/virtual-guest-no-thp
cat > /etc/tuned/virtual-guest-no-thp/tuned.conf << EOF
[main]
include=virtual-guest

[vm]
transparent_hugepages=never
EOF

tuned-adm profile virtual-guest-no-thp
```



#### 文件系统优化

Linux默认方式下会对文件访问的时间进行记录，这些操作是没有必要的，因此可以关掉

直接改**/etc/fstab**即可，使得挂载记录为如下配置：



```text
UUID=ecdbaaaa-1113-222b-3336-444fa1112227 /data xfs defaults,noatime        0 0

```



重启后即可看到生效了：/dev/sdb1 on /data type xfs (rw,noatime,attr2,inode64,noquota)

#### 关闭磁盘预读

这个应该归属到阵列卡设置里，将阵列卡的读写策略进行调整即可。

#### 放开资源限制

ulimit，该优化已直接写进systemd的service文件中

#### 禁用NUMA

由于我用的不是宿主机，因此无法直接管理NUMA调度域

按照一些文献和资料的说法，假设一台服务器有两个CPU，即他会存在两个NUMA调度域，由于内存和CPU是直连的，因此不跨调度域执行的情况下响应速度会比跨调度域执行快，同时如果两个调度域内内存命中情况不一样的话（A节点剩余0.1G内存可用，B节点剩余32G内存可用）并且某个CPU节点的内存不足时，会导致swap交换发生，而不是从远程节点分配内存。即swap insanity

### 新建用户


```bash
groupadd mongod
useradd -s /sbin/nologin -M -g mongod mongod
```



### 检查目录结构

正确的目录结构应该如下（.为/data）：



```bash
.
├── db
│   ├── admin
│   │   ├── collection
│   │   │   ├── 17--7409093569969147507.wt
│   │   │   ├── 19--7409093569969147507.wt
│   │   │   └── 31--7409093569969147507.wt
│   │   └── index
│   │       ├── 18--7409093569969147507.wt
│   │       ├── 20--7409093569969147507.wt
│   │       ├── 32--7409093569969147507.wt
│   │       └── 33--7409093569969147507.wt
│   ├── config
│   │   ├── collection
│   │   │   ├── 21--7409093569969147507.wt
│   │   │   └── 27--7409093569969147507.wt
│   │   └── index
│   │       ├── 22--7409093569969147507.wt
│   │       ├── 24--7409093569969147507.wt
│   │       └── 28--7409093569969147507.wt
│   ├── diagnostic.data
│   │   ├── metrics.2019-12-07T15-08-54Z-00000
│   │   ├── metrics.2019-12-07T15-16-56Z-00000
│   │   ├── metrics.2019-12-07T15-24-55Z-00000
│   │   └── metrics.interim
│   ├── journal
│   │   ├── WiredTigerLog.0000000003
│   │   ├── WiredTigerPreplog.0000000001
│   │   └── WiredTigerPreplog.0000000002
│   ├── local
│   │   ├── collection
│   │   │   ├── 0--7409093569969147507.wt
│   │   │   ├── 10--7409093569969147507.wt
│   │   │   ├── 16--7409093569969147507.wt
│   │   │   ├── 2--7409093569969147507.wt
│   │   │   ├── 4--7409093569969147507.wt
│   │   │   ├── 6--7409093569969147507.wt
│   │   │   └── 8--7409093569969147507.wt
│   │   └── index
│   │       ├── 11--7409093569969147507.wt
│   │       ├── 1--7409093569969147507.wt
│   │       ├── 3--7409093569969147507.wt
│   │       ├── 5--7409093569969147507.wt
│   │       ├── 7--7409093569969147507.wt
│   │       └── 9--7409093569969147507.wt
│   ├── _mdb_catalog.wt
│   ├── mongod.lock
│   ├── sizeStorer.wt
│   ├── storage.bson
│   ├── WiredTiger
│   ├── WiredTigerLAS.wt
│   ├── WiredTiger.lock
│   ├── WiredTiger.turtle
│   └── WiredTiger.wt
├── etc
│   ├── mongod.key
│   └── mongod.yml
├── log
│   ├── mongod.log
│   ├── mongod.log.2019-12-06T08-16-12
│   ├── mongod.log.2019-12-07T08-48-16
│   ├── mongod.log.2019-12-07T14-13-29
│   ├── mongod.log.2019-12-07T14-13-49
│   ├── mongod.log.2019-12-07T14-14-09
│   ├── mongod.log.2019-12-07T14-14-30
│   ├── mongod.log.2019-12-07T14-14-50
│   ├── mongod.log.2019-12-07T14-15-10
│   ├── mongod.log.2019-12-07T14-15-22
│   ├── mongod.log.2019-12-07T14-15-42
│   ├── mongod.log.2019-12-07T14-16-03
│   ├── mongod.log.2019-12-07T14-16-23
│   ├── mongod.log.2019-12-07T14-23-03
│   ├── mongod.log.2019-12-07T14-56-40
│   ├── mongod.log.2019-12-07T15-07-18
│   ├── mongod.log.2019-12-07T15-08-53
│   ├── mongod.log.2019-12-07T15-16-55
│   └── mongod.log.2019-12-07T15-24-53
├── mongodb-linux-x86_64-rhel80-4.2.1
│   ├── bin
│   │   ├── bsondump
│   │   ├── install_compass
│   │   ├── mongo
│   │   ├── mongod
│   │   ├── mongodump
│   │   ├── mongoexport
│   │   ├── mongofiles
│   │   ├── mongoimport
│   │   ├── mongoreplay
│   │   ├── mongorestore
│   │   ├── mongos
│   │   ├── mongostat
│   │   └── mongotop
│   ├── LICENSE-Community.txt
│   ├── MPL-2
│   ├── README
│   ├── THIRD-PARTY-NOTICES
│   └── THIRD-PARTY-NOTICES.gotools
└── mongodb-linux-x86_64-rhel80-4.2.1.tgz

16 directories, 81 files

```



## 配置文件

该配置文件参考官方文档，对应mongodb的4.2版本，其他版本慎用。配置文件为yaml语法



```yaml
systemLog:
    # 日志等级，0为Info等级
    verbosity: 0
    # 静默启动，交由systemd管理所以不用
    quiet: false
    # 追踪所有的异常，将会输出所有的日志
    traceAllExceptions: true
    # 日志facility
    syslogFacility: "daemon"
    # 日志位置
    path: "/data/log/mongod.log"
    # 每次启动后使用新的日志文件
    logAppend: false
    # 使用新日志文件，重命名旧日志
    logRotate: "rename"
    # 日志独立，不给syslog接管
    destination: "file"
    # 日志输出时间格式，日志时间为本地时区
    timeStampFormat: "iso8601-local"
    # 全局日志等级
    # component:

processManagement:
    # 不使用fork
    fork: false
    # PID文件路径
    pidFilePath: "/tmp/mongod.pid"

# 云监控    
# cloud:
#     monitoring:
#         free:
#             state: <string>
#             tags: <string>

net:
    port: 27017
    bindIp: "0.0.0.0"
    # bindIpAll: true
    # 最大连接
    maxIncomingConnections: 65536
    # 启用写入对象检查
    wireObjectCheck: true
    # 启用IPv6
    ipv6: false
    
    # 域描述符
    unixDomainSocket:
        enabled: false
        # pathPrefix: <string>
        # filePermissions: <int>

    tls:
        # 关闭TLS
        mode: "disabled"
        # certificateSelector: <string>
        # clusterCertificateSelector: <string>
        # certificateKeyFile: <string>
        # certificateKeyFilePassword: <string>
        # clusterFile: <string>
        # clusterPassword: <string>
        # CAFile: <string>
        # clusterCAFile: <string>
        # CRLFile: <string>
        # allowConnectionsWithoutCertificates: <boolean>
        # allowInvalidCertificates: <boolean>
        # allowInvalidHostnames: <boolean>
        # disabledProtocols: <string>
        # FIPSMode: <boolean>
    
    compression:
        # 压缩模式
        # 默认配置：snappy,zstd,zlib，不需要压缩因此关闭
        compressors: "disabled"
    # 同步执行
    serviceExecutor: "synchronous"
    
security:
    # key文件，用于副本集间认证
    keyFile: "/data/etc/mongod.key"
    # 集群认证模式
    clusterAuthMode: "keyFile"
    # 安全认证
    # 禁用的话数据库将会没有权限控制，初次配置完后记得改回去
    # 要改为"enabled"
    authorization: "disabled"
    # 滚动认证，没看懂文档啥意思，默认关了吧
    transitionToAuth: false
    # 允许执行JS脚本
    javascriptEnabled:  true
    # 企业版才有
    # redactClientLogData: <boolean>
    # 集群IP白名单
    # clusterIpSourceWhitelist:
    #    - 192.168.0.0/16
    #    - 192.167.0.0/16
    
    # Kerberos认证
    # sasl:
    #     hostName: <string>
    #     serviceName: <string>
    #     saslauthdSocketPath: <string>
    
    # 数据库加密，关闭，报错，注释掉
    # enableEncryption: false
    # encryptionCipherMode: <string>
    # encryptionKeyFile: <string>
    # kmip:
    #     keyIdentifier: <string>
    #     rotateMasterKey: <boolean>
    #     serverName: <string>
    #     port: <string>
    #     clientCertificateFile: <string>
    #     clientCertificatePassword: <string>
    #     clientCertificateSelector: <string>
    #     serverCAFile: <string>
    
    # LDAP关闭，企业版才有
    # ldap:
    #     servers: <string>
    #     bind:
    #         method: <string>
    #         saslMechanisms: <string>
    #         queryUser: <string>
    #         queryPassword: <string>
    #         useOSDefaults: <boolean>
    # transportSecurity: <string>
    # timeoutMS: <int>
    # userToDNMapping: <string>
    # authz:
    #     queryTemplate: <string>
    
storage:
    # 指定数据库存储的目录
    dbPath: "/data/db"
    # 启动后继续重建不完整的索引，副本集模式下不允许修改
    # indexBuildRetry: true
    # 
    journal:
        # 启用文件系统日志，副本集成员无法指定
        enabled: true
        # 日志提交周期，默认100，单位为毫秒，取值范围1-500
        commitIntervalMs: 500
    # 使用独立的目录存储每个数据库
    directoryPerDB: true
    # fsync刷新操作到磁盘的周期，默认为60
    syncPeriodSecs: 60
    # 存储引擎，wiredTiger/inMemory
    engine: "wiredTiger"
    wiredTiger:
        engineConfig:
            # 缓存大小，小数
            cacheSizeGB: 1.0
            # 日志压缩方法，默认snappy
            journalCompressor: "none"
            # 分离存储索引
            directoryForIndexes: true
            # 最大缓存文件大小，超出会直接导致程序退出。0为无限制大小
            maxCacheOverflowFileSizeGB: 0
        collectionConfig:
            # 块压缩方法
            blockCompressor: "none"
        indexConfig:
            # 前缀压缩
            prefixCompression: false
    # inMemory:
    #     engineConfig:
    #         # 浮点数，Default: 50% of physical RAM less 1 GB
    #         inMemorySizeGB: <number>

operationProfiling:
    # 操作分析模式，打开会影响性能
    mode: "off"
    # slowOpThresholdMs: <int>
    # slowOpSampleRate: <double>

replication:
    # 副本同步日志的最大大小，MB
    # 建议为磁盘大小的5%
    oplogSizeMB: 10240
    # 副本集名称，一个集群名称要相同
    replSetName: "BSDB"
    # 官方文档没说，注释掉
    # secondaryIndexPrefetch: <string>
    # 启动读取事件关注，事务使用，关掉会影响事务
    enableMajorityReadConcern: true

# 分片集
# sharding:
#     clusterRole: <string>
#     archiveMovedChunks: <boolean>

# 审计日志，开了影响性能
# auditLog:
#     # 目标，该选项一旦设置将会启用日志审计
#     destination: "file"
#     format: <string>
#     path: <string>
#     filter: <string>

```



### KeyFile配置

博主我在KeyFile上栽了将近一天时间。这个KeyFile在被mongod加载时会检查权限是否过大，如果过大daemon会直接退出，然而日志里却只有一个INFO等级的日志，trace并没有任何直接相关的内容输出。所以在保存完配置文件后，接着开始生成key，严格按照下面的步骤进行



```bash
openssl rand -base64 741 > /data/etc/mongod.key
# 0600的权限一定要给，否则就是无法启动
chmod 0600 /data/etc/mongod.key
```



## service配置

mongodb交由systemd管理，对应的service文件如下



```ini
[Unit]
Description=MongoDB Database Server
Documentation=https://docs.mongodb.org/manual
After=network.target

[Service]
User=mongod
Group=mongod
Environment="OPTIONS=-f /data/etc/mongod.yml"
ExecStart=/data/mongodb-linux-x86_64-rhel80-4.2.1/bin/mongod $OPTIONS
ExecStartPre=/usr/bin/chown mongod:mongod /data -R
PermissionsStartOnly=true
PIDFile=/tmp/mongod.pid
Type=simple
Restart=on-failure
RestartSec=20
# file size
LimitFSIZE=infinity
# cpu time
LimitCPU=infinity
# virtual memory size
LimitAS=infinity
# open files
LimitNOFILE=64000
# processes/threads
LimitNPROC=64000
# locked memory
LimitMEMLOCK=infinity
# total threads (user+kernel)
TasksMax=infinity
TasksAccounting=false
# Recommended limits for mongod as specified in
# https://docs.mongodb.com/manual/reference/ulimit/#recommended-ulimit-settings

[Install]
WantedBy=multi-user.target

```



## 启动


```bash
systemctl start mongod.service
systemctl enable mongod.service
systemctl status mongod.service

● mongod.service - MongoDB Database Server
   Loaded: loaded (/etc/systemd/system/mongod.service; enabled; vendor preset: disabled)
   Active: active (running) since Fri 2019-12-06 16:00:48 CST; 4s ago
     Docs: https://docs.mongodb.org/manual
  Process: 3917 ExecStartPre=/usr/bin/chown mongod:mongod /data -R (code=exited, status=0/SUCCESS)
 Main PID: 3919 (mongod)
   Memory: 64.1M
   CGroup: /system.slice/mongod.service
           └─3919 /data/mongodb-linux-x86_64-rhel80-4.2.1/bin/mongod -f /data/etc/mongod.yml

Dec 06 16:00:48 BS-DB-M systemd[1]: Starting MongoDB Database Server...
Dec 06 16:00:48 BS-DB-M systemd[1]: Started MongoDB Database Server.

```



## 后置操作

### 关firewalld开iptables


```bash
systemctl disable firewalld.service
dnf install iptables-services

cat > /etc/sysconfig/iptables << EOF
# sample configuration for iptables service
# you can edit this manually or use system-config-firewall
# please do not ask us to add additional ports/services to this default configuration
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -p tcp -m state --state NEW -m tcp --dport 22 -j ACCEPT
-A INPUT -p tcp -m state --state NEW -m tcp --dport 27017 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -j REJECT --reject-with icmp-host-prohibited
COMMIT
EOF
systemctl restart iptables.service
systemctl enable iptables.service
```



### 增加根用户

增加根用户前一定要先初始化副本集，否则无法写入



```js
rs.initiate()
use admin
db.createUser(
{
    user: "User",
    pwd: "Password",
    roles: ['root']
})
```



进而修改配置文件重启到带角色认证的模式(security.authorization改成enabled)

到此处，主节点就成功部署完成了，紧接着是从节点和仲裁节点

## 副节点（S1）

副节点只需要把配置文件中的身份认证打开即可，其他的复制粘贴即可。但是需要注意的是，同一集群的KeyFile应当相同，因此这个KeyFile要手工同步到各个节点去

待到服务运行后，在主节点里按照如下步骤添加副节点，需要特别注意的是，只有主节点才能添加从（副）节点和仲裁节点。同时，所有节点间必须要使用~~主机名~~域名通讯，否则可能会出现无法同步的问题，~~可以使用类似于如下的脚本给每个节点加上hosts记录就行~~，需要使用域名直接连接，后续客户端驱动也可以直接使用，如果使用主机名可能会导致客户端驱动连接异常。

紧接着再在主节点添加副节点和仲裁即可



```js

# shell命令
/data/mongodb-linux-x86_64-rhel80-4.2.1/bin/mongo --port 27017 -u <username> -p

# 数据库CLI中执行的命令
rs.status();
rs.add("域名:27017");
rs.addArb("域名:27017");

```



添加完成后，使用rs.status()即可看到节点的投票情况和当前等级。使用如下命令执行同步即可(主节点执行)



```js
rs.slaveOk()
```



到这一步，就意味着配置已经完成了，如果没有问题，就可以将日志等级调低了。输出完整的跟踪日志就可以关闭了，在systemLog.traceAllExceptions即可置为false

完工~
