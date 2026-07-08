# server-metrics-dashboard · 专业 README 编写提示词

> 适用对象：开源项目维护者 / 技术文档工程师 / 前端工程师 / 数据大屏课程助教
>
> 适用项目：**server-metrics-dashboard**（中文名：服务器监控数据可视化大屏）

---

## 1. 任务目标

为 `server-metrics-dashboard`（服务器监控数据可视化大屏）编写 / 重写 / 完善根目录 `README.md`：

- 面向 **学生、初学者、开源访问者和课程使用者**
- 风格：专业、清晰、开源项目友好、教学项目有亲和力
- **不要**写成企业官网广告稿，**不要**出现浮夸口号
- **不要**虚构已经接入真实后端、已经部署上线等尚未发生的事
- **不要**把提示词文件内容原样塞进 README

---

## 2. 你所在项目的真实情况（请在动手前先阅读这些文件以确认）

> 所有路径均为相对于项目根目录。

| 文件 | 读取目的 |
| :--- | :--- |
| `README.md` | 了解当前 README 结构与用语风格 |
| `LICENSE` | 确认开源协议（本项目为 MIT License） |
| `index.html` | 确认大屏页面实际包含的模块（E-R 关系图、CPU、网络、磁盘、内存、雷达、采样数、箱线图、主机汇总表等） |
| `process_data.py` | 确认数据清洗流程（.dat 解析、时间戳解析、小时级聚合） |
| `generate_figures.py` | 确认 PNG 图表生成逻辑与输出文件（8 张图表 + E-R 关系图） |
| `generate_pdf.py` | 确认 PDF 报告生成逻辑与输出文件（方案 A、方案 B） |
| `host_detail.dat` / `mod_detail.dat` / `disk_tsar.dat` / `pref_tsar.dat` | 确认原始数据源（4 张表） |
| `output/host_detail.json` 等 output 目录下文件 | 确认清洗后的数据结构 |
| `.gitignore` | 确认哪些文件（PDF、图表 PNG 等）通过 .gitignore 不提交到仓库 |
| `docs/screenshots/`（如果存在） | 确认是否存在 1920x1080 大屏截图 |

> 注意：如果你在其他类似项目（如 RuyiBigScreen）读过的提示词内容，**不要**直接套用；必须按 server-metrics-dashboard 的实际文件内容进行改写。

---

## 3. 项目真实定位

- **项目英文名**：`server-metrics-dashboard`
- **项目中文名**：服务器监控数据可视化大屏
- **项目性质**：公开开源的 **教学型数据大屏项目**
- **项目用途**：帮助学生和初学者从 0 到 1 学习如何制作一个完整的数据可视化大屏（含 E-R 关系建模、时间戳清洗、指标聚合、可视化与 PDF 报告自动化）
- **数据源**：当前为本地 `.dat` 原始数据 → 清洗为 `output/*.json` → 由 `index.html` 读取并渲染
- **真实后端**：当前没有真实后端，不要写“已接入真实后端”
- **在线部署**：如未在 `README.md` 中出现可访问的公开链接，不要虚构部署地址
- **开发服务端口**：当前为 `python -m http.server 8000`；若有定制脚本，按脚本实际情况写
- **报告输出端口**：PDF 报告为本地文件输出，不依赖端口服务

---

## 4. README 推荐结构（可根据项目情况微调）

请使用中文为主，保留必要英文技术名词。

```md
# server-metrics-dashboard｜服务器监控数据可视化大屏

项目一句话介绍（1-2 行），说明这是一个教学型数据可视化大屏项目。

## 项目预览

- 若 `docs/screenshots/dashboard-1920x1080.png` 确实存在，则使用 Markdown 图片引用：
  ![服务器监控数据可视化大屏](docs/screenshots/dashboard-1920x1080.png)

- 若该图片不存在：
  - 写一句说明：「项目大屏截图可通过浏览器访问后手动截取，或在未来版本提供自动化截图脚本。」
  - **不要**引用不存在的图片，避免在 GitHub 上显示破图。

## 项目简介

说明这是一个教学型数据可视化大屏项目，用来演示：
- 从 4 份 .dat 原始数据到结构化 JSON 的清洗流程
- E-R 关系建模（HOST_DETAIL / MOD_DETAIL / DISK_TSAR / PREF_TSAR 的 1:N 关系）
- 毫秒级时间戳到小时槽位的解析与聚合
- 前端单文件 HTML+ECharts 的大屏布局
- 报告文档（PDF）自动生成

## 核心特性

按代码实际实现列出 6-10 个特性，例如：
- 单文件 `index.html` 实现可交互大屏（无需构建）
- 4 张表的 E-R 关系建模与可视化（表格化实体 + 关系连线）
- 毫秒时间戳解析到 `YYYY-MM-DD HH:mm`
- 按小时聚合计算 `avg / max / min / sample_count`
- ECharts 折线图 / 柱状图 / 雷达图 / 箱线图的代码示例
- 两份 PDF 报告：方案 A（图表优先）与方案 B（正式分析报告）
- 代码风格统一，便于学生逐块阅读与改造

## 技术栈

列出本项目真实使用的技术：
- 数据清洗与聚合：Python 3（标准库 + pandas/matplotlib/reportlab）
- 图表渲染：ECharts（通过 CDN 加载）
- 前端实现：原生 HTML / CSS / JavaScript（单文件大屏）
- 报告输出：reportlab + matplotlib
- 关系图实现：原生 SVG 绘制（表格化实体 + 箭头连线）
- 代码版本管理：Git / GitHub

> 注意：本项目 **不是** Vue 3 / Vite / TypeScript 项目，不要写这些关键字。

## 页面内容 / 大屏模块

按 index.html 实际实现列出，例如：
- 顶部标题与数据源说明
- E-R 关系图（4 张表格化实体 + 1:N 关系连线）
- 时间戳解析表（原始毫秒 → 本地时区 → 小时槽位）
- CPU 使用率 / 空闲率折线图
- 网络入 / 出带宽折线图
- 磁盘 sda / sdb 使用率折线图
- 内存已用柱状图
- 关键指标 Max / Avg 雷达图
- 每小时采样数柱状图
- 机房分组箱线图
- 主机汇总表

## 实时数据模拟

- 若代码中 **尚未** 实现数据定时刷新：
  - 将此节写成「后续计划」或「可扩展方向」，不要假装已经完成。
- 若未来实现：
  - 明确说明“数据刷新为前端 mock，不是真实后端推送”。
  - 说明刷新间隔（如 5-30 秒）与刷新的模块（顶部指标、趋势图、动态列表等）。

## 项目结构

只写核心目录树，不要列 node_modules / dist / 大量无关内容：

```text
server-metrics-dashboard/
├── index.html                  # 交互式可视化大屏（单文件，无需构建）
├── process_data.py             # 数据清洗：.dat → JSON + 小时级聚合
├── generate_figures.py         # 生成 8 张图表 PNG（含 E-R 关系图）
├── generate_pdf.py             # 生成方案 A / 方案 B 两份 PDF
├── host_detail.dat / mod_detail.dat / disk_tsar.dat / pref_tsar.dat
│                               # 原始输入（.dat 为 tab 分隔文本）
├── output/
│   ├── host_detail.json        # 清洗后的主机维度
│   ├── mod_detail.json         # 清洗后的指标字典
│   ├── disk_tsar.json          # 清洗后的磁盘采集
│   ├── pref_tsar.json          # 清洗后的性能采集
│   ├── timestamp_samples.json  # 时间戳覆盖范围统计
│   ├── hourly_aggregation.json # 小时级聚合结果
│   ├── er_diagram.md / .json   # ER 关系图说明
│   └── figures/                # 图表 PNG（本地生成，不提交到仓库）
├── tsar_learning_report_A_dashboard.pdf
├── tsar_learning_report_B_analysis.pdf
├── LICENSE                     # MIT License
├── .gitignore                  # 忽略 PDF / figures / __pycache__ 等
└── README.md
```

## 快速开始

### 环境要求

- Python ≥ 3.8
- 依赖：`pandas`、`matplotlib`、`reportlab`

### 安装依赖

```bash
pip install pandas matplotlib reportlab
```

### 一键生成

```bash
# 1) 数据清洗 + 小时级聚合
python process_data.py

# 2) 生成 8 张图表 PNG
python generate_figures.py

# 3) 生成两份 PDF 报告
python generate_pdf.py
```

### 打开可视化大屏

```bash
# 用 Python 起一个本地 HTTP 服务
python -m http.server 8000

# 浏览器访问：
# http://127.0.0.1:8000/
```

> 也可以直接双击 `index.html` 用浏览器打开（需要网络以加载 ECharts CDN）。

## 常用命令

只写项目中实际存在的脚本。本项目当前仅包含 Python 脚本，没有 package.json：

- `python process_data.py`：清洗与聚合
- `python generate_figures.py`：生成图表 PNG
- `python generate_pdf.py`：生成 PDF 报告
- `python -m http.server 8000`：启动本地静态服务访问大屏

> 若后续引入 package.json（如把前端升级为 Vue 3 / Vite），再补充 `npm run dev / build / lint / test` 等命令。

## 数据源说明

- **当前**：默认使用项目根目录下 `.dat` 原始文件，经 `process_data.py` 清洗为 JSON，由 `index.html` 本地读取。
- **未来**：可通过环境变量（例如 `DATA_SOURCE=api`）或参数切换为后端接口，当前尚未实现。
- **E-R 关系图**：当前通过 index.html 中的自定义 SVG 绘制；也可参考 `output/er_diagram.md` 中的 Mermaid 源。

## 自动化截图

- 若项目中 **尚无** 自动化截图脚本（例如 `scripts/capture-dashboard.mjs` 或类似）：
  - 写成后续计划：「自动化截图脚本可基于 Playwright 实现，输出路径为 `docs/screenshots/dashboard-1920x1080.png`，目前暂未提供。」
- 若已有脚本：说明命令与输出路径（例如 `node scripts/capture-dashboard.mjs`，输出到指定目录）。

> 不要写 `npm run screenshot` 等不存在的命令。

## 测试与质量保障

- 代码质量工具：如果当前项目没有 ESLint / Prettier / Stylelint / Vitest / Playwright 等配置，请不要描述这些工具。
- 构建验证：本项目为单文件 HTML + Python 脚本，没有 build 步骤；`python process_data.py` 等脚本可作为过程验证。
- 若未来引入前端工程化，再补充 TypeScript 类型检查、单元测试、E2E 测试。

## 适合学习什么

面向学生 / 初学者，写一份清晰列表：

- 数据建模与 E-R 关系图设计（维度表 / 事实表的 1:N 关系）
- 毫秒级时间戳解析与时区处理
- 小时级聚合统计（avg / max / min / sample_count 的实现思路）
- 单文件 HTML + ECharts 的数据大屏布局
- 图表选型：折线图、柱状图、雷达图、箱线图的适用场景
- reportlab + matplotlib 自动生成 PDF 报告
- Python 脚本与前端 JSON 数据的分层结构

## 后续计划

只写尚未完成的内容，例如：

- 增加按主机切换的交互（下拉筛选 hostid）
- 增加告警阈值配置与高亮（如 CPU > 80%）
- 把 `.dat` 抽象为通用 CSV / JSON Loader，适配任意监控数据源
- 接入 Flask / FastAPI 等后端，提供 RESTful 指标接口
- 增加 Docker 化部署方案（Nginx + 静态文件 + Flask）
- 自动化截图脚本，输出 1920x1080 大屏快照
- 单元测试覆盖 process_data.py 的聚合函数

## License

本项目基于 **MIT License** 开源，详见 [LICENSE](LICENSE) 文件。
```

---

## 5. 品牌与命名规范

- 项目英文名称：`server-metrics-dashboard`
- 项目中文名称：服务器监控数据可视化大屏
- 在 README 标题与正文中可使用：`server-metrics-dashboard｜服务器监控数据可视化大屏`
- 项目描述可用：**教学型数据可视化大屏项目**
- 目标学习者画像：
  - 前端初学者（想学习 ECharts 数据可视化）
  - 数据建模 / 数据可视化学习者（想了解 E-R 图与时间序列分析）
  - 想了解数据大屏工程结构的学生
  - AI 辅助编程课堂案例（可作为“从原始数据到大屏”教学示例）
- **不要**写成商业产品官网，不要出现“生产级”、“企业级”、“世界领先”等夸张表达
- **不要**出现不严谨的经验年限描述

---

## 6. 命令与链接的准确性要求

### 6.1 关于 npm 与 package.json

- **当前项目没有** `package.json`、`scripts`、`npm run ...` 等概念。
- 因此 README 中 **不要**出现 `npm install`、`npm run dev`、`npm run build`、`npm run lint`、`npm run test`、`npm run screenshot` 等命令。
- 如果未来项目升级为 Vue 3 + Vite 等前端工程化结构，再补充对应命令。

### 6.2 关于端口

- 当前 Python 静态服务使用 **8000** 端口（`python -m http.server 8000`）
- 如果后续引入前端工程化服务（例如 Vite），可统一为 **10001** 端口，并在 README 中说明切换原因；当前仍以 8000 为主
- README 中所有命令必须经过实际运行验证，不可写虚假命令

### 6.3 关于 VITE_DATA_SOURCE 等环境变量

- 当前项目不存在 `VITE_*` 环境变量
- 不要写诸如 `VITE_DATA_SOURCE=api` 的启动方式，除非真的实现并验证过

### 6.4 关于截图引用

- 截图路径约定为：`docs/screenshots/dashboard-1920x1080.png`
- 编写 README 前先 **检查文件是否存在**；不存在就用文字说明，不要写假链接
- 若存在，则放在「项目预览」章节的顶部

### 6.5 关于 GitHub 链接

- 真实仓库地址：`https://github.com/junzhe456/server-metrics-dashboard`
- 只有验证可访问后才在 README 中写成链接；不要虚构“部署地址”、“在线 Demo”等

---

## 7. 内容风格要求

- 标题清晰，层级合理（建议 2-4 级标题）
- 每节内容不要太长，控制读屏节奏
- 重要命令使用代码块包裹（```bash / ```text）
- 说明要准确，不要混淆 mock / 离线数据与真实后端
- 语言自然，不要“AI 味”太重；不要把提示词内容复制进 README
- 可以适量使用 emoji，但不要求；可用可不用
- 不要写“本项目由 AI 自动生成”等内容作为卖点
- 不要把提示词里的章节直接粘贴进 README
- README 要像一个可以公开给学生阅读的项目说明

---

## 8. 完成后的验证步骤

编写 / 修改 README 后，请至少完成以下验证：

### 8.1 静态页面验证

```bash
python process_data.py
python generate_figures.py
python generate_pdf.py
python -m http.server 8000
```

浏览器打开 `http://127.0.0.1:8000/`，确认：
- 页面加载正常，没有报错
- E-R 关系图正常显示（4 张表格 + 关系连线）
- 所有图表正常渲染
- 主机汇总表有数据

### 8.2 README 文本验证

- 检查 README 中出现的所有命令都能实际运行
- 检查所有提到的文件路径确实存在（或在 .gitignore 中显式标注为“本地生成”）
- 检查链接是否可跳转，图片引用是否真实存在
- 检查是否有拼写错误、错别字、中英文混排格式问题

### 8.3 仓库大小检查

- `*.pdf`、`output/figures/*.png` 应通过 `.gitignore` 排除，不要提交到仓库
- 确认 `git status` 仅显示源码与必要的文本/JSON 文件

---

## 9. 最终交付清单

完成 README 编写与验证后，整理一份简要说明，包含：

- README 修改了哪些主要内容（列出关键章节）
- 是否引用了项目截图（docs/screenshots/dashboard-1920x1080.png）
- 如果没有引用截图，原因是什么（如“当前项目尚未生成截图文件”）
- README 中写了哪些可用命令（与项目实际脚本对应）
- 开发服务端口是否已确认（当前为 8000；若改为 10001 则需说明）
- 已运行的验证命令与结果（process_data.py / generate_figures.py / generate_pdf.py / HTTP server 访问是否成功）
- 是否存在未完成事项（如自动化截图、后端 API、Docker 化等）

---

## 10. 参考材料（编写者内部参考，不要放进 README）

- `index.html`：真实页面模块
- `process_data.py`、`generate_figures.py`、`generate_pdf.py`：数据到图表到报告的完整流程
- `output/*.json`：数据结构
- `LICENSE`：MIT License
- `.gitignore`：确认哪些文件不应该在 README 中被当作“已上传”的东西
- GitHub 仓库地址：<https://github.com/junzhe456/server-metrics-dashboard>

> 提示：本提示词文件位于 `docs/提示词/`，供内部参考使用，不应被粘贴进 README.md 中。
