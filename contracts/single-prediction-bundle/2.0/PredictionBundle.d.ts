/**
 * PredictionBundle — 正式 API 契約
 * schema_version: single-prediction-bundle/2.0
 *
 * 正本: contracts/single-prediction-bundle/2.0/schema.json
 */

export type PredictionBundleSchemaVersion = "single-prediction-bundle/2.0";

export type BundleStatus = "ok" | "partial" | "error" | "list" | "unknown" | string;

export type Surface = "turf" | "dirt" | "obstacle" | string;

export type RaceStatus = "scheduled" | "running" | "finished" | "cancelled" | string;

export type ConfidenceBand = "high" | "medium" | "low" | "unknown" | string;

export type MarkCode =
  | "honmei"
  | "taikou"
  | "ana"
  | "chuuken"
  | "none"
  | string;

export interface RaceInfo {
  race_id: string;
  date: string;
  venue: string;
  meeting_id?: string | null;
  race_no: number;
  post_time?: string | null;
  distance?: number | null;
  surface?: Surface | null;
  course?: string | null;
  class_label?: string | null;
  grade?: string | null;
  field_size?: number | null;
  race_status?: RaceStatus | null;
  /** UI 補助（一覧フィルタ用）。ISO date から派生可 */
  date_label?: string | null;
  /** UI 補助（お気に入り表示用） */
  date_full?: string | null;
  /** UI 補助（カード背景バリエーション 1–4） */
  bg?: number | null;
}

export interface EvaluationRunner {
  candidate_id?: string | null;
  horse_number: number;
  horse_name?: string | null;
  model_rank?: number | null;
  win_prob?: number | null;
  mark?: MarkCode | null;
  mark_rank?: number | null;
}

export interface Evaluation {
  status?: BundleStatus;
  world?: string | null;
  sub_world?: string | null;
  runners: EvaluationRunner[];
}

export interface ConfidenceInputsRef {
  schema_version?: string;
  kpi_snapshot_id?: string | null;
  evaluation_fingerprint?: string | null;
  used_channels?: string[];
}

export interface AiConfidence {
  schema_version?: string;
  status?: BundleStatus;
  /** 0–1 正規化。UI は ×100 で％表示 */
  score?: number | null;
  score_unit?: "normalized" | "percent" | string;
  band?: ConfidenceBand;
  inputs_ref?: ConfidenceInputsRef | null;
  factors?: string[];
  component_scores?: Record<string, number>;
  notes?: string | null;
  computed_at?: string | null;
}

export interface ExplainReason {
  candidate_id?: string | null;
  horse_number?: number | null;
  bullets?: string[];
}

export interface ExplainMeta {
  world?: string | null;
  sub_world?: string | null;
  strategy_id?: string | null;
  confidence_band?: ConfidenceBand | null;
}

export interface Explain {
  meta?: ExplainMeta;
  reasons?: ExplainReason[];
  narrative?: string;
}

export interface CombinationLeg {
  position?: number | null;
  horse_number: number;
  candidate_id?: string | null;
}

export interface Combination {
  schema_version?: string;
  selection_mode?: "exact_order" | "unordered_set" | string;
  is_ordered?: boolean;
  cardinality?: number;
  legs: CombinationLeg[];
}

export interface BettingRecommendationItem {
  recommendation_id: string;
  bet_type: string;
  combination: Combination;
  recommendation_rank?: number | null;
  recommendation_score?: number | null;
  score_unit?: string | null;
  comment?: string | null;
  legs_display?: string | null;
  derived_from?: Record<string, unknown> | null;
}

export interface BettingRecommendations {
  schema_version?: string;
  race_id?: string;
  generated_at?: string | null;
  strategy_id?: string | null;
  status?: BundleStatus;
  items: BettingRecommendationItem[];
  by_bet_type?: Record<string, string[]>;
}

/**
 * PredictionService が返す唯一の共通契約 DTO。
 * Analysis / Confidence / Ticket / Kaoba は race_id で参照する。
 */
export interface PredictionBundle {
  schema_version: PredictionBundleSchemaVersion;
  race_id: string;
  generated_at?: string | null;
  model_version?: string | null;
  core_version?: string | null;
  product_version?: string | null;
  status?: BundleStatus;
  warnings?: string[];
  race_info: RaceInfo;
  evaluation: Evaluation;
  ai_confidence: AiConfidence;
  explain: Explain;
  betting_recommendations: BettingRecommendations;
}

export type PredictionBundleList = PredictionBundle[];
