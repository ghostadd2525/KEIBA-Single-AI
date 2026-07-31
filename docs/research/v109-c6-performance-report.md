# Version109 Phase C6 — Performance Report

**Date:** 2026-07-29  
**Mode:** Staging library harness · fixture `stg-r1` · repeats=25  
**Check:** `performance` · **PASS**

---

## 実測

| 指標 | Legacy (Flag OFF) | Staging (Flag ON) | Δ |
|---|---|---|---|
| mean latency | **0.63 ms** | **1.37 ms** | +0.74 ms |
| peak traced memory | **18.2 KB** | **34.5 KB** | +16.3 KB |
| exceptions | none | none | — |

（環境により数値は変動しうる。予算内であることが判定基準。）

---

## 予算（Staging soft）

| 予算 | 閾値 | 結果 |
|---|---|---|
| staging_mean_ms | < 50 ms | PASS |
| staging_peak_kb | < 50,000 KB | PASS |
| exceptions | none | PASS |

---

## 解釈

Consumer（Presentation + Ticket + Composer）追加のコストは同一プロセス内で **ミリ秒未満〜数 ms 級**。  
本測定は InMemory Core Client であり、ネットワーク I/O は含まない。Production HTTP 配線後の SLA は **別 Gate**。

---

## 禁止遵守

Prediction / Semantic / Core 変更なし。計測のみ。
