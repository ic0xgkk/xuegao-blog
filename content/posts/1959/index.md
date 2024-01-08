---
title: 转向模式驱动——用buf管理云原生系统的API
date: 2024-01-08T21:33:11+08:00
draft: false
categories:
  - Go
  - 云原生
---

# 前言

最近在对既有系统向云原生改造，为了平衡服务间的独立性、互通性，在参考了Medium和OREILLY的资料后，decoupling服务时决定仅允许服务间通过gRPC调用、不暴露中间件和数据库，因此，需要一个仓库来存放、管理所有的gRPC API，也就是一堆的protobuf文件。

众多的protobuf揉在一个仓库里，还有不同的版本需要做区分，相互间可能还会有依赖，可能还会引用外部的依赖，这要手写Makefile得多累？为了解决这个问题，尝试引入了buf，本文就来讲讲它怎么帮助解决这些问题。

# buf是什么

buf是一家来自加拿大的公司推出的开源工具，它目标为将API的开发转向为模式驱动，提高API稳健性的同时提高开发效率，打通各个生态系统的最后一环。我使用buf已经有一年了，从最开始的小打小闹写着玩、到现在全量投入使用，能够很明显地看到收益：

- 我不再需要关注protobuf依赖的更新，这是buf的工作。
- 我不再需要手工拉下来依赖的proto文件，这也是buf的工作。
- 我不再需要为`protoc-gen`写一堆又臭又长的`-I`参数，这还是buf的工作。
- 我不再需要满Google查code style，buf自带有lint会提醒。
- 我不再需要为不同接口写重复的业务代码，buf能够自动管理proto文件间的依赖关系并生成代码。

看了这么多，是不是觉得buf就是管理protobuf的go module？我也觉得是。

# 安装buf

在安装了Go之后，直接使用下边的命令安装即可，注意检查一下是否为最新的版本。这里只贴了安装命令，PATH需要单独配置。

```bash
apt install -y protobuf-compiler
go install github.com/bufbuild/buf/cmd/buf@v1.28.1
```

# 注册登录BSR

BSR全称Buf Schema Registry，就是buf放依赖的仓库，如果你需要把你的API存放到BSR中，就需要注册BSR并登录，在设置中创建新Token，然后使用如下命令配置到系统中。由于本文我不需要推到BSR中，因此就不多赘述，只放个配置文件，有需要的可以再去官网找文档。

```bash
cat > ~/.netrc << EOF
machine buf.build
    login <你的用户名>
    password <你的Token>
machine go.buf.build
    login <你的用户名>
    password <你的Token>
EOF
```

# 创建项目

我创建了一个项目目录，名为`apis`，接下来，我就以`apis/`开头的路径讲述步骤所在的目录层级。路径名称可能会比较随意，建议生产使用时再去参考一下protobuf的code style建议。

首先，在`apis/`中，创建如下两个目录。

```bash
mkdir gen # 放生成的代码。
mkdir proto # 放proto文件。
```

初始化go mod，名称随意。

```bash
go mod init apis
```

创建`apis/buf.gen.yaml`，填入如下内容。

```yaml
version: v1
managed:
  enabled: true
  go_package_prefix:
    # 决定go的包前缀，一定要设置正确
    default: gitlab.com/myusername/apis/gen
plugins:
  - plugin: buf.build/protocolbuffers/go:v1.32.0
    out: gen
    opt: paths=source_relative
  - plugin: buf.build/grpc/go:v1.3.0
    out: gen
    opt:
      - paths=source_relative
      - require_unimplemented_servers=false
```

进入到`apis/proto`目录中，初始化buf mod。

```bash
buf mod init
```

初始化buf mod后，你会在`apis/proto`得到一个`buf.yaml`文件，它的内容如下。

```yaml
version: v1
breaking:
  use:
    - FILE
lint:
  use:
    - DEFAULT
```

此时，你就完成项目的创建了。

# 什么是protovalidate

此处，我引入了一个名为protovalidate的依赖，这里用到它了，介绍一下它。

在以往protoc-gen-validate的时代，我会把参数校验写在proto文件中，通过这个插件生成go代码，以便对message做参数校验，业务代码就不再需要写一堆验证逻辑了。相对人工在业务代码中写一坨参数验证的代码，它已经提升了一些效率，但是，由于它基于模板生成代码，它也有解决不了的问题——灵活性。这里我举个场景，限制一个message中两个字段必须符合如下两个条件之一：

- 一个字段长度为4时，另一个字段的数值必须在0-32之间。
- 一个字段的长度为16时，另一个字段的数值必须在0-128之间。

熟悉的朋友看到这个可能已经想到了，这不就是IP网络地址吗，对的，我就是需要IP地址的字段为4字节长度时（即IPv4），掩码只能在0-32之间，而在IP地址的字段为16字节时（即IPv6），掩码就可以在0-128之间。然而，这在protoc-gen-validate的时代，是不可能的事情。

那么接下来，我们来看看新的插件——protovalidate。得益于Google推出的CEL，现在的protovalidate可以直接将验证规则生成到message的raw desc中了，没错，这样一来参数校验也不再需要生成一个单独的代码文件出来了，而是生成为raw desc，在protobuf解析时顺带做评估验证，不再需要生成代码处理。可以使用CEL，那么意味着用户可以自己编写验证规则，上边所提到的IP网络，就可以像下边这样写规则。

创建`apis/proto/address/address.proto`文件，并填入如下内容。

```protobuf
syntax = "proto3";

package address;

import "buf/validate/validate.proto";

message Prefix {
    option (buf.validate.message).cel = {
      id: "must_ipv4_or_ipv6",
      message: "must be valid ipv4 or ipv6",
      // IPv4时掩码0-32，IPv6时掩码0-128
      expression: "(size(this.ip) == 4 && this.mask >= 0 && this.mask <=32) || (size(this.ip) == 16 && this.mask >= 0 && this.mask <= 128)"
    };

    bytes ip = 1 [(buf.validate.field).bytes.ip = true];
    uint32 mask = 2 [(buf.validate.field).uint32 = { gte: 0, lte: 128 }];
}
```

# 引入protovalidate

Google搜索protovalidate，在文档中可以看到proto文件中的引用名称为`buf/validate/validate.proto`，buf的依赖名称为`buf.build/bufbuild/protovalidate`。

那么，修改`apis/proto/buf.yaml`，在其中添加依赖名称，如下。

```yaml
version: v1
# 添加到下边这里
deps:
  - buf.build/bufbuild/protovalidate
breaking:
  use:
    - FILE
lint:
  use:
    - DEFAULT
```

然后在`apis/proto`中，使用下边的命令更新依赖，这一步结束后，就会看到有一个`apis/proto/buf.lock`的文件生成了。

```bash
buf mod update
```

最后，我们再在`apis/buf.gen.yaml`中添加依赖，如下。

```yaml
version: v1
managed:
  enabled: true
  go_package_prefix:
    default: gitlab.com/myusername/apis/gen
    # 添加到下边这里，就是引入的BSR中的依赖
    except:
      - buf.build/bufbuild/protovalidate
plugins:
  - plugin: buf.build/protocolbuffers/go:v1.32.0
    out: gen
    opt: paths=source_relative
  - plugin: buf.build/grpc/go:v1.3.0
    out: gen
    opt:
      - paths=source_relative
      - require_unimplemented_servers=false
```

这时候，在`apis/`中，我们就可以使用下边的命令生成代码，并且更新依赖了。

```bash
buf generate proto
go mod tidy
```

生成代码后，我们就得到了如下这么个结构。

```bash
.
├── buf.gen.yaml
├── gen
│   └── address
│       └── address.pb.go <- 这就是生成的代码，其中的raw desc也包含了参数校验的规则。
├── go.mod
├── go.sum
└── proto
    ├── address
    │   └── address.proto
    ├── buf.lock
    └── buf.yaml
```

# 不同目录间调用

如何在不同的目录间使用现有的proto文件呢？在buf mod中，proto文件可以在mod层级中直接按照文件路径来引用。

创建一个文件`apis/proto/usage/usage.proto`，填入如下内容。

```protobuf
syntax = "proto3";

package usage;

// 这里引用了刚刚的address.proto文件。
import "address/address.proto";

message Example {
    // 引用了刚刚的Prefix。
    address.Prefix addr = 1;
}
```

再执行生成，就可以得到如下的目录结构，也就成功引用到了Prefix。

```bash
.
├── buf.gen.yaml
├── gen
│   ├── address
│   │   └── address.pb.go
│   └── usage
│       └── usage.pb.go
├── go.mod
├── go.sum
└── proto
    ├── address
    │   └── address.proto
    ├── buf.lock
    ├── buf.yaml
    └── usage
        └── usage.proto
```

# 总结

写的比较仓促，简单介绍了一下buf。一开始所提到的管理gRPC API遇到的问题，在贴出的步骤中可以很清楚得看到buf交出的解决办法，从以往的API开发模式到现在面向架构、模式驱动的开发方式，大幅提高了开发、维护API的效率，云原生服务间的API，从此也将可以通过protobuf和buf进一步连通，生态系统间的最后一环就此完工。

# 参考资料

- [https://medium.com/cloud-native-daily/rethink-the-way-you-share-the-data-between-micro-services-with-change-data-capture-a666a4473388](https://medium.com/cloud-native-daily/rethink-the-way-you-share-the-data-between-micro-services-with-change-data-capture-a666a4473388)
- [https://learning.oreilly.com/library/view/cloud-native/9781492053811/](https://learning.oreilly.com/library/view/cloud-native/9781492053811/)
- [https://buf.build/blog/api-design-is-stuck-in-the-past](https://buf.build/blog/api-design-is-stuck-in-the-past)
- [https://github.com/google/cel-spec](https://github.com/google/cel-spec)
- [https://github.com/bufbuild/protovalidate-go](https://github.com/bufbuild/protovalidate-go)
- [https://buf.build/blog/protoc-gen-validate-v1-and-v2/](https://buf.build/blog/protoc-gen-validate-v1-and-v2/)
- [https://buf.build/bufbuild/protovalidate/docs/main:buf.validate](https://buf.build/bufbuild/protovalidate/docs/main:buf.validate)
- [https://github.com/bufbuild/protovalidate/blob/main/examples/option_string_len.proto](https://github.com/bufbuild/protovalidate/blob/main/examples/option_string_len.proto)
- [https://buf.build/docs/tutorials/getting-started-with-bsr](https://buf.build/docs/tutorials/getting-started-with-bsr)
- [https://github.com/bufbuild/buf-tour/tree/main/finish/getting-started-with-bsr](https://github.com/bufbuild/buf-tour/tree/main/finish/getting-started-with-bsr)
