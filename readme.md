# server-metrics-dashboard｜服务器监控数据可视化大屏

一个面向教学用途的数据中心运行监控大屏：从 4 份原始 Tsar 采集数据出发，完成 E-R 关系建模、时间戳清洗、小时级指标聚合，最终形成可交互的可视化大屏与两份 PDF 报告。

## 项目预览

项目大屏截图可通过浏览器访问后手动截取，约定路径为 `docs/screenshots/dashboard-1920x1080.png`，目前尚未生成，暂不引用不存在的图片。

## 项目简介

**server-metrics-dashboard**（中文名：服务器监控数据可视化大屏）把一组散乱的服务器运行指标（CPU / 网络 / 磁盘 / 内存 / 采样数）整理成结构化的 JSON，并通过 ECharts 渲染成可交互的可视化大屏，同时提供两份 PDF 报告供审阅。

本项目主要用于 **数据建模与数据可视化课程实践作业**，作为教学案例帮助学习者：

- 理解维度表（主机、指标）与事实表（磁盘采集、性能采集）之间的 1:N 关联
- 把毫秒级时间戳转换为本地时区的年月日时分，并按小时槽位做聚合
- 对每一组 `(hostid, hour_slot, mod)` 计算 `avg / max / min / sample_count`
- 使用 ECharts + 原生 HTML / CSS / JavaScript 制作单文件数据大屏
- 使用 reportlab + matplotlib 自动生成正式报告

## 核心特性

- 单文件 `index.html` 实现可交互大屏，无需构建步骤即可运行
- 4 张表的 E-R 关系建模，并在页面内以表格化实体 + 关系连线展示
- 毫秒时间戳解析到 `YYYY-MM-DD HH:mm`，并给出小时槽位统计
- 按小时聚合计算 `avg / max / min / sample_count`，代码结构便于学生阅读与改造
- ECharts 折线图、柱状图、雷达图、箱线图的代码示例集中在同一文件
- 两份 PDF 报告：方案 A（图表优先版）与方案 B（正式分析报告版）
- 源码与清洗后 JSON 均提交到仓库，便于复现、修改和扩展

## 技术栈

- 数据清洗与聚合：Python 3（标准库，可选使用 pandas）
- 图表渲染：ECharts（通过 CDN 加载）
- 前端实现：原生 HTML / CSS / JavaScript（单文件大屏）
- 报告输出：reportlab + matplotlib
- 关系图实现：页面内原生 SVG 绘制（表格化实体 + 箭头连线）
- 代码版本管理：Git / GitHub

## 页面内容（大屏模块）

`index.html` 当前包含以下模块：

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

当前大屏读取的是静态 JSON，**没有**做定时刷新。可把“实时数据模拟”作为后续扩展：

- 在前端通过 `setInterval` 对部分模块做随机扰动刷新
- 明确标注“这是前端 mock，不是真实后端推送”
- 设定合理的刷新间隔（如 5–30 秒），避免过度抖动

目前该能力尚未实现，因此不在“已完成功能”内。

## 项目结构

```text
server-metrics-dashboard/
├── index.html                  # 交互式可视化大屏（单文件，无需构建）
├── process_data.py             # 数据清洗：.dat → JSON + 小时级聚合
├── generate_figures.py         # 生成 8 张图表 PNG（含 E-R 关系图）
├── generate_pdf.py             # 生成方案 A / 方案 B 两份 PDF
│
├── host_detail.dat             # 原始输入：主机信息维度表
├── mod_detail.dat              # 原始输入：指标字典
├── disk_tsar.dat               # 原始输入：磁盘采集
├── pref_tsar.dat               # 原始输入：性能采集
│
├── output/
│   ├── host_detail.json        # 清洗后的主机维度
│   ├── mod_detail.json         # 清洗后的指标字典
│   ├── disk_tsar.json          # 清洗后的磁盘采集
│   ├── pref_tsar.json          # 清洗后的性能采集
│   ├── timestamp_samples.json  # 时间戳覆盖范围统计
│   ├── hourly_aggregation.json # 小时级聚合结果
│   ├── er_diagram.md           # ER 关系图（Mermaid 源）
│   ├── er_diagram.json         # ER 关系图（JSON 描述）
│   └── figures/                # 图表 PNG（本地生成，不提交到仓库）
│
├── tsar_learning_report_A_dashboard.pdf  # 方案 A：图表优先版
├── tsar_learning_report_B_analysis.pdf   # 方案 B：正式分析报告版
│
├── docs/
│   └── 提示词/                 # 项目写作与维护提示词（README 等）
│
├── LICENSE                     # MIT License
├── .gitignore                  # 忽略 PDF / figures / __pycache__ 等
└── README.md
```

## 快速开始

### 环境要求

- Python ≥ 3.8
- 可选依赖：`pandas`、`matplotlib`、`reportlab`（用于生成图表与 PDF）

### 安装可选依赖

```bash
pip install pandas matplotlib reportlab
```

### 一键生成 JSON 与图表

```bash
# 1) 数据清洗 + 小时级聚合
python process_data.py

# 2) 生成 8 张图表 PNG（输出到 output/figures/）
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

也可以直接双击 `index.html` 用浏览器打开（需要网络以加载 ECharts CDN）。

## 常用命令

当前项目以 Python 脚本与原生 HTML 组织，**尚未**使用 `package.json`。可用命令如下：

- `python process_data.py`：清洗 .dat → output/*.json，并完成小时级聚合
- `python generate_figures.py`：生成图表 PNG（含 E-R 关系图）
- `python generate_pdf.py`：生成方案 A、方案 B 两份 PDF
- `python -m http.server 8000`：启动本地静态服务访问大屏

若后续引入 Vue 3 / Vite 等前端工程化，再补充 `npm run dev / build / lint / test` 等命令。

## 数据源说明

- 当前默认使用项目根目录下 `.dat` 原始文件，经 `process_data.py` 清洗为 JSON，由 `index.html` 本地读取。
- E-R 关系图在页面中以自定义 SVG 绘制；也可参考 `output/er_diagram.md` 中的 Mermaid 源。
- 未来可通过环境变量或参数切换为后端接口（如 Flask / FastAPI），目前尚未实现。

## 自动化截图

本项目当前**尚未**提供自动化截图脚本。后续可基于 Playwright 实现，约定输出路径：

```text
docs/screenshots/dashboard-1920x1080.png
```

在脚本落地前，README 中不出现 `npm run screenshot` 或类似命令，避免误导。

## 测试与质量保障

- 当前项目为单文件 HTML + Python 脚本，没有 TypeScript / ESLint / Prettier / Stylelint / Vitest / Playwright 配置。
- 作为过程验证，可执行 `python process_data.py`、`python generate_figures.py`、`python generate_pdf.py` 并访问大屏确认渲染正常。
- 若后续引入前端工程化或后端模块，再补充单元测试、类型检查与 E2E 测试。

## 适合学习什么

本项目适合作为以下主题的教学案例：

- 数据建模与 E-R 关系图设计：维度表 / 事实表的 1:N 关系
- 毫秒级时间戳解析与时区处理
- 小时级聚合统计（avg / max / min / sample_count 的实现思路）
- 单文件 HTML + ECharts 的数据大屏布局
- 图表选型：折线图、柱状图、雷达图、箱线图的适用场景
- reportlab + matplotlib 自动生成 PDF 报告
- Python 脚本与前端 JSON 数据的分层结构

## 后续计划

以下为尚未完成、欢迎后续迭代的方向：

- 新增按主机切换的交互（下拉选择 hostid，图表实时切换）
- 增加告警阈值配置与高亮（如 CPU > 80%）
- 把 `.dat` 抽象为通用 CSV / JSON Loader，适配任意监控数据源
- 接入 Flask / FastAPI 等后端，提供 RESTful 指标接口
- 增加 Docker 化部署方案（Nginx + 静态文件 + Flask）
- 自动化截图脚本，输出 1920x1080 大屏快照
- 单元测试覆盖 process_data.py 的聚合函数

## License

本项目基于 MIT License 开源，详见 [LICENSE](LICENSE) 文件。
