# -*- coding: utf-8 -*-
"""Canonical remaining W5 maiden-history horses (Production 2026-09-09).

Source: remaining_http_features read-only audit
W5_QUEUE_LINES=851 complete:835 pending:13 fetch_failed:3
W5_REMAINING_COUNT=16 = pending 13 + fetch_failed 3.

Do not treat 474 FAILED history or 2099-01-02 canary rows as this set.
"""
from __future__ import annotations

# attempt_count=0, next_eligible_at=NONE, cache_present=NO, retry_eligible_now=YES
PENDING_W5_13: tuple[str, ...] = (
    "2021100029",
    "2021100043",
    "2021101529",
    "2021102022",
    "2021102542",
    "2021102774",
    "2021102897",
    "2021103448",
    "2021103571",
    "2021103917",
    "2021104461",
    "2021104551",
    "2021104644",
)

# attempt_count=1, error_category=retryable_timeout, allowlist=YES,
# next_eligible_at=NONE, retry_flag=UNSET, same_fail_loop=HTTP_OFF_AND_RETRY_OFF
FETCH_FAILED_W5_3: tuple[str, ...] = (
    "2021100988",
    "2021107235",
    "2021107273",
)

REMAINING_W5_16: tuple[str, ...] = PENDING_W5_13 + FETCH_FAILED_W5_3
