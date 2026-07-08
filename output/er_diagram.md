# E-R 关系图

## 说明

- 事实表：`tsar_detail`（由 `disk_tsar.dat` 与 `pref_tsar.dat` 合并而成）
- 维度表：`host_detail`（主机）、`mod_detail`（指标字典）
- 关系：`host_detail 1:N tsar_detail`；`mod_detail 1:N tsar_detail`

## Mermaid E-R 图

```mermaid
erDiagram
    host_detail "主机信息明细表（维度表）" {
        string hostid PK
        string hostname
        string owner
        string model
        string location1
        string location2
    }
    mod_detail "指标(MOD)字典表（维度表）" {
        string mod PK
        string type
        string desc
        string unit
        string tag
    }
    tsar_detail "监控采集明细表（事实表）= disk_tsar + pref_tsar" {
        long_(ms) ts PK
        string hostid PK FK
        string type
        string mod PK FK
        double value
        string tag
    }
    host_detail ||--o{ tsar_detail : "hostid / 1:N"
    mod_detail ||--o{ tsar_detail : "mod / 1:N"
```
