# xuegao-blog
雪糕博客-静态版

## 构建方式

使用GitHub Action自动构建和推送

## 发布流程

在发布前，需要执行以下操作：

```bash
chmod a+x ./before_publish.sh && ./before_publish.sh
```

## 本地预览

```bash
./hugo server -e production --bind 0.0.0.0 --baseURL "http://X.X.X.X:1313"
```
