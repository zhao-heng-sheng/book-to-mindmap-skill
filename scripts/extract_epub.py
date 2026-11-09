#!/usr/bin/env python3
"""从 EPUB 抽取分节正文、插图清单与图注。

用法：
    python extract_epub.py "book.epub" --out "D:/project/works/书名"

产出：
    <out>/正文/NNN.txt      每节一个文本文件，首两行为 FILE / TITLE
    <out>/images/           原书图片（保留原文件名）
    <out>/图片索引.tsv      小节 -> 图片 -> 图注，按阅读顺序
"""

import argparse
import html
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")


def read_text(zf, name):
    try:
        raw = zf.read(name)
    except KeyError:
        return ""
    for enc in ("utf-8", "utf-8-sig", "gb18030", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def strip_tags(fragment):
    """HTML -> 纯文本，保留段落换行。"""
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", fragment, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|h[1-6]|li|tr|blockquote)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    lines = []
    for line in s.split("\n"):
        line = re.sub(r"[ \t\u00a0]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def clean_caption(text):
    s = re.sub(r"<[^>]+>", "", text)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip(" 　）。，、；:：·…")
    return s[:40]


def extract_images(fragment):
    """返回 [(本地图片文件名, 图注)]，忽略 http/data 开头的远程地址。

    图注并非紧跟在图片后面（有时在前），因此按字符位置取最近的一条。
    距离超过 500 字符视为无关，留空。
    """
    imgs = [(m.start(), m.group(0)) for m in re.finditer(r"<img\b[^>]*>", fragment, re.I)]
    caps = [(m.start(), m.group(0)) for m in
            re.finditer(r"图\s*\d+\s*[-－–—.]\s*\d+[^\n。；]{0,30}", fragment)]

    out = []
    for pos, tag in imgs:
        src = None
        for attr in ("src", "xlink:href", "href"):
            mm = re.search(r'\b%s\s*=\s*["\']([^"\']+)["\']' % attr, tag, re.I)
            if mm:
                val = mm.group(1).strip()
                if not val.lower().startswith(("http", "data:", "//")):
                    src = val
                    break
        if not src:
            continue
        name = os.path.basename(src.split("?")[0])
        if not name.lower().endswith(IMG_EXT):
            continue
        caption = ""
        if caps:
            near = min(caps, key=lambda c: abs(c[0] - pos))
            if abs(near[0] - pos) <= 500:
                caption = clean_caption(near[1])
        out.append((name, caption))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("epub")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    epub = Path(args.epub).expanduser()
    if not epub.exists():
        sys.exit("找不到文件：%s" % epub)

    out = Path(args.out).expanduser()
    text_dir = out / "正文"
    img_dir = out / "images"
    text_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(epub) as zf:
        names = zf.namelist()
        container = read_text(zf, "META-INF/container.xml")
        m = re.search(r'full-path\s*=\s*"([^"]+)"', container)
        opf_path = m.group(1) if m else next((n for n in names if n.endswith(".opf")), None)
        if not opf_path:
            sys.exit("无法定位 OPF，可能不是标准 EPUB")
        opf = read_text(zf, opf_path)
        base = os.path.dirname(opf_path)

        manifest = {}
        for mm in re.finditer(r"<item\b[^>]*>", opf, re.I):
            tag = mm.group(0)
            i = re.search(r'\bid\s*=\s*"([^"]+)"', tag)
            h = re.search(r'\bhref\s*=\s*"([^"]+)"', tag)
            t = re.search(r'media-type\s*=\s*"([^"]+)"', tag)
            if i and h:
                manifest[i.group(1)] = (h.group(1), t.group(1) if t else "")
        spine = re.findall(r'<itemref\b[^>]*idref\s*=\s*"([^"]+)"', opf)

        index_rows = []
        sec = 0
        total_chars = 0
        seen_imgs = set()

        for idref in spine:
            href, mtype = manifest.get(idref, ("", ""))
            if not href or ("html" not in mtype and not href.lower().endswith((".xhtml", ".html", ".htm"))):
                continue
            path = os.path.normpath(os.path.join(base, href)).replace("\\", "/")
            if path not in names:
                continue
            raw = read_text(zf, path)
            body = re.sub(r"<(head|script|style)[^>]*>.*?</\1>", "", raw, flags=re.S | re.I)
            text = strip_tags(body)
            if len(text) < 60:  # 封面页、版权页、纯图片页
                continue
            sec += 1
            title = ""
            tm = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", body, re.S | re.I)
            if tm:
                title = re.sub(r"<[^>]+>", "", tm.group(1)).strip()
            if not title:
                tm = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
                title = html.unescape(tm.group(1)).strip() if tm else ""

            (text_dir / ("%03d.txt" % sec)).write_text(
                "### FILE: %s\n### TITLE: %s\n\n%s\n" % (path, title, text),
                encoding="utf-8",
            )
            total_chars += len(text)

            for img_name, caption in extract_images(body):
                src_path = os.path.normpath(
                    os.path.join(os.path.dirname(path), img_name)
                ).replace("\\", "/")
                actual = src_path if src_path in names else next(
                    (n for n in names if n.endswith("/" + img_name) or n == img_name), None
                )
                if not actual:
                    continue
                target = img_dir / os.path.basename(actual)
                if not target.exists():
                    target.write_bytes(zf.read(actual))
                seen_imgs.add(target.name)
                index_rows.append(
                    ("%03d" % sec, title, os.path.basename(actual),
                     str(target.stat().st_size), caption)
                )

    with (out / "图片索引.tsv").open("w", encoding="utf-8", newline="") as f:
        f.write("小节\t小节标题\t图片文件\t大小\t图注\n")
        for row in index_rows:
            f.write("\t".join(row) + "\n")

    print("分节文本：%d 个，共 %d 字符" % (sec, total_chars))
    print("插图：%d 处引用，%d 个文件 -> %s" % (len(index_rows), len(seen_imgs), img_dir))
    print("图片索引：%s" % (out / "图片索引.tsv"))


if __name__ == "__main__":
    main()
