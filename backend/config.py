"""数据库与项目路径配置。

使用策略：
1. 若环境变量 `USE_MYSQL=1`（默认），优先连接 MySQL；如果 MySQL 不可用（未安装/未启动）
   则自动回退到 SQLite，保证本地能完整跑通。
2. 数据库配置通过环境变量覆盖，示例：
   set MYSQL_HOST=127.0.0.1
   set MYSQL_PORT=3306
   set MYSQL_USER=root
   set MYSQL_PWD=123456
   set MYSQL_DB=server_metrics
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR  # 原始 .dat 数据文件位于项目根目录

# MySQL 配置
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PWD", "123456"),
    "database": os.environ.get("MYSQL_DB", "server_metrics"),
    "charset": "utf8mb4",
}

SQLITE_PATH = BASE_DIR / "server_metrics.db"
USE_MYSQL = os.environ.get("USE_MYSQL", "1") == "1"


def build_mysql_url() -> str:
    return (
        f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
        f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
        f"?charset={MYSQL_CONFIG['charset']}"
    )


def build_sqlite_url() -> str:
    return f"sqlite:///{SQLITE_PATH}"


__all__ = [
    "BASE_DIR",
    "DATA_DIR",
    "MYSQL_CONFIG",
    "SQLITE_PATH",
    "USE_MYSQL",
    "build_mysql_url",
    "build_sqlite_url",
]
