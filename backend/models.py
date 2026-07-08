"""SQLAlchemy ORM 模型。

4 张表：
1. host_detail  -- 主机信息明细表（维度表）
2. mod_detail   -- 指标字典表（维度表）
3. disk_tsar    -- 磁盘采集表（5 分钟/次，事实表）
4. pref_tsar    -- 性能采集表（1 小时/次，事实表）

为了让查询与前端聚合更快，disk_tsar / pref_tsar 同时保留：
- ts       原始毫秒时间戳
- dt       YYYY-MM-DD 日期分区
- hour     0-23 小时
- minute   0-59 分钟
- value    数值化后的 value（DECIMAL(18,2)）
"""
from sqlalchemy import (
    Column,
    Index,
    Integer,
    BigInteger,
    String,
    DECIMAL,
    SmallInteger,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class HostDetail(Base):
    __tablename__ = "host_detail"

    hostid = Column(String(64), primary_key=True, comment="主机ID")
    hostname = Column(String(190), nullable=False, comment="主机名/域名")
    owner = Column(String(64), comment="负责人")
    model = Column(String(128), comment="型号")
    location1 = Column(String(64), comment="机房名称")
    location2 = Column(String(64), comment="机柜编号")

    __table_args__ = (
        Index("ix_host_owner", "owner"),
        Index("ix_host_location1", "location1"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    def to_dict(self) -> dict:
        return {
            "hostid": self.hostid,
            "hostname": self.hostname,
            "owner": self.owner,
            "model": self.model,
            "location1": self.location1,
            "location2": self.location2,
        }


class ModDetail(Base):
    __tablename__ = "mod_detail"

    mod = Column(String(64), primary_key=True, comment="指标代码")
    type = Column(String(16), nullable=False, comment="分类: disk / pref")
    desc = Column(String(190), comment="中文描述")
    unit = Column(String(32), comment="单位")
    tag = Column(String(64), comment="二级标签")

    __table_args__ = (
        Index("ix_mod_type", "type"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    def to_dict(self) -> dict:
        return {
            "mod": self.mod,
            "type": self.type,
            "desc": self.desc,
            "unit": self.unit,
            "tag": self.tag,
        }


class DiskTsar(Base):
    __tablename__ = "disk_tsar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(BigInteger, nullable=False, index=True, comment="毫秒时间戳")
    hostid = Column(String(64), nullable=False, index=True, comment="主机ID")
    mod = Column(String(64), nullable=False, index=True, comment="指标代码")
    value = Column(DECIMAL(18, 2), nullable=False, comment="采集数值")
    dt = Column(String(10), nullable=False, index=True, comment="YYYY-MM-DD")
    hour = Column(SmallInteger, nullable=False, index=True, comment="0-23")
    minute = Column(SmallInteger, nullable=False, index=True, comment="0-59")

    __table_args__ = (
        Index("ix_disk_host_mod_hour", "hostid", "mod", "dt", "hour"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "sqlite_autoincrement": True},
    )

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "hostid": self.hostid,
            "mod": self.mod,
            "value": float(self.value) if self.value is not None else None,
            "dt": self.dt,
            "hour": int(self.hour),
            "minute": int(self.minute),
        }


class PrefTsar(Base):
    __tablename__ = "pref_tsar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(BigInteger, nullable=False, index=True, comment="毫秒时间戳")
    hostid = Column(String(64), nullable=False, index=True, comment="主机ID")
    mod = Column(String(64), nullable=False, index=True, comment="指标代码")
    value = Column(DECIMAL(18, 2), nullable=False, comment="采集数值")
    dt = Column(String(10), nullable=False, index=True, comment="YYYY-MM-DD")
    hour = Column(SmallInteger, nullable=False, index=True, comment="0-23")
    minute = Column(SmallInteger, nullable=False, index=True, comment="0-59")

    __table_args__ = (
        Index("ix_pref_host_mod_hour", "hostid", "mod", "dt", "hour"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "sqlite_autoincrement": True},
    )

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "hostid": self.hostid,
            "mod": self.mod,
            "value": float(self.value) if self.value is not None else None,
            "dt": self.dt,
            "hour": int(self.hour),
            "minute": int(self.minute),
        }
