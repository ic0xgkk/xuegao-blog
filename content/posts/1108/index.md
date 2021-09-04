---
aliases:
- /archives/1108
categories:
- Go语言
date: 2020-02-29 08:31:18+00:00
draft: false
title: golang搬砖填坑指南 1
---

写这篇文章是因为这两天在写一个运维小工具，自动备份数据并加密上传到对象存储用的，由于牵扯到备份，免不了需要压缩，在使用golang做数据压缩时出了点问题，本文针对这个问题做相关研究和探讨。





## 前言

不过其实说真的，这个备份过程其实可以完全不需要go来解决，仅仅依靠shell script我觉得就能解决备份和加密问题。但是很遗憾，最后的关头——上传操作，官方没有提供HTTP接口，所以想用CURL上传就不可能了，要使用SDK只能通过撸码解决。希望借此机会能再诞生出来一个比较好用的小工具吧，同时也再熟悉一下go，太久没写go了。

虽然Python香是香，但是每次装依赖我想我能不能省掉这一步………还是用go比较舒服，编译完就一个二进制文件，分发也很方便。

## 代码逻辑

我写了一个名为Backuper的小工具，它会按照如下顺序进行工作（当前版本）：

懒得写了，自己看代码吧……..

<https: backuper="" github.com="" ic0xgkk="">

## 遇到的问题

那么在实际debug的过程中发现，总是有一些文件备份不上。主要表现是这样：

  * EOF错误
  * archive/tar: write too long错误
  * 符号链接压缩不上或者空目录无法备份进去

对于EOF问题，其实也就是找不到文件的结尾而已。尝试直接保存为tar.gz发现解压时仍然出EOF，感觉文件尾部应该缺失了什么…查了查文档发现（如下），压缩结束时需要Close一下，此时同时会将footer写入进去。顿时感觉不对劲，debug看了一下发现不小心把Close写反了，先关了文件才关tar，难怪没有footer…….修改完再次尝试就可以了

<blockquote class="wp-block-quote">
<p>
    Close closes the tar archive by flushing the padding, and writing the footer. If the current file (from a prior call to WriteHeader) is not fully written, then this returns an error.
  </p>
<cite>func (tw *<a href="https://golang.org/pkg/archive/tar/#Writer">Writer</a>) Close() <a href="https://golang.org/pkg/builtin/#error">error</a> – Go Doc</cite>
</blockquote>

对于archive/tar: write too long问题或许要多点东西说。起初以为是遍历的问题，就去查了Walk和其实现源码

<blockquote class="wp-block-quote">
<p>
    Walk walks the file tree rooted at root, calling walkFn for each file or directory in the tree, including root. All errors that arise visiting files and directories are filtered by walkFn. The files are walked in lexical order, which makes the output deterministic but means that for very large directories Walk can be inefficient. Walk does not follow symbolic links.
  </p>
<cite>func Walk() – Go Doc</cite>
</blockquote>

文档中对于Walk有了详细的说明，尤其是最后一句，遍历不会跟随符号链接，在StackOverflow上查了一下，有说法乘如果遍历跟随符号链接的情况下容易造成死循环，想想确实有道理。

但是我要压缩备份文件，如果符号链接解决不了，至少我要知道它会潜在哪些问题，避免出现文件没备份上的情况。



```

// Walk walks the file tree rooted at root, calling walkFn for each file or
// directory in the tree, including root. All errors that arise visiting files
// and directories are filtered by walkFn. The files are walked in lexical
// order, which makes the output deterministic but means that for very
// large directories Walk can be inefficient.
// Walk does not follow symbolic links.
func Walk(root string, walkFn WalkFunc) error {
	info, err := os.Lstat(root)
	if err != nil {
		err = walkFn(root, nil, err)
	} else {
		err = walk(root, info, walkFn)
	}
	if err == SkipDir {
		return nil
	}
	return err
}
```



看了下Walk的实现，发现其依靠的是os包的Lstat方法，在Walk的中貌似并没有看到相关的判断

<blockquote class="wp-block-quote">
<p>
    Lstat returns a FileInfo describing the named file. If the file is a symbolic link, the returned FileInfo describes the symbolic link. Lstat makes no attempt to follow the link. If there is an error, it will be of type *PathError.
  </p>
<cite>func Lstat() – Go Doc</cite>
</blockquote>

在上边的描述中可以看到，Lstat会返回文件的信息，如果是符号链接的情况下，将会返回符号链接的描述并且不会跟随



```

type FileInfo interface {
    Name() string       // base name of the file
    Size() int64        // length in bytes for regular files; system-dependent for others
    Mode() FileMode     // file mode bits
    ModTime() time.Time // modification time
    IsDir() bool        // abbreviation for Mode().IsDir()
    Sys() interface{}   // underlying data source (can return nil)
}
```



IsDir()说明能支持文件和文件夹，FileMode包含的信息



```

const (
    // The single letters are the abbreviations
    // used by the String method's formatting.
    ModeDir        FileMode = 1 &lt;&lt; (32 - 1 - iota) // d: is a directory
    ModeAppend                                     // a: append-only
    ModeExclusive                                  // l: exclusive use
    ModeTemporary                                  // T: temporary file; Plan 9 only
    ModeSymlink                                    // L: symbolic link
    ModeDevice                                     // D: device file
    ModeNamedPipe                                  // p: named pipe (FIFO)
    ModeSocket                                     // S: Unix domain socket
    ModeSetuid                                     // u: setuid
    ModeSetgid                                     // g: setgid
    ModeCharDevice                                 // c: Unix character device, when ModeDevice is set
    ModeSticky                                     // t: sticky
    ModeIrregular                                  // ?: non-regular file; nothing else is known about this file

    // Mask for the type bits. For regular files, none will be set.
    ModeType = ModeDir | ModeSymlink | ModeNamedPipe | ModeSocket | ModeDevice | ModeCharDevice | ModeIrregular

    ModePerm FileMode = 0777 // Unix permission bits
)
```



可以看到在FileMode中标识了文件类型，其实是有符号链接支持的



```

// walk recursively descends path, calling walkFn.
func walk(path string, info os.FileInfo, walkFn WalkFunc) error {
	if !info.IsDir() {
		return walkFn(path, info, nil)
	}

	names, err := readDirNames(path)
	err1 := walkFn(path, info, err)
	// If err != nil, walk can't walk into this directory.
	// err1 != nil means walkFn want walk to skip this directory or stop walking.
	// Therefore, if one of err and err1 isn't nil, walk will return.
	if err != nil || err1 != nil {
		// The caller's behavior is controlled by the return value, which is decided
		// by walkFn. walkFn may ignore err and return nil.
		// If walkFn returns SkipDir, it will be handled by the caller.
		// So walk should return whatever walkFn returns.
		return err1
	}

	for _, name := range names {
		filename := Join(path, name)
		fileInfo, err := lstat(filename)
		if err != nil {
			if err := walkFn(filename, fileInfo, err); err != nil &amp;&amp; err != SkipDir {
				return err
			}
		} else {
			err = walk(filename, fileInfo, walkFn)
			if err != nil {
				if !fileInfo.IsDir() || err != SkipDir {
					return err
				}
			}
		}
	}
	return nil
}
```



在Walk的实现子方法walk中，发现了存在的判断逻辑。walk判断了是否为文件夹，如果不是文件夹才会继续向下，全程似乎只看到了对Dir的判断

针对上边的FileMode又查了查，发现了如下表格<figure class="wp-block-table">
<table class="">
<tr>
<th>
<strong>Type name</strong>
</th>
<th>
<strong>Symbolic name</strong>
</th>
<th>
<strong>Bitmask</strong>
</th>
</tr>
<tr>
<td>
<a href="https://www.computerhope.com/jargon/s/socket.htm">Socket</a>
</td>
<td>
      S_IFSOCK
    </td>
<td>
      0140000
    </td>
</tr>
<tr>
<td>
<a href="https://www.computerhope.com/jargon/s/symblink.htm">Symbolic link</a>
</td>
<td>
      S_IFLNK
    </td>
<td>
      0120000
    </td>
</tr>
<tr>
<td>
      Regular file
    </td>
<td>
      S_IFREG
    </td>
<td>
      0100000
    </td>
</tr>
<tr>
<td>
<a href="https://www.computerhope.com/jargon/s/special-file.htm#block-special-file">Block special file</a>
</td>
<td>
      S_IFBLK
    </td>
<td>
      0060000
    </td>
</tr>
<tr>
<td>
<a href="https://www.computerhope.com/jargon/d/director.htm">Directory</a>
</td>
<td>
      S_IFDIR
    </td>
<td>
      0040000
    </td>
</tr>
<tr>
<td>
<a href="https://www.computerhope.com/jargon/s/special-file.htm#character-special-file">Character device</a>
</td>
<td>
      S_IFCHR
    </td>
<td>
      0020000
    </td>
</tr>
<tr>
<td>
<a href="https://www.computerhope.com/jargon/f/fifo.htm">FIFO (named pipe)</a>
</td>
<td>
      S_IFIFO
    </td>
<td>
      0010000
    </td>
</tr>
</table></figure> 

现在我知道了，使用Dir做判断只是为了进行遍历而已。但是对文件进行压缩时要特别注意，符号链接不能做跟随，否则容易出现死循环问题。其次，查了下发现文件夹、符号链接都是只有一个Header而并没有Data，因此Header中的长度是负值或者0。处理这类的时候，只需要向流中写入Header后即可结束，而无需再Open。

<blockquote class="wp-block-quote">
<p>
    WriteHeader writes hdr and prepares to accept the file’s contents. The Header.Size determines how many bytes can be written for the next file. If the current file is not fully written, then this returns an error. This implicitly flushes any padding necessary before writing the header.
  </p>
<cite>func (tw *Writer) WriteHeader(hdr *Header) error – Go Doc</cite>
</blockquote>

可以看到，Header在写入后将会准备写入文件内容，Header中的Size决定了接下来Content能写入的大小，正是由于符号链接和文件夹本身就是没有Data的，所以Size也并非常规值，写入文件时自然会超出大小然后提示文件过长……..

知道了问题所在，改了下代码，在处理句柄上加一个判断类型——是链接、是常规文件、还是文件夹，仅仅只处理这三种即可，毕竟，备份/dev/sda、/var/test.socket好像也没有什么意义吧？

对于空目录无法备份上去的问题，其实也是我判断了是否为常规文件后直接选择跳过了的结果。相当于有文件存在时目录才会被创建，并且目录的Header可能已经丢失，因此判断如果是Dir的话写个Header到流里即可解决。

最后问题全部解决。填坑成功</https:>