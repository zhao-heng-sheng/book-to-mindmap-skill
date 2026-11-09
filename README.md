# book-to-mindmap

> 把一本书变成能直接导入 XMind 的思维导图，并让插图说中文。

一个 WorkBuddy / Claude 风格的个人技能：读取 EPUB，逐章通读，按**因果链**而不是目录结构重组成 Markdown 导图，同时处理原书插图——英文图先译成中文再按原结构重绘，最后附一份 HTML 图集兜底。

## 它解决的四个老问题

| 问题 | 常见做法 | 这个技能的做法 |
|---|---|---|
| 只交文字，图全丢了 | 抽取时只读文本层 | 必做步骤之一：检查 `<img>`，按**所在小节**定位（图注会前后漂移，按图号定位必错） |
| 英文图直接塞进中文导图 | 原图贴上去 | 译成中文后**按原结构重绘**，原图归档不删 |
| 写成要点清单，读起来散 | 按章节罗列事实 | 每章第一个分支固定是「本章论证链」，全书开头是「全书论证主线」 |
| 交付前没校验 | 凭感觉 | `check_mindmap.py` 查编号断裂、空小节、加粗/表格残留、图片引用失效 |

## 安装

把整个目录放到技能目录下：

```bash
# Windows
git clone https://github.com/zhao-heng-sheng/book-to-mindmap.git \
  "$USERPROFILE/.workbuddy/skills/book-to-mindmap"

# macOS / Linux
git clone https://github.com/zhao-heng-sheng/book-to-mindmap.git \
  ~/.workbuddy/skills/book-to-mindmap
```

重启助手后生效。技能靠 `SKILL.md` 的 description 自动触发，说「总结这本书，整理成可以导入思维导图的 md」即可。

## 目录结构

```
book-to-mindmap/
├── SKILL.md                  主流程：8 步工作法 + 格式硬性要求 + 常见坑
├── scripts/
│   ├── extract_epub.py       EPUB → 分节正文 + 图片索引 + 图注
│   ├── check_mindmap.py      导图 md 结构与兼容性校验
│   └── svg2png.py            SVG → 2 倍高清 PNG（自动探测 Edge/Chrome）
├── references/
│   └── diagram-redraw.md     英文插图中文重绘规范：版式、配色、译名、验证回路
└── assets/
    └── gallery.html          图集模板，填 IMAGES 数组即可
```

## 工作流

1. 建任务文件夹，所有产物收在里面
2. `extract_epub.py` 抽正文与图片清单
3. **逐章通读**，不许抽样
4. 先搭因果链：全书主线 → 部分主线 → 每章论证链
5. 写详细版（逐章逐节，编号 `1 / 1.1 / 1.1.1`）
6. 写精简版（60–120 节点，纯推理主干）
7. 处理插图：筛选结构图 → 英文图重绘 → 插入 → 生成图集
8. `check_mindmap.py` 校验，通过后交付

## 三个脚本

```bash
# 1. 抽取。产出 正文/NNN.txt、图片索引.tsv、images/
python scripts/extract_epub.py "book.epub" --out "D:/project/works/书名"

# 2. 校验。有错误时退出码为 1
python scripts/check_mindmap.py "书名-全书思维导图.md" "书名-思维导图-精简版.md"

# 3. 渲染。SVG 1280 宽 → PNG 2560 宽
python scripts/svg2png.py "图片/xxx-中文版.svg" --scale 2
```

`extract_epub.py` 的两个细节值得一提：

- 只取非 `http` 开头的 `src`。很多 EPUB 的 `<img>` 同时带本地 `src` 和远程 `data-src`，先匹配到远程就会误判成"书里没图"。
- 图注按**字符距离**取最近的一条，而不是"本节第一条图号"。同一节有多张图时，后者会让所有图共用同一个图注。

`svg2png.py` 在 Windows 上会优先用 Edge：Chrome 常被沙箱拒绝执行，Edge 通常可用。

## 导图格式的硬性要求

XMind / 幕布 / markmap 导入 Markdown 时只认标题层级与无序列表。所以生成的文件里：

- 只用 `#` 标题和 `-` 列表，两个空格表示下一层
- 禁用 `**加粗**`、行内代码、表格、引用块、分割线——导入后会变成乱码字符
- 禁用有序列表 `1.`，导图工具不认它的层级
- 图片用标准语法，alt 里写完整说明，因为 XMind 不渲染图片，只能看到文字

## 实测

在两本真实书上跑通：

| 书 | 详细版 | 精简版 | 插图 |
|---|---|---|---|
| 《碰撞：人工智能对我们做什么》 | 163 标题 / 2335 节点 | 71 节点 | 1 张（英文原图重绘为中文） |
| 《如何找到想做的事》 | 92 标题 / 1156 节点 | 99 节点 | 13 张（中文原图） |

四份 Markdown 全部通过校验。

## License

MIT
