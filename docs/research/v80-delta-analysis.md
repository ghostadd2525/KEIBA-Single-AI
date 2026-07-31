# Version80 — Delta Analysis（Attribution）

**Generated:** `2026-07-28T08:53:51+00:00`  
定義: ΔTrigger=CL−LL / ΔStrategy=CP−CL / ΔBoth=CP−LL / ΔInteraction=ΔBoth−ΔTrigger−ΔStrategy

## Full 285R

| Delta | Hit | Purchase | rank710 | other_1_3 | other_10_13 | rank46 | fpΔ |
|---|---:|---:|---:|---:|---:|---:|---|
| ΔTrigger (CL−LL) | 0 | 0 | 0 | 0 | 0 | 0 | N |
| ΔStrategy (CP−CL) | -133 | -133 | 18 | 79 | 1 | 36 | Y |
| ΔBoth (CP−LL) | -133 | -133 | 18 | 79 | 1 | 36 | Y |
| ΔInteraction | 0 | 0 | 0 | 0 | 0 | 0 | — |
| Audit LP−LL | 0 | 0 | 0 | 0 | 0 | 0 | N |

- LP fingerprint == LL: **Y**
- CL fingerprint == LL: **Y**

## rank7 only

| Delta | Hit | Purchase | rank710 | other_1_3 | other_10_13 | rank46 | fpΔ |
|---|---:|---:|---:|---:|---:|---:|---|
| ΔTrigger (CL−LL) | 0 | 0 | 0 | 0 | 0 | 0 | N |
| ΔStrategy (CP−CL) | -41 | -41 | 11 | 21 | 1 | 8 | Y |
| ΔBoth (CP−LL) | -41 | -41 | 11 | 21 | 1 | 8 | Y |
| ΔInteraction | 0 | 0 | 0 | 0 | 0 | 0 | — |
| Audit LP−LL | 0 | 0 | 0 | 0 | 0 | 0 | N |

- LP fingerprint == LL: **Y**
- CL fingerprint == LL: **Y**

## unsatisfied Residual

| Delta | Hit | Purchase | rank710 | other_1_3 | other_10_13 | rank46 | fpΔ |
|---|---:|---:|---:|---:|---:|---:|---|
| ΔTrigger (CL−LL) | 0 | 0 | 0 | 0 | 0 | 0 | N |
| ΔStrategy (CP−CL) | -92 | -92 | 7 | 58 | 0 | 28 | Y |
| ΔBoth (CP−LL) | -92 | -92 | 7 | 58 | 0 | 28 | Y |
| ΔInteraction | 0 | 0 | 0 | 0 | 0 | 0 | — |
| Audit LP−LL | 0 | 0 | 0 | 0 | 0 | 0 | N |

- LP fingerprint == LL: **Y**
- CL fingerprint == LL: **Y**

## Non-Ready（発火ゼロ期待）

| Delta | Hit | Purchase | rank710 | other_1_3 | other_10_13 | rank46 | fpΔ |
|---|---:|---:|---:|---:|---:|---:|---|
| ΔTrigger (CL−LL) | 0 | 0 | 0 | 0 | 0 | 0 | N |
| ΔStrategy (CP−CL) | 0 | 0 | 0 | 0 | 0 | 0 | N |
| ΔBoth (CP−LL) | 0 | 0 | 0 | 0 | 0 | 0 | N |
| ΔInteraction | 0 | 0 | 0 | 0 | 0 | 0 | — |
| Audit LP−LL | 0 | 0 | 0 | 0 | 0 | 0 | N |

- LP fingerprint == LL: **Y**
- CL fingerprint == LL: **Y**

## 归因読み（V79 規則）

- ΔTrigger が非ゼロ → Trigger/ラベル要因（本 Shadow では legacy_pe がラベル非依存のため通常 0）
- ΔStrategy が非ゼロ → Strategy/Pilot Shadow PE 要因
- LL+CP のみで断言しない（本報告は 2×2 完備）

### 本実行の一意結論（Full）

| 要因 | Hit Δ | 判定 |
|---|---:|---|
| ΔTrigger | 0 | Trigger/ラベル単独では Prediction 非変化（legacy_pe=fixture） |
| ΔStrategy | **-133** | Pilot Shadow PE（V75 契約の研究用スコア）が Hit を大きく悪化 |
| ΔBoth | -133 | = ΔStrategy（加法・Interaction 0） |
| Audit LP | 0 / fp一致 | 境界 PASS（legacy ラベルでは pilot 不発火） |

**归因:** 観測された Prediction 差分は **Strategy（Pilot Shadow PE）単独**に帰属。Trigger 交絡なし。  
**注意:** Pilot Shadow PE は Production PE ではない。Hit 悪化は「V75 契約の素朴スコア化」の結果であり、Production 適用を正当化しない。
