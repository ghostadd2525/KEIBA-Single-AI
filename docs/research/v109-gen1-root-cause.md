# GEN1 — Root Cause

**Primary:** `2026-08-01` Feature CSV 未生成。  
PI は features 無しでは CE できず、BFF は永続 202 PENDING。  
HTTP 202 後に生成ジョブを開始する Queue は存在しない。

**Why not Ready:** race_refresh 自動実行は **today (2026-07-29)** のみ。未来日 `2026-08-01-01-02` は自動対象外。

**Secondary:** 当日レースも PENDING → refresh 健全性を EC2 で要確認。

**Not the cause:** UI4 / Contract / Result Automation / Research Scheduler.
