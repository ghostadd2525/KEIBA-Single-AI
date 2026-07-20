/** Auto-synced schema module for Pages Functions (JSON import avoided). */
export default {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://expect.keiba/contracts/single-prediction-bundle/2.0/schema.json",
  "title": "PredictionBundle",
  "description": "Single-AI 共通 API 契約。schema_version 固定: single-prediction-bundle/2.0。正本は contracts/single-prediction-bundle/2.0/schema.json",
  "type": "object",
  "additionalProperties": true,
  "required": [
    "schema_version",
    "race_id",
    "race_info",
    "evaluation",
    "ai_confidence",
    "explain",
    "betting_recommendations"
  ],
  "properties": {
    "schema_version": {
      "const": "single-prediction-bundle/2.0"
    },
    "race_id": {
      "type": "string",
      "minLength": 1
    },
    "generated_at": {
      "type": ["string", "null"]
    },
    "model_version": {
      "type": ["string", "null"]
    },
    "core_version": {
      "type": ["string", "null"]
    },
    "product_version": {
      "type": ["string", "null"]
    },
    "status": {
      "type": "string"
    },
    "warnings": {
      "type": "array",
      "items": { "type": "string" }
    },
    "race_info": {
      "$ref": "#/$defs/RaceInfo"
    },
    "evaluation": {
      "$ref": "#/$defs/Evaluation"
    },
    "ai_confidence": {
      "$ref": "#/$defs/AiConfidence"
    },
    "explain": {
      "$ref": "#/$defs/Explain"
    },
    "betting_recommendations": {
      "$ref": "#/$defs/BettingRecommendations"
    }
  },
  "$defs": {
    "RaceInfo": {
      "type": "object",
      "additionalProperties": true,
      "required": ["race_id", "date", "venue", "race_no"],
      "properties": {
        "race_id": { "type": "string", "minLength": 1 },
        "date": { "type": "string", "minLength": 1 },
        "venue": { "type": "string", "minLength": 1 },
        "meeting_id": { "type": ["string", "null"] },
        "race_no": { "type": "integer", "minimum": 1 },
        "post_time": { "type": ["string", "null"] },
        "distance": { "type": ["number", "null"] },
        "surface": { "type": ["string", "null"] },
        "course": { "type": ["string", "null"] },
        "class_label": { "type": ["string", "null"] },
        "grade": { "type": ["string", "null"] },
        "field_size": { "type": ["integer", "null"] },
        "race_status": { "type": ["string", "null"] },
        "date_label": { "type": ["string", "null"] },
        "date_full": { "type": ["string", "null"] },
        "bg": { "type": ["integer", "null"], "minimum": 1, "maximum": 4 }
      }
    },
    "EvaluationRunner": {
      "type": "object",
      "additionalProperties": true,
      "required": ["horse_number"],
      "properties": {
        "candidate_id": { "type": ["string", "null"] },
        "horse_number": { "type": "integer", "minimum": 1 },
        "horse_name": { "type": ["string", "null"] },
        "model_rank": { "type": ["integer", "null"] },
        "win_prob": { "type": ["number", "null"], "minimum": 0, "maximum": 1 },
        "mark": { "type": ["string", "null"] },
        "mark_rank": { "type": ["integer", "null"] }
      }
    },
    "Evaluation": {
      "type": "object",
      "additionalProperties": true,
      "required": ["runners"],
      "properties": {
        "status": { "type": "string" },
        "world": { "type": ["string", "null"] },
        "sub_world": { "type": ["string", "null"] },
        "runners": {
          "type": "array",
          "items": { "$ref": "#/$defs/EvaluationRunner" }
        }
      }
    },
    "AiConfidence": {
      "type": "object",
      "additionalProperties": true,
      "required": ["score"],
      "properties": {
        "schema_version": { "type": "string" },
        "status": { "type": "string" },
        "score": { "type": ["number", "null"] },
        "score_unit": { "type": "string" },
        "band": { "type": "string" },
        "inputs_ref": { "type": ["object", "null"] },
        "factors": { "type": "array", "items": { "type": "string" } },
        "component_scores": {
          "type": "object",
          "additionalProperties": { "type": "number" }
        },
        "notes": { "type": ["string", "null"] },
        "computed_at": { "type": ["string", "null"] }
      }
    },
    "ExplainReason": {
      "type": "object",
      "additionalProperties": true,
      "properties": {
        "candidate_id": { "type": ["string", "null"] },
        "horse_number": { "type": ["integer", "null"] },
        "bullets": { "type": "array", "items": { "type": "string" } }
      }
    },
    "Explain": {
      "type": "object",
      "additionalProperties": true,
      "required": ["narrative"],
      "properties": {
        "meta": { "type": "object" },
        "reasons": {
          "type": "array",
          "items": { "$ref": "#/$defs/ExplainReason" }
        },
        "narrative": { "type": "string" }
      }
    },
    "CombinationLeg": {
      "type": "object",
      "additionalProperties": true,
      "required": ["horse_number"],
      "properties": {
        "position": { "type": ["integer", "null"] },
        "horse_number": { "type": "integer", "minimum": 1 },
        "candidate_id": { "type": ["string", "null"] }
      }
    },
    "Combination": {
      "type": "object",
      "additionalProperties": true,
      "required": ["legs"],
      "properties": {
        "schema_version": { "type": "string" },
        "selection_mode": { "type": "string" },
        "is_ordered": { "type": "boolean" },
        "cardinality": { "type": "integer" },
        "legs": {
          "type": "array",
          "items": { "$ref": "#/$defs/CombinationLeg" }
        }
      }
    },
    "BettingRecommendationItem": {
      "type": "object",
      "additionalProperties": true,
      "required": ["recommendation_id", "bet_type", "combination"],
      "properties": {
        "recommendation_id": { "type": "string" },
        "bet_type": { "type": "string" },
        "combination": { "$ref": "#/$defs/Combination" },
        "recommendation_rank": { "type": ["integer", "null"] },
        "recommendation_score": { "type": ["number", "null"] },
        "score_unit": { "type": ["string", "null"] },
        "comment": { "type": ["string", "null"] },
        "legs_display": { "type": ["string", "null"] },
        "derived_from": { "type": ["object", "null"] }
      }
    },
    "BettingRecommendations": {
      "type": "object",
      "additionalProperties": true,
      "required": ["items"],
      "properties": {
        "schema_version": { "type": "string" },
        "race_id": { "type": "string" },
        "generated_at": { "type": ["string", "null"] },
        "strategy_id": { "type": ["string", "null"] },
        "status": { "type": "string" },
        "items": {
          "type": "array",
          "items": { "$ref": "#/$defs/BettingRecommendationItem" }
        },
        "by_bet_type": {
          "type": "object",
          "additionalProperties": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    }
  }
}
;
