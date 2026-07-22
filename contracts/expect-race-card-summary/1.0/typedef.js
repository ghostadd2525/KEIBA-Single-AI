/**
 * RaceCardSummary — expect-race-card-summary/1.0
 *
 * @typedef {"ready"|"processing"|"failed"|"missing"} RaceCardPredictionStatus
 * @typedef {"high"|"medium"|"low"} ConfidenceBand
 *
 * @typedef {object} RaceCardRaceInfo
 * @property {string} venue
 * @property {number|null} race_number
 * @property {string} race_name
 * @property {string|null} [post_time]
 *
 * @typedef {object} RaceCardPredictionState
 * @property {RaceCardPredictionStatus} status
 * @property {string} [engine_source]
 *
 * @typedef {object} RaceCardHonmei
 * @property {number} horse_number
 * @property {string|null} horse_name
 * @property {"honmei"} mark
 *
 * @typedef {object} RaceCardConfidence
 * @property {number|null} score
 * @property {ConfidenceBand} band
 *
 * @typedef {object} RaceCardSummaryBlock
 * @property {RaceCardHonmei|null} [honmei]
 * @property {RaceCardConfidence|null} [confidence]
 * @property {string|null} [short_reason] Phase1: always null
 *
 * @typedef {object} RaceCardSummary
 * @property {"expect-race-card-summary/1.0"} schema_version
 * @property {string} race_id
 * @property {RaceCardRaceInfo} race_info
 * @property {RaceCardPredictionState} prediction
 * @property {RaceCardSummaryBlock|null} [summary]
 */
export {};
