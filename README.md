# textstats

命令行文本统计工具，只使用 Python 3 标准库，无任何第三方依赖。

统计指定文本文件的 **行数**、**单词数**、**字符数**，以及出现频率最高的前 N 个单词。

## 用法

```bash
python3 textstats.py <文件路径> [--top N]
```

| 参数 | 说明 |
| --- | --- |
| `file` | 要统计的文本文件路径（必需，UTF-8 编码） |
| `--top N` | 显示频率最高的前 N 个单词，`N` 必须是正整数，默认 `5` |

`--top` 也支持等号写法：`--top=3`。

### 示例

```console
$ printf 'Hello world\nhello there\nWorld WORLD of code\n' > sample.txt
$ python3 textstats.py sample.txt
行数: 3
单词数: 8
字符数: 44
高频单词 Top 5:
  1. world (3)
  2. hello (2)
  3. code (1)
  4. of (1)
  5. there (1)
```

自定义 Top N（取前 2 个）：

```console
$ python3 textstats.py sample.txt --top 2
行数: 3
单词数: 8
字符数: 44
高频单词 Top 2:
  1. world (3)
  2. hello (2)
```

## 统计规则

* **行数**：按换行分隔后的行数；空文件为 0，结尾的换行符不算多出一行
  （`"a\nb\n"` 是 2 行，`"a\nb"` 也是 2 行，`""` 是 0 行）。
* **单词数**：由连续的字母 / 数字 / 下划线（正则 `\w+`）构成的词，不区分大小写。
  标点会作为分隔符，因此 `it's` 计为 `it` 和 `s` 两个词。
* **字符数**：文件包含的字符总数（含空格与换行符），与 `wc -m` 一致。
  读取时不做换行符翻译，因此 CRLF 文件的每个 `\r`、`\n` 都计入字符数；
  行数则按 `\n`、`\r\n`、`\r` 统一分隔后的行。
* **Top N**：单词统一转小写后统计；按出现次数降序排列，次数相同的单词按字母升序排列。
  例如 `b b b a a c c c` 排序为 `b(3), c(3), a(2)`。

## 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 统计成功 |
| `1` | 文件读取失败（不存在、是目录、无权限、非 UTF-8 文本等），错误信息输出到 stderr |
| `2` | 命令行参数非法（缺少文件路径；`--top` 为 `0`、负数或非整数） |

`--top` 边界示例：

```console
$ python3 textstats.py notes.txt --top 0
usage: textstats.py [-h] [--top N] file
textstats.py: error: argument --top: --top 必须是正整数，收到: 0
$ echo $?
2

$ python3 textstats.py notes.txt --top 3.5
textstats.py: error: argument --top: --top 需要一个整数，收到: '3.5'

$ python3 textstats.py missing.txt
错误: 文件不存在: missing.txt
$ echo $?
1
```

空文件各项均为 0：

```console
$ : > empty.txt && python3 textstats.py empty.txt
行数: 0
单词数: 0
字符数: 0
高频单词 Top 5:
```

## 测试

```bash
python3 -m unittest test_textstats -v
```

覆盖范围：正常统计、大小写归一与同频排序、无结尾换行与 CRLF 文件、空文件、
纯空白文件、文件不存在 / 目录 / 非 UTF-8、`--top` 边界（`0`、负数、非整数、超大值）
以及本 README 可直接运行。

## 项目结构

```
textstats.py        # 工具实现（CLI 入口为 main()）
test_textstats.py   # unittest 测试套件
README.md           # 本文件
```

### 可复用的函数

| 函数 | 说明 |
| --- | --- |
| `compute_stats(text)` | 返回 `{"lines", "words", "chars", "counts"}` |
| `top_words(counts, n)` | 取前 n 个 `(单词, 次数)`，次数降序、同频字母升序 |
| `read_text(path)` | 读取 UTF-8 文件，失败抛出 `TextStatsError` |
| `parse_top(value)` | 校验 `--top`，非正整数时抛出 `argparse.ArgumentTypeError` |
| `format_report(stats, n)` | 生成多行统计报告 |
