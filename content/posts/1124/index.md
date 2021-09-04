---
aliases:
- /archives/1124
categories:
- Go语言
date: 2020-03-12 05:04:53+00:00
draft: false
title: Golang的io.MultiWriter实现原理
---

Golang的标准库中包含一个io包，其中有个MultiWriter方法。这个方法不论传入什么样的Writer甚至是os.File都能够正常接受，这让我有些好奇他是怎么实现的。本篇文章对此进行阐述



## 深挖过程


```
        var file *os.File
	_, w, _ := os.Pipe()
	var writer io.Writer
	var wc io.WriteCloser
	iii := io.MultiWriter(file, w, writer, wc)
```


在如上这段代码中，MultiWriter同时接受了3种数据类型，分别是*os.File（第二个也是）、io.Writer、io.WriteCloser

下面是这个方法的实现，注释中对此解释大意是这样的：MultiWriter创建了一个writer，这个writer重复它的writes（我有点迷这个writes到底词性是什么，此处应该是个名词吧）实现到所有提供的writer里边去。那么继续向下看



```

// MultiWriter creates a writer that duplicates its writes to all the
// provided writers, similar to the Unix tee(1) command.
//
// Each write is written to each listed writer, one at a time.
// If a listed writer returns an error, that overall write operation
// stops and returns the error; it does not continue down the list.
func MultiWriter(writers ...Writer) Writer {
	allWriters := make([]Writer, 0, len(writers))
	for _, w := range writers {
		if mw, ok := w.(*multiWriter); ok {
			allWriters = append(allWriters, mw.writers...)
		} else {
			allWriters = append(allWriters, w)
		}
	}
	return &amp;multiWriter{allWriters}
}
```



上边代码中首先创建了一个writers长度的Writer列表，然后遍历获取传入参数Writer

传入参数的定义是这样的，可以看到Writer中存在一个Write方法，这个interface应该是鸭子类型的用法，通过这一方法实现运行时多态的效果。



```

// Writer is the interface that wraps the basic Write method.
//
// Write writes len(p) bytes from p to the underlying data stream.
// It returns the number of bytes written from p (0 &lt;= n &lt;= len(p))
// and any error encountered that caused the write to stop early.
// Write must return a non-nil error if it returns n &lt; len(p).
// Write must not modify the slice data, even temporarily.
//
// Implementations must not retain p.
type Writer interface {
	Write(p []byte) (n int, err error)
}

```



遍历获取每个传入的Writer并进行类型断言，判断其是否为*multiWriter，我们再来看一下这个断言的类型的定义



```

type multiWriter struct {
	writers []Writer
}

```



结合上边的代码来看，相当于对w进行了断言，判断其类型是否为一个指针类型的multiWriter，对于断言非该类型的，append到allWriters中，直接添加这个Writer本身，而断言为*multiWriter类型的，则直接打散append进去 ，个人觉得这个断言可能是为了避免multiWriter重叠导致性能损失吧 。

这个allWriters最终初始化进一个multiWriter中。最后，返回这个结构体的指针，其内部通过指针方法实现了新的Write方法，下边对其内部的新的Writer的实现做一个解析



```

func (t *multiWriter) Write(p []byte) (n int, err error) {
	for _, w := range t.writers {
		n, err = w.Write(p)
		if err != nil {
			return
		}
		if n != len(p) {
			err = ErrShortWrite
			return
		}
	}
	return len(p), nil
}
```



可以看到，它遍历所有的writer并分别将流写入各个writer的Write方法中。

那到这里，不仅就好奇，我看os.File的实现，并没有Writer的实现，这又是什么原理？

在os.File中，通过组合的方式继承了file 这个结构体指针，关于file的数据类型，我们看下边的代码



```

// file is the real representation of *File.
// The extra level of indirection ensures that no clients of os
// can overwrite this data, which could cause the finalizer
// to close the wrong file descriptor.
type file struct {
	pfd        poll.FD
	name       string
	dirinfo    *dirInfo // nil unless directory being read
	appendMode bool     // whether file is opened for appending
}
```



可以看到，在file中已经没有组合继承了，那么对于file中的方法，我只看到了指针方法write，但是这是个包内的实现，包外肯定是用不了的，经过再一番的寻找，发现原来Write写在了另外一个文件中，通过指针方法组合进了File这个结构体中，打扰了。那这么一来，就解释得通了

## 总结

那么其实总结下来，原理也很简单，就单纯的——鸭子类型，而已。

个人觉得，Writer到interface接收这一过程，相当于将所有Writer中的Write实现组合进这个interface中，凡是interface中存在的定义，那么都可以通过这个interface将传入参数中的元素组合进来，借此方式实现泛型，至于多态应该也可以借此实现，不过目前还没有脑部出来实现的思路。

这个interface只接受了传入Writer的Write方法，就造成了一种能接受多种类型的效果，实际它只接了Write的实现而已。这个接受的Write的实现，在后边就被用于新的Write，就实现了MultiWrite这样一个效果。