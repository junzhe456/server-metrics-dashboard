"""
生成服务器监控数据的可视化图表（PNG），供 PDF 报告使用。
依赖：matplotlib / 标准库 json / datetime
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")  # 非交互式
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.dates import DateFormatter, HourLocator, DayLocator

# ---------- 中文字体处理（Windows 环境下尽量使用微软雅黑/宋体） ----------
rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False
rcParams["figure.dpi"] = 150

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "output"
FIG_DIR = OUT_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)


def load_json(name: str) -> Any:
    with (OUT_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _plot(title: str, filename: str, figsize=(9.6, 4.2)):
    """装饰器：统一设置标题 / 保存 / 关闭 Figure"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            fig, ax = plt.subplots(figsize=figsize)
            func(ax, *args, **kwargs)
            fig.suptitle(title, fontsize=15, fontweight="bold", color="#1f3a8a")
            fig.tight_layout(rect=(0, 0, 1, 0.96))
            out = FIG_DIR / filename
            fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            return str(out)
        return wrapper
    return decorator


# ---------- 图表 1: CPU 小时级折线 ----------
def chart_cpu_line(agg: dict) -> str:
    pref = agg["by_hour_and_mod"]["pref"]
    slots = [datetime.strptime(s, "%Y-%m-%d %H:%M") for s in pref["hour_slots"]]
    cpu_usage = [x["value"] for x in pref["series"]["cpu_usage"]]
    cpu_idle = [x["value"] for x in pref["series"]["cpu_idle"]]

    fig, ax = plt.subplots(figsize=(9.6, 4.2))
    ax.plot(slots, cpu_usage, label="CPU 使用率 avg", color="#2563eb", lw=1.6)
    ax.plot(slots, cpu_idle, label="CPU 空闲率 avg", color="#059669", lw=1.6)
    ax.set_xlabel("时间"); ax.set_ylabel("百分比 (%)")
    ax.set_ylim(-5, 105); ax.grid(alpha=0.3)
    ax.xaxis.set_major_locator(DayLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))
    ax.legend(); fig.suptitle("图 1 CPU 使用率 / 空闲率（按小时平均，所有主机）", fontsize=15, fontweight="bold", color="#1f3a8a")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG_DIR / "fig01_cpu_line.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return str(out)


# ---------- 图表 2: 网络入/出折线 ----------
def chart_net_line(agg: dict) -> str:
    pref = agg["by_hour_and_mod"]["pref"]
    slots = [datetime.strptime(s, "%Y-%m-%d %H:%M") for s in pref["hour_slots"]]
    net_in = [x["value"] for x in pref["series"]["net_in"]]
    net_out = [x["value"] for x in pref["series"]["net_out"]]

    fig, ax = plt.subplots(figsize=(9.6, 4.2))
    ax.plot(slots, net_in, label="入站带宽 avg(MB/s)", color="#f59e0b", lw=1.6)
    ax.plot(slots, net_out, label="出站带宽 avg(MB/s)", color="#ec4899", lw=1.6)
    ax.set_xlabel("时间"); ax.set_ylabel("MB/s")
    ax.xaxis.set_major_locator(DayLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))
    ax.grid(alpha=0.3); ax.legend()
    fig.suptitle("图 2 网络入/出带宽（按小时平均）", fontsize=15, fontweight="bold", color="#1f3a8a")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG_DIR / "fig02_net_line.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return str(out)


# ---------- 图表 3: 磁盘 sda/sdb 使用率折线 ----------
def chart_disk_line(agg: dict) -> str:
    disk = agg["by_hour_and_mod"]["disk"]
    slots = [datetime.strptime(s, "%Y-%m-%d %H:%M") for s in disk["hour_slots"]]
    # 原始数据中可能没有 sda_util/sdb_util（如果 mod 为其他名字），兼容处理
    series = disk["series"]
    available = [m for m in disk["mods"] if "util" in m]
    fig, ax = plt.subplots(figsize=(9.6, 4.2))
    for mod in available[:2]:
        ax.plot(slots, [x["value"] for x in series[mod]], label=f"{mod} avg", lw=1.2)
    ax.set_xlabel("时间"); ax.set_ylabel("百分比 (%)")
    ax.xaxis.set_major_locator(DayLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))
    ax.grid(alpha=0.3); ax.legend()
    title_text = "图 3 磁盘使用率（按小时平均，" + ", ".join(available[:2]) + "）"
    fig.suptitle(title_text, fontsize=15, fontweight="bold", color="#1f3a8a")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG_DIR / "fig03_disk_line.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return str(out)


# ---------- 图表 4: 内存柱状 ----------
def chart_mem_bar(agg: dict) -> str:
    pref = agg["by_hour_and_mod"]["pref"]
    slots = pref["hour_slots"]
    mem_used = [x["value"] for x in pref["series"]["mem_used"]]

    fig, ax = plt.subplots(figsize=(9.6, 4.2))
    ax.bar(range(len(slots)), mem_used, color="#6ee7b7", edgecolor="#047857", linewidth=0.4)
    ax.set_xlabel("时间（小时槽）"); ax.set_ylabel("已用内存 (MB)")
    # 横轴标签稀疏显示
    step = max(1, len(slots) // 10)
    ax.set_xticks(range(0, len(slots), step))
    ax.set_xticklabels([s.split(" ")[0] for s in slots[::step]], rotation=30, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.suptitle("图 4 内存已用（按小时平均，所有主机）", fontsize=15, fontweight="bold", color="#1f3a8a")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG_DIR / "fig04_mem_bar.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return str(out)


# ---------- 图表 5: 关键指标雷达图（avg vs max） ----------
def chart_radar(agg: dict) -> str:
    pref = agg["by_hour_and_mod"]["pref"]
    mods = ["cpu_usage", "mem_used", "net_in", "net_out", "load1", "cpu_idle"]
    max_limits = {"cpu_usage": 100, "mem_used": 120000, "net_in": 400, "net_out": 400, "load1": 20, "cpu_idle": 100}

    # 先对每个 mod 计算 avg / max 全局再平均
    def stat(mod: str):
        series = pref["series"][mod]
        values = [x["value"] for x in series if x["value"] is not None]
        return sum(values) / len(values), max(values)

    stats = {m: stat(m) for m in mods}
    labels = ["CPU使用率", "内存使用", "网络入站", "网络出站", "负载load1", "CPU空闲率"]
    display_mods = ["cpu_usage", "mem_used", "net_in", "net_out", "load1", "cpu_idle"]

    import numpy as np
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()

    def normalize(values, mod_names):
        return [v / max_limits[m] * 100 for v, m in zip(values, mod_names)]

    avgs = normalize([stats[m][0] for m in display_mods], display_mods)
    maxs = normalize([stats[m][1] for m in display_mods], display_mods)
    avgs += avgs[:1]; maxs += maxs[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6.6, 5.6), subplot_kw=dict(polar=True))
    ax.plot(angles, avgs, "o-", label="小时级平均(归一化)", color="#2563eb", lw=2)
    ax.fill(angles, avgs, color="#2563eb", alpha=0.18)
    ax.plot(angles, maxs, "o-", label="小时内峰值(归一化)", color="#f59e0b", lw=2)
    ax.fill(angles, maxs, color="#f59e0b", alpha=0.18)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 100); ax.set_yticks([20, 40, 60, 80, 100]); ax.set_yticklabels(["20%", "40%", "60%", "80%", "100%"])
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    fig.suptitle("图 5 关键指标 Max / Avg 对比（雷达）", fontsize=15, fontweight="bold", color="#1f3a8a")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG_DIR / "fig05_radar.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return str(out)


# ---------- 图表 6: 每小时采样数柱状 ----------
def chart_samples_bar(agg: dict) -> str:
    pref = agg["by_hour_and_mod"]["pref"]
    slots = pref["hour_slots"]
    counts = [x["sample_count"] or 0 for x in pref["series"]["cpu_usage"]]

    fig, ax = plt.subplots(figsize=(9.6, 4.2))
    ax.bar(range(len(slots)), counts, color="#8b5cf6", edgecolor="#4c1d95", linewidth=0.4)
    ax.set_xlabel("时间（小时槽）"); ax.set_ylabel("采样数（条/小时）")
    step = max(1, len(slots) // 10)
    ax.set_xticks(range(0, len(slots), step))
    ax.set_xticklabels([s.split(" ")[0] for s in slots[::step]], rotation=30, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.suptitle("图 6 每小时采样数（以 cpu_usage 为例）", fontsize=15, fontweight="bold", color="#1f3a8a")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG_DIR / "fig06_samples.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return str(out)


# ---------- 图表 7: 主机 × sda_util_avg（按机房箱线） ----------
def chart_host_boxplot(host_rows: list[dict], agg: dict) -> str:
    from collections import defaultdict
    # 聚合每个主机的 sda_util 平均（磁盘指标）
    disk = agg["by_host_and_mod"]["disk"]
    host_avg: Dict[str, List[float]] = defaultdict(list)
    for rec in disk["records"]:
        if rec["mod"].endswith("_util"):
            host_avg[rec["hostid"]].append(rec["avg"] or 0.0)
    # 每个主机取一个平均值
    host_map = {h["hostid"]: h for h in host_rows}
    by_location: Dict[str, List[float]] = defaultdict(list)
    for hostid, vals in host_avg.items():
        if hostid in host_map and vals:
            by_location[host_map[hostid]["location1"]].append(sum(vals) / len(vals))

    locs = sorted(by_location.keys())
    data = [by_location[loc] for loc in locs]

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    bp = ax.boxplot(data, labels=locs, patch_artist=True, showmeans=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#bfdbfe")
    for median in bp["medians"]:
        median.set_color("#1d4ed8")
    ax.set_ylabel("磁盘使用率 %"); ax.grid(axis="y", alpha=0.3)
    fig.suptitle("图 7 各机房主机磁盘使用率分布（箱线图）", fontsize=15, fontweight="bold", color="#1f3a8a")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG_DIR / "fig07_host_box.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return str(out)


# ---------- 图表 8: ER 关系图（表格式，4 张表） ----------
def chart_er_diagram() -> str:
    """绘制标准的表格式 ER 关系图（4 张表 + 关系线 + 中文关系描述）。"""
    import matplotlib.patches as mpatches

    # —— 4 张表定义：表头表名；字段行：(类型, 字段名, 约束(PK/FK), 中文注释) ——
    table_defs = {
        "HOST_DETAIL": {
            "title": "HOST_DETAIL",
            "title_cn": "主机信息明细表（维度表）",
            "color": "#1f3a8a",
            "rows": [
                ("varchar(32)", "hostid",    "PK", "主机ID"),
                ("varchar(128)","hostname",  "",   "主机名"),
                ("varchar(64)", "owner",     "",   "负责人"),
                ("varchar(64)", "model",     "",   "型号"),
                ("varchar(32)", "location1", "",   "机房"),
                ("varchar(64)", "location2", "",   "机柜"),
            ],
        },
        "MOD_DETAIL": {
            "title": "MOD_DETAIL",
            "title_cn": "指标字典表（维度表）",
            "color": "#1d4ed8",
            "rows": [
                ("varchar(64)", "mod",    "PK", "指标代码"),
                ("varchar(16)", "type",   "",   "资源类型"),
                ("varchar(128)","desc",   "",   "中文说明"),
                ("varchar(32)", "unit",   "",   "单位"),
                ("varchar(64)", "tag",    "",   "分类标签"),
            ],
        },
        "DISK_TSAR": {
            "title": "DISK_TSAR",
            "title_cn": "磁盘监控采集明细（5 分钟/次）",
            "color": "#b45309",
            "rows": [
                ("bigint",       "ts",     "PK", "毫秒时间戳"),
                ("varchar(32)",  "hostid", "FK → HOST_DETAIL.hostid", "主机ID"),
                ("varchar(16)",  "type",   "",   "固定为 disk"),
                ("varchar(64)",  "mod",    "FK → MOD_DETAIL.mod",    "指标代码"),
                ("varchar(64)",  "value",  "",   "采集值"),
                ("varchar(64)",  "tag",    "",   "分类标签"),
            ],
        },
        "PREF_TSAR": {
            "title": "PREF_TSAR",
            "title_cn": "性能监控采集明细（1 小时/次）",
            "color": "#b45309",
            "rows": [
                ("bigint",       "ts",     "PK", "毫秒时间戳"),
                ("varchar(32)",  "hostid", "FK → HOST_DETAIL.hostid", "主机ID"),
                ("varchar(16)",  "type",   "",   "固定为 pref"),
                ("varchar(64)",  "mod",    "FK → MOD_DETAIL.mod",    "指标代码"),
                ("varchar(64)",  "value",  "",   "采集值"),
                ("varchar(64)",  "tag",    "",   "分类标签"),
            ],
        },
    }

    # 画布大小（横向宽屏，便于并排 2 张表）
    fig_w, fig_h = 20, 12
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w); ax.set_ylim(0, fig_h); ax.axis("off")

    # —— 布局坐标（左下为 0,0）————————————————
    # 左上: HOST_DETAIL    右上: MOD_DETAIL
    # 左下: DISK_TSAR      右下: PREF_TSAR
    # 每张表宽 7.5，高根据字段行数自动计算
    # ——————————————————————————————————————
    col_x = {"left": 1.2, "right": fig_w - 1.2 - 7.5}  # 左右两列表的 x 起点
    row_y = {"top": fig_h - 2.0, "bottom": fig_h / 2 + 0.2}

    positions = {
        "HOST_DETAIL": (col_x["left"],  row_y["top"]),
        "MOD_DETAIL":  (col_x["right"], row_y["top"]),
        "DISK_TSAR":   (col_x["left"],  row_y["bottom"]),
        "PREF_TSAR":   (col_x["right"], row_y["bottom"]),
    }

    col_widths = [1.6, 2.0, 1.4, 2.5]  # 四列：字段类型 / 字段名 / 约束 / 中文注释
    table_w = sum(col_widths)
    row_h = 0.6  # 每行高度
    header_h = 0.8

    # 记录表中心坐标（用于画连线）
    table_anchors = {}  # {name: (center_x, top_y, bottom_y, header_right_y)}

    for name, (x0, y0) in positions.items():
        tdef = table_defs[name]
        n = len(tdef["rows"])
        table_h = header_h + n * row_h
        y_top = y0              # 表顶部
        y_bottom = y0 - table_h # 表底部

        # 外框（主表格矩形）
        outer = mpatches.Rectangle((x0, y_bottom), table_w, table_h,
                                   facecolor="#f8fafc", edgecolor=tdef["color"], lw=2.2)
        ax.add_patch(outer)

        # 表头（深色背景）
        header_rect = mpatches.Rectangle((x0, y_top - header_h), table_w, header_h,
                                         facecolor=tdef["color"], edgecolor=tdef["color"], lw=2.2)
        ax.add_patch(header_rect)
        ax.text(x0 + table_w / 2, y_top - header_h / 2,
                tdef["title"], ha="center", va="center",
                color="white", fontsize=12, fontweight="bold")
        ax.text(x0 + table_w / 2, y_top - header_h - 0.3,
                tdef["title_cn"], ha="center", va="center",
                color=tdef["color"], fontsize=10, fontweight="bold")

        # 表头分隔线
        line_y = y_top - header_h
        ax.plot([x0, x0 + table_w], [line_y, line_y], color=tdef["color"], lw=1.6)

        # 列分隔线（整个表高度）
        cx = x0
        for cw in col_widths[:-1]:
            cx += cw
            ax.plot([cx, cx], [y_bottom, line_y], color=tdef["color"], lw=0.8)

        # 字段行
        for i, (ftype, fname, constraint, cname) in enumerate(tdef["rows"]):
            ry_top = line_y - i * row_h
            ry_bot = ry_top - row_h

            # 行底分隔线
            ax.plot([x0, x0 + table_w], [ry_bot, ry_bot], color="#cbd5e1", lw=0.6)

            # 每个字段居中显示
            cells = [ftype, fname, constraint, cname]
            cx_cell = x0
            for cw, txt in zip(col_widths, cells):
                ax.text(cx_cell + cw / 2, (ry_top + ry_bot) / 2,
                        txt, ha="center", va="center",
                        fontsize=9.5, color="#1e293b")
                cx_cell += cw

        # 记录锚点
        table_anchors[name] = {
            "x0": x0, "y_top": y_top, "y_bottom": y_bottom,
            "xc": x0 + table_w / 2,
            "x_left": x0, "x_right": x0 + table_w,
            "y_top_mid": line_y + header_h / 2,  # 表头中间 y
            "y_bottom_table": y_bottom,
        }

    # —— 画关系连线（带箭头 + 基数标注 + 中文描述） ——
    def draw_connector(from_name, from_side, to_name, to_side,
                       card_left, card_right, label_text,
                       color="#475569", curve=True):
        """
        在两张表之间画一条线，并在两端标注基数（如 "1", "N"），
        中间标注中文关系描述 label_text。
        from_side / to_side ∈ {'left','right','top','bottom'}
        """
        a = table_anchors[from_name]
        b = table_anchors[to_name]

        def anchor(tab, side):
            if side == "right": return (tab["x_right"], tab["y_bottom_table"] + (tab["y_top"] - tab["y_bottom_table"]) * 0.4)
            if side == "left":  return (tab["x_left"],  tab["y_bottom_table"] + (tab["y_top"] - tab["y_bottom_table"]) * 0.4)
            if side == "top":   return (tab["xc"],      tab["y_top"])
            if side == "bottom":return (tab["xc"],      tab["y_bottom_table"])
            return (tab["xc"], tab["y_bottom_table"])

        (x1, y1), (x2, y2) = anchor(a, from_side), anchor(b, to_side)

        if curve:
            # 二次贝塞尔样条：控制点向上或向外偏移，得到弧线
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2 + (0.6 if from_side in ("top","bottom") else 0.0)
            import numpy as np
            t = np.linspace(0, 1, 40)
            xs = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * mid_x + t ** 2 * x2
            ys = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * mid_y + t ** 2 * y2
            ax.plot(xs, ys, color=color, lw=1.6)
            # 末端箭头
            ax.annotate("", xy=(x2, y2), xytext=(xs[-3], ys[-3]),
                        arrowprops=dict(facecolor=color, edgecolor=color,
                                         shrink=0.02, width=1.2, headwidth=7))
            # 中部文字
            ax.text(mid_x, mid_y + 0.25, label_text,
                    ha="center", va="center", fontsize=10,
                    color=color, bbox=dict(boxstyle="round,pad=0.3",
                                           facecolor="white", edgecolor=color, alpha=0.9))
        else:
            ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(facecolor=color, edgecolor=color,
                                         shrinkA=3, shrinkB=3, lw=1.6,
                                         arrowstyle="-"))
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x, mid_y + 0.3, label_text,
                    ha="center", va="center", fontsize=10,
                    color=color,
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor="white", edgecolor=color, alpha=0.9))

        # 两端基数标注
        ax.text(x1 + (0.3 if x1 < x2 else -0.3),
                y1 + (0.3 if y1 < (y1+y2)/2 else -0.3),
                card_left, fontsize=11, color=color, fontweight="bold",
                ha="center", va="center",
                bbox=dict(boxstyle="circle,pad=0.2",
                          facecolor="white", edgecolor=color))
        ax.text(x2 + (0.3 if x2 > x1 else -0.3),
                y2 + (0.3 if y2 > (y1+y2)/2 else -0.3),
                card_right, fontsize=11, color=color, fontweight="bold",
                ha="center", va="center",
                bbox=dict(boxstyle="circle,pad=0.2",
                          facecolor="white", edgecolor=color))

    # 按图片中的关系线绘制：
    # 左上 HOST_DETAIL 与 左下 DISK_TSAR 关系 1:N
    # 左上 HOST_DETAIL 与 右下 PREF_TSAR 关系 1:N
    # 右上 MOD_DETAIL  与 左下 DISK_TSAR 关系 1:N
    # 右上 MOD_DETAIL  与 右下 PREF_TSAR 关系 1:N
    draw_connector("HOST_DETAIL", "bottom", "DISK_TSAR",  "top",
                   "1", "N", "1 主机 → N 次磁盘采集（5 分钟/次）",
                   color="#1f3a8a", curve=False)
    draw_connector("HOST_DETAIL", "bottom", "PREF_TSAR", "top",
                   "1", "N", "1 主机 → N 次性能采集（1 小时/次）",
                   color="#1f3a8a", curve=False)
    draw_connector("MOD_DETAIL", "bottom", "DISK_TSAR",  "top",
                   "1", "N", "1 指标 → N 次磁盘采集记录",
                   color="#b45309", curve=False)
    draw_connector("MOD_DETAIL", "bottom", "PREF_TSAR",  "top",
                   "1", "N", "1 指标 → N 次性能采集记录",
                   color="#b45309", curve=False)

    # 标题（图名）
    fig.suptitle("E-R 关系图 · 数据建模作业（4 张表，4 条 1:N 关系）",
                 fontsize=16, fontweight="bold", color="#0f172a", y=0.98)

    # 图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color="#1f3a8a", lw=2, label="HOST_DETAIL 相关关系"),
        Line2D([0], [0], color="#b45309", lw=2, label="MOD_DETAIL 相关关系"),
    ]
    ax.legend(handles=legend_elements, loc="upper center",
              bbox_to_anchor=(0.5, 1.015), ncol=2, frameon=True, fontsize=11)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = FIG_DIR / "fig08_er.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return str(out)


# ---------- 生成所有图表 ----------
def generate_all_figures() -> Dict[str, str]:
    host_rows = load_json("host_detail.json")
    agg = load_json("hourly_aggregation.json")

    return {
        "cpu": chart_cpu_line(agg),
        "net": chart_net_line(agg),
        "disk": chart_disk_line(agg),
        "mem": chart_mem_bar(agg),
        "radar": chart_radar(agg),
        "samples": chart_samples_bar(agg),
        "host_box": chart_host_boxplot(host_rows, agg),
        "er": chart_er_diagram(),
    }


if __name__ == "__main__":
    files = generate_all_figures()
    for name, path in files.items():
        print(f"{name:10s} -> {path}")
