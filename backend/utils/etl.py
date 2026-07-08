"""ETL：把 4 个 .dat 文件解析后写入 MySQL/SQLite。

用法：
    python -m backend.utils.etl           # 执行导入
    python -m backend.utils.etl --reset   # 清空表后再导入
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# 允许在 `python -m backend.utils.etl` 方式下导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.config import (  # noqa: E402
    BASE_DIR,
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

BATCH_SIZE = 2000  # 每 2000 条提交一次事务，降低内存压力


def _parse_header_tsar(line: str) -> list[str]:
    """disk_tsar / pref_tsar 的表头：`ts\thostid\tmod\tvalue`。"""
    return [c.strip() for c in line.split("\t") if c.strip() != ""]


def _parse_ts_beijing(ts_ms: int) -> tuple[str, int, int]:
    """把毫秒时间戳拆成 (YYYY-MM-DD, hour, minute) — 按北京时区。"""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=BEIJING)
    return dt.strftime("%Y-%m-%d"), dt.hour, dt.minute


def _read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    """读取 tab 分隔文件，返回 (表头字段列表, 数据二维列表)。

    - 第 1 行为表头
    - 其他行为数据；若某行字段数与表头不一致，自动补齐/裁剪
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\r\n") for ln in f if ln.strip() != ""]
    if not lines:
        return [], []

    header = [c.strip() for c in lines[0].split("\t") if c.strip() != ""]
    rows: list[list[str]] = []
    for ln in lines[1:]:
        cols = ln.split("\t")
        # 对齐字段数，防止脏数据
        if len(cols) < len(header):
            cols = cols + [""] * (len(header) - len(cols))
        elif len(cols) > len(header):
            cols = cols[: len(header)]
        rows.append([c.strip() for c in cols])
    return header, rows


def _ensure_mysql_database() -> None:
    """如果 USE_MYSQL=1：先尝试连接到 MySQL 并创建库；失败则关闭 USE_MYSQL。"""
    if not USE_MYSQL:
        return
    try:
        import pymysql  # noqa: F401
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] pymysql 未安装: {exc}，自动回退到 SQLite。")
        globals()["USE_MYSQL_RUNTIME"] = False  # type: ignore[attr-defined]
        return

    cfg = MYSQL_CONFIG
    try:
        import pymysql

        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            charset=cfg["charset"],
        )
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        cur.close()
        conn.close()
        print(f"[INFO] 已确认 MySQL 库 `{cfg['database']}` 存在。")
    except Exception as exc:
        print(
            f"[WARN] 无法连接 MySQL({cfg['host']}:{cfg['port']}, user={cfg['user']}): {exc}。"
            "将自动回退到 SQLite 模式，保证本地功能可用。"
        )
        globals()["USE_MYSQL_RUNTIME"] = False  # type: ignore[attr-defined]


def _make_engine() -> Engine:
    # 优先：MySQL；不可用时回退到 SQLite
    if getattr(sys.modules[__name__], "USE_MYSQL_RUNTIME", None) is False:
        url = build_sqlite_url()
    else:
        url = build_mysql_url() if USE_MYSQL else build_sqlite_url()

    engine = create_engine(
        url,
        echo=False,
        future=True,
        # SQLite: 支持多线程；MySQL: 连接池
        **(
            {"connect_args": {"check_same_thread": False}}
            if "sqlite" in url
            else {"pool_size": 10, "pool_recycle": 1800, "max_overflow": 20}
        ),
    )
    return engine


def _create_tables(engine: Engine, reset: bool = False) -> None:
    with engine.begin() as conn:
        if reset:
            # 按外键依赖的相反顺序删表
            for tbl in reversed(Base.metadata.sorted_tables):
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {tbl.name}"))
                except Exception as exc:  # pragma: no cover
                    print(f"[WARN] 删除 {tbl.name} 失败: {exc}")
        Base.metadata.create_all(conn)
    print(f"[INFO] 数据表已就绪 (engine: {engine.url.drivername}).")


# ---------- 维度表：host_detail / mod_detail ----------

def _upsert_host_detail(session: Session, rows: list[list[str]], header: list[str]) -> int:
    """批量 upsert。若 hostid 已存在则更新其他字段。

    为了在 MySQL/SQLite 都能用，这里采用“先查询再插入/更新”的简单策略，
    实际行数不大（20 条），性能足够。
    """
    idx_hostid = header.index("hostid") if "hostid" in header else 0
    idx_hostname = header.index("hostname") if "hostname" in header else 1
    idx_owner = header.index("owner") if "owner" in header else 2
    idx_model = header.index("model") if "model" in header else 3
    idx_loc1 = header.index("location1") if "location1" in header else 4
    idx_loc2 = header.index("location2") if "location2" in header else 5

    existing = {h.hostid: h for h in session.query(HostDetail).all()}
    written = 0
    for r in rows:
        if len(r) <= idx_hostid:
            continue
        hostid = r[idx_hostid] or ""
        if not hostid:
            continue
        h = existing.get(hostid)
        if h is None:
            h = HostDetail(hostid=hostid)
            session.add(h)
            existing[hostid] = h
        h.hostname = r[idx_hostname] if len(r) > idx_hostname else ""
        h.owner = r[idx_owner] if len(r) > idx_owner else ""
        h.model = r[idx_model] if len(r) > idx_model else ""
        h.location1 = r[idx_loc1] if len(r) > idx_loc1 else ""
        h.location2 = r[idx_loc2] if len(r) > idx_loc2 else ""
        written += 1
    session.commit()
    return written


def _upsert_mod_detail(session: Session, rows: list[list[str]], header: list[str]) -> int:
    idx_mod = header.index("mod") if "mod" in header else 0
    idx_type = header.index("type") if "type" in header else 1
    idx_desc = header.index("desc") if "desc" in header else 2
    idx_unit = header.index("unit") if "unit" in header else 3
    idx_tag = header.index("tag") if "tag" in header else 4

    existing = {m.mod: m for m in session.query(ModDetail).all()}
    written = 0
    for r in rows:
        if len(r) <= idx_mod:
            continue
        mod = r[idx_mod] or ""
        if not mod:
            continue
        m = existing.get(mod)
        if m is None:
            m = ModDetail(mod=mod)
            session.add(m)
            existing[mod] = m
        m.type = r[idx_type] if len(r) > idx_type else ""
        m.desc = r[idx_desc] if len(r) > idx_desc else ""
        m.unit = r[idx_unit] if len(r) > idx_unit else ""
        m.tag = r[idx_tag] if len(r) > idx_tag else ""
        written += 1
    session.commit()
    return written


# ---------- 事实表：disk_tsar / pref_tsar（批量 insert） ----------

def _bulk_insert_fact(
    session: Session,
    rows: list[list[str]],
    header: list[str],
    cls,
) -> int:
    idx_ts = header.index("ts") if "ts" in header else 0
    idx_hostid = header.index("hostid") if "hostid" in header else 1
    idx_mod = header.index("mod") if "mod" in header else 2
    idx_value = header.index("value") if "value" in header else 3

    buffer: list[dict] = []
    total = 0

    def flush() -> None:
        nonlocal buffer, total
        if buffer:
            session.bulk_insert_mappings(cls, buffer)
            session.commit()
            total += len(buffer)
            buffer = []

    for r in rows:
        if len(r) <= idx_value:
            continue
        try:
            ts = int(r[idx_ts])
        except ValueError:
            continue
        hostid = r[idx_hostid] or ""
        mod = r[idx_mod] or ""
        try:
            value = float(r[idx_value])
        except ValueError:
            continue
        dt, hour, minute = _parse_ts_beijing(ts)
        buffer.append(
            {
                "ts": ts,
                "hostid": hostid,
                "mod": mod,
                "value": value,
                "dt": dt,
                "hour": hour,
                "minute": minute,
            }
        )
        if len(buffer) >= BATCH_SIZE:
            flush()
    flush()
    return total


def run_etl(reset: bool = False) -> dict:
    t0 = time.time()
    _ensure_mysql_database()
    engine = _make_engine()
    _create_tables(engine, reset=reset)

    files = {
        "host_detail": BASE_DIR / "host_detail.dat",
        "mod_detail": BASE_DIR / "mod_detail.dat",
        "disk_tsar": BASE_DIR / "disk_tsar.dat",
        "pref_tsar": BASE_DIR / "pref_tsar.dat",
    }

    # 校验文件存在
    for name, fp in files.items():
        if not fp.exists():
            raise FileNotFoundError(f"找不到数据文件: {fp}")

    stats: dict[str, int] = {}
    with Session(engine) as session:
        # 1) host_detail
        header, rows = _read_tsv(files["host_detail"])
        stats["host_detail"] = _upsert_host_detail(session, rows, header)
        print(f"[INFO] host_detail 写入 {stats['host_detail']} 行。")

        # 2) mod_detail
        header, rows = _read_tsv(files["mod_detail"])
        stats["mod_detail"] = _upsert_mod_detail(session, rows, header)
        print(f"[INFO] mod_detail 写入 {stats['mod_detail']} 行。")

        # 3) disk_tsar
        header, rows = _read_tsv(files["disk_tsar"])
        stats["disk_tsar"] = _bulk_insert_fact(session, rows, header, DiskTsar)
        print(f"[INFO] disk_tsar 写入 {stats['disk_tsar']} 行。")

        # 4) pref_tsar
        header, rows = _read_tsv(files["pref_tsar"])
        stats["pref_tsar"] = _bulk_insert_fact(session, rows, header, PrefTsar)
        print(f"[INFO] pref_tsar 写入 {stats['pref_tsar']} 行。")

    elapsed = time.time() - t0
    stats["elapsed_sec"] = round(elapsed, 2)
    stats["engine"] = engine.url.drivername
    print(f"[INFO] 入库完成 ({stats['engine']})，总耗时 {elapsed:.2f}s。")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL：把 .dat 写入 MySQL/SQLite")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="导入前先清空 4 张表（默认否）",
    )
    args = parser.parse_args()
    run_etl(reset=args.reset)


if __name__ == "__main__":
    main()
