"""
数据建模作业 - 数据清洗脚本
===============================================
功能：
  1. 解析 4 份 .dat 原始数据（tab 分隔）
  2. 生成 ER 关系图描述（Mermaid + JSON）
  3. 时间戳解析：把毫秒级大整数 -> 人类可读的年月日时分
  4. 按小时汇总指标：平均值、最大值、分钟级采样数

产出（本目录下 output/ 子目录）：
  output/host_detail.json        - 主机信息
  output/mod_detail.json         - 指标字典
  output/disk_tsar.json          - 磁盘采集明细
  output/pref_tsar.json          - 性能采集明细
  output/tsar_summary.json       - 合并后汇总视图
  output/timestamp_samples.json  - 时间戳解析样例
  output/hourly_aggregation.json - 按小时聚合结果
  output/er_diagram.md           - ER 关系图（Mermaid）
  output/er_diagram.json         - ER 关系描述（供前端读取）

运行：
  python process_data.py
"""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# -------- 路径与常量 --------
BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(exist_ok=True)

# 采用东八区（北京时间）
BEIJING_TZ = timezone(timedelta(hours=8))

# 关键指标（用于按小时聚合、可视化）
KEY_DISK_METRICS = ["sda_util", "sdb_util", "sda_await", "sdb_await"]
KEY_PREF_METRICS = [
    "cpu_usage",
    "cpu_idle",
    "mem_used",
    "net_in",
    "net_out",
    "load1",
]


# -------- 1. TSV 解析 --------
def read_tsv(path: Path) -> list[dict[str, str]]:
    """读取 tab 分隔的 .dat 文件，返回 list[dict]。"""
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        header: list[str] | None = None
        for lineno, raw in enumerate(reader, start=1):
            # 跳过空行
            if not raw or all((not c or not c.strip()) for c in raw):
                continue
            if header is None:
                header = [c.strip() for c in raw]
                continue
            # 按表头对齐；多出的列丢弃
            row: dict[str, str] = {}
            for key, value in zip(header, raw):
                row[key] = value.strip() if isinstance(value, str) else value
            rows.append(row)
    return rows


# -------- 2. 时间戳解析 --------
def parse_ts(ts_ms: int | str) -> dict[str, Any]:
    """把毫秒级大整数解析成人类可读形式。"""
    ts_int = int(ts_ms)
    dt_utc = datetime.fromtimestamp(ts_int / 1000, tz=timezone.utc)
    dt_bj = dt_utc.astimezone(BEIJING_TZ)
    return {
        "ts_ms": ts_int,
        "iso_utc": dt_utc.isoformat(),
        "iso_beijing": dt_bj.isoformat(),
        "yyyy_mm_dd": dt_bj.strftime("%Y-%m-%d"),
        "hh_mi": dt_bj.strftime("%H:%M"),
        "yyyy_mm_dd_hh_mi_ss": dt_bj.strftime("%Y-%m-%d %H:%M:%S"),
        "hour_slot": dt_bj.strftime("%Y-%m-%d %H:00"),
        "date_hour_key": dt_bj.strftime("%Y-%m-%dT%H"),
        "weekday": dt_bj.strftime("%A"),
    }


def build_timestamp_samples(disk_rows: list[dict], pref_rows: list[dict]) -> dict[str, Any]:
    """时间戳解析样例：展示几个不同时间点的解析结果，并给出时间范围。"""
    all_ts: list[int] = []
    for r in disk_rows + pref_rows:
        try:
            all_ts.append(int(r["ts"]))
        except (KeyError, ValueError):
            continue
    all_ts.sort()

    start = parse_ts(all_ts[0])
    end = parse_ts(all_ts[-1])

    # 在全区间内按等间隔取 10 个样例，展示解析过程
    picks: list[int] = []
    step = max(1, len(all_ts) // 10)
    for i in range(0, len(all_ts), step):
        picks.append(all_ts[i])
    picks = picks[:10]

    return {
        "timezone": "Asia/Shanghai (UTC+8)",
        "range": {
            "start": start,
            "end": end,
            "hours_span": round((all_ts[-1] - all_ts[0]) / (1000 * 3600), 2),
            "days_span": round((all_ts[-1] - all_ts[0]) / (1000 * 86400), 2),
        },
        "raw_example": {
            "before": "1782835200000",
            "after": parse_ts(1782835200000),
        },
        "samples": [parse_ts(t) for t in picks],
    }


# -------- 3. 小时级聚合 --------
def _bucket_key(ts_ms: int, hostid: str, mod: str) -> tuple[str, str, str]:
    dt = datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc).astimezone(BEIJING_TZ)
    return (dt.strftime("%Y-%m-%d %H:00"), hostid, mod)


def aggregate_hourly(rows: list[dict], label: str) -> dict[str, Any]:
    """按 (小时, host, mod) 聚合：avg, max, min, sample_count。"""
    # key: (hour_slot, hostid, mod) -> list[float]
    bucket: dict[tuple[str, str, str], list[float]] = defaultdict(list)

    for r in rows:
        try:
            val = float(r["value"])
        except (KeyError, ValueError):
            continue
        key = _bucket_key(r["ts"], r["hostid"], r["mod"])
        bucket[key].append(val)

    records: list[dict[str, Any]] = []
    for (slot, hostid, mod), values in bucket.items():
        n = len(values)
        if n == 0:
            continue
        avg = sum(values) / n
        records.append(
            {
                "hour_slot": slot,
                "hostid": hostid,
                "mod": mod,
                "avg": round(avg, 4),
                "max": round(max(values), 4),
                "min": round(min(values), 4),
                "sample_count": n,
            }
        )

    records.sort(key=lambda x: (x["hour_slot"], x["hostid"], x["mod"]))
    return {
        "type": label,
        "total_records": len(records),
        "records": records,
    }


def aggregate_global_hourly(rows: list[dict], mods: list[str], label: str) -> dict[str, Any]:
    """只按 (小时, mod) 聚合（所有主机平均）—— 用于折线图可视化。"""
    bucket: dict[tuple[str, str], list[float]] = defaultdict(list)
    mod_set = set(mods)

    for r in rows:
        if r.get("mod") not in mod_set:
            continue
        try:
            val = float(r["value"])
        except ValueError:
            continue
        dt = datetime.fromtimestamp(int(r["ts"]) / 1000, tz=timezone.utc).astimezone(BEIJING_TZ)
        key = (dt.strftime("%Y-%m-%d %H:00"), r["mod"])
        bucket[key].append(val)

    # 收集所有小时槽，保证时间轴连续
    all_slots: set[str] = set()
    for (slot, _m), _ in bucket.items():
        all_slots.add(slot)
    sorted_slots = sorted(all_slots)

    series: dict[str, list[dict[str, Any]]] = {m: [] for m in mods}
    for slot in sorted_slots:
        for m in mods:
            values = bucket.get((slot, m), [])
            n = len(values)
            entry = {
                "hour_slot": slot,
                "value": round(sum(values) / n, 4) if n else None,
                "max": round(max(values), 4) if n else None,
                "min": round(min(values), 4) if n else None,
                "sample_count": n,
            }
            series[m].append(entry)

    return {
        "type": label,
        "hour_slots": sorted_slots,
        "mods": mods,
        "series": series,
    }


# -------- 4. ER 关系图 --------
def build_er_json(host_rows: list[dict], mod_rows: list[dict], disk_rows: list[dict], pref_rows: list[dict]) -> dict[str, Any]:
    return {
        "entities": [
            {
                "name": "host_detail",
                "description": "主机信息明细表（维度表）",
                "primary_key": ["hostid"],
                "attributes": [
                    {"name": "hostid", "type": "string", "comment": "主机ID（主键）"},
                    {"name": "hostname", "type": "string", "comment": "主机FQDN名"},
                    {"name": "owner", "type": "string", "comment": "负责人"},
                    {"name": "model", "type": "string", "comment": "硬件型号"},
                    {"name": "location1", "type": "string", "comment": "机房位置"},
                    {"name": "location2", "type": "string", "comment": "机柜编号"},
                ],
                "row_count": len(host_rows),
            },
            {
                "name": "mod_detail",
                "description": "指标(MOD)字典表（维度表）",
                "primary_key": ["mod"],
                "attributes": [
                    {"name": "mod", "type": "string", "comment": "指标代码（主键）"},
                    {"name": "type", "type": "string", "comment": "资源类型 disk/pref"},
                    {"name": "desc", "type": "string", "comment": "指标中文说明"},
                    {"name": "unit", "type": "string", "comment": "单位"},
                    {"name": "tag", "type": "string", "comment": "指标分类标签"},
                ],
                "row_count": len(mod_rows),
            },
            {
                "name": "tsar_detail",
                "description": "监控采集明细表（事实表）= disk_tsar + pref_tsar",
                "primary_key": ["ts", "hostid", "mod"],
                "attributes": [
                    {"name": "ts", "type": "long (ms)", "comment": "采集时间戳（毫秒）"},
                    {"name": "hostid", "type": "string", "comment": "主机ID（外键 → host_detail.hostid）"},
                    {"name": "type", "type": "string", "comment": "资源类型 disk/pref"},
                    {"name": "mod", "type": "string", "comment": "指标代码（外键 → mod_detail.mod）"},
                    {"name": "value", "type": "double", "comment": "采集数值"},
                    {"name": "tag", "type": "string", "comment": "指标分类标签"},
                ],
                "row_count": len(disk_rows) + len(pref_rows),
                "sub_tables": [
                    {"name": "disk_tsar", "type": "disk", "row_count": len(disk_rows)},
                    {"name": "pref_tsar", "type": "pref", "row_count": len(pref_rows)},
                ],
            },
        ],
        "relationships": [
            {
                "from": "host_detail",
                "to": "tsar_detail",
                "type": "1:N",
                "on": ["hostid"],
                "description": "一台主机产生多条采集记录",
            },
            {
                "from": "mod_detail",
                "to": "tsar_detail",
                "type": "1:N",
                "on": ["mod"],
                "description": "一个指标出现在多条采集记录中",
            },
        ],
        "keys": {
            "host_hostid_sample": [r["hostid"] for r in host_rows[:5]],
            "mod_sample": [r["mod"] for r in mod_rows[:5]],
        },
    }


def build_er_mermaid(er_json: dict[str, Any]) -> str:
    """生成 Mermaid erDiagram 代码。"""
    entity_blocks: list[str] = []
    for ent in er_json["entities"]:
        lines: list[str] = []
        lines.append(f'    {ent["name"]} "{ent["description"]}" {{')
        for attr in ent["attributes"]:
            # 标记主键/外键
            name = attr["name"]
            dtype = attr["type"].replace(" ", "_")
            markers: list[str] = []
            if name in ent.get("primary_key", []):
                markers.append("PK")
            if "外键" in attr.get("comment", ""):
                markers.append("FK")
            tag = f' {" ".join(markers)}' if markers else ""
            lines.append(f"        {dtype} {name}{tag}")
        lines.append("    }")
        entity_blocks.append("\n".join(lines))

    rel_lines: list[str] = []
    for rel in er_json["relationships"]:
        if rel["type"] == "1:N":
            rel_lines.append(f'    {rel["from"]} ||--o{{ {rel["to"]} : "{rel["on"][0]} / {rel["type"]}"')
        else:
            rel_lines.append(f'    {rel["from"]} -- {rel["to"]} : "{rel["type"]}"')

    mermaid = "erDiagram\n" + "\n".join(entity_blocks) + "\n" + "\n".join(rel_lines) + "\n"
    return mermaid


# -------- 5. 工具：写 JSON --------
def write_json(obj: Any, name: str) -> Path:
    p = OUT_DIR / name
    with p.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    return p


# -------- 6. 主机-指标概要（供大屏表格展示） --------
def build_host_metric_summary(host_rows: list[dict], disk_rows: list[dict], pref_rows: list[dict]) -> list[dict[str, Any]]:
    host_map: dict[str, dict] = {r["hostid"]: r for r in host_rows}

    # 每个主机收集 cpu_usage / mem_used / sda_util 的均值
    agg: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in disk_rows + pref_rows:
        if r["mod"] not in {"cpu_usage", "mem_used", "sda_util"}:
            continue
        try:
            agg[r["hostid"]][r["mod"]].append(float(r["value"]))
        except ValueError:
            continue

    summary: list[dict[str, Any]] = []
    for hostid, info in host_map.items():
        mods = agg.get(hostid, {})
        summary.append(
            {
                "hostid": hostid,
                "hostname": info.get("hostname", ""),
                "owner": info.get("owner", ""),
                "model": info.get("model", ""),
                "location1": info.get("location1", ""),
                "location2": info.get("location2", ""),
                "cpu_usage_avg": round(sum(v) / len(v), 2) if (v := mods.get("cpu_usage", [])) else None,
                "mem_used_avg": round(sum(v) / len(v), 2) if (v := mods.get("mem_used", [])) else None,
                "sda_util_avg": round(sum(v) / len(v), 2) if (v := mods.get("sda_util", [])) else None,
            }
        )
    return summary


# -------- 主流程 --------
def main() -> None:
    print(f"[1/5] 读取 .dat 原始文件：{BASE_DIR}")
    host_rows = read_tsv(BASE_DIR / "host_detail.dat")
    mod_rows = read_tsv(BASE_DIR / "mod_detail.dat")
    disk_rows = read_tsv(BASE_DIR / "disk_tsar.dat")
    pref_rows = read_tsv(BASE_DIR / "pref_tsar.dat")
    print(f"      host_detail={len(host_rows)} 行, mod_detail={len(mod_rows)} 行")
    print(f"      disk_tsar={len(disk_rows)} 行, pref_tsar={len(pref_rows)} 行")

    print("[2/5] 写原始 JSON ...")
    write_json(host_rows, "host_detail.json")
    write_json(mod_rows, "mod_detail.json")
    write_json(disk_rows, "disk_tsar.json")
    write_json(pref_rows, "pref_tsar.json")

    print("[3/5] 时间戳解析 ...")
    ts_samples = build_timestamp_samples(disk_rows, pref_rows)
    write_json(ts_samples, "timestamp_samples.json")
    print(f"      时间范围：{ts_samples['range']['start']['yyyy_mm_dd_hh_mi_ss']}"
          f" ~ {ts_samples['range']['end']['yyyy_mm_dd_hh_mi_ss']}")
    print(f"      共覆盖 {ts_samples['range']['hours_span']} 小时 / {ts_samples['range']['days_span']} 天")

    print("[4/5] 小时级指标聚合 ...")
    hourly_disk = aggregate_hourly(disk_rows, "disk")
    hourly_pref = aggregate_hourly(pref_rows, "pref")
    global_disk = aggregate_global_hourly(disk_rows, KEY_DISK_METRICS, "disk_global")
    global_pref = aggregate_global_hourly(pref_rows, KEY_PREF_METRICS, "pref_global")
    write_json(
        {
            "by_host_and_mod": {
                "disk": hourly_disk,
                "pref": hourly_pref,
            },
            "by_hour_and_mod": {
                "disk": global_disk,
                "pref": global_pref,
            },
            "host_summary": build_host_metric_summary(host_rows, disk_rows, pref_rows),
        },
        "hourly_aggregation.json",
    )
    print(f"      磁盘聚合记录：{hourly_disk['total_records']}")
    print(f"      性能聚合记录：{hourly_pref['total_records']}")

    print("[5/5] ER 关系图 ...")
    er_json = build_er_json(host_rows, mod_rows, disk_rows, pref_rows)
    write_json(er_json, "er_diagram.json")
    mermaid = build_er_mermaid(er_json)
    (OUT_DIR / "er_diagram.md").write_text(
        "# E-R 关系图\n\n"
        "## 说明\n\n"
        "- 事实表：`tsar_detail`（由 `disk_tsar.dat` 与 `pref_tsar.dat` 合并而成）\n"
        "- 维度表：`host_detail`（主机）、`mod_detail`（指标字典）\n"
        "- 关系：`host_detail 1:N tsar_detail`；`mod_detail 1:N tsar_detail`\n\n"
        "## Mermaid E-R 图\n\n"
        "```mermaid\n" + mermaid + "```\n",
        encoding="utf-8",
    )
    print("      ER 图已生成（er_diagram.json / er_diagram.md）")

    print("\n✅ 全部完成，输出目录：", OUT_DIR)


if __name__ == "__main__":
    main()
