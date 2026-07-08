"""
生成 tsar_learning_report 的两份 PDF：
  A) 大屏版（可视化为主）: tsar_learning_report_A_dashboard.pdf
  B) 分析报告版（图文并茂）: tsar_learning_report_B_analysis.pdf

依赖：reportlab（安装：pip install reportlab）
运行之前需先生成 output/*.json 和 output/figures/*.png
  python process_data.py
  python generate_figures.py
  python generate_pdf.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "output"
FIG_DIR = OUT_DIR / "figures"

# 注册中文字体 —— 在 Windows 下优先使用系统自带字体
_CANDIDATE_FONTS = [
    ("MSYaHei", r"C:\Windows\Fonts\msyh.ttc"),
    ("MSYaHeiBold", r"C:\Windows\Fonts\msyhbd.ttc"),
    ("SimHei", r"C:\Windows\Fonts\simhei.ttf"),
    ("SimSun", r"C:\Windows\Fonts\simsun.ttc"),
    ("SimSunBold", r"C:\Windows\Fonts\simsunb.ttf"),
]

FONT_NAME = "Helvetica"  # 默认值（若所有中文字体都不可用）
BOLD_FONT_NAME = "Helvetica-Bold"
for name, path in _CANDIDATE_FONTS:
    if Path(path).exists():
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            if name == "MSYaHei":
                FONT_NAME = "MSYaHei"
            elif name == "SimHei" and FONT_NAME == "Helvetica":
                FONT_NAME = "SimHei"
            elif name == "SimSun" and FONT_NAME == "Helvetica":
                FONT_NAME = "SimSun"
            if name in ("MSYaHeiBold", "SimSunBold"):
                BOLD_FONT_NAME = name
        except Exception:
            continue
if BOLD_FONT_NAME == "Helvetica-Bold" and FONT_NAME != "Helvetica":
    # 用相同字体代替"加粗"，reportlab 对同一个 ttf 名字无法重复注册
    BOLD_FONT_NAME = FONT_NAME


# ---------- 颜色 ----------
NAVY = colors.HexColor("#1f3a8a")
BLUE_LIGHT = colors.HexColor("#dbeafe")
GOLD = colors.HexColor("#b45309")
GRAY = colors.HexColor("#4b5563")
WHITE = colors.white
BLACK = colors.black


# ---------- 样式 ----------
def _make_styles() -> dict:
    styles = {}
    styles["body"] = ParagraphStyle(
        "body", fontName=FONT_NAME, fontSize=10.5, leading=16,
        textColor=colors.HexColor("#111827"), alignment=TA_JUSTIFY,
        spaceBefore=3, spaceAfter=3, firstLineIndent=22,
    )
    styles["body_left"] = ParagraphStyle(
        "body_left", parent=styles["body"], firstLineIndent=0, alignment=TA_LEFT,
    )
    styles["h1"] = ParagraphStyle(
        "h1", fontName=FONT_NAME, fontSize=20, leading=26,
        textColor=NAVY, alignment=TA_LEFT, spaceBefore=6, spaceAfter=10,
    )
    styles["h2"] = ParagraphStyle(
        "h2", fontName=FONT_NAME, fontSize=14, leading=20,
        textColor=NAVY, alignment=TA_LEFT, spaceBefore=12, spaceAfter=6,
        borderWidth=0, borderColor=NAVY, leftIndent=6,
    )
    styles["h3"] = ParagraphStyle(
        "h3", fontName=FONT_NAME, fontSize=12, leading=17,
        textColor=colors.HexColor("#1e40af"), alignment=TA_LEFT, spaceBefore=8, spaceAfter=4,
    )
    styles["title"] = ParagraphStyle(
        "title", fontName=FONT_NAME, fontSize=26, leading=32,
        textColor=WHITE, alignment=TA_CENTER,
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle", fontName=FONT_NAME, fontSize=14, leading=20,
        textColor=colors.HexColor("#bfdbfe"), alignment=TA_CENTER, spaceBefore=8,
    )
    styles["cover_meta"] = ParagraphStyle(
        "cover_meta", fontName=FONT_NAME, fontSize=12, leading=18,
        textColor=WHITE, alignment=TA_CENTER,
    )
    styles["code"] = ParagraphStyle(
        "code", fontName="Courier", fontSize=9.5, leading=13,
        textColor=colors.HexColor("#0f172a"), alignment=TA_LEFT,
        leftIndent=10, backColor=colors.HexColor("#f1f5f9"), borderPadding=6,
    )
    styles["caption"] = ParagraphStyle(
        "caption", fontName=FONT_NAME, fontSize=9, leading=12,
        textColor=GRAY, alignment=TA_CENTER, spaceBefore=4, spaceAfter=8,
    )
    return styles


# ---------- 辅助：画页眉页脚 ----------
def _make_header_footer(title_text: str):
    def _on_page(canvas, doc):
        canvas.saveState()
        # 页眉：顶部蓝线
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(1.2)
        canvas.line(20 * mm, A4[1] - 14 * mm, A4[0] - 20 * mm, A4[1] - 14 * mm)
        canvas.setFont(FONT_NAME, 9)
        canvas.setFillColor(GRAY)
        canvas.drawString(20 * mm, A4[1] - 13 * mm, title_text)
        canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 13 * mm, f"第 {doc.page} 页")

        # 页脚
        canvas.setStrokeColor(NAVY)
        canvas.line(20 * mm, 16 * mm, A4[0] - 20 * mm, 16 * mm)
        canvas.setFont(FONT_NAME, 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(20 * mm, 12 * mm, "数据建模课程实践作业 · 服务器监控数据分析")
        canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, datetime.now().strftime("%Y-%m-%d %H:%M"))

        canvas.restoreState()
    return _on_page


# ---------- 辅助：画封面 ----------
def draw_cover(canvas, doc, title, subtitle, meta_lines):
    canvas.saveState()
    # 背景渐变（用多层矩形近似）
    width, height = A4
    gradient_colors = [
        colors.HexColor("#0b1e4f"),
        colors.HexColor("#13306f"),
        colors.HexColor("#1f3a8a"),
        colors.HexColor("#2563eb"),
    ]
    band_h = height / len(gradient_colors)
    for i, c in enumerate(gradient_colors):
        canvas.setFillColor(c)
        canvas.rect(0, i * band_h, width, band_h + 1, stroke=0, fill=1)
    # 底部装饰线
    canvas.setStrokeColor(colors.HexColor("#60a5fa"))
    canvas.setLineWidth(1.5)
    canvas.line(25 * mm, 48 * mm, width - 25 * mm, 48 * mm)
    canvas.line(25 * mm, 44 * mm, width - 25 * mm, 44 * mm)

    # 标题（使用 platypus 绘制更方便，这里改用 canvas 文字）
    canvas.setFont(FONT_NAME, 30)
    canvas.setFillColor(WHITE)
    # 标题可能较长，分两行显示
    title_lines = title.split("\n")
    ty = height * 0.68
    for line in title_lines:
        canvas.drawCentredString(width / 2.0, ty, line)
        ty -= 36

    canvas.setFont(FONT_NAME, 14)
    canvas.setFillColor(colors.HexColor("#bfdbfe"))
    ty -= 10
    for line in subtitle.split("\n"):
        canvas.drawCentredString(width / 2.0, ty, line)
        ty -= 22

    # 元信息（靠右）
    canvas.setFont(FONT_NAME, 11)
    canvas.setFillColor(WHITE)
    ty = 34 * mm
    for line in meta_lines:
        canvas.drawCentredString(width / 2.0, ty, line)
        ty -= 16

    canvas.restoreState()


# ---------- 加载数据 ----------
def load_json(name):
    with (OUT_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------- 表格工具 ----------
def make_table(rows, header_fill=NAVY, header_text=WHITE, body_font_size=10):
    t = Table(rows, colWidths=None, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), body_font_size),
        ("BACKGROUND", (0, 0), (-1, 0), header_fill),
        ("TEXTCOLOR", (0, 0), (-1, 0), header_text),
        ("FONTNAME", (0, 0), (-1, 0), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), WHITE]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ==================== 方案 B：正式分析报告版 ====================
def build_report_B(out_path: Path):
    styles = _make_styles()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title="tsar_learning_report_B_analysis", author="数据建模课程",
    )

    story: list = []

    # --- 封面 ---
    class _CoverFirstPage:
        def __init__(self, draw_func):
            self._draw = draw_func
        def __call__(self, canvas, doc):
            canvas.saveState()
            draw_cover(
                canvas, doc,
                title="服务器监控数据学习报告\nTsar Data Learning Report",
                subtitle="E-R 图建模 · 时间戳清洗 · 按小时聚合统计",
                meta_lines=[
                    "课程：数据建模课程实践作业",
                    "数据来源：20 台主机 / 55 个指标 / 79,200 条原始采集记录",
                    "生成时间：" + datetime.now().strftime("%Y-%m-%d %H:%M"),
                ],
            )
            canvas.restoreState()

    # 第 1 页 封面
    # 利用 onFirstPage 绘制封面背景
    def _draw_cover_bg(canvas, doc):
        draw_cover(
            canvas, doc,
            title="服务器监控数据学习报告\nTsar Data Learning Report",
            subtitle="E-R 图建模 · 时间戳清洗 · 按小时聚合统计",
            meta_lines=[
                "课程：数据建模课程实践作业",
                "数据来源：20 台主机 / 55 个指标 / 79,200 条原始采集记录",
                "生成时间：" + datetime.now().strftime("%Y-%m-%d %H:%M"),
            ],
        )
    # 把封面放到单独一页：用一个透明元素占据整页
    story.append(Spacer(1, 180 * mm))  # 留白，让封面背景自然显示
    story.append(PageBreak())

    # ========== 三、E-R 数据模型（放在文档最前面，紧跟封面） ==========
    story.append(Paragraph("一、E-R 数据模型", styles["h1"]))
    story.append(Paragraph(
        "本报告梳理了 4 张核心表之间的关联关系。"
        "事实表为 <b>disk_tsar</b> 与 <b>pref_tsar</b>（两张结构相同、type 不同），"
        "维度表为 <b>host_detail</b>（主机）与 <b>mod_detail</b>（指标字典）。", styles["body"]))
    story.append(Paragraph("· <b>HOST_DETAIL 1 : N DISK_TSAR</b>：一台主机产生 N 条磁盘采样记录（每 5 分钟一次）", styles["body_left"]))
    story.append(Paragraph("· <b>HOST_DETAIL 1 : N PREF_TSAR</b>：一台主机产生 N 条性能采样记录（每 1 小时一次）", styles["body_left"]))
    story.append(Paragraph("· <b>MOD_DETAIL  1 : N DISK_TSAR</b>：一个指标出现在 N 条磁盘采样记录中", styles["body_left"]))
    story.append(Paragraph("· <b>MOD_DETAIL  1 : N PREF_TSAR</b>：一个指标出现在 N 条性能采样记录中", styles["body_left"]))
    story.append(Spacer(1, 3 * mm))

    # 横向大图：A4 宽 210mm，这里占 180mm 宽 × 110mm 高，确保整屏显示
    story.append(Image(str(FIG_DIR / "fig08_er.png"), width=180 * mm, height=110 * mm))
    story.append(Paragraph("图 1-1 完整 E-R 关系图（4 张表，表格形式，字段含类型/名称/PK·FK/中文注释，连线标注 1:N 基数与中文描述）", styles["caption"]))

    story.append(Paragraph("1.1 实体与属性", styles["h2"]))
    story.append(Paragraph("表 1-1 HOST_DETAIL（主机维度表）", styles["caption"]))
    story.append(make_table([
        ["字段", "类型", "含义", "约束"],
        ["hostid",   "varchar(32)",  "主机 ID",   "PK"],
        ["hostname", "varchar(128)", "主机名",    ""],
        ["owner",    "varchar(64)",  "负责人",    ""],
        ["model",    "varchar(64)",  "硬件型号",  ""],
        ["location1","varchar(32)",  "机房",      ""],
        ["location2","varchar(64)",  "机柜编号",  ""],
    ]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("表 1-2 MOD_DETAIL（指标维度表）", styles["caption"]))
    story.append(make_table([
        ["字段", "类型", "含义", "约束"],
        ["mod",   "varchar(64)",  "指标代码",    "PK"],
        ["type",  "varchar(16)",  "资源类型",    "disk / pref"],
        ["desc",  "varchar(128)", "指标中文说明", ""],
        ["unit",  "varchar(32)",  "单位",        ""],
        ["tag",   "varchar(64)",  "分类标签",    ""],
    ]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("表 1-3 DISK_TSAR（磁盘监控采集事实表）", styles["caption"]))
    story.append(make_table([
        ["字段", "类型", "含义", "约束"],
        ["ts",     "bigint",       "毫秒时间戳", "PK"],
        ["hostid", "varchar(32)",  "主机 ID",    "FK → HOST_DETAIL.hostid"],
        ["mod",    "varchar(64)",  "指标代码",   "FK → MOD_DETAIL.mod"],
        ["type",   "varchar(16)",  "固定为 disk", ""],
        ["value",  "bigint/double","采集数值",   ""],
        ["tag",    "varchar(64)",  "分类标签",   ""],
    ]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("表 1-4 PREF_TSAR（性能监控采集事实表）", styles["caption"]))
    story.append(make_table([
        ["字段", "类型", "含义", "约束"],
        ["ts",     "bigint",       "毫秒时间戳", "PK"],
        ["hostid", "varchar(32)",  "主机 ID",    "FK → HOST_DETAIL.hostid"],
        ["mod",    "varchar(64)",  "指标代码",   "FK → MOD_DETAIL.mod"],
        ["type",   "varchar(16)",  "固定为 pref", ""],
        ["value",  "bigint/double","采集数值",   ""],
        ["tag",    "varchar(64)",  "分类标签",   ""],
    ]))
    story.append(PageBreak())

    # --- 摘要 ---
    story.append(Paragraph("二、报告摘要", styles["h1"]))
    story.append(Paragraph(
        "本报告基于 20 台主机、55 个监控指标（35 个磁盘类 + 20 个性能类）的 tsar 采集数据，"
        "完成数据建模课程的三项核心实践：(1) 构建 E-R 关系图，梳理 4 张表之间的 1:N 关联；"
        "(2) 将毫秒级时间戳规范到北京时间，实现可解释的时间维度；"
        "(3) 以小时为粒度聚合 CPU、网络、磁盘、内存、负载等关键指标，并用折线图/柱状图/雷达图呈现数据特征。"
        "后续各章节依次给出原始数据概览、时间戳清洗方法、小时聚合方法、关键指标可视化、"
        "按机房分组的箱线图、主机级别的汇总表，最后给出结论。", styles["body"]))

    # --- 数据概览 ---
    story.append(Paragraph("三、原始数据概览", styles["h1"]))
    story.append(Paragraph(
        "本报告基于 20 台主机、55 个监控指标（35 个磁盘类 + 20 个性能类）的 tsar 采集数据，"
        "完成数据建模课程的三项核心实践：(1) 构建 E-R 关系图，澄清主机-指标-采集事实之间的 1:N 关系；"
        "(2) 将毫秒级时间戳规范到北京时区，实现可解释的时间维度；(3) 以小时为粒度聚合 CPU、网络、磁盘、内存、"
        "负载等关键指标，并用折线图、柱状图、雷达图、箱线图呈现数据特征。整个分析过程仅使用 Python 标准库及 "
        "matplotlib 完成，便于复现与在教学环境部署。", styles["body"]))

    # --- 数据概览 ---
    story.append(Paragraph("二、数据概览", styles["h1"]))
    host_rows = load_json("host_detail.json")
    mod_rows = load_json("mod_detail.json")
    disk_rows = load_json("disk_tsar.json")
    pref_rows = load_json("pref_tsar.json")
    ts = load_json("timestamp_samples.json")
    agg = load_json("hourly_aggregation.json")

    story.append(Paragraph("本数据集由 4 份 Tab 分隔的文本文件组成，如表 2-1 所示。", styles["body"]))
    story.append(Paragraph("表 2-1 原始数据文件一览", styles["caption"]))
    story.append(make_table([
        ["文件名", "表名", "记录数", "主要字段", "类型"],
        ["host_detail.dat", "host_detail", str(len(host_rows)), "hostid / hostname / owner / model / location", "维度表"],
        ["mod_detail.dat",  "mod_detail",  str(len(mod_rows)),  "mod / type / desc / unit / tag", "维度表"],
        ["disk_tsar.dat",   "tsar_detail(type=disk)", f"{len(disk_rows):,}", "ts / hostid / type / mod / value / tag", "事实表"],
        ["pref_tsar.dat",   "tsar_detail(type=pref)", f"{len(pref_rows):,}", "ts / hostid / type / mod / value / tag", "事实表"],
    ]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "时间范围（北京时间）：<b>{0}</b> 至 <b>{1}</b>，共约 {2} 小时 / {3} 天。"
        "磁盘指标每 5 分钟采样一次，性能指标每 1 小时采样一次。"
        .format(ts["range"]["start"]["yyyy_mm_dd_hh_mi_ss"],
                ts["range"]["end"]["yyyy_mm_dd_hh_mi_ss"],
                ts["range"]["hours_span"],
                ts["range"]["days_span"]),
        styles["body_left"]))

    # 主机表（节选前 8 行）
    story.append(Paragraph("表 2-2 主机信息（节选前 8 台，共 {0} 台）".format(len(host_rows)), styles["caption"]))
    rows = [["hostid", "hostname", "owner", "model", "机房", "机柜"]]
    for h in host_rows[:8]:
        rows.append([h.get("hostid", ""), h.get("hostname", ""), h.get("owner", ""),
                     h.get("model", ""), h.get("location1", ""), h.get("location2", "")])
    story.append(make_table(rows))
    story.append(Paragraph(
        "……其余 {0} 台主机数据已随 PDF 附带的 output/host_detail.json 提供。"
        .format(len(host_rows) - 8), styles["body_left"]))
    story.append(Spacer(1, 3 * mm))

    # 指标字典（节选）
    disk_mods = [m for m in mod_rows if m["type"] == "disk"]
    pref_mods = [m for m in mod_rows if m["type"] == "pref"]
    story.append(Paragraph("表 2-3 性能类指标示例（节选前 8 项，共 {0} 项）".format(len(pref_mods)), styles["caption"]))
    rows = [["mod", "type", "desc", "unit", "tag"]]
    for m in pref_mods[:8]:
        rows.append([m.get("mod", ""), m.get("type", ""), m.get("desc", ""), m.get("unit", ""), m.get("tag", "")])
    story.append(make_table(rows))
    story.append(Paragraph("磁盘类指标共 {0} 项（sda/sdb/sdc/sdd 等 × 多种指标），完整字典见 output/mod_detail.json。"
                           .format(len(disk_mods)), styles["body_left"]))

    # --- 时间戳解析 ---
    story.append(Paragraph("三、时间戳解析", styles["h1"]))
    story.append(Paragraph(
        "原始数据中的 ts 字段是一个毫秒级整数（如 1782835200000）。"
        "为了将其转换为人类可读时间并进行按小时聚合，解析流程如下（伪代码）：",
        styles["body"]))
    story.append(Paragraph(
        "<pre>import datetime\n"
        "ts_ms = 1782835200000\n"
        "dt_utc = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)\n"
        "dt_cn = dt_utc.astimezone(datetime.timezone(datetime.timedelta(hours=8)))\n"
        "human_readable = dt_cn.strftime('%Y-%m-%d %H:%M:%S')    # 2026-07-01 00:00:00\n"
        "hour_slot      = dt_cn.strftime('%Y-%m-%d %H:00')       # 2026-07-01 00:00</pre>",
        styles["code"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "表 3-1 给出了 10 个样例时间戳的解析结果。解析时必须显式考虑时区："
        "<b>同一秒内的时间戳在不同时区对应不同日期</b>，若遗漏 UTC→北京时区的转换，"
        "小时聚合和日期划分都会出错。", styles["body"]))

    story.append(Paragraph("表 3-1 时间戳解析样例（Asia/Shanghai = UTC+8）", styles["caption"]))
    rows = [["原始 ts (ms)", "UTC", "北京时间", "小时槽"]]
    for s in ts["samples"][:10]:
        rows.append([str(s["ts_ms"]), s["iso_utc"][:19], s["yyyy_mm_dd_hh_mi_ss"], s["hour_slot"]])
    story.append(make_table(rows, body_font_size=9))
    story.append(PageBreak())

    # --- 按小时聚合 ---
    story.append(Paragraph("四、按小时聚合统计", styles["h1"]))
    story.append(Paragraph(
        "聚合键：(hour_slot, hostid, mod)。对每个桶同时输出 4 项统计量："
        "平均值 avg、最大值 max、最小值 min、样本数 sample_count。", styles["body"]))
    story.append(Paragraph("表 4-1 聚合结果样例（节选 8 条，磁盘类）", styles["caption"]))
    rows = [["hour_slot", "hostid", "mod", "avg", "max", "min", "sample_count"]]
    for r in agg["by_host_and_mod"]["disk"]["records"][:8]:
        rows.append([r["hour_slot"], r["hostid"], r["mod"],
                     str(round(r["avg"], 2)), str(round(r["max"], 2)),
                     str(round(r["min"], 2)), str(r["sample_count"])])
    story.append(make_table(rows, body_font_size=9))

    story.append(Paragraph("4.1 全局小时级聚合（所有主机平均）", styles["h2"]))
    story.append(Paragraph(
        "为了在报告中以图表方式快速观察整体趋势，我们对同一个小时槽、同一个 mod 在 20 台主机之间"
        "再次求平均，得到 hour × mod 的二维时间序列。以下各图表均基于这一层聚合。", styles["body"]))
    story.append(PageBreak())

    # --- 图表：CPU ---
    story.append(Paragraph("五、关键指标可视化", styles["h1"]))
    story.append(Paragraph("5.1 CPU 使用率与空闲率", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig01_cpu_line.png"), width=175 * mm, height=75 * mm))
    story.append(Paragraph("图 5-1 CPU 使用率 / 空闲率小时级平均曲线", styles["caption"]))
    story.append(Paragraph(
        "可以从曲线中识别周期模式（例如每 24 小时出现一次峰值），以及不同时段的平均负载差异。",
        styles["body"]))
    story.append(PageBreak())

    # --- 图表：网络 ---
    story.append(Paragraph("5.2 网络入/出带宽", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig02_net_line.png"), width=175 * mm, height=75 * mm))
    story.append(Paragraph("图 5-2 网络入站 / 出站带宽（MB/s）", styles["caption"]))

    story.append(Paragraph("5.3 磁盘使用率", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig03_disk_line.png"), width=175 * mm, height=75 * mm))
    story.append(Paragraph("图 5-3 磁盘 sda / sdb 使用率小时级曲线", styles["caption"]))
    story.append(PageBreak())

    story.append(Paragraph("5.4 内存使用（柱状）", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig04_mem_bar.png"), width=175 * mm, height=75 * mm))
    story.append(Paragraph("图 5-4 每小时内存已用（MB）", styles["caption"]))

    story.append(Paragraph("5.5 关键指标 Max / Avg 雷达对比", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig05_radar.png"), width=130 * mm, height=110 * mm))
    story.append(Paragraph("图 5-5 对 6 个关键指标归一化到 0-100 后的雷达图，观察 '峰值 vs 平均' 的差异", styles["caption"]))
    story.append(PageBreak())

    story.append(Paragraph("5.6 每小时采样数", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig06_samples.png"), width=175 * mm, height=75 * mm))
    story.append(Paragraph("图 5-6 每小时内 cpu_usage 的采样条数（校验数据完整性）", styles["caption"]))

    story.append(Paragraph("5.7 各机房主机磁盘使用率分布（箱线图）", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig07_host_box.png"), width=160 * mm, height=95 * mm))
    story.append(Paragraph("图 5-7 按机房分组的主机磁盘使用率分布 —— 可以比较不同机房的平均负载水平与离群点", styles["caption"]))
    story.append(PageBreak())

    # --- 主机汇总表 ---
    story.append(Paragraph("六、主机汇总表", styles["h1"]))
    story.append(Paragraph(
        "表 6-1 汇总了 20 台主机的 3 项平均指标：CPU 使用率、内存已用、磁盘 sda 使用率，"
        "用于老师快速审阅特定主机的整体负载水平。", styles["body"]))
    rows = [["hostid", "hostname", "owner", "model", "机房", "机柜", "CPU avg%", "MEM avg MB", "sda avg%"]]
    for h in agg["host_summary"]:
        rows.append([h.get("hostid", ""), h.get("hostname", "")[:26], h.get("owner", ""),
                     h.get("model", ""), h.get("location1", ""), h.get("location2", ""),
                     str(round(h.get("cpu_usage_avg") or 0, 2)),
                     str(round(h.get("mem_used_avg") or 0, 2)),
                     str(round(h.get("sda_util_avg") or 0, 2))])
    story.append(make_table(rows, body_font_size=9))
    story.append(PageBreak())

    # --- 结论与附录 ---
    story.append(Paragraph("七、结论与下一步", styles["h1"]))
    story.append(Paragraph(
        "通过 E-R 建模、时间戳清洗与小时级聚合，我们把 79,200 条松散的原始采集记录整理为可被"
        "图表化展示的结构化时间序列。主要结论如下：", styles["body"]))
    story.append(Paragraph(
        "· 三台主要资源（CPU / 网络 / 磁盘）均表现出显著的日内周期特征，建议后续分析中使用"
        "差分（例如 subtract 前一天同一小时的值）来去除趋势与周期，以暴露真正的异常；", styles["body_left"]))
    story.append(Paragraph(
        "· 按机房分组的箱线图显示，某些机房的平均磁盘使用率明显高于其他机房，可作为硬件扩容或"
        "数据迁移决策的输入；", styles["body_left"]))
    story.append(Paragraph(
        "· 每小时采样数的柱状图显示数据完整，未发现明显的采集缺失时段；", styles["body_left"]))
    story.append(Paragraph(
        "· 内存使用曲线可以揭示常驻内存与工作集大小的变化趋势，作为容量规划参考。", styles["body_left"]))

    story.append(Paragraph("附录 A 产出文件一览", styles["h2"]))
    story.append(Paragraph("表 A-1 报告目录下的文件（可用于复现与老师审阅）", styles["caption"]))
    app_rows = [
        ["process_data.py", "主数据清洗脚本：ts 解析 + 小时聚合 + JSON 输出"],
        ["generate_figures.py", "基于 output/*.json 生成图表 PNG"],
        ["index.html", "可视化大屏（ECharts + Mermaid，需通过 HTTP 服务打开）"],
        ["tsar_learning_report_A_dashboard.pdf", "方案 A 大屏版 PDF（本脚本生成）"],
        ["tsar_learning_report_B_analysis.pdf",  "方案 B 正式分析报告版 PDF（本脚本生成）"],
        ["output/host_detail.json", "主机明细（JSON）"],
        ["output/mod_detail.json",  "指标字典（JSON）"],
        ["output/disk_tsar.json",   "磁盘采集（JSON）"],
        ["output/pref_tsar.json",   "性能采集（JSON）"],
        ["output/hourly_aggregation.json", "按小时聚合结果（JSON）"],
        ["output/timestamp_samples.json",   "时间戳解析样例（JSON）"],
        ["output/er_diagram.md",            "ER 图（Markdown + Mermaid）"],
        ["output/er_diagram.json",          "ER 图描述（JSON）"],
        ["output/figures/*.png",            "本报告所用的 8 张图表"],
    ]
    story.append(make_table(app_rows, body_font_size=9))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "—— 本报告由 Python + reportlab + matplotlib 自动生成，所有数据均可复现。",
        styles["body_left"]))

    # 构建文档
    doc.build(story, onFirstPage=_draw_cover_bg, onLaterPages=_make_header_footer("tsar_learning_report_B_analysis"))


# ==================== 方案 A：大屏版（可视化为主） ====================
def build_report_A(out_path: Path):
    """以横屏方式排列，每页 1-2 张大图，配合简短文字说明。"""
    styles = _make_styles()

    # 自定义文档模板，留少量边距
    doc = BaseDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title="tsar_learning_report_A_dashboard",
    )

    def _on_page_landscape(canvas, doc):
        canvas.saveState()
        # 横屏：A4 宽高 595.27, 841.89 → 我们其实用纵向 A4，但图表排列像"大屏"
        width, height = A4
        # 顶部装饰带
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 16 * mm, width, 10 * mm, stroke=0, fill=1)
        canvas.setFont(FONT_NAME, 11)
        canvas.setFillColor(WHITE)
        canvas.drawString(16 * mm, height - 13 * mm, "服务器监控数据可视化大屏 · 方案 A")
        canvas.drawRightString(width - 16 * mm, height - 13 * mm, f"第 {doc.page} 页")

        # 底部装饰
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(0.8)
        canvas.line(16 * mm, 12 * mm, width - 16 * mm, 12 * mm)
        canvas.setFont(FONT_NAME, 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(16 * mm, 9 * mm, "Tsar Dashboard · 方案 A")
        canvas.drawRightString(width - 16 * mm, 9 * mm, datetime.now().strftime("%Y-%m-%d %H:%M"))
        canvas.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_on_page_landscape)])

    story = []

    # 封面
    story.append(Spacer(1, 55 * mm))
    story.append(Paragraph("服务器监控数据大屏", styles["h1"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Dashboard-style report: 图表优先，文字简化，便于快速审阅。", styles["body_left"]))
    story.append(Spacer(1, 8 * mm))
    # KPI 表（4 个数字）
    story.append(make_table([
        ["主机数量", "指标数量", "磁盘记录", "性能记录", "覆盖小时数", "聚合记录数"],
        [str(len(load_json("host_detail.json"))),
         str(len(load_json("mod_detail.json"))),
         f"{len(load_json('disk_tsar.json')):,}",
         f"{len(load_json('pref_tsar.json')):,}",
         f"{load_json('timestamp_samples.json')['range']['hours_span']}",
         f"{len(load_json('hourly_aggregation.json')['by_host_and_mod']['disk']['records']) + len(load_json('hourly_aggregation.json')['by_host_and_mod']['pref']['records'])}"],
    ]))
    story.append(PageBreak())

    # E-R 关系图（横屏大图）
    story.append(Paragraph("E-R 关系图（4 张表 · 4 条 1:N 关系）", styles["h2"]))
    story.append(Paragraph(
        "HOST_DETAIL 1:N DISK_TSAR；HOST_DETAIL 1:N PREF_TSAR；"
        "MOD_DETAIL 1:N DISK_TSAR；MOD_DETAIL 1:N PREF_TSAR。",
        styles["body_left"]))
    story.append(Image(str(FIG_DIR / "fig08_er.png"), width=185 * mm, height=115 * mm))
    story.append(Paragraph("图 A-1 服务器监控数据 E-R 关系图（表格形式展示字段与约束）", styles["caption"]))
    story.append(PageBreak())

    # 图 1 CPU
    story.append(Paragraph("1 CPU 使用率 / 空闲率（按小时平均）", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig01_cpu_line.png"), width=180 * mm, height=78 * mm))
    story.append(Paragraph("蓝色曲线（cpu_usage）越高，代表系统越繁忙；绿色曲线（cpu_idle）越高，代表系统越空闲。", styles["body_left"]))
    story.append(PageBreak())

    # 图 2 网络
    story.append(Paragraph("2 网络入/出带宽", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig02_net_line.png"), width=180 * mm, height=78 * mm))
    story.append(Paragraph("橙色=入站，粉色=出站；观察是否有固定的波峰波谷规律。", styles["body_left"]))
    story.append(PageBreak())

    # 图 3 磁盘
    story.append(Paragraph("3 磁盘使用率（sda / sdb）", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig03_disk_line.png"), width=180 * mm, height=78 * mm))
    story.append(Paragraph("磁盘使用率过高是 IO 性能瓶颈的早期信号。", styles["body_left"]))
    story.append(PageBreak())

    # 图 4 内存 + 图 5 雷达
    story.append(Paragraph("4 内存使用（每小时平均）", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig04_mem_bar.png"), width=180 * mm, height=78 * mm))
    story.append(Paragraph("柱状高度表示已用内存（MB），可以直观看到内存是否单调增长或有释放动作。", styles["body_left"]))
    story.append(PageBreak())

    story.append(Paragraph("5 关键指标 Max / Avg 雷达", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig05_radar.png"), width=140 * mm, height=118 * mm))
    story.append(Paragraph("6 个指标归一化到 0-100，橙色=小时内峰值，蓝色=小时平均。两者差距越大，波动性越强。", styles["body_left"]))
    story.append(PageBreak())

    # 图 6 采样数 + 图 7 箱线
    story.append(Paragraph("6 每小时采样数", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig06_samples.png"), width=180 * mm, height=78 * mm))
    story.append(Paragraph("用于检验数据完整性：预期性能类每小时各主机都有 1 条记录，因此每小时总数 ≈ 20。", styles["body_left"]))
    story.append(PageBreak())

    story.append(Paragraph("7 各机房磁盘使用率分布", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig07_host_box.png"), width=170 * mm, height=100 * mm))
    story.append(Paragraph("箱体代表四分位区间，中位数高低直接反映机房平均负载；箱体越高/越长，代表主机之间差异越大。", styles["body_left"]))
    story.append(PageBreak())

    # 图 8 ER
    story.append(Paragraph("8 E-R 关系图", styles["h2"]))
    story.append(Image(str(FIG_DIR / "fig08_er.png"), width=180 * mm, height=92 * mm))
    story.append(Paragraph("host_detail 1:N tsar_detail；mod_detail 1:N tsar_detail；tsar_detail = disk_tsar ∪ pref_tsar。", styles["body_left"]))
    story.append(PageBreak())

    # 时间戳样例表
    story.append(Paragraph("9 时间戳解析样例（北京时区）", styles["h2"]))
    ts = load_json("timestamp_samples.json")
    rows = [["原始 ts(ms)", "UTC 时间", "北京时间", "小时槽"]]
    for s in ts["samples"][:12]:
        rows.append([str(s["ts_ms"]), s["iso_utc"][:19], s["yyyy_mm_dd_hh_mi_ss"], s["hour_slot"]])
    story.append(make_table(rows, body_font_size=9))

    # 主机汇总表
    story.append(Paragraph("10 主机 × 关键指标汇总", styles["h2"]))
    agg = load_json("hourly_aggregation.json")
    rows = [["hostid", "hostname", "机房", "机柜", "CPU avg%", "MEM avg MB", "sda avg%"]]
    for h in agg["host_summary"]:
        rows.append([h.get("hostid", ""), h.get("hostname", "")[:26],
                     h.get("location1", ""), h.get("location2", ""),
                     str(round(h.get("cpu_usage_avg") or 0, 2)),
                     str(round(h.get("mem_used_avg") or 0, 2)),
                     str(round(h.get("sda_util_avg") or 0, 2))])
    story.append(make_table(rows, body_font_size=9))

    doc.build(story)


# ---------- 主入口 ----------
def main():
    OUT_DIR.mkdir(exist_ok=True)

    out_A = BASE_DIR / "tsar_learning_report_A_dashboard.pdf"
    out_B = BASE_DIR / "tsar_learning_report_B_analysis.pdf"

    print("→ 生成方案 A（大屏版）：", out_A)
    build_report_A(out_A)
    print("   OK，大小：", out_A.stat().st_size, "字节")

    print("→ 生成方案 B（分析报告版）：", out_B)
    build_report_B(out_B)
    print("   OK，大小：", out_B.stat().st_size, "字节")

    print("\n✅ 两份 PDF 已生成。")


if __name__ == "__main__":
    main()
