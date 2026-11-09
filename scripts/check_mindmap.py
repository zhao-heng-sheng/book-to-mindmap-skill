#!/usr/bin/env python3
"""校验思维导图 Markdown 的结构与导图工具兼容性。

用法：
    python check_mindmap.py "书名-全书思维导图.md" ["书名-思维导图-精简版.md" ...]

检查项：
    1. 标题层级分布、节点规模
    2. 编号连续性与重复编号
    3. 空小节（标题下没有内容）
    4. 导图工具不兼容语法：**加粗**、`行内代码`、表格、引用块、分割线
    5. 图片引用指向的文件是否存在

有错误时退出码为 1。
"""

import collections
import re
import sys
from pathlib import Path

BAD_PATTERNS = [
    (r"\*\*", "加粗 ** **"),
    (r"`", "行内代码 ``"),
    (r"^\s*\|", "表格"),
    (r"^\s*>", "引用块"),
    (r"^\s*(-{3,}|\*{3,})\s*$", "分割线"),
]


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


def check(path):
    p = Path(path)
    if not p.exists():
        print("!! 文件不存在：%s" % p)
        return 1, 0
    lines = p.read_text(encoding="utf-8").split("\n")

    heads = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    bullets = [l for l in lines if re.match(r"^\s*-\s+", l)]
    depths = sorted({indent_of(l) for l in bullets})

    errors = []
    warns = []

    # 1. 规模
    level_count = collections.Counter(h[1] for h in heads)
    print("文件：%s" % p.name)
    print("  行数 %d | 标题 %d %s | 节点 %d | 最大缩进 %s"
          % (len(lines), len(heads), dict(sorted(level_count.items())),
             len(bullets), (max(depths) if depths else 0)))

    # 2. 编号连续性
    numbered = []
    for idx, level, text in heads:
        m = re.match(r"^(\d+(?:\.\d+)*)\s+", text)
        if m:
            numbered.append((m.group(1), level, text))
    groups = collections.OrderedDict()
    for num, level, text in numbered:
        parts = num.split(".")
        parent = ".".join(parts[:-1]) or "root"
        groups.setdefault((parent, level), []).append(int(parts[-1]))
    dup = [n for n, c in collections.Counter(n for n, _, _ in numbered).items() if c > 1]
    if dup:
        errors.append("重复编号：%s" % ", ".join(dup))
    for (parent, level), seq in groups.items():
        # 允许两种编号体系：从 1 起（章节）、从 0 起（总览章）
        if seq != list(range(1, len(seq) + 1)) and seq != list(range(0, len(seq))):
            errors.append("编号不连续：%s 下为 %s" % (parent, seq))

    # 3. 空小节
    for k, (idx, level, text) in enumerate(heads):
        if level < 3:
            continue
        end = len(lines)
        for j in range(k + 1, len(heads)):
            if heads[j][1] <= level:
                end = heads[j][0]
                break
        body = lines[idx + 1:end]
        if not any(re.match(r"^\s*-\s+", b) for b in body):
            warns.append("空小节：%s" % text)

    # 4. 兼容性
    for pat, name in BAD_PATTERNS:
        hit = [i + 1 for i, l in enumerate(lines) if re.search(pat, l, re.M)]
        if hit:
            errors.append("含导图不兼容语法（%s），出现在第 %s 行"
                          % (name, ", ".join(map(str, hit[:6]))))

    # 5. 图片引用
    imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", "\n".join(lines))
    missing = [s for s in imgs
               if not s.lower().startswith(("http://", "https://"))
               and not (p.parent / s).exists()]
    if missing:
        errors.append("图片文件缺失：%s" % ", ".join(missing))
    print("  图片引用 %d 处%s" % (len(imgs), "，全部存在" if imgs and not missing else ""))

    for w in warns:
        print("  - 提示 %s" % w)
    for e in errors:
        print("  !! %s" % e)
    print("  结论：%s" % ("通过" if not errors else "需修正"))
    return (1 if errors else 0), len(errors)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rc = 0
    for arg in sys.argv[1:]:
        code, _ = check(arg)
        rc = rc or code
        print()
    sys.exit(rc)


if __name__ == "__main__":
    main()
