---
title: "kube-proxy中iptables下负载均衡如何保证会话一致性?"
date: 2021-08-31T21:10:21+08:00
draft: true
categories:
  - Kubernetes
---

Kubernetes中存在Service资源，其本质上是面向应用提供了一个支持故障隔离的负载均衡器。那么在iptables模式下，这个负载均衡器的前后会话的一致性又是如何保障的呢？
本篇文章，让我们一起来瞅一瞅实现这一特性的kube-proxy是如何调教iptables的。
