# server-metrics-dashboard｜服务器监控数据可视化大屏

一个面向教学用途的数据中心运行监控大屏：从 4 份原始 Tsar 采集数据出发，完成 E-R 关系建模、时间戳清洗、小时级指标聚合，通过 Flask 后端提供 REST API，最终形成 PC 端与移动端两份可交互的可视化大屏，并支持自动生成 PDF 报告。

---

## 项目预览

项目大屏截图可通过浏览器访问后手动截取，约定路径为 `docs/screenshots/dashboard-1920x1080.png`，目前尚未生成自动化截图脚本。

---

## 项目简介

**server-metrics-dashboard**（中文名：服务器监控数据可视化大屏）把一组散乱的服务器运行指标（CPU / 网络 / 磁盘 / 内存 / 采样数）整理成结构化的数据库表与 JSON，并通过 Flask 提供的 REST API 动态读取，最终用 ECharts 渲染成可交互的 PC 端大屏与移动端适配页面，同时提供两份 PDF 报告供审阅。

本项目主要用于 **数据建模与数据可视化课程实践作业**，作为教学案例帮助学习者：

- 理解维度表（主机、指标）与事实表（磁盘采集、性能采集）之间的 1:N 关联
- 把毫秒级时间戳转换为本地时区的年月日时分，并按小时槽位做聚合
- 使用 SQLAlchemy ORM 设计数据模型，将 .dat 原始数据写入 MySQL / SQLite
- 通过 Flask 提供 REST API，前后端分离式地驱动前端大屏
- 使用 ECharts + 原生 HTML / CSS / JavaScript 制作单文件数据大屏（PC + 移动端）
- 使用 reportlab + matplotlib 自动生成正式报告

---

## 核心特性

- **前后端分离架构**：前端 `index.html` / `mobile.html` 从 Flask API 动态获取数据，而非读取本地 JSON
- **数据库接入**：SQLAlchemy ORM 模型 + MySQL 优先 / SQLite 自动兜底的双支持
- **ETL 能力**：内置 `backend/utils/etl.py`，可一键将 4 份 .dat 原始数据写入数据库
- **Flask REST API**：提供健康检查、主机列表、指标字典、原始数据查询、大屏汇总等接口
- **单文件 PC 端大屏**：`index.html` 无需构建，包含 E-R 关系图与 7 个图表模块
- **移动端适配大屏**：`mobile.html` 单列卡片式布局，自适应手机屏幕宽度
- **毫秒时间戳解析**：到 `YYYY-MM-DD HH:mm`，并给出小时槽位与时区覆盖范围
- **小时级聚合**：按 `(hostid, hour_slot, mod)` 聚合计算 `avg / max / min / sample_count`
- **多图表类型**：ECharts 折线图、柱状图、雷达图、箱线图的代码示例集中在同一项目
- **两份 PDF 报告**：方案 A（图表优先版）与方案 B（正式分析报告版），中文字体正常渲染

---

## 技术栈

- **数据清洗与聚合**：Python 3（标准库）
- **后端框架**：Flask + Flask-CORS
- **ORM / 数据库**：SQLAlchemy 2.x + MySQL（pymysql）/ SQLite 3
- **前端实现**：原生 HTML / CSS / JavaScript（单文件大屏，无需构建）
- **图表渲染**：ECharts（通过 CDN 加载）
- **报告输出**：reportlab + matplotlib
- **关系图实现**：页面内原生 SVG 绘制（表格化实体 + 箭头连线）
- **代码版本管理**：Git / GitHub

> 注意：本项目 **不是** Vue 3 / Vite / TypeScript 项目，不要套用这些关键字。

---

## 数据模型（E-R 关系）

项目核心包含 4 张相互关联的表，在 `backend/models.py` 中定义为 SQLAlchemy ORM 模型：

- **HOST_DETAIL**（主机维度表）：`hostid`, `hostname`, `location1`, `location2`, `model`, `owner`
- **MOD_DETAIL**（指标维度表）：`mod`（指标名），`metric_unit`（可选单位）
- **DISK_TSAR**（磁盘采集事实表）：`hostid` → HOST_DETAIL，`ts`（毫秒时间戳），`disk_read`, `disk_write`, `sda_util`, `sdb_util`
- **PREF_TSAR**（性能采集事实表）：`hostid` → HOST_DETAIL，`mod` → MOD_DETAIL，`ts`，`cpu_user`, `cpu_system`, `cpu_idle`, `mem_used`, `net_in`, `net_out` 等指标值

一对多关系：`HOST_DETAIL : DISK_TSAR = 1:N`，`HOST_DETAIL : PREF_TSAR = 1:N`，`MOD_DETAIL : PREF_TSAR = 1:N`。

---

## 大屏模块

### PC 端 `index.html`

- 顶部标题与数据源说明
- E-R 关系图（4 张表格化实体 + 1:N 关系连线）
- 时间戳解析表（原始毫秒 → Beijing 时区 → 小时槽位）
- CPU 使用率 / 空闲率折线图
- 网络入 / 出带宽折线图
- 磁盘 sda / sdb 使用率折线图
- 内存已用柱状图
- 关键指标 Max / Avg 雷达图
- 每小时采样数柱状图
- 机房分组箱线图
- 主机汇总表

### 移动端 `mobile.html`

- 顶部标题与 KPI 数值卡片（主机数、指标数、磁盘记录数、性能记录数、小时覆盖范围、聚合记录数）
- 时间戳解析表
- CPU 折线图
- 网络折线图
- 磁盘折线图
- 内存柱状图
- 雷达图
- 采样数柱状图
- 箱线图
- 主机汇总表

---

## 实时数据模拟

当前大屏通过 Flask API 从数据库读取静态历史数据，**没有**做定时刷新。可把"实时数据模拟"作为后续扩展：

- 在 Flask 后端增加模拟数据写入接口，或在前端通过 `setInterval` 对部分模块做扰动刷新
- 若实现，需明确标注"这是前端 mock，不是真实后端推送"
- 设定合理的刷新间隔（如 5–30 秒），避免过度抖动

目前该能力尚未实现，因此不在"已完成功能"内。

---

## 项目结构

```text
server-metrics-dashboard/
├── index.html                  # PC 端交互式可视化大屏（从 Flask API 读取数据）
├── mobile.html                 # 移动端适配大屏（从 Flask API 读取数据）
│
├── process_data.py             # 数据清洗：.dat → JSON + 小时级聚合
├── generate_figures.py         # 生成 8 张图表 PNG（含 E-R 关系图）
├── generate_pdf.py             # 生成方案 A / 方案 B 两份 PDF
│
├── host_detail.dat             # 原始输入：主机信息维度表
├── mod_detail.dat              # 原始输入：指标字典
├── disk_tsar.dat               # 原始输入：磁盘采集
├── pref_tsar.dat               # 原始输入：性能采集
├── query_results_sample.txt    # 查询结果示例
│
├── backend/                    # Flask 后端
│   ├── app.py                  #   Flask 应用入口与 REST API
│   ├── config.py               #   数据库配置（MySQL 优先，SQLite 兜底）
│   ├── models.py               #   SQLAlchemy ORM 模型
│   ├── requirements.txt        #   Python 依赖清单
│   └── utils/
│       └── etl.py              #   ETL：.dat 文件 → 数据库
│
├── output/                     # process_data.py 的产物（本地生成，已提交 JSON）
│   ├── host_detail.json        #   清洗后的主机维度
│   ├── mod_detail.json         #   清洗后的指标字典
│   ├── disk_tsar.json          #   清洗后的磁盘采集
│   ├── pref_tsar.json          #   清洗后的性能采集
│   ├── timestamp_samples.json  #   时间戳覆盖范围统计
│   ├── hourly_aggregation.json #   小时级聚合结果
│   ├── er_diagram.md           #   ER 关系图（Mermaid 源）
│   ├── er_diagram.json         #   ER 关系图（JSON 描述）
│   └── figures/                #   图表 PNG（本地生成，不提交到仓库）
│
├── docs/
│   └── 提示词/                 # 项目写作与维护提示词（README 等，内部参考）
│
├── LICENSE                     # MIT License
├── .gitignore                  # 忽略 PDF / figures / *.db / *.log / __pycache__ 等
└── README.md
```

> 说明：`tsar_learning_report_A_dashboard.pdf` 与 `tsar_learning_report_B_analysis.pdf` 为本地生成的 PDF 报告，通过 `.gitignore` 排除，不提交到仓库。可运行 `python generate_pdf.py` 在本地生成。`server_metrics.db` 为本地 SQLite 数据库文件，同样不提交。

---

## 快速开始

### 环境要求

- Python ≥ 3.8
- 后端依赖：`flask`, `flask-cors`, `sqlalchemy`
- 可选数据库：MySQL 5.7+（推荐），若不可用自动降级到 SQLite 3
- 生成图表与 PDF 的可选依赖：`pandas`, `matplotlib`, `reportlab`

### 安装后端依赖

```bash
pip install flask flask-cors sqlalchemy pymysql

# 可选：用于生成图表 PNG 和 PDF 报告
pip install pandas matplotlib reportlab
```

也可使用后端目录的 `requirements.txt`：

```bash
pip install -r backend/requirements.txt
```

### 启动后端 Flask API（必须先启动，前后端分离架构）

```bash
cd backend
python app.py
```

启动后 Flask 会在 `http://127.0.0.1:5001/` 提供 REST API。首次启动时会自动：

1. 尝试连接 MySQL（配置在 `backend/config.py` 中，默认主机 `127.0.0.1`，端口 `3306`，数据库名 `server_metrics`，用户名 `root`）
2. 若 MySQL 不可用，自动降级到 SQLite，使用根目录下的 `server_metrics.db`
3. 创建 4 张表（host_detail, mod_detail, disk_tsar, pref_tsar）
4. 自动运行 ETL，将根目录下 4 份 .dat 文件写入数据库

API 接口示例：

- `GET /health` — 健康检查，返回数据库引擎与记录数
- `GET /hosts` — 主机列表（host_detail）
- `GET /metrics` — 指标字典（mod_detail）
- `GET /data?hostid=xxx&mod=yyy&limit=100` — 原始指标数据（pref_tsar）
- `GET /dashboard/summary` — 大屏汇总数据（KPI + 小时聚合 + 箱线图分组 + 雷达图 + 主机汇总）
- `POST /etl` — 手动触发 ETL 重新写入

### 启动前端静态服务并访问大屏

```bash
# 在项目根目录（而非 backend 目录）执行
cd ..
python -m http.server 8000
```

然后用浏览器访问：

- **PC 端大屏**：`http://127.0.0.1:8000/index.html`
- **移动端大屏**：`http://127.0.0.1:8000/mobile.html`

> 也可以直接双击 `index.html` / `mobile.html` 用浏览器打开（需要网络以加载 ECharts CDN；需要 Flask 后端运行以获取动态数据）。

### 一键生成图表与 PDF 报告

```bash
# 1) 数据清洗 + 小时级聚合（也可跳过，Flask 后端直接读取 .dat）
python process_data.py

# 2) 生成 8 张图表 PNG（输出到 output/figures/）
python generate_figures.py

# 3) 生成两份 PDF 报告
python generate_pdf.py
```

生成后在项目根目录查看：

- `output/figures/` — 8 张 PNG 图表
- `tsar_learning_report_A_dashboard.pdf` — 方案 A：图表优先版
- `tsar_learning_report_B_analysis.pdf` — 方案 B：正式分析报告版

> PDF 与 PNG 文件已通过 `.gitignore` 排除，不会被提交到仓库。

---

## 常用命令

当前项目以 Python 脚本与原生 HTML 组织，**尚未**使用 `package.json`。可用命令如下：

- `cd backend && python app.py`：启动 Flask 后端 API（端口 5001）
- `python process_data.py`：清洗 .dat → output/*.json，并完成小时级聚合
- `python generate_figures.py`：生成图表 PNG（含 E-R 关系图）
- `python generate_pdf.py`：生成方案 A、方案 B 两份 PDF
- `python -m http.server 8000`：启动本地静态服务访问大屏（端口 8000）

> 注意：`8000` 是 Python 静态服务端口，`5001` 是 Flask 后端端口，两者互不冲突。如果后续引入前端工程化（如 Vite），可统一开发服务端口到 `10001` 并在 README 中说明切换原因。

---

## 数据源说明

- **当前默认方案（推荐）**：`.dat` 原始数据 → Flask ETL 写入数据库 → Flask REST API → `index.html` / `mobile.html` ECharts 渲染
- **替代方案**：`.dat` → `process_data.py` 清洗为 `output/*.json` → `index.html` 直接读取 JSON（需修改前端脚本的 fetch URL 为本地文件路径）
- **E-R 关系图**：在页面中以自定义 SVG 绘制；也可参考 `output/er_diagram.md` 中的 Mermaid 源
- **数据库选择**：MySQL 为推荐方案，若 MySQL 不可用，Flask 启动时自动降级到 SQLite（`server_metrics.db`，单文件数据库）
- **未来可扩展**：通过环境变量（例如 `DATABASE_URL`）配置数据库连接串，或切换到 PostgreSQL

---

## 自动化截图

本项目当前**尚未**提供自动化截图脚本。后续可基于 Playwright 实现，约定输出路径：

```text
docs/screenshots/dashboard-1920x1080.png
```

在脚本落地前，README 中不出现 `npm run screenshot` 或类似命令，避免误导。

---

## 测试与质量保障

- 当前项目为单文件 HTML + Flask 后端 + Python 脚本，没有 TypeScript / ESLint / Prettier / Stylelint / Vitest / Playwright 配置
- 作为过程验证，可依次执行：`cd backend && python app.py`（验证后端 API）、浏览器打开大屏（验证前端渲染）、`python process_data.py` / `python generate_figures.py` / `python generate_pdf.py`（验证数据处理与报告输出）
- 若后续引入前端工程化或后端模块测试框架，可补充单元测试、类型检查与 E2E 测试

---

## 适合学习什么

本项目适合作为以下主题的教学案例：

- 数据建模与 E-R 关系图设计：维度表 / 事实表的 1:N 关系
- 毫秒级时间戳解析与时区处理（Beijing 时区的日期运算）
- 小时级聚合统计（avg / max / min / sample_count 的实现思路）
- Flask 后端 + SQLAlchemy ORM 的基础数据服务设计
- 前后端分离：前端 fetch REST API，后端 JSON 响应
- 移动端适配：如何在单文件 HTML 中通过 CSS 媒体查询适配手机屏幕
- 单文件 HTML + ECharts 的数据大屏布局
- 图表选型：折线图、柱状图、雷达图、箱线图的适用场景
- reportlab + matplotlib 自动生成 PDF 报告（含中文排版）

---

## 后续计划

以下为尚未完成、欢迎后续迭代的方向：

- 新增按主机切换的交互（在大屏顶部下拉选择 hostid，图表实时切换数据源）
- 增加告警阈值配置与高亮（如 CPU 使用率 > 80%，在对应时间点红色标记）
- 把 `.dat` 抽象为通用 CSV / JSON Loader，适配任意监控数据源
- 实现 Docker 化部署方案（Nginx 托管静态文件 + Flask 容器）
- 自动化截图脚本，输出 1920×1080 大屏快照
- 单元测试覆盖 `process_data.py` 的聚合函数与 `backend/utils/etl.py` 的 ETL 流程
- 将 Flask 升级为 FastAPI，获得自动生成的 OpenAPI / Swagger 文档

---

## License

本项目基于 **MIT License** 开源，详见 [LICENSE](LICENSE) 文件。
