/**
 * PredictionBundle JSDoc typedef（ブラウザ / エディタ用）
 * TypeScript 正本: PredictionBundle.d.ts
 * JSON Schema 正本: schema.json
 *
 * @typedef {"single-prediction-bundle/2.0"} PredictionBundleSchemaVersion
 *
 * @typedef {Object} RaceInfo
 * @property {string} race_id
 * @property {string} date
 * @property {string} venue
 * @property {number} race_no
 * @property {string|null} [meeting_id]
 * @property {string|null} [post_time]
 * @property {number|null} [distance]
 * @property {string|null} [surface]
 * @property {string|null} [course]
 * @property {string|null} [class_label]
 * @property {string|null} [grade]
 * @property {number|null} [field_size]
 * @property {string|null} [race_status]
 * @property {string|null} [date_label] UI補助
 * @property {string|null} [date_full] UI補助
 * @property {number|null} [bg] UI補助 1–4
 *
 * @typedef {Object} EvaluationRunner
 * @property {number} horse_number
 * @property {string|null} [candidate_id]
 * @property {string|null} [horse_name]
 * @property {number|null} [model_rank]
 * @property {number|null} [win_prob]
 * @property {string|null} [mark] honmei|taikou|ana|chuuken|none
 * @property {number|null} [mark_rank]
 *
 * @typedef {Object} Evaluation
 * @property {string} [status]
 * @property {string|null} [world]
 * @property {string|null} [sub_world]
 * @property {EvaluationRunner[]} runners
 *
 * @typedef {Object} AiConfidence
 * @property {string} [schema_version]
 * @property {string} [status]
 * @property {number|null} score 0–1 正規化
 * @property {string} [score_unit]
 * @property {string} [band]
 * @property {string[]} [factors]
 * @property {Object.<string, number>} [component_scores]
 * @property {string|null} [notes]
 * @property {string|null} [computed_at]
 *
 * @typedef {Object} Explain
 * @property {Object} [meta]
 * @property {Array<{candidate_id?: string, horse_number?: number, bullets?: string[]}>} [reasons]
 * @property {string} narrative
 *
 * @typedef {Object} BettingRecommendations
 * @property {string} [schema_version]
 * @property {string} [race_id]
 * @property {string} [status]
 * @property {Array<Object>} items
 * @property {Object.<string, string[]>} [by_bet_type]
 *
 * @typedef {Object} PredictionBundle
 * @property {PredictionBundleSchemaVersion} schema_version
 * @property {string} race_id
 * @property {string|null} [generated_at]
 * @property {string|null} [model_version]
 * @property {string|null} [core_version]
 * @property {string|null} [product_version]
 * @property {string} [status]
 * @property {string[]} [warnings]
 * @property {RaceInfo} race_info
 * @property {Evaluation} evaluation
 * @property {AiConfidence} ai_confidence
 * @property {Explain} explain
 * @property {BettingRecommendations} betting_recommendations
 */
export {};
