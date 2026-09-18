#!/usr/bin/env python3
"""textstats —— 命令行文本统计工具（仅使用 Python 标准库）。

用法:
    python3 textstats.py <文件路径> [--top N]

输出文件的行数、单词数、字符数，以及出现频率最高的前 N 个单词。

统计规则:
    * 行数   : 按换行分隔后的行数；空文件为 0，结尾的换行符不算多出一行。
    * 单词数 : 由连续的字母/数字/下划线（正则 \\w+）构成的词，不区分大小写。
    * 字符数 : 文件包含的字符总数（含空格与换行符）。
    * Top N  : 出现次数降序排列；次数相同的单词按字母升序排列。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from typing import Dict, List, Sequence, Tuple

DEFAULT_TOP = 5
EXIT_ERROR = 1
WORD_RE = re.compile(r"\w+")


class TextStatsError(Exception):
    """可预期的用户错误（文件不存在、无法读取等），由 main 捕获后转为退出码。"""


def compute_stats(text: str) -> Dict[str, object]:
    """统计文本，返回行数、单词数、字符数以及每个单词的出现次数。"""
    words = WORD_RE.findall(text.lower())
    return {
        "lines": len(text.splitlines()),
        "words": len(words),
        "chars": len(text),
        "counts": Counter(words),
    }


def top_words(counts: Counter, n: int) -> List[Tuple[str, int]]:
    """取出现次数最多的前 n 个单词（次数降序，同频按字母升序）。"""
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:n]


def read_text(path: str) -> str:
    """以 UTF-8 读取文本文件；失败时抛出 TextStatsError。

    newline="" 关闭换行符翻译，否则 CRLF 文件的 \\r 会被吞掉，字符数偏少。
    """
    try:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except FileNotFoundError:
        raise TextStatsError("错误: 文件不存在: {}".format(path))
    except IsADirectoryError:
        raise TextStatsError("错误: 目标是目录而不是文件: {}".format(path))
    except PermissionError:
        raise TextStatsError("错误: 没有读取权限: {}".format(path))
    except UnicodeDecodeError:
        raise TextStatsError("错误: 文件不是有效的 UTF-8 文本: {}".format(path))
    except OSError as exc:
        raise TextStatsError("错误: 无法读取文件 {}: {}".format(path, exc))


def parse_top(value: str) -> int:
    """解析 --top 参数，必须是正整数，否则报错。"""
    try:
        number = int(str(value).strip())
    except ValueError:
        raise argparse.ArgumentTypeError("--top 需要一个整数，收到: {!r}".format(value))
    if number <= 0:
        raise argparse.ArgumentTypeError("--top 必须是正整数，收到: {}".format(number))
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textstats.py",
        description="统计文本文件的行数、单词数、字符数与高频单词。",
    )
    parser.add_argument("file", help="要统计的文本文件路径")
    parser.add_argument(
        "--top",
        metavar="N",
        type=parse_top,
        default=DEFAULT_TOP,
        help="显示出现频率最高的前 N 个单词（默认 %(default)s，须为正整数）",
    )
    return parser


def format_report(stats: Dict[str, object], n: int) -> str:
    """把统计结果格式化为多行报告。"""
    lines = [
        "行数: {}".format(stats["lines"]),
        "单词数: {}".format(stats["words"]),
        "字符数: {}".format(stats["chars"]),
        "高频单词 Top {}:".format(n),
    ]
    for index, (word, count) in enumerate(top_words(stats["counts"], n), start=1):
        lines.append("  {}. {} ({})".format(index, word, count))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """命令行入口，返回进程退出码。"""
    args = build_parser().parse_args(argv)
    try:
        text = read_text(args.file)
    except TextStatsError as exc:
        print(exc, file=sys.stderr)
        return EXIT_ERROR
    print(format_report(compute_stats(text), args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
