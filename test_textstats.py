#!/usr/bin/env python3
"""textstats 的单元测试。

运行:
    python3 -m unittest test_textstats -v
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

import textstats

HERE = os.path.dirname(os.path.abspath(__file__))

# 行数 3 / 单词数 8 / 字符数 44
# 词频: world=3, hello=2, code=1, of=1, there=1（同频按字母升序）
SAMPLE = "Hello world\nhello there\nWorld WORLD of code\n"


class StatsTestCase(unittest.TestCase):
    """公共辅助：在临时目录里生成样例文件并捕获 CLI 输出。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmpdir = self._tmp.name

    def write(self, name, content, encoding="utf-8"):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding=encoding) as handle:
            handle.write(content)
        return path

    def run_main(self, *argv):
        """直接调用 main()，返回 (退出码, 标准输出, 标准错误)。"""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = textstats.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def run_cli(self, *argv):
        """以子进程方式运行 CLI，返回 CompletedProcess。"""
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "textstats.py"), *argv],
            capture_output=True,
            text=True,
        )


class TestPureFunctions(StatsTestCase):
    """compute_stats / top_words 的纯函数行为。"""

    def test_compute_stats_counts_lines_words_chars(self):
        stats = textstats.compute_stats(SAMPLE)
        self.assertEqual(stats["lines"], 3)
        self.assertEqual(stats["words"], 8)
        self.assertEqual(stats["chars"], 44)

    def test_compute_stats_empty_text_is_all_zero(self):
        stats = textstats.compute_stats("")
        self.assertEqual((stats["lines"], stats["words"], stats["chars"]), (0, 0, 0))
        self.assertEqual(dict(stats["counts"]), {})

    def test_stats_case_insensitive(self):
        stats = textstats.compute_stats("Abc abc ABC")
        self.assertEqual(stats["counts"]["abc"], 3)

    def test_top_words_orders_by_count_then_alphabet(self):
        counts = textstats.compute_stats("b b b a a c c c d")["counts"]
        self.assertEqual(textstats.top_words(counts, 10),
                         [("b", 3), ("c", 3), ("a", 2), ("d", 1)])

    def test_top_words_handles_ascii_and_digits(self):
        counts = textstats.compute_stats("it's 2026 ok ok it")["counts"]
        self.assertEqual(textstats.top_words(counts, 5),
                         [("it", 2), ("ok", 2), ("2026", 1), ("s", 1)])

    def test_top_words_n_larger_than_vocabulary(self):
        counts = textstats.compute_stats("a b c")["counts"]
        self.assertEqual(textstats.top_words(counts, 99), [("a", 1), ("b", 1), ("c", 1)])


class TestNormalFiles(StatsTestCase):
    """正常文件的统计与输出。"""

    def test_report_for_sample_file(self):
        path = self.write("sample.txt", SAMPLE)
        code, out, err = self.run_main(path)
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")
        self.assertIn("行数: 3", out)
        self.assertIn("单词数: 8", out)
        self.assertIn("字符数: 44", out)
        self.assertIn("高频单词 Top 5:", out)

    def test_top_five_defaults(self):
        path = self.write("sample.txt", SAMPLE)
        code, out, _ = self.run_main(path)
        ranked = [line.split(". ", 1)[1] for line in out.splitlines() if line.startswith("  ")]
        self.assertEqual(code, 0)
        self.assertEqual(ranked, ["world (3)", "hello (2)", "code (1)", "of (1)", "there (1)"])

    def test_top_n_option_limits_result(self):
        path = self.write("sample.txt", SAMPLE)
        code, out, _ = self.run_main(path, "--top", "2")
        ranked = [line.split(". ", 1)[1] for line in out.splitlines() if line.startswith("  ")]
        self.assertEqual(code, 0)
        self.assertEqual(ranked, ["world (3)", "hello (2)"])

    def test_top_n_form_equals_form(self):
        path = self.write("sample.txt", SAMPLE)
        code, out, _ = self.run_main(path, "--top=3")
        self.assertEqual(code, 0)
        self.assertIn("高频单词 Top 3:", out)

    def test_text_without_trailing_newline(self):
        path = self.write("no_newline.txt", "one two")
        code, out, _ = self.run_main(path)
        self.assertEqual(code, 0)
        self.assertIn("行数: 1", out)
        self.assertIn("单词数: 2", out)
        self.assertIn("字符数: 7", out)


class TestEmptyFile(StatsTestCase):
    """空文件各项为 0。"""

    def test_empty_file_report(self):
        path = self.write("empty.txt", "")
        code, out, err = self.run_main(path)
        self.assertEqual(code, 0, err)
        self.assertIn("行数: 0", out)
        self.assertIn("单词数: 0", out)
        self.assertIn("字符数: 0", out)
        self.assertIn("高频单词 Top 5:", out)
        self.assertEqual([line for line in out.splitlines() if line.startswith("  ")], [])

    def test_whitespace_only_file_has_no_words(self):
        # "\n\n   \n" -> 空行、空行、纯空格行，共 3 行 6 个字符
        path = self.write("blank.txt", "\n\n   \n")
        code, out, _ = self.run_main(path)
        self.assertEqual(code, 0)
        self.assertIn("行数: 3", out)
        self.assertIn("字符数: 6", out)
        self.assertIn("单词数: 0", out)


class TestMissingFile(StatsTestCase):
    """文件不存在等读取失败的情况。"""

    def test_missing_file_via_main(self):
        missing = os.path.join(self.tmpdir, "nope.txt")
        code, out, err = self.run_main(missing)
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("错误", err)
        self.assertIn("nope.txt", err)

    def test_missing_file_via_cli_exit_code(self):
        result = self.run_cli(os.path.join(self.tmpdir, "nope.txt"))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(result.stderr.strip(), "")

    def test_directory_argument_is_rejected(self):
        code, _, err = self.run_main(self.tmpdir)
        self.assertNotEqual(code, 0)
        self.assertNotEqual(err.strip(), "")

    def test_non_utf8_file_is_rejected(self):
        path = self.write("binary.bin", "\xff\xfe\x00bad", encoding="latin-1")
        code, _, err = self.run_main(path)
        self.assertNotEqual(code, 0)
        self.assertNotEqual(err.strip(), "")


class TestTopOptionValidation(StatsTestCase):
    """--top 的边界值：0、负数、非整数。"""

    def setUp(self):
        super().setUp()
        self.path = self.write("sample.txt", SAMPLE)

    def assert_rejected(self, *argv):
        result = self.run_cli(self.path, *argv)
        self.assertNotEqual(
            result.returncode, 0, "应非零退出: {}\n{}".format(argv, result.stdout)
        )
        self.assertNotEqual(result.stderr.strip(), "")
        return result

    def test_top_zero_is_rejected(self):
        result = self.assert_rejected("--top", "0")
        self.assertIn("正整数", result.stderr)

    def test_top_negative_is_rejected(self):
        self.assert_rejected("--top", "-1")
        self.assert_rejected("--top=-7")

    def test_top_non_integer_is_rejected(self):
        for bad in ("abc", "3.5", "2x", ""):
            with self.subTest(top=bad):
                self.assert_rejected("--top", bad)

    def test_top_zero_via_main_raises_system_exit(self):
        with self.assertRaises(SystemExit) as ctx:
            textstats.main([self.path, "--top", "0"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_missing_positional_argument_is_rejected(self):
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(result.stderr.strip(), "")

    def test_top_huge_but_valid_is_accepted(self):
        code, out, _ = self.run_main(self.path, "--top", "999")
        self.assertEqual(code, 0)
        # 词表只有 5 个单词，最多输出 5 行
        self.assertEqual(len([l for l in out.splitlines() if l.startswith("  ")]), 5)


class TestAcceptance(StatsTestCase):
    """验收要求：README.md 可直接运行，且测试与实现同目录。"""

    def test_readme_can_be_analyzed(self):
        readme = os.path.join(HERE, "README.md")
        self.assertTrue(os.path.exists(readme), "缺少 README.md")
        result = self.run_cli(readme)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("高频单词", result.stdout)

    def test_implementation_uses_stdlib_only(self):
        with open(os.path.join(HERE, "textstats.py"), encoding="utf-8") as handle:
            source = handle.read()
        for banned in ("import requests", "import pandas", "import numpy", "pip install"):
            self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main()
