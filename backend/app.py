"""Flask REST API：服务器监控数据可视化后端。

启动方式：
    cd 数据建模作业
    python -m backend.app            # 开发模式，默认监听 http://127.0.0.1:5001
    # 或生产模式（需要 gunicorn/ waitress）
    python -m flask --app backend.app run --host 0.0.0.0 --port 5001

主要路由：
    GET  /health
    GET  /api/hosts
    GET  /api/metrics
    GET  /api/disk?hostid=xxx&mod=xxx&start=YYYY-MM-DD&end=YYYY-MM-DD
    GET  /api/pref?hostid=xxx&mod=xxx&start=YYYY-MM-DD&end=YYYY-MM-DD
    GET  /api/agg/disk-hourly?hostid=&mod=
    GET  /api/agg/pref-hourly
    GET  /api/dashboard/summary
    POST /api/etl/run
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# 让 `python -m backend.app` 在命令行也能正确解析项目根路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, request  # noqa: E402
from flask_cors import CORS  # noqa: E402
from sqlalchemy import and_, func, select, text  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.config import (  # noqa: E402
    MYSQL_CONFIG,
    USE_MYSQL,
    build_mysql_url,
    build_sqlite_url,
)
from backend.models import (  # noqa: E402
    Base,
    DiskTsar,
    HostDetail,
    ModDetail,
    PrefTsar,
)

BEIJING = timezone(timedelta(hours=8))

# ---------- Flask 初始化 ----------
app = Flask(__name__, static_folder=None)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = False


def _resolve_engine() -> Engine:
    """创建 SQLAlchemy Engine；MySQL 不可用时自动回退到 SQLite。"""
    from sqlalchemy import create_engine

    urls_to_try = []
    if USE_MYSQL:
        urls_to_try.append(build_mysql_url())
    urls_to_try.append(build_sqlite_url())

    last_err: Optional[Exception] = None
    for url in urls_to_try:
        try:
            engine = create_engine(
                url,
                echo=False,
                future=True,
                **(
                    {"connect_args": {"check_same_thread": False}}
                    if "sqlite" in url
                    else {"pool_size": 10, "pool_recycle": 1800, "max_overflow": 20}
                ),
            )
            # 测试一次实际连接
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            # 建表（如果尚未创建）
            Base.metadata.create_all(engine)
            print(f"[INFO] 后端已连接 {engine.url.drivername}.")
            return engine
        except Exception as exc:
            last_err = exc
            print(f"[WARN] 无法连接 {url.split('?')[0]}: {exc}")
    raise RuntimeError(f"所有数据库引擎都不可用，最后一次错误: {last_err}")


engine = _resolve_engine()


# ---------- 工具函数 ----------

def _parse_dt(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        return None


def _paginate(query, page: int, page_size: int):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


# ---------- 健康检查 ----------

@app.route("/health", methods=["GET"])
def health():
    with Session(engine) as session:
        host_cnt = session.query(HostDetail).count()
        mod_cnt = session.query(ModDetail).count()
    return jsonify(
        {
            "ok": True,
            "engine": engine.url.drivername,
            "host_detail_rows": host_cnt,
            "mod_detail_rows": mod_cnt,
            "now_beijing": datetime.now(tz=BEIJING).strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


# ---------- 主机与指标维度接口 ----------

@app.route("/api/hosts", methods=["GET"])
def list_hosts():
    with Session(engine) as session:
        hosts = session.query(HostDetail).all()
        return jsonify([h.to_dict() for h in hosts])


@app.route("/api/metrics", methods=["GET"])
def list_metrics():
    type_filter = request.args.get("type", "").strip()
    with Session(engine) as session:
        q = session.query(ModDetail)
        if type_filter in ("disk", "pref"):
            q = q.filter(ModDetail.type == type_filter)
        return jsonify([m.to_dict() for m in q.all()])


# ---------- 事实表：原始查询 ----------

def _query_fact(cls, _unused_base=None):
    hostid = request.args.get("hostid")
    mod = request.args.get("mod")
    start = _parse_dt(request.args.get("start"))
    end = _parse_dt(request.args.get("end"))
    page = max(1, int(request.args.get("page", 1) or 1))
    page_size = min(500, max(1, int(request.args.get("page_size", 200) or 200)))

    conds: list = []
    if hostid:
        conds.append(cls.hostid == hostid)
    if mod:
        conds.append(cls.mod == mod)
    if start:
        conds.append(cls.dt >= start)
    if end:
        conds.append(cls.dt <= end)

    with Session(engine) as session:
        base = session.query(cls)
        if conds:
            base = base.filter(and_(*conds))
        base = base.order_by(cls.ts.asc())
        total = base.count()
        items = base.offset((page - 1) * page_size).limit(page_size).all()

    return jsonify(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [r.to_dict() for r in items],
        }
    )


@app.route("/api/disk", methods=["GET"])
def list_disk():
    return _query_fact(DiskTsar, None)  # type: ignore[arg-type]


@app.route("/api/pref", methods=["GET"])
def list_pref():
    return _query_fact(PrefTsar, None)  # type: ignore[arg-type]


# ---------- 聚合接口：按小时 avg/max/min/count ----------

def _hourly_agg(cls) -> dict:
    hostid = request.args.get("hostid")
    mod = request.args.get("mod")
    start = _parse_dt(request.args.get("start"))
    end = _parse_dt(request.args.get("end"))
    limit = min(2000, max(1, int(request.args.get("limit", 720) or 720)))

    with Session(engine) as session:
        # 同时 JOIN 到 host_detail / mod_detail，给出中文维度信息
        q = (
            session.query(
                cls.dt,
                cls.hour,
                cls.hostid,
                cls.mod,
                func.avg(cls.value).label("avg_value"),
                func.max(cls.value).label("max_value"),
                func.min(cls.value).label("min_value"),
                func.count(cls.value).label("sample_cnt"),
            )
        )
        conds: list = []
        if hostid:
            conds.append(cls.hostid == hostid)
        if mod:
            conds.append(cls.mod == mod)
        if start:
            conds.append(cls.dt >= start)
        if end:
            conds.append(cls.dt <= end)
        if conds:
            q = q.filter(and_(*conds))
        q = q.group_by(cls.dt, cls.hour, cls.hostid, cls.mod).order_by(cls.dt.asc(), cls.hour.asc()).limit(limit)

        rows = []
        for r in q.all():
            rows.append(
                {
                    "dt": r.dt,
                    "hour": int(r.hour),
                    "hostid": r.hostid,
                    "mod": r.mod,
                    "avg_value": float(r.avg_value) if r.avg_value is not None else None,
                    "max_value": float(r.max_value) if r.max_value is not None else None,
                    "min_value": float(r.min_value) if r.min_value is not None else None,
                    "sample_cnt": int(r.sample_cnt),
                }
            )
    return {"rows": rows, "count": len(rows)}


@app.route("/api/agg/disk-hourly", methods=["GET"])
def agg_disk_hourly():
    return jsonify(_hourly_agg(DiskTsar))


@app.route("/api/agg/pref-hourly", methods=["GET"])
def agg_pref_hourly():
    return jsonify(_hourly_agg(PrefTsar))


# ---------- 大屏汇总数据（一次性返回） ----------

@app.route("/api/dashboard/summary", methods=["GET"])
def dashboard_summary():
    """返回大屏需要的所有数据：

    - 主机、指标计数
    - 每类数据的行数
    - CPU/内存/网络/磁盘 等按小时平均（20 主机合并平均）
    - 按机房分组的 CPU / 磁盘 sda 箱线图统计（5 数）
    - 主机汇总表（每台主机的 cpu_usage / mem_used / sda_util 均值）
    """
    result: dict = {
        "counts": {},
        "cpu_hourly": [],
        "net_hourly": [],
        "disk_hourly": [],
        "mem_hourly": [],
        "radar": {},
        "samples_hourly": [],
        "box_by_idc": {},
        "host_summary": [],
        "now_beijing": datetime.now(tz=BEIJING).strftime("%Y-%m-%d %H:%M:%S"),
    }

    with Session(engine) as session:
        # ------ 计数 ------
        result["counts"]["host_detail"] = session.query(HostDetail).count()
        result["counts"]["mod_detail"] = session.query(ModDetail).count()
        result["counts"]["disk_tsar"] = session.query(DiskTsar).count()
        result["counts"]["pref_tsar"] = session.query(PrefTsar).count()

        # ------ CPU / Net / MEM 小时级平均 (20 主机平均) ------
        def avg_by_hour(mod_key: str) -> list[dict]:
            q = (
                session.query(
                    PrefTsar.dt,
                    PrefTsar.hour,
                    func.avg(PrefTsar.value).label("avg_value"),
                )
                .filter(PrefTsar.mod == mod_key)
                .group_by(PrefTsar.dt, PrefTsar.hour)
                .order_by(PrefTsar.dt.asc(), PrefTsar.hour.asc())
                .limit(336)  # 最多 2 周
            )
            return [
                {
                    "dt": r.dt,
                    "hour": int(r.hour),
                    "avg": float(r.avg_value) if r.avg_value is not None else None,
                }
                for r in q.all()
            ]

        result["cpu_hourly"] = {
            "cpu_usage": avg_by_hour("cpu_usage"),
            "cpu_idle": avg_by_hour("cpu_idle"),
        }
        result["net_hourly"] = {
            "net_in": avg_by_hour("net_in"),
            "net_out": avg_by_hour("net_out"),
        }
        result["mem_hourly"] = {
            "mem_used": avg_by_hour("mem_used"),
        }

        # ------ 磁盘 sda / sdb 小时平均（20 主机平均） ------
        def disk_avg_by_hour(mod_key: str) -> list[dict]:
            q = (
                session.query(
                    DiskTsar.dt,
                    DiskTsar.hour,
                    func.avg(DiskTsar.value).label("avg_value"),
                )
                .filter(DiskTsar.mod == mod_key)
                .group_by(DiskTsar.dt, DiskTsar.hour)
                .order_by(DiskTsar.dt.asc(), DiskTsar.hour.asc())
                .limit(336)
            )
            return [
                {
                    "dt": r.dt,
                    "hour": int(r.hour),
                    "avg": float(r.avg_value) if r.avg_value is not None else None,
                }
                for r in q.all()
            ]

        result["disk_hourly"] = {
            "sda_util": disk_avg_by_hour("sda_util"),
            "sdb_util": disk_avg_by_hour("sdb_util"),
        }

        # ------ 雷达：关键指标整体平均 / 最大 ------
        def agg_for_radar() -> dict:
            keys = [
                ("cpu_usage", "pref"),
                ("cpu_idle", "pref"),
                ("mem_used", "pref"),
                ("net_in", "pref"),
                ("net_out", "pref"),
                ("sda_util", "disk"),
                ("sdb_util", "disk"),
                ("load1", "pref"),
            ]
            out = {}
            for mod_key, mtype in keys:
                cls = PrefTsar if mtype == "pref" else DiskTsar
                row = (
                    session.query(
                        func.avg(cls.value).label("avg_v"),
                        func.max(cls.value).label("max_v"),
                    )
                    .filter(cls.mod == mod_key)
                    .first()
                )
                out[mod_key] = {
                    "avg": float(row.avg_v) if row and row.avg_v is not None else 0.0,
                    "max": float(row.max_v) if row and row.max_v is not None else 0.0,
                }
            return out

        result["radar"] = agg_for_radar()

        # ------ 每小时采样数（pref） ------
        sample_rows = (
            session.query(PrefTsar.dt, PrefTsar.hour, func.count(PrefTsar.id).label("cnt"))
            .group_by(PrefTsar.dt, PrefTsar.hour)
            .order_by(PrefTsar.dt.asc(), PrefTsar.hour.asc())
            .limit(500)
            .all()
        )
        result["samples_hourly"] = [
            {"dt": r.dt, "hour": int(r.hour), "count": int(r.cnt)} for r in sample_rows
        ]

        # ------ 按机房分组的箱线图统计 ------
        def box_for_metric(mod_key: str, mtype: str) -> dict:
            cls = PrefTsar if mtype == "pref" else DiskTsar
            q = (
                session.query(
                    HostDetail.location1, cls.value,
                )
                .join(HostDetail, HostDetail.hostid == cls.hostid)
                .filter(cls.mod == mod_key)
                .all()
            )
            by_loc: dict[str, list[float]] = {}
            for loc, val in q:
                if loc is None:
                    loc = "未知"
                by_loc.setdefault(loc, []).append(float(val or 0))

            out = {}
            for loc, vals in by_loc.items():
                if not vals:
                    continue
                vals_sorted = sorted(vals)
                n = len(vals_sorted)
                def pct(p):
                    idx = p * (n - 1)
                    lo = int(idx)
                    hi = min(lo + 1, n - 1)
                    return vals_sorted[lo] + (vals_sorted[hi] - vals_sorted[lo]) * (idx - lo)
                out[loc] = [
                    vals_sorted[0],
                    pct(0.25),
                    pct(0.5),
                    pct(0.75),
                    vals_sorted[-1],
                ]
            return out

        result["box_by_idc"] = {
            "cpu_usage": box_for_metric("cpu_usage", "pref"),
            "sda_util": box_for_metric("sda_util", "disk"),
        }

        # ------ 主机汇总表 ------
        host_summary_rows = []
        hosts = session.query(HostDetail).all()
        for h in hosts:
            cpu_row = (
                session.query(func.avg(PrefTsar.value))
                .filter(PrefTsar.mod == "cpu_usage", PrefTsar.hostid == h.hostid)
                .scalar()
            )
            mem_row = (
                session.query(func.avg(PrefTsar.value))
                .filter(PrefTsar.mod == "mem_used", PrefTsar.hostid == h.hostid)
                .scalar()
            )
            sda_row = (
                session.query(func.avg(DiskTsar.value))
                .filter(DiskTsar.mod == "sda_util", DiskTsar.hostid == h.hostid)
                .scalar()
            )
            host_summary_rows.append(
                {
                    "hostid": h.hostid,
                    "hostname": h.hostname,
                    "owner": h.owner,
                    "model": h.model,
                    "location1": h.location1,
                    "location2": h.location2,
                    "cpu_avg": float(cpu_row) if cpu_row is not None else None,
                    "mem_avg": float(mem_row) if mem_row is not None else None,
                    "sda_avg": float(sda_row) if sda_row is not None else None,
                }
            )
        result["host_summary"] = host_summary_rows

    return jsonify(result)


# ---------- ETL 手动触发接口 ----------

@app.route("/api/etl/run", methods=["POST"])
def api_run_etl():
    """触发一次 ETL，参数 reset=true 会先清空表。

    示例：
        curl -X POST "http://127.0.0.1:5001/api/etl/run?reset=true"
    """
    reset = request.args.get("reset", "false").lower() == "true"
    try:
        from backend.utils.etl import run_etl

        stats = run_etl(reset=reset)
        return jsonify({"ok": True, "stats": stats})
    except Exception as exc:  # pragma: no cover
        return jsonify({"ok": False, "error": str(exc)}), 500


# ---------- 自定义查询示例：query_results_sample.txt 风格 ----------

@app.route("/api/query/samples", methods=["GET"])
def query_samples():
    """返回与 `query_results_sample.txt` 里四份查询等价的 JSON：

    q1. disk_tsar 前 10 条（按 ts 排序，带日期/小时/分钟解析列）
    q2. pref_tsar 按 (hostid, mod) 汇总，前 20 条
    q3. host001 × cpu_usage 24 小时走势
    q4. JOIN 主机 + 指标维度，按 (idc, hostname, metric_desc) 汇总，前 30 条
    """
    out = {}
    with Session(engine) as session:
        # q1
        q1_rows = (
            session.query(DiskTsar)
            .order_by(DiskTsar.ts.asc())
            .limit(10)
            .all()
        )
        out["q1_disk_tsar_sample"] = [r.to_dict() for r in q1_rows]

        # q2
        q2_rows = (
            session.query(
                PrefTsar.dt,
                PrefTsar.hour,
                PrefTsar.hostid,
                PrefTsar.mod,
                func.avg(PrefTsar.value).label("avg_value"),
                func.max(PrefTsar.value).label("max_value"),
                func.min(PrefTsar.value).label("min_value"),
                func.count(PrefTsar.value).label("sample_cnt"),
            )
            .group_by(PrefTsar.dt, PrefTsar.hour, PrefTsar.hostid, PrefTsar.mod)
            .order_by(PrefTsar.dt.asc(), PrefTsar.hour.asc(), PrefTsar.hostid.asc(), PrefTsar.mod.asc())
            .limit(20)
            .all()
        )
        out["q2_pref_hourly"] = [
            {
                "dt": r.dt,
                "hour": int(r.hour),
                "hostid": r.hostid,
                "mod": r.mod,
                "avg_value": float(r.avg_value) if r.avg_value is not None else None,
                "max_value": float(r.max_value) if r.max_value is not None else None,
                "min_value": float(r.min_value) if r.min_value is not None else None,
                "sample_cnt": int(r.sample_cnt),
            }
            for r in q2_rows
        ]

        # q3
        q3_rows = (
            session.query(
                PrefTsar.dt,
                PrefTsar.hour,
                func.avg(PrefTsar.value).label("avg_value"),
                func.max(PrefTsar.value).label("max_value"),
            )
            .filter(PrefTsar.hostid == "host001", PrefTsar.mod == "cpu_usage")
            .group_by(PrefTsar.dt, PrefTsar.hour)
            .order_by(PrefTsar.dt.asc(), PrefTsar.hour.asc())
            .limit(24)
            .all()
        )
        out["q3_host001_cpu_usage_24h"] = [
            {
                "dt": r.dt,
                "hour": int(r.hour),
                "avg_value": float(r.avg_value) if r.avg_value is not None else None,
                "max_value": float(r.max_value) if r.max_value is not None else None,
            }
            for r in q3_rows
        ]

        # q4
        q4_rows = (
            session.query(
                PrefTsar.dt,
                PrefTsar.hour,
                HostDetail.location1.label("idc_name"),
                HostDetail.hostname,
                ModDetail.desc.label("metric_desc"),
                ModDetail.unit,
                func.count(PrefTsar.value).label("sample_cnt"),
                func.avg(PrefTsar.value).label("avg_value"),
            )
            .join(HostDetail, HostDetail.hostid == PrefTsar.hostid)
            .join(ModDetail, ModDetail.mod == PrefTsar.mod)
            .group_by(PrefTsar.dt, PrefTsar.hour, HostDetail.location1, HostDetail.hostname, ModDetail.desc, ModDetail.unit)
            .order_by(PrefTsar.dt.asc(), PrefTsar.hour.asc(), HostDetail.location1.asc(), HostDetail.hostname.asc())
            .limit(30)
            .all()
        )
        out["q4_pref_joined_summary"] = [
            {
                "dt": r.dt,
                "hour": int(r.hour),
                "idc_name": r.idc_name,
                "hostname": r.hostname,
                "metric_desc": r.metric_desc,
                "unit": r.unit,
                "sample_cnt": int(r.sample_cnt),
                "avg_value": float(r.avg_value) if r.avg_value is not None else None,
            }
            for r in q4_rows
        ]
    return jsonify(out)


# ---------- 主入口 ----------

def run_server():
    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", "5001"))
    print(
        f"[INFO] 启动服务器监控数据可视化后端 "
        f"(http://{host}:{port})"
    )
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    run_server()
