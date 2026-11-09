#!/usr/bin/env python3
"""把 SVG 渲染成高清 PNG（默认 2 倍像素）。

用法：
    python svg2png.py "图.svg" ["输出.png"] [--scale 2]

说明：
    - 依次探测 Edge / Chrome / Chromium；本机 Chrome 常被沙箱拦，Edge 可用。
    - 画布尺寸取自 SVG 的 width/height，缺失时退回 viewBox。
    - 渲染后校验文件大小，小于 2KB 视为失败并尝试下一个浏览器。
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATES = [
    os.environ.get("SVG_RENDER_BROWSER", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


def canvas_size(svg_text, default=(1280, 900)):
    w = re.search(r'\bwidth\s*=\s*"([\d.]+)(?:px)?"', svg_text)
    h = re.search(r'\bheight\s*=\s*"([\d.]+)(?:px)?"', svg_text)
    if w and h:
        return int(float(w.group(1))), int(float(h.group(1)))
    vb = re.search(r'viewBox\s*=\s*"([\d.\-\s]+)"', svg_text)
    if vb:
        parts = vb.group(1).split()
        if len(parts) == 4:
            return int(float(parts[2])), int(float(parts[3]))
    return default


def render(browser, svg_path, out_path, width, height, scale):
    tmp_profile = tempfile.mkdtemp(prefix="svgrender_")
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--user-data-dir=%s" % tmp_profile,
        "--force-device-scale-factor=%s" % scale,
        "--window-size=%d,%d" % (width, height),
        "--screenshot=%s" % out_path,
        svg_path.as_uri(),
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if out_path.exists() and out_path.stat().st_size > 2048:
        return True, ""
    return False, "输出为空或过小"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--scale", type=float, default=2)
    args = ap.parse_args()

    svg_path = Path(args.svg).expanduser().resolve()
    if not svg_path.exists():
        sys.exit("找不到 SVG：%s" % svg_path)
    out_path = Path(args.out).expanduser().resolve() if args.out else svg_path.with_suffix(".png")

    text = svg_path.read_text(encoding="utf-8", errors="ignore")[:4000]
    width, height = canvas_size(text)

    tried = []
    for browser in CANDIDATES:
        if not browser or not Path(browser).exists():
            continue
        tried.append(Path(browser).name)
        ok, err = render(browser, svg_path, out_path, width, height, args.scale)
        if ok:
            print("渲染成功：%s" % out_path)
            print("  浏览器 %s | 画布 %dx%d | 输出 %d 字节"
                  % (Path(browser).name, width, height, out_path.stat().st_size))
            return
        print("  跳过 %s：%s" % (Path(browser).name, err))
    sys.exit("渲染失败，已尝试：%s" % (", ".join(tried) or "无可用浏览器"))


if __name__ == "__main__":
    main()
