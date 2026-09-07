# Version102 — Explainability Flow

**Generated:** `2026-07-28T13:10:35+00:00`

## Flow

```text
Prediction → World → Near Miss → Affinity → Expected Strategy → Explanation Confidence
```

- flow closed rate: **1.0000**

Positive World では Near Miss / Affinity ノードをスキップして評価。

## Edge failures

```
{}
```

## 論理閉鎖の条件

各矢印の両端スロットが現有情報（または許容導出）で True であること。
Hit/ROI はフローに含めない。
