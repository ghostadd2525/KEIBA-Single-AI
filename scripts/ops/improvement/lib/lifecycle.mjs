/**
 * Proposal Lifecycle — Development only.
 * Scaffolded in I-1; enforced from I-3 onward.
 */
export const ProposalStatus = Object.freeze({
  DRAFT: "DRAFT",
  UNDER_REVIEW: "UNDER_REVIEW",
  APPROVED: "APPROVED",
  CANARY_RUNNING: "CANARY_RUNNING",
  CANARY_PASS: "CANARY_PASS",
  CANARY_FAIL: "CANARY_FAIL",
  RC_CREATED: "RC_CREATED",
  DEPLOYED: "DEPLOYED",
  REJECTED: "REJECTED",
  ARCHIVED: "ARCHIVED",
});

/** @type {ReadonlySet<string>} */
export const PROPOSAL_STATUSES = Object.freeze(new Set(Object.values(ProposalStatus)));

/** @type {Readonly<Record<string, ReadonlyArray<string>>>} */
export const TRANSITIONS = Object.freeze({
  DRAFT: Object.freeze(["UNDER_REVIEW", "REJECTED", "ARCHIVED"]),
  UNDER_REVIEW: Object.freeze(["APPROVED", "REJECTED", "DRAFT", "ARCHIVED"]),
  APPROVED: Object.freeze(["CANARY_RUNNING", "REJECTED", "ARCHIVED"]),
  CANARY_RUNNING: Object.freeze(["CANARY_PASS", "CANARY_FAIL"]),
  CANARY_PASS: Object.freeze(["RC_CREATED", "ARCHIVED"]),
  CANARY_FAIL: Object.freeze(["DRAFT", "UNDER_REVIEW", "ARCHIVED"]),
  RC_CREATED: Object.freeze(["DEPLOYED", "ARCHIVED"]),
  DEPLOYED: Object.freeze(["ARCHIVED"]),
  REJECTED: Object.freeze(["ARCHIVED", "DRAFT"]),
  ARCHIVED: Object.freeze([]),
});

/**
 * @param {string} current
 * @param {string} nxt
 */
export function canTransition(current, nxt) {
  const allowed = TRANSITIONS[current] || [];
  return allowed.includes(nxt);
}

/**
 * @param {string} current
 * @param {string} nxt
 */
export function assertTransition(current, nxt) {
  if (!canTransition(current, nxt)) {
    throw new Error(`illegal proposal lifecycle transition ${current} -> ${nxt}`);
  }
}

/**
 * @param {string} status
 */
export function assertKnownStatus(status) {
  if (!PROPOSAL_STATUSES.has(status)) {
    throw new Error(`unknown proposal lifecycle status: ${status}`);
  }
}

/**
 * @param {string} status
 * @param {{ by?: string, note?: string, proposal_id?: string }} [meta]
 */
export function createLifecycle(status, meta = {}) {
  assertKnownStatus(status);
  const at = new Date().toISOString();
  return {
    schema_version: "expect-proposal-lifecycle/1.0",
    proposal_id: meta.proposal_id || null,
    status,
    previous_status: null,
    updated_at: at,
    updated_by: meta.by || null,
    note: meta.note || null,
    history: [{ status, at, by: meta.by || null, note: meta.note || null }],
  };
}

/**
 * @param {object} lifecycle
 * @param {string} nxt
 * @param {{ by?: string, note?: string }} [meta]
 */
export function transitionLifecycle(lifecycle, nxt, meta = {}) {
  const current = lifecycle.status;
  assertTransition(current, nxt);
  const at = new Date().toISOString();
  const history = Array.isArray(lifecycle.history) ? [...lifecycle.history] : [];
  history.push({ status: nxt, at, by: meta.by || null, note: meta.note || null });
  return {
    ...lifecycle,
    schema_version: "expect-proposal-lifecycle/1.0",
    previous_status: current,
    status: nxt,
    updated_at: at,
    updated_by: meta.by || null,
    note: meta.note || null,
    history,
  };
}

/**
 * Attach DRAFT lifecycle to a proposal document.
 * @param {object} proposal
 * @param {{ by?: string, note?: string }} [meta]
 */
export function withDraftLifecycle(proposal, meta = {}) {
  const lifecycle = createLifecycle(ProposalStatus.DRAFT, {
    ...meta,
    proposal_id: proposal.proposal_id,
    note:
      meta.note ||
      "I-3 generated DRAFT — Human Review required; analyzer confidence is advisory only",
  });
  return {
    ...proposal,
    status: ProposalStatus.DRAFT,
    lifecycle,
    updated_at: lifecycle.updated_at,
  };
}

/**
 * Transition proposal.status + embedded lifecycle together.
 * Does not consult analyzer confidence.
 * @param {object} proposal
 * @param {string} nxt
 * @param {{ by?: string, note?: string }} [meta]
 */
export function transitionProposal(proposal, nxt, meta = {}) {
  assertKnownStatus(proposal.status);
  assertTransition(proposal.status, nxt);
  const base =
    proposal.lifecycle && proposal.lifecycle.status === proposal.status
      ? proposal.lifecycle
      : createLifecycle(proposal.status, { proposal_id: proposal.proposal_id });
  const lifecycle = transitionLifecycle(base, nxt, meta);
  lifecycle.proposal_id = proposal.proposal_id;
  return {
    ...proposal,
    status: nxt,
    lifecycle,
    updated_at: lifecycle.updated_at,
  };
}
