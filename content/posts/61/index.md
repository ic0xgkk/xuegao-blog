---
aliases:
- /archives/61
categories:
- 虚拟化
date: 2018-06-11 09:20:48+00:00
draft: false
title: VMware ESXi 硬盘RDM直通
summary: ESXi把逻辑硬盘直接直通到虚拟机中，不再划分虚拟磁盘。适用于NAS等场景
---

有时候很尴尬需要把整个物理硬盘都给虚拟机使用，就好比NAS系统，好在ESXi提供了RDM直通功能，可以按照以下办法实现

## 步骤

1. 打开vSphere Client，在`服务器>配置>存储器`页面中找到要创建RDM链接的物理设备,并记下ID
2. SSH连接到ESXi，使用`vmkfstools -r /vmfs/devices/disks/ /<路径>/file.vmdk`即可，具体操作如下 

```bash
~ # vmkfstools -r /vmfs/devices/disks/naa.6782bcb05600390020ae8ce955723213 /vmfs/volumes/SAS-SYS/sea.vmdk
/vmfs/volumes/59032095-fcac8d1a-20a8-782bcb77b96c # du -sh sea*
0 sea-rdm.vmdk
0 sea.vmdk
```

## 结果

再次查看文件类型，发现RDM映射的文件已经跟传统的虚拟磁盘文件类型已经有不同


```bash
RW 8388608 VMFS “sea.vmdk”
RW 8388608 VMFSRDM “sea-rdm.vmdk”
```


此时直接就可以去给虚拟机添加虚拟磁盘了，然后直通就完成了