# Version 3 — Admission Correction Experiment Plan

**Date:** 2026-07-24  
**Status:** Plan Only · **実行なし**  
**Parent:** [`v3-admission-correction-design.md`](./v3-admission-correction-design.md)  
**Candidate:** A-05（Favorite-Safe Coverage Admission）

---

## 1. Objective

A-05 が Offline Gate で A-03 起因の本命破壊を抑えつつ、net Hit を Control より改善できるかを、  
**実装承認後の別 Round** で検証する計画を定義する。

本 Round では実験を実行しない。

---

## 2. Experiment IDs（予約）

| ID | 内容 |
|----|------|
| `v3-a05-design` | 本設計 Round（完了） |
| `v3-a05-accuracy` | Lab Accuracy（未実施） |
| `v3-a05-offline-gate` | Offline Gate 再評価（未実施） |
| `v3-a05-validation` | 再現・隔離 Validation（未実施） |
| `v3-a05-candidate-review` | A-03 置換可否レビュー（未実施） |

---

## 3. Arms

| Arm | Flags | 目的 |
|-----|-------|------|
| C0 Control | 全 Lab Flag OFF | Offline / Lab 基準 |
| T1 A-05 solo | A-05 ON のみ | Admission 単体効果 |
| T2 Stack-A05 | A-01 + A-05 + A-04 | Baseline v3 の A-03→A-05 置換相当 |
| R1 Contrast-A03 | A-01 + A-03 + A-04 | 現行 Baseline v3（参照・改変なし） |
| X Forbidden | A-03 ∧ A-05 同時 ON | **実行禁止**（設計違反） |

---

## 4. Corpora

| Corpus | 役割 | Gate |
|--------|------|------|
| Lab Accuracy 285R（既存合成） | 回帰・Pool 層観測 | Lab Gate |
| Offline Real labeled_test 285R | **主判定** | Offline Hard Gate |
|（推奨・任意） Lab Real-like field 拡張 | 過適合早期検知 | Soft 監視 |

---

## 5. Metrics

| Metric | 定義 | 主用途 |
|--------|------|--------|
| Hit | top-1 pick == winner | 主指標 |
| ΔHit | Treatment − Control | Offline 必須 |
| churn_hit | pick 変更レース数 | 監視 |
| worsened_rank1 | Control HIT かつ winner_rank=1 かつ Treatment MISS | **必須 Hard** |
| improved | Control MISS → Treatment HIT | 深掘り回収 |
| promote_rate | journal.promote / n | 発火率 |
| promote_precision | promote かつ promoted==winner / promote | 品質 |
| favsafe_block_rate | favsafe により不発火した割合 | 保護動作確認 |

---

## 6. Procedure（実装後 Round の手順案）

1. A-05 実装 + Flag 追加（既定 OFF）· A-03 非変更  
2. Isolation チェック（差分が Admission/Flag/Registry のみ）  
3. Lab: C0 / T1 / T2 実行 · LG-* 確認  
4. Offline: C0 / T1 / T2 / R1 実行 · OG-* 判定  
5. Race Diff · worsened_rank1 ゼロ確認  
6. Validation（再現 2 回）  
7. Candidate Review（A-03 を Baseline から外すか Decision）  

**Shadow / Production は Candidate Review PASS かつ PRR 更新後のみ。**

---

## 7. AB 比較マトリクス

| 比較 | 仮説 |
|------|------|
| T1 vs C0 | A-05 単独で本命非破壊かつ ΔHit≥0 か |
| T2 vs C0 | 置換スタックが Offline PASS か |
| T2 vs R1 | A-05 が A-03 スタックより優れるか（Hit・worsened_rank1） |
| T2 Lab vs R1 Lab | Lab 279 からの落ち幅が許容か（参考） |

---

## 8. パラメータ校正プロトコル

1. FavSafe `MARGIN_MIN` を強めから開始（promote 抑制）  
2. Offline で `worsened_rank1=0` を満たす最大のゆるさまで緩和  
3. その上で ΔHit・improved・promote_precision を最大化  
4. 閾値は事前に少数候補を登録し、無制限探索しない  

---

## 9. Stop（本 Round）

実験計画の文書化まで。Accuracy / Offline / AB 実行には着手しない。
