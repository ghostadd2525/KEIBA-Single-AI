/**
 * KaobaService — expect-kaoba/1.0
 * AI Concierge。PB / Analysis は race_id 参照のみ（契約本体は変更しない）。
 *
 * LLM 差し替え: BFF の generateKaobaReply() / Python kaoba_reply() を
 * provider=llm 実装に差し替え。Request/Response 契約は維持。
 */

export type KaobaSchemaVersion = "expect-kaoba/1.0";

export type KaobaEmotion =
  | "joy"
  | "fun"
  | "anger"
  | "sorrow"
  | "tantrum"
  | "neutral"
  | string;

export type ChatRole = "user" | "assistant" | "system";

export interface ChatHistoryItem {
  role: ChatRole;
  content: string;
}

export interface KaobaChatRequest {
  message: string;
  history?: ChatHistoryItem[];
  /** PredictionBundle.race_id。任意 */
  race_id?: string | null;
  context?: Record<string, unknown>;
}

export interface KaobaChatResponse {
  schema_version: KaobaSchemaVersion;
  reply: string;
  suggestions: string[];
  emotion: KaobaEmotion;
  /** 内部参照した race_id。未参照時 null */
  referenced_race_id: string | null;
  live2d?: {
    motion?: string;
    expression?: string;
  };
  /** rule | llm | mock … 観測・差し替え用 */
  provider?: string;
}
