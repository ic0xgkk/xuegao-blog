---
aliases:
- /archives/592
categories:
- Linux
date: 2019-12-12 08:37:40+00:00
draft: false
title: etcd安装配置服务发现
---



直接贴service

```bash
cat > /etc/systemd/system/etcd.service <<EOF
[Unit]
Description=etcd
After=network.target

[Service]
User=etcd
Group=etcd
ExecStart=/data/etcd/etcd-v3.3.18-linux-amd64/etcd -name bs-etcd -data-dir /data/etcd/db -listen-peer-urls "http://192.168.100.133:2379" -advertise-client-urls "http://192.168.100.133:2380"
ExecStartPre=/usr/bin/chown etcd:etcd /data/etcd -R
PermissionsStartOnly=true
Type=notify
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

[Install]
WantedBy=multi-user.target
EOF
```

目录位置和结构如下

```bash
[root@BS-OTHSER etcd]# pwd
/data/etcd
[root@BS-OTHSER etcd]# tree -a
.
├── db
│   └── member
│       ├── snap
│       │   └── db
│       └── wal
│           └── 0000000000000000-0000000000000000.wal
├── etc
├── etcd-v3.3.18-linux-amd64
│   ├── Documentation
│   │   ├── benchmarks
│   │   │   ├── etcd-2-1-0-alpha-benchmarks.md
│   │   │   ├── etcd-2-2-0-benchmarks.md
│   │   │   ├── etcd-2-2-0-rc-benchmarks.md
│   │   │   ├── etcd-2-2-0-rc-memory-benchmarks.md
│   │   │   ├── etcd-3-demo-benchmarks.md
│   │   │   ├── etcd-3-watch-memory-benchmark.md
│   │   │   ├── etcd-storage-memory-benchmark.md
│   │   │   └── _index.md
│   │   ├── branch_management.md
│   │   ├── demo.md
│   │   ├── dev-guide
│   │   │   ├── api_concurrency_reference_v3.md
│   │   │   ├── api_grpc_gateway.md
│   │   │   ├── api_reference_v3.md
│   │   │   ├── apispec
│   │   │   │   └── swagger
│   │   │   │       ├── rpc.swagger.json
│   │   │   │       ├── v3election.swagger.json
│   │   │   │       └── v3lock.swagger.json
│   │   │   ├── experimental_apis.md
│   │   │   ├── grpc_naming.md
│   │   │   ├── _index.md
│   │   │   ├── interacting_v3.md
│   │   │   ├── limit.md
│   │   │   └── local_cluster.md
│   │   ├── dev-internal
│   │   │   ├── discovery_protocol.md
│   │   │   ├── logging.md
│   │   │   └── release.md
│   │   ├── dl_build.md
│   │   ├── faq.md
│   │   ├── _index.md
│   │   ├── integrations.md
│   │   ├── learning
│   │   │   ├── api_guarantees.md
│   │   │   ├── api.md
│   │   │   ├── auth_design.md
│   │   │   ├── client-architecture.md
│   │   │   ├── client-feature-matrix.md
│   │   │   ├── data_model.md
│   │   │   ├── glossary.md
│   │   │   ├── _index.md
│   │   │   ├── learner.md
│   │   │   └── why.md
│   │   ├── metrics.md
│   │   ├── op-guide
│   │   │   ├── authentication.md
│   │   │   ├── clustering.md
│   │   │   ├── configuration.md
│   │   │   ├── container.md
│   │   │   ├── etcd3_alert.rules
│   │   │   ├── etcd3_alert.rules.yml
│   │   │   ├── etcd-sample-grafana.png
│   │   │   ├── failures.md
│   │   │   ├── gateway.md
│   │   │   ├── grafana.json
│   │   │   ├── grpc_proxy.md
│   │   │   ├── hardware.md
│   │   │   ├── _index.md
│   │   │   ├── maintenance.md
│   │   │   ├── monitoring.md
│   │   │   ├── performance.md
│   │   │   ├── recovery.md
│   │   │   ├── runtime-configuration.md
│   │   │   ├── runtime-reconf-design.md
│   │   │   ├── security.md
│   │   │   ├── supported-platform.md
│   │   │   ├── v2-migration.md
│   │   │   └── versioning.md
│   │   ├── platforms
│   │   │   ├── aws.md
│   │   │   ├── container-linux-systemd.md
│   │   │   ├── freebsd.md
│   │   │   └── _index.md
│   │   ├── production-users.md
│   │   ├── README.md -> docs.md
│   │   ├── reporting_bugs.md
│   │   ├── rfc
│   │   │   └── _index.md
│   │   ├── tuning.md
│   │   └── upgrades
│   │       ├── _index.md
│   │       ├── upgrade_3_0.md
│   │       ├── upgrade_3_1.md
│   │       ├── upgrade_3_2.md
│   │       ├── upgrade_3_3.md
│   │       ├── upgrade_3_5.md
│   │       └── upgrading-etcd.md
│   ├── etcd
│   ├── etcdctl
│   ├── README-etcdctl.md
│   ├── README.md
│   └── READMEv2-etcdctl.md
└── etcd-v3.3.18-linux-amd64.tar.gz

17 directories, 87 files
```



新建用户



```bash
groupadd etcd
useradd -s /sbin/nologin -M -g etcd etcd
```



