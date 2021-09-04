---
aliases:
- /archives/570
categories:
- Linux
date: 2019-12-08 07:50:35+00:00
draft: false
title: MongoDB副本集节点权重和读写分离
---

重配节点权重，从而设置最低权重的节点为冷备节点（跨机房同步使用，要避免切成主节点），而配置读写分离可以加快某一节点上的数据查询速度~

本篇文章分为两部分，分别为节点权重和读写分离



## 注意

新增新节点到副本集中需要先在各个节点增加hosts记录，私有dns域的除外~

## 节点权重

首先进入的mongodb的cli模式，执行如下内容

```js
# 获取当前配置
cfg = rs.conf()

# 根据节点设置权重
cfg.members[0].priority = 10
cfg.members[1].priority = 5
cfg.members[3].priority = 1

# 保存回去
rs.reconfig(cfg)
```



特别注意的，mongodb中priority为权重，权重越大节点越优先生效成为主节点

这样配置完成之后，即可

## 读写分离

看官方文档有个In-Memory Storage Engine，到部署的时候发现用不了，再仔细一看Enterprise Only，我服

曲线救国，用tmpfs解决，增加如下记录行fstab即可：

```
tmpfs       /data/db tmpfs   nodev,nosuid,noexec,nodiratime,size=10G   0 0
```



然后重启

配置文件直接如下即可

需要特别注意的是，如下的配置关闭了数据库的日志，借此来提高读性能。由于tmpfs将内存占满后会触发swap交换，因此请确保数据库的数据大小不会超过内存大小，避免swap交换导致的大幅度降低读速度。同时，由于数据在内存中，掉电或者重启后数据会丢失，请确保该节点只是作为一个只读副节点使用，避免数据丢失



```yaml

systemLog:
    # 日志等级，0为Info等级
    verbosity: 0
    # 静默启动，交由systemd管理所以不用
    quiet: false
    # 追踪所有的异常，将会输出所有的日志
    traceAllExceptions: false
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
    authorization: "enabled"
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
    # journal:
        # 启用文件系统日志，副本集成员无法指定
        #enabled: false
        # 日志提交周期，默认100，单位为毫秒，取值范围1-500
        # commitIntervalMs: 500
    # 使用独立的目录存储每个数据库
    directoryPerDB: true
    # fsync刷新操作到磁盘的周期，默认为60
    syncPeriodSecs: 60
    # 存储引擎，wiredTiger/inMemory
    engine: "wiredTiger"
    wiredTiger:
        engineConfig:
            # 缓存大小，小数
            cacheSizeGB: 0.1
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
    #         inMemorySizeGB: 10.0

operationProfiling:
    # 操作分析模式，打开会影响性能
    mode: "off"
    # slowOpThresholdMs: <int>
    # slowOpSampleRate: <double>

replication:
    # 副本同步日志的最大大小，MB
    # 建议为磁盘大小的5%
    oplogSizeMB: 1024
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

配完这个后，在主节点数据库配置该节点的标签，使用如下命令（mongo cli）：



```js
cfg = rs.conf()
cfg.members[1].tags = {"mem_node": "yes"}
rs.reconfig(cfg)
```



配置完节点的tag后，在驱动连接时对tag进行选择即可指定读偏好为特定一个节点，然后即可实现读写分离

