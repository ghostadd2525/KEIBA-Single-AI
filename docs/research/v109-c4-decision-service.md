# Version109 Phase C4 — Decision Service（Composer）

**Date:** 2026-07-29  
**Status:** Shadow library · Production 配線禁止  
**Parents:** PLATFORM-V1-CONTRACT · ADR-009/010/011 · C1–C3

---

## 一文

**Decision Service は Composer である。Reasoner ではない。**

---

## 入出力

| 入力 | 出力 |
|---|---|
| Core Payload（read-only） | `SingleResponseDTO` / `single-response/v1` |
| Presentation DTO | 埋め込み（再計算しない） |
| Ticket DTO | 埋め込み（再計算しない） |
| Policy Metadata | registry / policy_metadata |
| Feature Flags | セクション省略のみ |

---

## パッケージ

```text
app/consumer/decision_service/
  dto.py        SingleResponseDTO + VersionInfo
  composer.py   compose() + validation
  service.py    DecisionService (legacy / shadow_assemble)
```

`build_single_response` → DecisionService → `consumer-api/single/v1` 互換 dict

---

## 禁止遵守

Prediction / Ranking / Score / World / NM / Affinity / EC / Policy 非変更  
Ticket 再計算なし（prebuilt 優先）  
NL / Decision Reason = null  
Core Payload 完全一致エコー

---

## Flag / Mode

| Mode | 条件 |
|---|---|
| LEGACY | presentation/ticket なし |
| SHADOW | force / include_* |

Production / Canary / Staging = **別 Gate**
