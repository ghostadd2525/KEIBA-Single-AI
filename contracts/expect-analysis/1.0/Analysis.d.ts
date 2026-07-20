/**
 * AnalysisService DTO
 * schema_version: expect-analysis/1.0
 * 参照キー: PredictionBundle.race_id
 */

export type AnalysisSchemaVersion = "expect-analysis/1.0";

export type AnalysisChartKey =
  | "pedigree"
  | "pace"
  | "jockey"
  | "form"
  | "odds"
  | string;

export interface AnalysisChart {
  key: AnalysisChartKey;
  label: string;
  value: number;
}

export interface Analysis {
  schema_version: AnalysisSchemaVersion;
  race_id: string;
  charts: AnalysisChart[];
  overall?: number | null;
  narrative?: string;
}
