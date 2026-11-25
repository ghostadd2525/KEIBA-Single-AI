#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single SSH stdin payload for 工程1 hunk-only code deploy v3. Pregenerated. Do not concatenate. sudo -n restart only. Bounded readiness poll after restart."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import py_compile
import re
import sqlite3
import stat
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

PACK = "production_disabled_post_hunk_only_step1_owner_deploy_execution_v3_fix_20260913"
REPO_ROOT = "/home/ubuntu/KEIBA-Single-AI"
WIN5_ROOT = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai"
CANONICAL_SOURCE = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
V1_APPROVAL = "OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED"
V2_APPROVAL = "OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED"
APPROVAL = "OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED"
RESTART_UNIT = "expect-ai.service"
RESTART_ARGV = ("sudo", "-n", "systemctl", "restart", RESTART_UNIT)
OLD_EXECUTION_PACK = "production_disabled_post_hunk_only_step1_owner_deploy_execution_20260913"
OLD_EXECUTION_ZIP_SHA256 = "a8d226c33d9825adf5c8a8cd269ba0665a304e9b268168350148e79a61afac13"
V2_EXECUTION_PACK = "production_disabled_post_hunk_only_step1_owner_deploy_execution_v2_20260913"
V2_EXECUTION_ZIP_SHA256 = "20a273c79e2fb925da46994259ec98dd3e1275ea760808b67146976ffdaffc17"
PARTIAL_INDEX = "uq_predictions_idempotency_key_not_null"
RACE_INDEX = "idx_predictions_race"
PERSIST_022 = "022_prediction_run_idempotency"
PERSIST_019 = "019_prediction_run_idempotency"
MAIN_PY_CANDIDATE_SHA256 = "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c"
MAIN_PY_CANDIDATE_SIZE = 48345
LIVE_MAIN_PY_SHA256 = "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235"
ORIGIN_MAIN_PY_SHA256 = "a54f1eaa5b8540c2f08d8b0e656a3ccbb78142d4d1cb2c8951e4105f3630184e"
V6_MAIN_PY_SHA256 = "7577973c16eb7aad395cd11acae3c8ef987a3c0533924c1994ae32afeaf818e5"
HUNK_ONLY_V3_ZIP_SHA256 = "4d7cdcf6ba9e7d6cc94d903364a302ac7f63bf0ec0db590460b1745b8d9b37ab"
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
REMOTE_HARD_DEADLINE_S = 300
WRAPPER_TIMEOUT_MS = 400000
DRAIN_WAIT_MS = 20000
KILL_DRAIN_WAIT_MS = 8000
SAFETY_BUFFER_MS = 40000
HTTP_LOCAL_TIMEOUT_S = 3
HTTP_PUBLIC_TIMEOUT_S = 3
SUBPROCESS_TIMEOUT_S = 8
RESTART_TIMEOUT_S = 60
READINESS_POLL_TIMEOUT_S = 45
READINESS_POLL_INTERVAL_S = 1.0
READINESS_HTTP_TIMEOUT_S = 2
READINESS_MAX_ATTEMPTS = 45
HTTP_MAX_INTERNAL_HEALTH_BYTES = 65536
HTTP_MAX_INTERNAL_LIST_BYTES = 2097152
HTTP_MAX_INTERNAL_DETAIL_BYTES = 262144
HTTP_MAX_PUBLIC_JSON_BYTES = 262144
HTTP_MAX_PUBLIC_HTML_BYTES = 524288
CLASS_INTERNAL_HEALTH = "INTERNAL_HEALTH"
CLASS_INTERNAL_LIST = "INTERNAL_LIST"
CLASS_INTERNAL_DETAIL = "INTERNAL_DETAIL"
CLASS_PUBLIC_JSON = "PUBLIC_JSON"
CLASS_PUBLIC_HTML = "PUBLIC_HTML"
CLASS_DISABLED_POST = "DISABLED_POST_PROBE"
WATCHED_ENV_KEYS = (
    "PREDICTION_RUNS_ENABLED",
    "EXPECT_AI_ALLOW_MIGRATION_022",
    "EXPECT_AI_ALLOW_MIGRATION_019",
)
PUBLIC_ORIGINS = (
    "https://expect-keiba.com",
    "https://keiba-single-ai.pages.dev",
)
PUBLIC_STATIC_PATHS = ("/", "/race.html", "/races.html")
PUBLIC_API_PATHS = ("/api/health", "/api/predictions")
ALLOWED_PUBLIC_HOSTS = ("expect-keiba.com", "keiba-single-ai.pages.dev")
SITE_IDENTIFIERS = ("Expect", "KEIBA")
PHASE_NOT_STARTED = "NOT_STARTED"
PHASE_PRECHECKS = "PRECHECKS"
PHASE_BACKED_UP = "BACKED_UP"
PHASE_REPLACED = "REPLACED"
PHASE_RESTARTED = "RESTARTED"
PHASE_VERIFIED = "VERIFIED"
PHASE_RESTORED = "RESTORED"
OWNER_MIGRATIONS = (
    "001_init",
    "002_race_identity",
    "003_supply_platform",
    "004_user_domain",
    "005_results_eval",
    "006_result_automation",
    "007_collect_c0",
    "008_collect_contract_1_1",
    "009_user_race_results",
    "010_user_progress_audit",
    "011_research_evidence",
    "012_research_snapshot_features",
    "013_research_prediction_corpus",
    "014_research_historical_ingest",
    "015_research_race_meta",
    "016_research_knowledge_base",
    "017_research_knowledge_validation",
    "018_research_candidate_review",
    "019_final_predictions",
    "020_research_corpus_canonical",
    "020_user_challenge_lifecycle",
    "021_user_challenge_point_events",
    "022_prediction_run_idempotency",
)
OWNER_PRED_COLUMNS = (
    "id",
    "race_id",
    "core_race_id",
    "engine_source",
    "fallback_reason",
    "model_version",
    "bundle_json",
    "created_at",
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
NEW_COLS = (
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
DEPLOY_TARGETS = (
    {
        "rel": "app/main.py",
        "pre": "LIVE_SHA",
        "live": "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235",
        "cand": "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c",
    },
    {
        "rel": "app/data/db.py",
        "pre": "LIVE_SHA",
        "live": "8a86f514b1b08fde9a90a71acc99eac3f6fc9c2aeae200e8787721093592ef1a",
        "cand": "81fc91adbe53aa091841fd9ea097b7cbd63cf4ede4a3699bf66e1c7a2343136f",
    },
    {
        "rel": "app/data/repository/__init__.py",
        "pre": "LIVE_SHA",
        "live": "557713a95b0e9f5a8f798eeb5e525c85adab3063b2e6529ee0be2155bb29992b",
        "cand": "9624699ec48d2af8b1fdc24ac81b8ae436c77ffa92a7f0b1378ecd17248b4c08",
    },
    {
        "rel": "app/core/feature_loader_bridge.py",
        "pre": "LIVE_SHA",
        "live": "e06e6ee971e2ae8d07bbcee4501ab9024052de52dd119ea007cb71481ae5272e",
        "cand": "f3c25c7b87941138555158e051d0520fc705889e8a2a17e8889c7fc5325eae44",
    },
    {
        "rel": "app/predictions/__init__.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "d4373c31ad5aac82a2d83a53d91bc2b95607bd891d7b9286c3c154478d5dc21c",
    },
    {
        "rel": "app/predictions/guards.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "7e6d74dd77b6645364679187a325b42676cd64d6546f5576022f19d30e6dfc82",
    },
    {
        "rel": "app/predictions/runs.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "d04bc99281474aa4e0e78b9951df6335f6b9995c9e7328b100afd552815f35c1",
    },
    {
        "rel": "app/predictions/feature_pin.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "49794f3671589a5ec13bc622161bac8c10609ff922c51033343dca30a31fbc36",
    },
    {
        "rel": "app/predictions/provenance.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "2cc2585d53a3dbdffd8c7a4dc56921aafaf4ce6cd5421d1928950a34194bb704",
    },
    {
        "rel": "app/predictions/snapshot.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "2114c953b57461f73d0450384f38df2a2b086a51e53591c77cc70b448cbde5f7",
    },
)
OPS_TARGETS = (
    {
        "rel": "app/ops/prediction_capacity.py",
        "live": "c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e",
    },
    {
        "rel": "app/ops/final_prediction_store.py",
        "live": "40352ff56b3267533267d5de9c893f3bda8963d5fe121474f7785b0152594a12",
    },
)
MUST_ABSENT = (
    "app/predictions/corpus.py",
    "app/predictions/raeval84_holdout.py",
    "app/predictions/data/raeval84_v1_holdout_race_ids.txt",
    "app/data/migrations/022_prediction_run_idempotency.sql",
    "app/data/migrations/019_prediction_run_idempotency.sql",
    "app/data/migrations_not_apply/019_prediction_run_idempotency.sql",
)
CANDIDATE_PREFIX = "services/win5-ai/"
# BEGIN_CANDIDATE_TAR_GZ_B64
CANDIDATE_TAR_GZ_B64 = (
    "H4sIAAAAAAAC/+y9a3sc13Eg7M/4Fe3Waj1DDwYARVEWnEkWBEAREQggAChZi0U6jZkG0MZgejTd"
    "AxCi8TwCFXslW4odr6+J9o2T2I7WXtnJOvtGb+LLfwkESv6Uv/CeqnO/9GUAkJJsjmVipvtc69Sp"
    "U1WnLmk0OIjbUTpxGPeeHg/jibDfn2gng2hiOwqz4SAKuknYiQbB1iDu7ETN/tGnRv5Mks/1a9fw"
    "L/mYf68/PXmVf6fPp565dvWpT3mTn3oEn2GahQPS/ad+Pz9PeONXxr120ol7O9PeMNse/xw8GfN9"
    "/wauuHeT4sFq1E/SOEsGR15t7U8W4yyqe3EvS7wwDvrdMNtOBvu87CKiTJO0MbY9SPa9INgeIi4F"
    "XrzfTwaZF/Z6SRZmcdJLx2iZ7KhPhsDfz/SOxsbY937Y64SpR/7rd8bGssHR9JhHPlhL6bwJWNtk"
    "WJs2dfTl7SoDXI3SYTdreINoJ04zguGdraA/SA5iUnwsutuO+pk3j3/IKKc97wnv9LV3T1/75en9"
    "n56+9tOJ/aS9N+2JmT94+ye//fJbH/zqZ6cn/3B6/7733Pz6xGzSO4gGKU7TO73/zQ//77+cfe3b"
    "Z1//+Yev/QqnYI3Ga3lLSS+Czgg8omkv3umRWW3sx2m7EaYp+bkf9bJNrO0aOGtgbGysE217wSA5"
    "TIMsCbYH4X5Ug1/TXpdU2ujE7WwjzQYNgPTmZsMD4AWDsB0FcWfaI2/q3vgfEoA358IsvAnVp1mn"
    "pGQnpxnS+wYdG4GJR7ojGOJhr/gQPv3wCFaElIS6MKTmTpTVfPbcr3uk5r3jullhw2eD86EXdbSi"
    "ZLztieZ2k0EaBb3h/lY0IG3GqUfwDUEjh6K1rlWALkhT5tOCnsi46oUts4ErrcITUYOBtUmob9Tr"
    "1FjlOgM5QZKethY1Vr7OFhoKB7AhAo72A7Fda+6ltXHvSwp8cHM1mx3SYVM2ZewiSRLG6EDJSpM5"
    "Wm9r9SZgS0CQAsdRI2PQRlWnEyVghVXSEYbNHrGajozMn/TiwO2Gl98wlmpG+/3sKL9t9tsCTU3U"
    "wGZa+G9DPmQwT5PhoB21/M6WL1/uR1kIYGzd09DDJwMO2smwl/lkL0W9GrZZb+iFaIvBdtyNSDGY"
    "48bkJsU79VWdYWTqRd00wvnIho7pV0CVYNgjRLYXdZAqBu2w2+U7mUCObV+KUY6SNcQbUXpaBRk8"
    "rbma5xhKSHKUBbmtSsxzlWm2u1E4qPG2grhHDu1uVyA7qWA2Q86eleW1de/99949PSFE+Tenr33r"
    "9LVfPHjvdfLdgfxAnn/zrdOT75++ep/Qbu/05OeEpNNKhKQ/+O7fnb37PdxnpAAcbNCJOIsu4zwi"
    "p47WVLPZH0RAJOGQbCpT5XUJGgQMVOwtNmAdXQa68x1BqocZ2S/6mQ3Da3h+IPuGPoLDAVCmjt/w"
    "boYExerORpNBvBP3wq6kAUqjlERwYlVLo+6269SZts6+XjJOdgl50hkntTdHBJK20tDzzWSwFXc6"
    "Ue9yoF29gT5hBYAKAjgH0cvDmBQfU8D48jAipzmcjCYVgyPR9+tN8jzu15SjEYdDKthjU0qRpWYF"
    "c09BoB6i/0/TAdA6TY2a6rVw2GGcRgVArlk1cHOyAdnbkAwRWIcnCS2HoT6Z+s4GnvRc42vIWdSt"
    "avoTfqbSRgbYuQYxx2LVjPmPPnefNeshadonogc98LCevme8cJuwdmSD9Lbjwb4OBTkVJ7FkPIQD"
    "FmzWfJ86NmGdYiS01syhAQTf1gdDm0cFYgI7NCbD2TTZW0YESF38Y/G3UbabdMYph7spjgzK35qk"
    "Pd52s74Ed3TUVkiTq0KtiGuiQHOfNGR8cmxjn2z5L3XJ/8CvTHS2ziXsjyz/XyUvnzLk/6euPXP1"
    "sfz/Ecv/VMoHEtSLkAp4n/X2450BFdu92kqSZjuDiBQbH0Rh58g7iENvbmZ95sbM2nxwZ3XRI5xQ"
    "NKhX1gOwZ0nKv6Uvd8kInqKV+2G22423eM0V8pNwtLcXnludWV9YXlojtAWe1QLkiYOgDmQ96R6Q"
    "s7DZDwdEbPYmPF9OwB8LVlbn5xZmoXawemcpmF1evHMbG6Kk2ydUgnSWRb32UbAXHTGunlNxxu/z"
    "p3GvPyTPemE/3U2yYDdMd0UFSUjTaD/sZXGbv6+PBQtz87dXltfnl2ZfChaW5ua/QAbgD19WyG8a"
    "GCMJCNSIWNrt+o7qAVkROYfZ1fmZ9XnvztLCn9yZ92j7Cze9peV1b/4LC2vra17Frjx6CPnLS55S"
    "vGYUr3sv3ppfnfeMx97CGna5dGdx0SeTXplfXSOdy+WDOU9evaqeOYNhTx2MP7Z2B6rNz83PBZNT"
    "z2KNqWcLazB5Ybsb7gRJr9YDNYaQgLeSpKsJMbUkbUa9g3iQ9FDGguJ1g/kix9ghHkmEsav5U4Qh"
    "9jNyGsLfoyj1hYhCDg0i4AlsC8jcau5exej8+S+szM+uBzMLwczi4vKLEjhQu6DpqWfNpmH3DgFN"
    "ow45sDnXAUDbIVuy6d0G1oMQviMi5w1JIWS6COXvHjW5bDPK6KaelaMj5/l+2I1fIeLwy4TDeLkr"
    "AU7+ajP3Pb/5xYScqFBMwLlP9nytLgDN2iUHcZ9QIQ07414nulsD+jTNSUVzVlArvUsyrWTP+xIh"
    "YITH6O3Qb/th1t4l8tzZN946e+Ot05MfnJ78JejvTn5yevJ1vmUmvLPXv0v+pXhN5MQHP3z7w3d+"
    "CaLi/a8pwiCIwMgdSUEf+OjBxtQmkWriXka+Xt2EaU5Kjgz1ZIBLMItmdDdqD7Oo5q+szjx3e8bD"
    "CQYoWytbrk6gtB2RkRNEYHz+Mf67HwJLguoxpTHRl782v0hWEEDl3Vxdvs1gFrBqdH7AlrU+gx1/"
    "xptZmvNgE7T+SFFo1GyK02B6CzYuwoTVhOLFQd6A5417HGBhr8NHnsPBAdXGVaOAHvZiwtkCK4kN"
    "4FZ1jImA2Wu1vCms0066oJraMJaGrgdBu5EWJO5tJ7UnyToQOcTu2FocygwD1Fvm9qDz3pjcBEgx"
    "IEh4wHNU6PABtpP9ftgGLTGpDHq5LmjTyDZqiCLkWAkEgNgXaLHmt8khnUX0Ec7Dp9OkTQIYeHl8"
    "QSaXwj/QFW0aVoAcrEDNWwygBKLWIbkpxkFxlnQKpPpwNxpERtk4JaiAx5gyFKpK6KlnEtRPekWn"
    "jtUAgacCCoCAMnz4qQ8Qnuh92kiY7GmU0ecEhB8zxkGUtnfJWR8QKpsN01wqxbSuTG9v0SyYUjci"
    "A/wS4X8GWRx2ybdoMCDL9SUv3EoJV4P0601CwujNw9mP/vKDf/7zsx9+hyIrKLJoBYVUJYc90NGA"
    "JocDC8Zn7z982uIsoKJUoC2AHGgrwtheuyeoX8mmysItsi64qXKp3LFofTc8iALWRQo7383E1b0/"
    "oEgqKoa9I6hHqsE5WSus+5+xqqJD6dzFhYR1Kj6JNL2LHCvgl9JIC7Fp2qWSEEvuqy3pdQXmuVvA"
    "5daq87mTdZAtfbolCau7IYZyvrUVKOb5qr6Ro/Y8dD5dWGMblA9dBWPICAlC6WNAVGl3kzQSPIB7"
    "g6HsMcr+0tgkwlnB+X568o7YYOzcPz1588HXXzs9+fvTkx+fnvw5HPYncN7DTd/J//rgW+8Am3D/"
    "DarLgV3G2azTk+8iB/Hnyo7j+qYyEoFHloICXBPSD+NB4Kxdnf/57avfev+9d/nYf+bB1Ak7c/az"
    "N9//168IdoZquhEkP/dmFtfnV7UJza0ur3h0n2jPqd6IEyLCSL0pCBH0JWkRNkD5AKz/4/d/9fbp"
    "/a9+8Nf/TJXv2A5nsX569sN/evDt72LBvwFgC3rI9fXfliNg0xx7uDQI2oGtRFrKIR8aXkNRxu/A"
    "mBw4LoZCgU3E58V5VcLyZubmOMTJkbw+/4V1OJZJa4zHGpE2VaEm+sCUJSOSI5Man0xz2B8n0dQ5"
    "ONcQDDKkjcAt4zKuBDcP6aJ8b/G+eRV1p+X0rF/HLSytza+ue8ur3ur8yuLMLMjT68se60qqFmpw"
    "7U++NFCmiqNOEGZ1T1fi+i/MLN6ZX/Nqf9TwOgQOWbwf1T7TSw4/U6/7+jVgzZKWG8pFoXZJTKfG"
    "yAboOkEjgpQAdCN0kkTEBfWAIewq8t3cjWBlZv2WX3ddPBD4kWoWgUfVC3mhjaZEH5MC/z3h+Qfh"
    "wIe/0V1E3jBudrY46ROsB1Izi8jRccAswaKAz1c8ZB019/c68aDGem0B29Ig5xbocJI9/Mn5a2R3"
    "eDe8b7wOIa3VZakmXN9uE2YTbsVljdXkcMzeP4zGEMoRxTs94EABX5eXfA1YUMcQdr+YkBdhN9hP"
    "OtF5OchVcjyOJ73ukae21vTmkoheBx0OQMv34swirDYVErzxw7A7MZ7u7jcpXV/Lov74lPdnf0Zx"
    "nCzhn/2ZvL8g9LG3ExntL2xjm3DnFIEWgsrIoBBseNluiFc9IeHgyKJAj8uHvQhVEIPkgJzBwC+R"
    "t9DtVdjZZPKdGGaLzWxFAEt68kY9IN1Nb30X7o6GPQoTnDADY/p5L868Dp8vrYDtkAE2vWVybuO2"
    "DbvIu/BrsvQQFS1EwNROlofLO4PNTMuNPip4fUvS1mjAAMwhmFSJVjjy4k8IlKZC60KcGUeLEXDU"
    "sCO4dLAyymuZNzjElVx6z3Sn9EjWlaYWzScStl6ZnQF4YHsrqwu3Z1Zf8p6ff0k9FOhLrhit+2P2"
    "FV+Hwk23HgHVgPYgh7thGh8+FKr1MUduq5OkSom3TZYUaSt0kSaDLOrUFNV7c6ebbNX8K01SzK8b"
    "16S885ZohKBetG9eQItiLU/X89qXzk94y11dq0kRfJxqML3no6jvhYP2bnwQdQhE+kdID5pWQwRY"
    "WdwbRgVjsY5eezjMbMmt8p123l87Oz4PN2OMo5izyZklY087lllALquaW+rSuSSr8epck/kR3dXz"
    "y9VHWy0JcbwN4OJyg4vgOatfKs65h8GgxO/3/SfTadoSMOIWno4+FY4PhbjwcRt71K0y8vNsdORB"
    "RtnYzk7SNjllM5X4gb4iyKK7GWGX6b1ry8d7V7+eKxzSVmr0T34xh8WJ3IwLzy0tr462F0fbbHkb"
    "TB/vE97k5BQRSglLFnbpvTFlOlN7VJ8nzFo6JJweMDHIr6fnm/t5CNHDmLyxDVidus6LEMq9H6uc"
    "zROM/54m2J3PcAO3TXlbzu/F5ASI23HWNDlENoxzsnyfevz53fnk2/9IW6iJAPdrEJzTIKjY/ufa"
    "tcmpKdP/Z/L6Y/ufj9T+ZwR7nS+mRCx3Wexwsskr898ND/59Bazu81x/uP+BMPdh8l6DK3kaXOaU"
    "dgeHNaeVAe+1CSV4x81h1q434zQBS+0wk6blrB+pQS1RPfm+f4tIHigbKZZSVEvcaw8HaHiUwkWQ"
    "2iTTq4CkkrK2ESjJkExx4fbt+bkFkDzJALsI7QZyI1vD9ChgxYgYRvWf4X40DpeaqMcZkNaiQYw3"
    "zB7qQUi7g7CXhjguRe1DzxBsQj9HmK5HaHrIMZ0mUn3iOnu4MkU5fxTVDtPi6BqehuOEGlET86i0"
    "fg2+Mq2nJpuTDbkoQTc6iLotX6yX/3AUhM7CGi60vKeAcuYqFDV+nWwD8v9pdUyI4rozF7O1JZK6"
    "4qvF2g9BSQWvqOZ4a9jrdKMA6AAbgaZggYIbrBA6QUFBNAdOa6Qp6rxCmkTN1L1j9VIRS/7x2vLS"
    "XERIVGTcLVoNs8ps/vCazL/dDdPUWw3bikfStHBG4Ecb2kIbhsZoU8O3gfRfGPbJFsuY8TRCUoec"
    "o5VcpZUGqAosrW+Lx4zLRdYWrLhTl3guLOR1e/n+cIvsP/n7ICLySwCgdsnIQElZmQZtsZcQOhwR"
    "8trbwfqEWSc4T952yC4Le21nM7ggQTfciggVINAlnREuNOp2gpRQLTKohOxQek5Q6Zr8RUtLV2NE"
    "jhqEiHoNJkcA994gi9Rh321PAIW1r/A/WxglsuHs8tLNxYXZ9Rq3m/fmlr07K3NAtNfm112zVgDf"
    "IujdHXZM9wVHLX2BZD1j4Rw15VLKWuXLK8viYue1azTZyMO4XiJLcoRxlJUoJIsraOWowRBNFueY"
    "55oXw0VlbtWwU1kmBWUddRCJZWmK045yEstlYQXzXevP94Ky9GJ7uOCCG0YBC91ArpLUWVGWrLDF"
    "ZGll2zlqyM0naxRsSELVHAK1W/0E/rPCE7iRV4aeS+rm8uslhfUdVVpcbqXSojDvau3llULjUV6S"
    "7SN6OztZ1q7cRqVDYFuofD5s95QWVHYNHa0xB8K5lraBe8movRV2dspryo1lVKfu19T3thQr+GYr"
    "hx7utPJi1GcgpxjyO53hfj+V641bjfvFN5hGLAjTdhy3qDOmuy0qEY32rlB55VZOWfoj+4qQM04w"
    "HcY1md7oOgeluaKPxj85LlBtesOuxa7QCzFkmpj5M/e4bHl/5Dc8fro3dEA4L19lXACHlySTRDUu"
    "+pJGrDmKfnKGrZPbcw7cHCC/7xZe8OfBUjS3l3bigK/i1xX5Fag64q9+ty0LIEUvLMEoOToH5JXp"
    "xmS70RIt7+rkJDO0FzfoRgSO82wZaplesFZTrSnfiG0xCPd55ADcsOJqXcEphJB9w0l6+yzpDp0L"
    "OtQ67I9sqYZ2wRXlUK5uX94AgIs7wDJVesCC9ragK5TvOW11yGtU6BJPdVq8Xh9ztri8Oje/6t14"
    "ySl6eYsLtxfWzX70PhB9nJtmg+6aPMNIMoQGa0s1D9g8z44K06AdZmE32ZFStkvZwPcENe3ubmPU"
    "EDqF1tOTitcMwgFLUVOEe4MNxkBtyunQlmARNQ5LCS3TwVsnrRXk1QoaobzcsWVzYwT3wGLTtION"
    "8alNvh1Sbn7TMG1FYEKkBv1ivMVBkJcbFkLdc7vXcyZ22huUcss6lzzNJ1qFdzZ5ZlG5Gi/NoSTA"
    "nlOMLhyWY4vcKJg24YzltMmPvMKSs5PDLmP2NI5Wgkplc3MqUpZVVGFcbU5hzoiL4iWcueTIRY0y"
    "Hl3ljkUllWPOGxrlcuXIGNeLlqJwsdoZdiFMiFX72Hqi7zHttbJmx0KDZ4UVugQlHipDy896lV2V"
    "T9XgUOoZ3jBjV5kKQkfkoCijnAIh+oMhObEHadCHTvfDwV6UKfBUwv4U8hY8xlRuoY9QS8lj4gh2"
    "TwNlQ4y9ocKnwaHJlH0KIFTNn62tcyr7Kin1zHEpoynX96mjVZQ36hxytTI4K1M1Q6fqqMPBJSvw"
    "JxfStOSrFnXULyqRV19d1zJBmIFsBMm3BF4flfhrxECzBOFGZXJwqew/i9o2kiTHd7AtNSMTrMyD"
    "SnY2zoktpm6qhkvs081S0dIXb7w2cixg9fBxgtcTt1j21u9siPCDxvUUaFv7Ijghu+HCs+7esW83"
    "RAYmJBYn000KjII57OS7BXvpd//yCklGWpPUn1EZiLWXc7dTSu2L6Tzvqpyay6GYVLYXujXxD1kH"
    "LmNIligc5Si5P8/HXV3IsH6+R/Drk4D1qKClsT01ja2pTKDlmEMD2nOIGodRvLObFQUqVTu6x8tP"
    "2y0cj7mvbjhdo2cqPneeqNpAdacRTaF28e0ekfWNS26rLVqgcYh5Ww9DaYqyX0zae9FRw0s6nRQu"
    "l/vDbjiIs6OGAp1R7ojPwTpWpS8uHq5xKdRIBYly96gCylGLgk6WZ6B0lATgynIIaudtJge+ep0p"
    "FqT47nF2eWZxfm12vua6hOTYpDyrP7J7RhkCuBotZlGJRyDcZVddyjqKYLDuV+am1guW9kQxoLQY"
    "IECFuzW+8nlFi26ZH+rZsyLMpS7pAAIDwHMrGqiFU74WIertxD0eftiou01mvBW29yBMQgpxzAt0"
    "BlY01ryCYPTXDZj1+sdRw6CGiqluDaXBsWGCzmm4ogKi4SmGcCrHWvV0qT80eb3MzMjAoRyhvRwe"
    "JkTKZHsKsEu41H7IknuS7A37wdaRGRyPcZTkW+WrbOYtCFVcEqLGZF3ytbdj0zCxHmPnXtamGGFn"
    "NMw4gbnt6TEXST072mLDy4uzaDWKSgyFSFgF3EEMW94f2cwfv6KLO97M2qz1nl7STVXc2gACtxrE"
    "eW3PwuXnXt1bLDuP6mfbA59rY5h27R/FCWcskvFWxxuzqo1EZvUcjPqYnbL+gliDNbIkNJi24vnL"
    "ouFjHIgmZUbqEI3n7IdvPIDAOzKODwt+9MFP/9+zb7z+4Pv3IWQPIxI0XI/H4eA9+Pm3Pvzla0qQ"
    "IypooOOGFgwdLP6jHlxHcW+OBblms0lvu0tKom13w3NNZEyJ2keAJ1R5FGvqxlumspMLF0PYeow7"
    "4MhCohxGtLrzMDIpstNN5BPFzJQf1JVJtkmbx1wGjBeh1iUG28UC+ejxaa3miPBO3t1aWHru94NB"
    "4zcuI+sJKx3m5djixhd3Yzk4NCqHiE5N1jUIv/Vgr2t1Le6KGYMDoloROsAK0+CjjpM5OcSbEizq"
    "6owIoBnEnWfX03HH7rbu8j13sLjGqe+irbUysMadFo6ikRcOoBseRR1KJ6sseKvS+uuI1KqGWDm4"
    "0KqOJJLutdhpUJJHAt3JwHnxgsx37hB1MqzD7pPD1prrNwKLKyBsRQKShBXycKwOe2C6g2xETQtK"
    "22YcBuymgEeacy+jAD7LwsKfb+SHcLciCBvjlk1+upXPTuZMKo9PykmrAr6g1uoynikkPNP2dkTd"
    "UfmQ5Hj8RgVCADRLggQ0o/VL2r86+CwGSlsjuiP0i1o5KtUZcdN9VVvJuTC/WwrQsWrkdyTSew5o"
    "CwKM7q1jJbTXwGk9jwFCS3/m6HDkpc0ly9YOsesyWmyuAZy0KaZmITJFzXjbQOGgTtXbLip+HoXw"
    "YrJzSZpgdNOuICijb7EhZkKo6h0YgP54P0rTcMcUbquImDkGah8zbW432UlrCI+GAEGDz1pRXOkG"
    "YiPahF1I+UoH5+bs+YDd3DibxOgSg20hdWkeQg/1akVNinpJW4qZ3JTvqZRAmxJXc68kXXP7QDQn"
    "Qq4tjZF4WOjVUabaibLwY77p2so6Bbtxiok8XRaLAqYNBGODQ67BgKVsUJj2R3M7oowy51Iyz1aQ"
    "zybPMTP3XdXdC0D5mG9dzYKRgZJdfZhbSndYenryIzBVzJe0mPWiC7VzRCU5vVIpaW5+bZa75FRE"
    "VXXvUE+dihaQuT48g+gAs/5gPtyRvHUeh8J6HP+Lx//aD+PeZSX/K4v/NfXU9aeeMuN/PTV19frj"
    "+F+P4gPU8sWFpae9mQXv31/9lmL5coPKWpAh4sv/9NtX/4rmczg9eYelinjtjdPX/vb0/g9PX/uF"
    "d2t9fcWbWVkY+6zG33mLRDQdeBPeXBzu9BIipbVT+HXD243CbrY7NmJmQDXSmMwSOIj4N1AAie9w"
    "/oI2nD8YDuMO7Ww3y/pNQHyZh/lGmEYwiVWaNPVWCHMnR9X6LoSoJMIlvFzDKnkxy/DxcNDtxlsQ"
    "gCoVl134I3g5bcBb/MHjmynBzQTMrFeDyAtTuHEi0NkaxJ0dTL3aS14mHOTNa5NTuGx67lgCYFqS"
    "NQbx/EQQti1ojuzyoLOlvCZ8ARkCEUXUfMf8mVquQ0T3rSQcdHjBOf5gjZIStXCUdXkxHiYWHcQC"
    "8kItdxB24w5FGVacPYkg+GpAPcSU8shbsXQCYg3Zb7iT62VxdsQrKLjHk0LPLC7emJl9Plidn1lb"
    "XlprePRLcGt+cQUY2G4XLveYrhCzwg4y1hy9h1FC2oUAT/rUXSQBcppq75phJ+xjtDaB7WH3KI3T"
    "gL1oeHthshXKn4oWhT1jDSb9tLmf9ECKUhDytniirwqU7kcDjHqn3MdCgP1BB3wfSQ1ZVGCw7Lwd"
    "9sO2BO4wlfAHjGHHCYAEfsJr/kyp0QyHEEqcVrtDHswMIZknpBZcWQien3+JMFtmegr5kmU7uwXR"
    "/53l4A0Umrr6THOS/G+KlF5ZXl1nty6OGvAWanwOg6jVx0SSw5U7NxYXZoMbC0tzrpwZrnLMzJ60"
    "o+WKpKHrpnhKUJo0kn6HxJGQCZTGakv2wN2dbG5CVBoVJMVcd2oITQh0mYw46ib9qImNwbX/b0++"
    "9sG33vHkvfx//PJ1i/CL/D3/8cs3lEv+PJURmKVDTiuPxtkDl96QukCHxzyiP07GVD5t+PAYPW/g"
    "i5YuiZZggIkGkBa9wwR1XevFAh9xuePaJBU8smG/G23EIIQ6xQ8ta0qDz4DeZfEg3tPkMcb5mfYw"
    "cpbns57JA6GD8jtk6HEXPGNhTY6l2yo7SmruE4aFkaaHUSBD5ftwJo/PLExMNq/5qiHaTsD6ZPLX"
    "9j5TUXhXwsFOiljj0Br0B4D5/saT6SbL3FOjHvakQSSzcHQGkBKit0PkSmiWlIEW64r8FxD63d4T"
    "hm8lIM4zfZM7udwCDiKswzgJv0AOtpTuui8QwIw/D2bIcKdS0hxgjX9naebO+q3l1YX/Oj8H+zzu"
    "4fkCTA/m9SUIM2X59ONA5NxT0DExoVciWyNvQzgWgcZNrOja2MTo4FHNig2O8IDBwAHYJ+wRQQUc"
    "j6sIhVvNn6VajPH1oz7mqsUI0G08cSdgQJ+HO27CmWSt/O7MthbJWZbt+g28KetGPQzmWC+qOdMm"
    "53g6Dg0Mku74DET1HF/GbPQwqCv+yJVvUbyA2uoUGx7HEbIY5GwhJ+ErONnRe7iNqemxh+fm1xuY"
    "dIb8O7M+e6vhLa9g/guzVdloWtMSArJsAZ+GUC7XjCgsUPEQfFab9IoAoKmYNoUDml2W7IAwIwCn"
    "mOgTJEB6ErASQZhZ1k60Y6yf61/EgqnmtQ6vAQTD3l4vOewZF2r7oJXB2LrIXNDYWnjyjfOe694V"
    "b4qcrsYWVdiOGkHK2G94LLpvyrdZC4iyArw/AOrO4miwNAvKLt2KCDLxYbNpQIvSPlefO4LdAUQy"
    "Icd8cqox4PUxJbkYyi6SeCNVQhpAlIk85fYTRFJKIYRux0NSS3MskWo85RHlmYDRy3ZZAiSIoRvt"
    "E8wPRX4k2tR+Ary2VyN7XTPHg1HUMUETzcNE2TBMzUSvnRXfnScgeiIdEBgOESDG3S4jkKn39ORT"
    "np4Dby2YW1iDdDlzTYPsWbyTWXF+Cesp7JMrQxHDZ2iT5S25Z2fhPnZsLUq/r+BxkDdmqJ8zLL5z"
    "oC8y7bpLH2cYQaow3xkSAUnw07rScn51dXk1gAOKyCN/cmeBDKDhKHBjee6lYH15OVicWX1u3lVi"
    "dWZ9PkANpNkCPbeNpB1wjRKg2rFhRhBKTbQNmBo86CLRNyroRbeSzhFtN9g6ysxoNoTHibePzOZB"
    "IGg4sh/ZkATs5XDkOwzitugNjin3qDBg3J2l06rZvIZx2CnrjjO0M/WYs9fxlo2GO4ESTGdP/pAp"
    "zgsR14kIns/IkAddo3FDRFANmwPOZqoEWS0te/4KafAxLF5A6IZtbofHcvBvUtgYXx32KC9ne9MP"
    "Cnm/3PLtbgxLGnY6hEFKTSu9+igbA4OA49QUGDLzkXn8A+w6yP9326ZuvRMp5yl53/CoGGGezgwz"
    "aIWWixpMu2FqIYZOQpgBU7tOuds8q8DicagkpeowNDKkjuLqs9VGgYeQcXxgVwNkj0AjV6Pbpq7s"
    "KeQItsDaJx+1cYeYAcibnUjjtG2jocoGQ9ZJc2NmDldknmokoDIdBOzZeAChklBYLdyhXDyVVuv5"
    "hK+GresGMvBIs4q5d2xyMlS40ftR2KpOEjBW1+BcpCpy6XOTV12NEka3gR1Kxgi1QoKeKFIkkZt4"
    "DKVyuVK5QUR1UktokhSS287ukhfwHnVOoBgEgwwHoTfEhLoptZKWcsXVhlvKvBGFA8JTZcle1NMX"
    "3BY2SfMNQ+IkQCcSRzWA+77/AlUefK75bHNq2uvBRaA3v9/PjsbBRuwI1cTDXjsc7uxmNCN86v37"
    "V75JdfdPE5YakLOp3p7akSJxWem4AuA7ayNSxUxGigG6ACr5JvxzrWbsAKqvsGOG+Ruka0qbNkVr"
    "rXv82zHy4K17uhjzGY1R/0yDzgNzOxw78s1t+/cyIkMi1WoG6IEdBMfT3j3y4NgfKzJbZFcOTRx+"
    "QMrXKhg2KpvFedf/NI/6aX7u5eaxU/VY+YWEfqs45R5TfvkLS+vzq0sziwGCvyTbnqIk4ycA0FUb"
    "sCXNZDK4YFZoUQGfY/er43Irbht3UTNgITCViZjWwdsPj0QSs62IJ5Anew1y3X8eLfnH4VYCxKtk"
    "JycJJUV1HbO3wxhErizBYYjd6cJ4snx8qMeaJKxu0xxxE1li2Iz8Yqomd8aYoRmgZfGdePVyKvjq"
    "l0GbhSXIThscmeeLLpbTDlQKSztpef4EvRk0slbKywvkzyK8mDqSd2T0vmaAZrVwsiT7zLiDXjMa"
    "3AV7jJYkxTWN7Vu0U6+6dum9kiiKsE/zYjpusa1Dr+qaIs1NbkRH3fsHmsf4qeZlV159CwaFlIFS"
    "GAFLFvZhzy9IrqkEj9SrFYdOx6pxmtIAqUZV9hxpy8Zmcd+EYYIsSAdAk0BdWZwt1OiI6vd5GPa6"
    "GLhslI0hP7dowejofg9AB5NmlzY8vdWLjK8TYcTSSx+h2e5Fxrgf9uJtOOS5i8dlDdJq+CKjTIf7"
    "++Hg6NIHabZ7zjE6jsrjIpNCJqlIR24UTyidlJdFGjNNiuQKTeQdkdcbUGZjarO4qye85T5NFoZm"
    "mCyZJzk62wSjUq+WJtvZOD0hpj0GFnLOtPdC8PQTyeu3CLnco2YWgwRSrRbYH9JjiN1nB0qvTSqQ"
    "yft8UjXoxCmh2O3dgCwQchRxAI/Jr1ym2QCMqMCuektHFmfnGRZc/404MFml4tCGMbVbqD6u4ajg"
    "GlrgUtFOeZt7CULK0NqycE1nhmRjhQ0ZaE2LI2azr1ObuZoQ7dpGBXRub1iKDlyt4B66KFx18LwC"
    "Dl/8qDyBKsMXgy8b+ogDV4Y9yqAlM3owNaHong2mlCUvqL2cqrHhke76/ib46VLXQEO5ShMSiFos"
    "LH1JNchll1JrEF3lzIyBMFR+cBhnuwGUwYQJLSVpQMuR30BT0kw2wPBE6aZeTH0hK+Agam4Pu919"
    "2LW1gQmtidrGn05sfrbOrvS0M2DfUKUIrcB+c4dQ4X5tSu+de3bZ8+f2SABMZf48LZsrYAoLNlKq"
    "zfSXlteDm8t3lui9kGkfA01tJ+Q7anSuVVNt5muqLklbxbW4prYKPqZFVq3eZDewCkAP4ujQzY+Q"
    "NtF6K9+Jggmn1eMYtBTvB8bIaO/zZAIRNDivFb1AXjNQrXWP52Qi4pgCB9KMX6o4cGwhFVVL9pBJ"
    "ahRLxQkuzY0Lae5ikigZ2ag6pPPJkVh1N+r2ST3VqtLNbo7mwFIGQLQTnWB2oAbEsuhuptJd+E3J"
    "Ln/ysk6Fnddbpo1pDZpxUhksMSqRgQnQoE60n5Foi4uewyCaYUqJYh0s3NjeB2ynOVGpEa1/PCqy"
    "Qo5wbiDsO+h5/vHIn4hi9vHniDV7QK/ThFFyTVRviW+lu5NUNoAwy6cwKgBUo+0yrZXmcZRsQffh"
    "VtwlCMQ54K1h3O2QuZFfPbi9dGmunvBmOp0YlA3estYG02fVVogYDaa9/EG0vxV1iHj9eVAkDdtA"
    "EeEKAAOUdOoPh6C4J5IXMcZYCgklbYKwNfpsblDw4JqTNF+EdJBV0leU7JgBIcQXWFJAVu3F2IUh"
    "bjVJjnAeJcfa3vngPL5cUAmXgAsAS7QRCKPfiwLLavKjg1BIhN3sIrgUHYTdIXWHgJYuDpx7Ph+T"
    "2XatfvyIwAR63xRIZ7Yf9p3AwRJc4aL5GcAL4VlgS1hpwKzONDErrSaeQeYQMIZreRsH3AgNXSwP"
    "wN5Mtt9M+wQKNb9BYy6Lsu4TDF1FWvboa8iyBgwM9J29jrTXljq+ItA7jj7o31jYNejrFoP/qOcf"
    "XT2md7y01etHgzjpqCtHn/CVw9O621UWkD8ZBdhs1DXadov+qRuHLZH44B4PdFEzC+OHMZo/kra8"
    "GnBo6Pmy8p8XjXtrYaJhM9ZXruAS2L7BYRzsxhmaHTGPCRYBnD+suytlSf8pu5Z8Ws/vK8yCp90d"
    "yjc51QdJrFWC3zlF+4NkO86YT4SjSNpO+oiIO91kK+wGYWzchh2XIbWwoLfxeo1h5qh4DQs7QUa+"
    "A9ZjBl6jlQbhqeNIqrmlNYslB9CSxUIALVNNeZBCUDjUEig6sEthKgy1ADziIKgpcr95gIIegzmY"
    "XfAsQC93IvtHE/tJL9vtHn3SII/DVukWPihX7FFpEQvbw0U6CoIN2KIrPof4u4EW6q9oim5zNLxs"
    "E+JF8OLNYdZG6+pteFLzn3xp/Ml9O4IZXExhO+hm8wwMHn9uXNuEB/64X0G8NQzg6Ljw8mUr8l4i"
    "n/Hbt502cDkr8YS3GL4CBhZZ1o0oEe4PBwR70ijlRvIgfISDqNzyxoH5tOEAAsqg6ydzNB12M30j"
    "FNqPTDsyv6ap44QUWK953fKHOSekOGKchckc2PzV8Tbo0tXPR09neSeztOXRZWWxu/kN/Cdrcxur"
    "1ezG21H7qN3V1k08rLJuVmHwcwAdPgVQPq6NvmiLvKuRl43AIt5mbmLp7+OacRt/sNAShJ1a1jPC"
    "/vSkJO1PT9bPs+IalO1jW9vFNBnyfni3NkW2dNyj2ZEbcLYba/vRYU3YIQPLVQo8BN0gdEVaMwMR"
    "ADVnfP55VIUdDL+qAUf0cE6YRFl3ghtBPWygMG85J1jIOAL6/lyQke7SCmzms+4aC+8wOCd42Dnr"
    "BpFiAmgaqqkb2no59rAB3Y/7UTfuMW8PewCcnWbFLMDrkBKmibw8k8yofpnZ/DjT1ENbNn0V7bkv"
    "eq5coQVys0SDoiHgibp5N3kmi9Qwqchs8MqVWoEpU3X7vY1Ci6m7hW9Bk3MXYzLUzmXhVy9snSzH"
    "XRuJCKKLn7nVN0ewEHxUAHDaEH4kELBtEB8VDHKsFD8SKDisHB8VGPLsID8SONh2lI+MJLgtLR81"
    "FFyWmo/aRKD49MB14scYWSD+tZjK76CZt376sccVrLxRegdneLsN+aronAkH7V16xOjV+fOiuoNh"
    "z6oHz4rqHDwzReoEAWVhgqDYFBjidlAeKAzAzLXXBn9SYI1Akmht+NyhgTQbkHIBv8UsMARu5tRR"
    "OJTKGGhd6dJI5zOCGbpF+ZjLvr2l/CNcu5FJjJdd3UrgmR4kBggeOu94nj1aYbn0NVjupy88M3Wb"
    "AeX4EgBNsHCQHITdfBDzEsFhMtjb7iaHIswE6jh4/TG3yCKgyz1DRgEkl1L0nniMHAM2M+z9nwyj"
    "4eiSLhdYOuHRuCAchrpyFr3RvXZIhCNQVe5EXhrvgNV6rZd4KwsL9SaGqPESbs1+EIfejZs3m58M"
    "8YdnocsXQcp0wjieQn/oHCXQ5UpebAEt0UtQfofs9UjM8MRilEpg6gkGHpNbSdKtsd/VDj32rfiQ"
    "C4QjV81x2JnyU5lrFwvXgFsDmuTroDajlbnIcUTgNxcezbD5PpxjCLQ8LKq0QQ3K1YlXmTrRUAqQ"
    "1tyaHMY28PjsVD1IQ0mX0UeoY1DDBWztFhv7BfV+woTVPCS23FMx/RdrpTPY3jLGf5M1scosVy86"
    "AyFc6Dd9zJfIOQseMxTux8tnwEob07hNn85BBMXzTiELJ6hZs/uMxut7VkA7mtmzsUqnKyts2VXB"
    "yNdY7+ebgIxoagKfsjEE+FaI05pgZSsAnjZjAl72em4NZgT0ayI6iJHBzJ8IXQdegTBMsXqO8/qB"
    "rF+6JDn1bLNf1uc8K3vRufI4vCV2gHlT5dUDUb3STO1q1kTXdsNOcnhuC+e8ae6AxRGGTT3fPGX9"
    "ClMeyYqjsAsXHmDp5+R8LkM4EACTzhTj7WTQz9Ho54FL9fHB2txo63JAldu8BSbp+DNLZzEakPYx"
    "jaXbW8oFKm7Om07U/lsnx3sKmzwnMHn7BhjpGHPK1oBhob0K/6y60+vBHpixSNcwHFBJnF3dKUJG"
    "EvH5gBTnq+Pj8zpHQGOXTRpVFx439xCM4MVXt30AWZRkFv0AnjhdvWnIciXChR7LnDr6lZ6StLB5"
    "uMsploInx0uQRzu/TBdBx/DNoOooDfKHwkXwfFOApJLsiL9MP0c3WsC4qV9ZsWPj5fk00owyLPTO"
    "CD5I6IFFJsHC3GM6NnxWq0vVghtl2a7oRXeJcDRQUtpgk3DLqSgn4o6iPke7RGdQPWwzJNOReyaM"
    "A7l2YLhd5E28tWGU3yy4Sa1tuXsoutsEE9gBbKttAqoM/RitLuveBITObU42zhVNptSGliUogDTt"
    "XwRSIfuubZ1zdxDisBdlD8EF+GL745Idf8+7SSqsAQMgT3F/DhNmcv584szs0oM2Y0J0q8zSk/yg"
    "jTiwH1U3Vh4NotvhQQJRudPfJ5AiNyJm/rBAC02Owy4aZ+r0TxqIwWNeczUiv6vYfWM9uHP2ubYQ"
    "AvO3wSEfEzKTH92uX3cZE6t2hYYBM7eGFjrBXEvSkewCi1Y4B3S/YxbxTgvywqVgngy5RuROo+xL"
    "WxVmlP5C2B3SULXOiJwVLmjUOMKTZfxAMBwM3DyBtc8LuQNo5xNGBxQWBkZfKqZc7MYox2tHwTUd"
    "1QSnXH5LomHVBa9I9oNkeztH+4HRGhgSTJBicTsOuww73EhBCk1fcFPyfjRIYctStfFQN+RikuwN"
    "+znZ5otZUT52jw67JARN2cHrvqP62G+z6jb59QtxQpW3p2CVHCcut9hn2V0fovdc9slzVVRS60qL"
    "D/G0itXHw1pSdw5pvs4AbX2R5ahb8uujJrVudTzKgh8r3LiISIJzylXVjyKGFFNalufIY3mPKHFV"
    "I7ND6p1qodkvGmR51ADKWhS2cUiX4owdVZSd6GMT41MkbwFiX56chWcOepw74lxhUs8V+RS1hSLv"
    "6Frc2+lGbA/O4qvLiKAKWKmEUIWfFYOCOgbEooMCaCAc/bQX7/QSw11Y6ei8sVdNwGTRgnybD5qR"
    "QrhKuLCwnyNBxjGiarBROrv88K98TsOR13poL9qY4gdF6AamuUyG1qjJTg6yhJMKI+EQy9g5vk7r"
    "jt9OfTMXGalcQS6xxgBUjdYuEd0rtGUFvIUToYkJ7VK4UaxRITyeIEQKbkRUYBUFxGXQVIrXHAKX"
    "ywegSiYad2CQkEW3jDotzCZbwATRYLzFszCoKyvPw/Hi9xEiw1owhf3AoarvDWVE+Na95Yrj+ra3"
    "YVM6azZhbwVR76Dmit1As4rxNpr74V2amwyzklWQPFdmXlpcJkeQyDTmj55qLI8DhEExxNIg9hGj"
    "FvLG2zstDrRGybYL9tOW/qQEVeXER4q+LNBV/roYwsKZKFG2CGHt0zN35BxTrSpV8PTjh6ISQT9u"
    "6GlhpitS9ohYpuLYyBgmBA9MWu/SRjjEOS3BPTlrexHm3cNkVVWzmFXUeOElixWzE4fZsIN5mlcu"
    "H2nMZiZ1wLRHTu2mtrHhB0xbgTYMivZC51smSxLfUjCj9hGMiyTUmqgVOc8Qwau21z4KirIIZ5M8"
    "gXBzspzRusQonVzVbkbdZIGzRQpud0BsCigdHvShARG3qkhCpiW/jprMqkIwImZ6c88Roc0dBZIr"
    "WRwx3brhUQTGfL62pYrCugELjTBhSYQG7V1CvwkxgNTO9uipjQwfGCCzHqBSrZ5TWcSSxdoH1/LK"
    "hTvgLrpJ4z6LAdKnFYzn6DqfIxA4EJKJbgJp0Q0HEngm8+fB1mL6b/aCaiDkc/7E983QNGl6SBDY"
    "aoi/cFcb/boFB1bjw2uIjh/uHctKNECDx6RX9Z7FzN0Y9w7CLgF0exBhqG9wdnQlUq26lIQ39KfH"
    "RgEbqTHqIXIpIKw0o5QUMkO2jo4c2Ao+dNNPjjatImT38xzCOKq1SjDcXRv0EYSWYZbClqytPs6r"
    "SnAHtTgdpZ54lleJnHT7aXBAk3gqFbXnrsq/S+YDj82u8I6jI6yu9GsmwIrHpldlJCfE6wx2slGO"
    "VPUlpa/Z7ucOBY504nE/Rx94MxkchoNO1IFvtJ0KecdRnRY6m4QlHJ9xcBUMrnxCZNW4dZcj9GYp"
    "tR1EO3EK4Zx4I/mxJkpTvVSVcvM4WwpgDqtW3M8vRhEOoNMahu5iNtSg83OAKA0PImoYghxktHMk"
    "fWAqAasiUCrO4neHkNvGXzQeyzgLtPpJIzyXTBxGJQxlXFVuCNvi6JL6jtR33mUElxzlrNrHgJmY"
    "jgqRQDMg02saIWZFoE1hW0YbYSZlY/Yk0LZM6e4TbHiozMJtgHgZYVGdx+4gOojCLhkEKC5dx1gO"
    "SQQ9s08rY9qYbpSRtQKdHZSazlGssL4wwoVklq1mHMre8qis++Fgj8GwPBMah37DMztv0QeXybBX"
    "iM5qWxlWp/eqCYxK7a99PEyLMVAuhIfouA1KtUC6YvNDebc1qWzv9zC0sXMP95CKUG9fCZ0Cw9iK"
    "m0ldGWyywr7qGarpR7Z1asreaShIXr/8jeRwFqeB7UezoGfMVI6vOL77XRDsPiYSWRXmSzUuP18y"
    "Tb5wYvO5i11ECKsggJUIX4/MUv7hb72cODTxDs2SoyNwv9+lW4d8CzpbTVasXL9zz2d1IdYW/QYR"
    "0LbITxgsa66zFcBYavX6+WKW0NRM9CwY3yKSPo3AmZuiiRdhUSg97U8g3rJEYXC66mfJdjJoRzY3"
    "ho8JC1aGnxgHwn3DWDCEGjbfwn8rX8ZoKHiDtUrDXl0gpjuDdCc8slNEh0EnHljXLPyFUELz3GG5"
    "4fqs+pF512NE7VMaLQrcx0dyrrh9dHLnid2H6Afg7MZbHN9WQjPjpRKsisDZwEsCbiQLWTeQT8bc"
    "eKQXqkFPNT7+esMrjYLP4hkQriEcBBjLMbWPyYIYiHiZFDK9JPsBCfe6LDpC6QD0g+eeTyYE8QDp"
    "tWSYBmggQGbiy57Ie/lDVzm51WOyfbPd84n781l3hYf/vUDCBJZVoCBlwkX2xiUHs5TDOs+uoAHV"
    "AjC9taalvDNnx7NcV9n2o5MkZzPV9q/Yfxg1ki1kJyDLanNFBbEtlam3lO92QT6Hlr7BkYfl886x"
    "vhp1v+ceMupuvOwMGZxyPKS94FzpC5MuB6Rkm2Y83mGWvCAp2MXyiGA87t99onE5oYHJxHZ2Ipss"
    "sOcmbNjjQCM9+2FvGHYtXfWA5k5Xr+DhETgc4YW4ozh7x5QR9FmdLje2ZhqqwphZqWacduKdmOw/"
    "udVH4VZ13N0jQlJ61Gvb5fEVAyqUMKuKUIxJr3tkV9de+/UcC7u8uMYEPCNRULZcLfa34Tj7FbC3"
    "tF92YYXzdhBrAy4tAUO7rAaElvZrxOy2TgbfjD5fSk+e8F6ghhafa37O47HBvRd5DPPaXNTvJkcE"
    "pchWhUF+3luZn5idn5hZ8Ia9LBkCea8r2hwIP051OVyP86eOKOpCjVOjj6IvDSKIAlT/T26NDpQa"
    "OfA6axrU1ND2mCnQ0lrsFgF+u68PxOW6VuiqVSixKQk+NekIN0qlBAQBY2eiVC7A2TQc998s5S8r"
    "UFOm1KADauG/zht2LggxC8Q9l91hmS8x/yCFL87iMLOysrr8wsxicHNmYRHszQqLAxTl4GiwRAYu"
    "OlePJukpirINn2uTk/kF6mPVnzrOoJxd6cg5XRxxP6d5GhLawij6uNrpjEXPcTTjbuEDOM/xzPCS"
    "NqSjJW21Rf8UYGlFDC3DzmLMHAEr8zGSgascIXORsV5ByVgxptqoyHfZLuIz67O3PjY+4o+9tj9J"
    "Xtu/rxH9Rgq6Qv2F9x1GkhVcUC4tFst5qMQYkAiI+FiTpGGMMqBRLx0OIm/uhgf6kv2Q8JkgOlAf"
    "aA29nXcPpveHdXHSH8Cu3PY7Wx6r6R2Gg17c25n27pGSsAvYUJZ70TiGWQNfCRp1CKMje1wd7/37"
    "V75JpQ5FL+/VZhY++Jevn33j9bOf/c0H7/2aAIjjkzb8ChcQFBaB8TZSoqVvxRhs1l3MoG4xs8Rm"
    "b80TlALGlnV8MVt1krwVAjTW8GcIukXw6DP1Y2+QHKae72isthtnaUvUgV+k/IR4sB3fzWAy0AB5"
    "UfdzMJGMSE4p7AKFPAqKp+aeCKsLYVVTkKz//dVvoQjHZugbXWIc1TiPC+HIJXpiCwkN9jVgUZ6H"
    "zNAfEW/Npt3Iu0t9N28tr62PsfXHR+gJONnE/8H2nJ6GfzempzeZNyzMb2YhmFlcXH4xWLlzY3Fh"
    "NrixsDQ3rZxOMaEga0dpFu3P340NlCEy5/YQ04NkCQEUabE/3OrGbQy+Mdgme6Vp4AWQHugSxtqa"
    "uvoMDm7KqxESERLpte5tRbvQTrubDDvbXSKZw5Wh3gReeLsH3ppCSRVj1bbJyTuAgOAdrxtupU3f"
    "sIUDeogqoPVdQAoyi1vr6ytr+LRWAwA2vJXl1XVCPG/REA60Hl+bFxeWniaD8GpWzNzPeqqPFvk5"
    "d6MOlG03y/rTExP3oO3j6XvQOMcIOhiMFRIFZPTRAToijo2RtQzQ/yII8HwMAqCkQcDORkpWxz71"
    "+FPlw47AdOIw7j09HsaglVDiB6UTQRD34iwImv2j8/YxST7Xr13Dv+Rj/p2cun5dfMfnU9evXp/8"
    "lDf5KAAwBO940v3v6fo/4Y1fGSeEoYM0FPlheDLm+z6EuPIc4aS8PujICDFFDrXWTdpht970npsn"
    "pfVtfnry87MfvvHgr//59OS7pyc/OT3589NX75OWH2/OT87+345CZEj6ce+8JKBk/1+bvDpl7P9n"
    "JqeuPd7/H/H+v0lXfjEB2d07+/KPzr7616cnPzt763vvv/fq6WvfOn3tF2Q7w7Y/PfkHstUfvP2T"
    "D9959+xnf0UKnZ78zen9kwff/buzd7/noVEBPvw1/EdJALL/QbA9ROwKhJq6RzgwbmOEZYBpie5m"
    "yj0ze7If9sKdaKCVOghlVKlZ+uiFcNDw1pO9qDfGg0eH7S7IrqkSP5o+oiWyoz4wcOzlTI/IjgtZ"
    "hB7lY2OwEXpRJ2D7YlrpZoMUBWdx+aTm66V9kNaRrWvRfBUBo6XQasA1BFqbcG1kNeqopDSN9lTA"
    "KeGcPGUdb6JerrY67IFcR61aKdcE6g1whr85P7N+Z3U+wLgqTBHoamk1glW9mQy24k4n6tWsTora"
    "XZ2nzS+v3liYm5tfgh7+i1iEGlmEV6IeBkCps55XEIxKJ7z1AbO1jDtoQTcmb8+mYeWYqE3TgKor"
    "QQVvq1nvS4owTmqQoRsVUXypj0lNABbT9Q3kScNuW72PzBtWAFClYyOjV4fhmoI6CrwKBbURjCal"
    "P7E/INwUIqxXF/bQLgHXptVG8c7SiaMUDFyVkeZMRFmJhnelYa8XdoubEzeP1rkJeNJJzQJqTW0S"
    "Pb3VB2DahUNo0T9iwCDsuoecwWCmlTEZGhpzVNgSrQWN/xeDOCHACdxGA0vDk7QA1oB51eBQOCna"
    "gDExiHFuLe5tE1I94Yk8Wacnb559483Tk+/pexdvl0/vf/PsK2+dvf6/PvjWO6cn3z+9/zVCmskT"
    "Sq8/+PHJg3f/jhFrEaaDDgolZR7cJDXCC1H52CY6PgMBNh8NlPqiWZBROXMJ82GS4EAEvFAB5br0"
    "4Zc9cafCeOhCeuqw+FBSbUnYMHCNUc1ahOz6arYGPOsCaTngLbh3FOARpXmWruwojrrUG2I77oXd"
    "rvLK3RbFStGnolsvRvzHcvNj/l/n/3eG4aCTXkD6L+P/r16dmnzalP8nJ596zP9/XOV/wsrjDe94"
    "u5vAteWDH7794G/+jRwVhHGDq72Od/b6f3/w178hMoEq+I+NgTzws7+a9lZW5+cWZtcXlpeC1TtL"
    "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"
    "f/7/9uCABAAAAEDQ/9dBO1QAABavmWh0AFgCAA=="
)
# END_CANDIDATE_TAR_GZ_B64
DEFAULT_BFF_HEALTH_JSON = (
    '{"ok":true,"meta":{"service":"BffHealth","cache":"no-store"},'
    '"data":{"status":"ok","service":"bff","runtime":"cloudflare-pages-functions",'
    '"ai_proxy_configured":true}}'
)
DEFAULT_BFF_PREDICTIONS_CLOSED_JSON = (
    '{"ok":false,"error":{"code":"OPS_CLOSED","message":"closed","details":null}}'
)
DEFAULT_STATIC_HTML = (
    "<!DOCTYPE html><html><head><title>Expect ~ KEIBA AI ~</title></head>"
    "<body><p class=\"brand-name\">Expect</p></body></html>"
)


class Halt(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class Deadline:
    def __init__(self, hard_s: float) -> None:
        self.started = time.monotonic()
        self.hard_s = float(hard_s)

    def remaining(self) -> float:
        return self.hard_s - (time.monotonic() - self.started)

    def require(self, seconds: float, code: str) -> None:
        left = self.remaining()
        emit("DEADLINE_REMAINING_S", "%.1f" % max(0.0, left))
        if left < seconds:
            raise Halt(code)


class FileRec:
    rel: str
    pre: str
    dest: Path
    kind: str
    backup_bytes: bytes | None
    created: bool
    live_sha: str
    cand_sha: str


class State:
    deploy_phase = PHASE_NOT_STARTED
    deploy_executed = False
    files_replaced = False
    restart_executed = False
    recovery_restart_executed = False
    restored = False
    audit_closed = False
    http_calls: list[tuple[str, str]] = []
    restart_counts: dict[str, int] = {}
    ai_key = ""
    ai_port = 8000
    unit = RESTART_UNIT
    deadline: Deadline | None = None
    backup_dir: Path | None = None
    records: list[FileRec] = []
    ops_sha: dict[str, str] = {}
    pre_main_pid = ""
    pre_exec_ts = ""
    restart_outcome = ""
    readiness_probe_count = 0


STATE = State()


def emit(key: str, value: object) -> None:
    if value is True:
        text = "YES"
    elif value is False:
        text = "NO"
    else:
        text = str(value)
    print("%s=%s" % (key, text.replace("\n", " ")))
    sys.stdout.flush()


def test_mode() -> bool:
    return (os.environ.get("OWNER_DEPLOY_PACK_TEST") or "").strip() == "1"


def test_fail_mode() -> str:
    return (os.environ.get("OWNER_DEPLOY_TEST_FAIL") or "").strip()


def candidate_sha_map() -> dict[str, str]:
    return {str(t["rel"]): str(t["cand"]) for t in DEPLOY_TARGETS}


def remote_hard_deadline_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_DEADLINE_S") or "").strip()
        if raw:
            return float(raw)
    return float(REMOTE_HARD_DEADLINE_S)


def deadline() -> Deadline:
    if STATE.deadline is None:
        STATE.deadline = Deadline(remote_hard_deadline_s())
    return STATE.deadline


def wrapper_budget_ok() -> bool:
    remote_ms = int(REMOTE_HARD_DEADLINE_S * 1000)
    need = remote_ms + DRAIN_WAIT_MS + KILL_DRAIN_WAIT_MS + SAFETY_BUFFER_MS
    return WRAPPER_TIMEOUT_MS >= need


def repo_root() -> Path:
    if test_mode():
        root = (os.environ.get("OWNER_DEPLOY_TEST_ROOT") or "").strip()
        if not root:
            raise Halt("TEST_ROOT_UNSET")
        return Path(root)
    return Path(REPO_ROOT)


def win5_root() -> Path:
    return repo_root() / "services" / "win5-ai"


def canonical_source() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_DEPLOY_TEST_SRC") or "").strip()
        if override:
            return Path(override)
    return Path(CANONICAL_SOURCE)


def refuse_unapproved() -> None:
    v1 = (os.environ.get(V1_APPROVAL) or "").strip()
    v2 = (os.environ.get(V2_APPROVAL) or "").strip()
    v3 = (os.environ.get(APPROVAL) or "").strip()
    emit("OLD_EXECUTION_PACK_RERUN_ALLOWED", "NO")
    emit("OLD_EXECUTION_PACK", OLD_EXECUTION_PACK)
    emit("OLD_EXECUTION_ZIP_SHA256", OLD_EXECUTION_ZIP_SHA256)
    emit("V2_EXECUTION_PACK", V2_EXECUTION_PACK)
    emit("V2_EXECUTION_ZIP_SHA256", V2_EXECUTION_ZIP_SHA256)
    emit("V2_RERUN_ALLOWED", "NO")
    if (v1 == "1" or v2 == "1") and v3 != "1":
        raise Halt("OLD_EXECUTION_PACK_RERUN_REFUSED")
    if v3 != "1":
        raise Halt("OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED_UNSET")


def _flag_01(raw: str | None) -> int:
    return 1 if (raw or "").strip().lower() in ("1", "true", "yes", "on") else 0


def file_sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def open_regular(path: Path, flags: int = os.O_RDONLY) -> int:
    fd = os.open(str(path), flags | O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            os.close(fd)
            raise Halt("NOT_REGULAR_FILE")
        return fd
    except Halt:
        raise
    except OSError:
        try:
            os.close(fd)
        except OSError:
            pass
        raise Halt("OPEN_FAIL")


def read_regular(path: Path) -> bytes:
    fd = open_regular(path)
    with os.fdopen(fd, "rb") as fh:
        return fh.read()


def file_sha_nofollow(path: Path) -> str:
    return file_sha_bytes(read_regular(path))


def lexical_join(root: Path, rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute() or any(part in ("..", "") for part in p.parts if part == ".."):
        raise Halt("PATH_ESCAPE")
    if any(part == ".." for part in p.parts):
        raise Halt("PATH_ESCAPE")
    dest = root.joinpath(*p.parts)
    root_s = str(root)
    dest_s = str(dest)
    if dest_s != root_s and not dest_s.startswith(root_s.rstrip("/") + "/"):
        raise Halt("PATH_ESCAPE")
    return dest


def exists_nofollow(path: Path) -> bool:
    try:
        os.lstat(str(path))
        return True
    except OSError:
        return False


def is_symlink(path: Path) -> bool:
    try:
        return stat.S_ISLNK(os.lstat(str(path)).st_mode)
    except OSError:
        return False


def extract_candidates() -> dict[str, bytes]:
    if CANDIDATE_TAR_GZ_B64 == "EMBED_CANDIDATE_TAR_GZ_B64":
        raise Halt("CANDIDATE_EMBED_MISSING")
    raw = base64.b64decode(CANDIDATE_TAR_GZ_B64.encode("ascii"))
    emit("CANDIDATE_TAR_GZ_SHA256", file_sha_bytes(raw))
    wanted = candidate_sha_map()
    out: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                raise Halt("CANDIDATE_TAR_NONFILE")
            name = member.name.replace("\\", "/")
            if name.startswith("./"):
                name = name[2:]
            if not name.startswith(CANDIDATE_PREFIX):
                raise Halt("CANDIDATE_TAR_PATH")
            rel = name[len(CANDIDATE_PREFIX) :]
            if rel.endswith("022_prediction_run_idempotency.sql"):
                raise Halt("CANDIDATE_022_SQL_FORBIDDEN")
            if rel not in wanted:
                raise Halt("CANDIDATE_UNEXPECTED")
            extracted = tf.extractfile(member)
            if extracted is None:
                raise Halt("CANDIDATE_TAR_EMPTY")
            data = extracted.read()
            got = file_sha_bytes(data)
            if got != wanted[rel]:
                raise Halt("CANDIDATE_SHA_MISMATCH")
            if rel == "app/main.py":
                if len(data) != MAIN_PY_CANDIDATE_SIZE:
                    raise Halt("MAIN_PY_CANDIDATE_SIZE_MISMATCH")
                if got in (ORIGIN_MAIN_PY_SHA256, V6_MAIN_PY_SHA256, LIVE_MAIN_PY_SHA256):
                    raise Halt("WHOLESALE_MAIN_PY_REPLACE")
                if got != MAIN_PY_CANDIDATE_SHA256:
                    raise Halt("MAIN_PY_CANDIDATE_SHA_MISMATCH")
                emit("MAIN_PY_HUNK_ONLY", "YES")
            out[rel] = data
    if len(out) != len(DEPLOY_TARGETS) or len(out) != 10:
        raise Halt("DEPLOY_TARGET_COUNT_MISMATCH")
    emit("DEPLOY_TARGET_COUNT", len(out))
    emit("CANDIDATE_BYTES_VERIFIED", "YES")
    return out


def migration_list(conn: sqlite3.Connection) -> list[str]:
    try:
        return [str(r[0]) for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")]
    except sqlite3.Error:
        return []


def prediction_columns(conn: sqlite3.Connection) -> list[str]:
    try:
        return [str(r[1]) for r in conn.execute("PRAGMA table_info(predictions)")]
    except sqlite3.Error:
        return []


def pred_row_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()
    return int(row[0] if row else 0)


def pred_row_count_ro(path: Path) -> int:
    conn = sqlite3.connect("file:%s?mode=ro" % path.resolve().as_posix(), uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        return pred_row_count(conn)
    finally:
        conn.close()


def normalize_sql(sql: str) -> str:
    return " ".join((sql or "").split()).lower()


def inspect_index(conn: sqlite3.Connection) -> str:
    listed = {
        str(r[1]): int(r[2] or 0)
        for r in conn.execute("PRAGMA index_list(predictions)").fetchall()
    }
    master = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
        (PARTIAL_INDEX,),
    ).fetchone()
    if PARTIAL_INDEX not in listed and master is None:
        return "missing"
    unique = listed.get(PARTIAL_INDEX, 0) == 1
    cols = [str(r[2] or "") for r in conn.execute("PRAGMA index_info(%s)" % PARTIAL_INDEX).fetchall()]
    sql = normalize_sql(master[0] if master and master[0] else "")
    compact = sql.replace(" ", "")
    has_unique = unique and ("createuniqueindex" in compact or " unique " in " %s " % sql)
    single_key = cols == ["idempotency_key"]
    has_predicate = "whereidempotency_keyisnotnull" in compact
    on_predictions = "onpredictions(idempotency_key)" in compact
    if has_unique and single_key and has_predicate and on_predictions:
        return "ok"
    return "mismatch"


def inspect_race_index(conn: sqlite3.Connection) -> str:
    names = {str(r[1]) for r in conn.execute("PRAGMA index_list(predictions)").fetchall()}
    if RACE_INDEX not in names:
        return "missing"
    rows = conn.execute("PRAGMA index_info(%s)" % RACE_INDEX).fetchall()
    cols = [str(r[2] or "") for r in sorted(rows, key=lambda r: int(r[0]))]
    if cols == ["race_id", "created_at"]:
        return "ok"
    return "mismatch"


def verify_schema_readonly(path: Path, *, prefix: str = "") -> int:
    emit("%sSCHEMA_WRITE" % prefix, "NO")
    emit("%sMIGRATE" % prefix, "NO")
    emit("%sBEGIN_IMMEDIATE" % prefix, "NO")
    conn = sqlite3.connect("file:%s?mode=ro" % path.resolve().as_posix(), uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        migrations = migration_list(conn)
        cols = prediction_columns(conn)
        have = set(migrations)
        owner = set(OWNER_MIGRATIONS)
        missing = sorted(owner - have)
        extra = sorted(have - owner)
        emit("%sSCHEMA_MIGRATIONS_COUNT" % prefix, len(migrations))
        emit("%sSCHEMA_MIGRATIONS_UNIQUE_COUNT" % prefix, len(have))
        emit("%sPREDICTIONS_COLUMN_COUNT" % prefix, len(cols))
        emit("%sHAS_PERSIST_022" % prefix, PERSIST_022 in have)
        emit("%sHAS_PERSIST_019" % prefix, PERSIST_019 in have)
        emit("%sPARTIAL_UNIQUE_INDEX_STATE" % prefix, inspect_index(conn))
        emit("%sEXISTING_RACE_INDEX" % prefix, inspect_race_index(conn))
        rows = pred_row_count(conn)
        emit("%sPRED_ROW_COUNT" % prefix, rows)
        if PERSIST_019 in have:
            raise Halt("HAS_PERSIST_019")
        if len(migrations) != 23 or have != owner or missing or extra:
            raise Halt("SCHEMA_MIGRATIONS_MISMATCH")
        if cols != list(OWNER_PRED_COLUMNS):
            raise Halt("PREDICTIONS_COLUMNS_MISMATCH")
        if inspect_index(conn) != "ok":
            raise Halt("PARTIAL_UNIQUE_MISMATCH")
        if inspect_race_index(conn) != "ok":
            raise Halt("EXISTING_INDEX_MISSING_OR_MISMATCH")
        emit("%sSCHEMA_READONLY_PASS" % prefix, "YES")
        return rows
    finally:
        conn.close()


def parse_systemd_show(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip()
    return out


def parse_assignment_blob(blob: str, *, split_null: bool, extra_keys: tuple[str, ...] = ()) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = blob.replace("\n", "\0") if split_null else blob
    parts = raw.split("\0") if split_null else raw.split()
    wanted = set(WATCHED_ENV_KEYS) | set(extra_keys)
    for part in parts:
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        if key in wanted:
            out[key] = val
    return out


def parse_env_file(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, val = stripped.split("=", 1)
                key = key.strip()
                if key in WATCHED_ENV_KEYS:
                    out[key] = val.strip().strip("'\"")
    except OSError:
        return {}
    return out


def environment_file_paths(raw: str) -> list[str]:
    paths: list[str] = []
    for chunk in (raw or "").replace(" ", "\n").splitlines():
        item = chunk.strip()
        if not item:
            continue
        path = item.split("(", 1)[0].strip()
        if path.startswith("/"):
            paths.append(path)
    return paths


SECRET_LINE_RE = re.compile(
    r"(AWS_|SECRET|TOKEN|PASSWORD|API_KEY|AUTHORIZATION|BEARER|"
    r"EXPECT_AI_API|X-AI-Key|Environment=)",
    re.IGNORECASE,
)
BASE64_LINE_RE = re.compile(r"^[A-Za-z0-9+/]{80,}={0,2}$")


def argv_is_allowed_sudo_restart(args: list[str]) -> bool:
    return list(args) == list(RESTART_ARGV)


def redact_text(text: str, *, cap: int = 4096) -> str:
    out_lines: list[str] = []
    used = 0
    for line in (text or "").splitlines():
        if SECRET_LINE_RE.search(line):
            line = "REDACTED_SECRET_LINE"
        elif BASE64_LINE_RE.match(line.strip()):
            line = "REDACTED_BASE64_LINE"
        if used + len(line) + 1 > cap:
            out_lines.append("REDACTED_TRUNCATED")
            break
        out_lines.append(line)
        used += len(line) + 1
    return "\n".join(out_lines)


def run_cmd(args: list[str], *, timeout_s: float | None = None) -> tuple[int, str, str, bool]:
    if any(a == "sudo" or str(a).startswith("sudo") for a in args):
        if not argv_is_allowed_sudo_restart(args):
            raise Halt("SUDO_REFUSED")
    if args[:2] == ["systemctl", "restart"] or (len(args) >= 3 and args[-2:] == ["restart", RESTART_UNIT] and args[0] != "sudo"):
        raise Halt("RESTART_ARGV_REFUSED")
    try:
        default_t = float(RESTART_TIMEOUT_S if argv_is_allowed_sudo_restart(args) else SUBPROCESS_TIMEOUT_S)
        use_t = float(timeout_s) if timeout_s is not None else default_t
        use_t = min(use_t, max(1.0, deadline().remaining() - 1.0))
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=use_t,
            check=False,
        )
        return int(p.returncode), (p.stdout or ""), (p.stderr or ""), False
    except Halt:
        raise
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ((exc.stdout or b"").decode("utf-8", errors="replace") if exc.stdout else "")
        err = exc.stderr if isinstance(exc.stderr, str) else ((exc.stderr or b"").decode("utf-8", errors="replace") if exc.stderr else "")
        return 124, out, (err or "TIMEOUT"), True
    except Exception:
        return 1, "", "", False


def read_proc_environ(pid: str) -> tuple[bool, dict[str, str]]:
    if not pid.isdigit() or int(pid) <= 0:
        return False, {}
    try:
        with open("/proc/%s/environ" % pid, "rb") as fh:
            blob = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return False, {}
    return True, parse_assignment_blob(
        blob,
        split_null=True,
        extra_keys=("AI_PORT", "AI_API_KEY", "AI_HOST"),
    )


def collect_production_env(*, after: bool = False) -> dict[str, object]:
    prefix = "AFTER_" if after else "BEFORE_"
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_ENV") or "").strip() == "1":
        show = os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_SHOW") or ""
        proc_blob = os.environ.get("OWNER_DEPLOY_TEST_PROC_ENVIRON") or ""
        file_blob = os.environ.get("OWNER_DEPLOY_TEST_ENVFILE") or ""
        sd = parse_systemd_show(show)
        proc = parse_assignment_blob(
            proc_blob.replace(" ", "\0"),
            split_null=True,
            extra_keys=("AI_PORT", "AI_API_KEY", "AI_HOST"),
        ) if proc_blob else {}
        files = parse_assignment_blob(file_blob.replace(" ", "\0"), split_null=True) if file_blob else {}
        systemd_ok = bool(show) or (os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_OK") or "") == "1"
        proc_ok = bool(proc_blob) or (os.environ.get("OWNER_DEPLOY_TEST_PROC_OK") or "") == "1"
        files_ok = bool(file_blob) or (os.environ.get("OWNER_DEPLOY_TEST_FILES_OK") or "") == "1"
    else:
        rc, show, _err, _to = run_cmd(["systemctl", "show", RESTART_UNIT, "--property=Id,LoadState,ActiveState,SubState,MainPID,FragmentPath,Environment,EnvironmentFiles,ActiveEnterTimestamp,ExecMainStartTimestamp,NRestarts,Result"])
        sd = parse_systemd_show(show) if rc == 0 else {}
        systemd_ok = rc == 0 and bool(sd)
        pid = str(sd.get("MainPID") or "")
        proc_ok, proc = read_proc_environ(pid)
        files = {}
        files_ok = True
        for env_path in environment_file_paths(sd.get("EnvironmentFiles") or ""):
            parsed = parse_env_file(env_path)
            files.update(parsed)
        unit_env = parse_assignment_blob(sd.get("Environment") or "", split_null=False)
        files.update(unit_env)
    emit("%sSYSTEMD_COLLECT_OK" % prefix, systemd_ok)
    emit("%sPROC_COLLECT_OK" % prefix, proc_ok)
    emit("%sENVFILE_COLLECT_OK" % prefix, files_ok)
    emit("SYSTEMD_CHANGED", "NO")
    emit("ENV_CHANGED", "NO")
    merged: dict[str, str] = {}
    merged.update(files)
    merged.update(proc)
    for key in WATCHED_ENV_KEYS:
        raw = merged.get(key)
        emit("%s%s" % (prefix, key), raw if raw not in (None, "") else "UNSET")
        if _flag_01(raw) == 1:
            raise Halt("%s_EFFECTIVE_1" % key)
    port = merged.get("AI_PORT") or proc.get("AI_PORT")
    if port and str(port).isdigit():
        STATE.ai_port = int(port)
    key = merged.get("AI_API_KEY") or proc.get("AI_API_KEY") or ""
    STATE.ai_key = key
    STATE.unit = str(sd.get("Id") or RESTART_UNIT)
    if STATE.unit and STATE.unit != RESTART_UNIT:
        raise Halt("UNEXPECTED_SYSTEMD_UNIT")
    emit("%sUNIT" % prefix, STATE.unit)
    emit("%sUNIT_LOADSTATE" % prefix, str(sd.get("LoadState") or ""))
    emit("%sUNIT_ACTIVESTATE" % prefix, str(sd.get("ActiveState") or ""))
    emit("%sUNIT_SUBSTATE" % prefix, str(sd.get("SubState") or ""))
    emit("%sUNIT_MAINPID" % prefix, str(sd.get("MainPID") or ""))
    emit("%sUNIT_EXECMAINSTARTTIMESTAMP" % prefix, str(sd.get("ExecMainStartTimestamp") or ""))
    if not after:
        STATE.pre_main_pid = str(sd.get("MainPID") or "")
        STATE.pre_exec_ts = str(sd.get("ExecMainStartTimestamp") or sd.get("ActiveEnterTimestamp") or "")
    emit("AI_PORT", STATE.ai_port)
    return {"systemd": sd, "proc": proc, "files": files}


def verify_ops_live(root: Path) -> None:
    emit("LIVE_OPS_DEPLOY", "NO")
    for item in OPS_TARGETS:
        dest = lexical_join(root, item["rel"])
        if is_symlink(dest):
            raise Halt("OPS_SYMLINK")
        if not exists_nofollow(dest):
            raise Halt("OPS_ABSENT")
        got = file_sha_nofollow(dest)
        emit("OPS_SHA_%s" % item["rel"].replace("/", "_"), got)
        if got != item["live"]:
            raise Halt("OPS_SHA_MISMATCH")
        STATE.ops_sha[item["rel"]] = got
    emit("OPS_SHA_VERIFIED", "YES")
    emit("OPS_DEPLOYED", "NO")


def verify_must_absent(root: Path) -> None:
    for rel in MUST_ABSENT:
        dest = lexical_join(root, rel)
        if exists_nofollow(dest):
            emit("MUST_ABSENT_PRESENT", rel)
            raise Halt("MUST_ABSENT_PRESENT")
    emit("MUST_ABSENT_OK", "YES")


def verify_preconditions(root: Path) -> None:
    for item in DEPLOY_TARGETS:
        dest = lexical_join(root, item["rel"])
        present = exists_nofollow(dest)
        if is_symlink(dest):
            raise Halt("DEST_SYMLINK")
        if item["pre"] == "ABSENT":
            emit("PRECONDITION_%s" % item["rel"].replace("/", "_"), "ABSENT" if not present else "PRESENT")
            if present:
                raise Halt("PRECONDITION_ABSENT_MISMATCH")
            continue
        emit("PRECONDITION_%s" % item["rel"].replace("/", "_"), "LIVE_SHA")
        if not present:
            raise Halt("PRECONDITION_LIVE_SHA_ABSENT")
        got = file_sha_nofollow(dest)
        emit("LIVE_SHA_%s" % item["rel"].replace("/", "_"), got)
        if got != item["live"]:
            raise Halt("PRECONDITION_LIVE_SHA_MISMATCH")
    emit("PRECONDITIONS_PASS", "YES")


def backup_targets(root: Path) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_BACKUP_DIR") or "").strip():
        bdir = Path(os.environ["OWNER_DEPLOY_TEST_BACKUP_DIR"])
    else:
        bdir = repo_root() / "var" / "code_backups" / stamp
    bdir.mkdir(parents=True, exist_ok=True)
    STATE.backup_dir = bdir
    emit("BACKUP_DIR", str(bdir))
    records: list[FileRec] = []
    for item in DEPLOY_TARGETS:
        dest = lexical_join(root, item["rel"])
        rec = FileRec()
        rec.rel = item["rel"]
        rec.pre = item["pre"]
        rec.dest = dest
        rec.cand_sha = item["cand"]
        rec.created = False
        rec.live_sha = ""
        rec.backup_bytes = None
        if exists_nofollow(dest):
            if is_symlink(dest):
                raise Halt("DEST_SYMLINK")
            data = read_regular(dest)
            rec.kind = "FILE"
            rec.backup_bytes = data
            rec.live_sha = file_sha_bytes(data)
            outp = lexical_join(bdir, item["rel"])
            outp.parent.mkdir(parents=True, exist_ok=True)
            outp.write_bytes(data)
            emit("BACKUP_SHA_%s" % item["rel"].replace("/", "_"), rec.live_sha)
        else:
            rec.kind = "ABSENT"
            marker = bdir.joinpath(*Path(item["rel"] + ".ABSENT").parts)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_bytes(b"ABSENT\n")
            emit("BACKUP_ABSENT_%s" % item["rel"].replace("/", "_"), "YES")
        records.append(rec)
    STATE.records = records
    STATE.deploy_phase = PHASE_BACKED_UP
    emit("DEPLOY_PHASE", PHASE_BACKED_UP)
    emit("BACKUP_RECORDED", "YES")


def stage_replace(root: Path, candidates: dict[str, bytes]) -> None:
    if test_fail_mode() == "before_replace":
        raise Halt("INJECTED_BEFORE_REPLACE")
    for rec in STATE.records:
        data = candidates[rec.rel]
        if file_sha_bytes(data) != rec.cand_sha:
            raise Halt("CANDIDATE_SHA_MISMATCH")
        dest = rec.dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        created = not exists_nofollow(dest)
        rec.created = created
        tmp = dest.parent / (".step1_staging_" + dest.name)
        if exists_nofollow(tmp) or is_symlink(tmp):
            try:
                tmp.unlink()
            except OSError:
                raise Halt("STAGING_TMP_BUSY")
        tmp.write_bytes(data)
        if rec.rel.endswith(".py"):
            py_compile.compile(str(tmp), doraise=True)
            emit("SYNTAX_OK_%s" % rec.rel.replace("/", "_"), "YES")
        if file_sha_bytes(tmp.read_bytes()) != rec.cand_sha:
            raise Halt("STAGING_SHA_MISMATCH")
        if test_fail_mode() == "syntax" and rec.rel.endswith(".py"):
            raise Halt("INJECTED_SYNTAX_FAIL")
        os.replace(str(tmp), str(dest))
        got = file_sha_nofollow(dest)
        emit("POST_REPLACE_SHA_%s" % rec.rel.replace("/", "_"), got)
        if got != rec.cand_sha:
            raise Halt("POST_REPLACE_SHA_MISMATCH")
    STATE.files_replaced = True
    STATE.deploy_phase = PHASE_REPLACED
    emit("DEPLOY_PHASE", PHASE_REPLACED)
    emit("FILES_REPLACED", "YES")
    if test_fail_mode() == "after_replace":
        raise Halt("INJECTED_AFTER_REPLACE")


def restore_code_only() -> None:
    emit("SCHEMA_ROLLBACK", "NO")
    emit("CODE_RESTORE_ONLY", "YES")
    if not STATE.records:
        emit("CODE_RESTORED", "NO")
        return
    for rec in reversed(STATE.records):
        dest = rec.dest
        if rec.kind == "ABSENT":
            if exists_nofollow(dest) and rec.created:
                dest.unlink()
            continue
        if rec.backup_bytes is None:
            raise Halt("BACKUP_BYTES_MISSING")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.parent / (".step1_restore_" + dest.name)
        if exists_nofollow(tmp) or is_symlink(tmp):
            try:
                tmp.unlink()
            except OSError:
                raise Halt("RESTORE_TMP_BUSY")
        tmp.write_bytes(rec.backup_bytes)
        os.replace(str(tmp), str(dest))
        got = file_sha_nofollow(dest)
        if rec.live_sha and got != rec.live_sha:
            raise Halt("RESTORE_SHA_MISMATCH")
    STATE.restored = True
    STATE.deploy_phase = PHASE_RESTORED
    emit("DEPLOY_PHASE", PHASE_RESTORED)
    emit("CODE_RESTORED", "YES")


def snapshot_unit(*, after_restart: bool) -> dict[str, str]:
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_ENV") or "").strip() == "1":
        fail = (os.environ.get("OWNER_DEPLOY_TEST_RESTART_FAIL") or "").strip() == "1"
        if after_restart and not fail:
            show = os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_SHOW_AFTER") or os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_SHOW") or ""
        else:
            show = os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_SHOW") or ""
        return parse_systemd_show(show)
    rc, show, _err, _to = run_cmd(
        [
            "systemctl",
            "show",
            RESTART_UNIT,
            "--property=Id,LoadState,ActiveState,SubState,MainPID,FragmentPath,ActiveEnterTimestamp,ExecMainStartTimestamp,NRestarts,Result",
        ]
    )
    if rc != 0:
        return {}
    return parse_systemd_show(show)


def classify_restart(*, phase: str, rc: int, timed_out: bool, before_pid: str, before_ts: str, after: dict[str, str]) -> str:
    load = str(after.get("LoadState") or "")
    active = str(after.get("ActiveState") or "")
    pid = str(after.get("MainPID") or "")
    ts = str(after.get("ExecMainStartTimestamp") or after.get("ActiveEnterTimestamp") or "")
    pid_ok = False
    try:
        pid_ok = int(pid) > 0
    except ValueError:
        pid_ok = False
    unit_ok = load == "loaded" and active == "active" and pid_ok
    changed = False
    if pid and before_pid and pid != before_pid:
        changed = True
    if ts and before_ts and ts != before_ts:
        changed = True
    emit("RESTART_UNIT_LOADSTATE", load)
    emit("RESTART_UNIT_ACTIVESTATE", active)
    emit("RESTART_UNIT_MAINPID", pid)
    emit("RESTART_UNIT_EXECMAINSTARTTIMESTAMP", ts)
    emit("RESTART_MAINPID_CHANGED", "YES" if (pid and before_pid and pid != before_pid) else "NO")
    emit("RESTART_EXECMAINSTARTTIMESTAMP_CHANGED", "YES" if (ts and before_ts and ts != before_ts) else "NO")
    if not after:
        return "UNKNOWN"
    if phase == "RECOVERY":
        if unit_ok:
            return "SUCCESS"
        return "FAIL" if not timed_out else "UNKNOWN"
    if unit_ok and changed:
        return "SUCCESS"
    if unit_ok and not changed:
        return "FAIL"
    if not unit_ok:
        return "FAIL"
    if timed_out:
        return "UNKNOWN"
    return "FAIL"


def restart_once(phase: str) -> None:
    if phase not in ("DEPLOY", "RECOVERY"):
        raise Halt("RESTART_PHASE_INVALID")
    if STATE.restart_counts.get(phase, 0) >= 1:
        raise Halt("RESTART_COUNT_EXCEEDED")
    emit("RESTART_UNIT", RESTART_UNIT)
    emit("RESTART_COMMAND", " ".join(RESTART_ARGV))
    emit("RESTART_PHASE", phase)
    emit("SUDO_USED", "YES")
    emit("SUDO_N_FLAG", "YES")
    emit("RESTART_TIMEOUT_S", RESTART_TIMEOUT_S)
    argv = list(RESTART_ARGV)
    if argv != ["sudo", "-n", "systemctl", "restart", RESTART_UNIT]:
        raise Halt("RESTART_ARGV_REFUSED")
    before_pid = STATE.pre_main_pid
    before_ts = STATE.pre_exec_ts
    emit("RESTART_BEFORE_MAINPID", before_pid)
    emit("RESTART_BEFORE_EXECMAINSTARTTIMESTAMP", before_ts)
    timed_out = False
    rc = 1
    out = ""
    err = ""
    if test_mode():
        log = (os.environ.get("OWNER_DEPLOY_TEST_RESTART_LOG") or "").strip()
        if log:
            with open(log, "a", encoding="utf-8") as fh:
                fh.write("sudo -n systemctl restart %s\n" % RESTART_UNIT)
        if (os.environ.get("OWNER_DEPLOY_TEST_RESTART_FAIL") or "").strip() == "1":
            rc = int((os.environ.get("OWNER_DEPLOY_TEST_RESTART_RC") or "1").strip() or "1")
            err = os.environ.get("OWNER_DEPLOY_TEST_RESTART_STDERR") or "FAILED"
            timed_out = (os.environ.get("OWNER_DEPLOY_TEST_RESTART_TIMEOUT") or "").strip() == "1"
        elif (os.environ.get("OWNER_DEPLOY_TEST_RESTART_TIMEOUT") or "").strip() == "1":
            rc = 124
            err = "TIMEOUT"
            timed_out = True
        else:
            rc = 0
            err = ""
            timed_out = False
            STATE.restart_counts[phase] = STATE.restart_counts.get(phase, 0)
    else:
        rc, out, err, timed_out = run_cmd(argv, timeout_s=float(RESTART_TIMEOUT_S))
    emit("SYSTEMCTL_RESTART_EXIT", rc)
    emit("SYSTEMCTL_RESTART_TIMEOUT", "YES" if timed_out else "NO")
    emit("SYSTEMCTL_RESTART_STDOUT_REDACTED", redact_text(out, cap=2048))
    emit("SYSTEMCTL_RESTART_STDERR_REDACTED", redact_text(err, cap=2048))
    if test_mode() and rc == 0 and not timed_out:
        STATE.restart_counts[phase] = STATE.restart_counts.get(phase, 0) + 0
    after = snapshot_unit(after_restart=True)
    outcome = classify_restart(phase=phase, rc=rc, timed_out=timed_out, before_pid=before_pid, before_ts=before_ts, after=after)
    STATE.restart_outcome = outcome
    emit("RESTART_OUTCOME", outcome)
    if outcome == "UNKNOWN":
        raise Halt("RESTART_UNKNOWN")
    if outcome != "SUCCESS":
        raise Halt("RESTART_FAIL")
    load = str(after.get("LoadState") or "")
    active = str(after.get("ActiveState") or "")
    pid = str(after.get("MainPID") or "0")
    if load != "loaded" or active != "active":
        raise Halt("RESTART_UNIT_NOT_ACTIVE")
    try:
        if int(pid) <= 0:
            raise Halt("RESTART_MAINPID_INVALID")
    except ValueError:
        raise Halt("RESTART_MAINPID_INVALID")
    STATE.pre_main_pid = pid
    STATE.pre_exec_ts = str(after.get("ExecMainStartTimestamp") or after.get("ActiveEnterTimestamp") or "")
    STATE.restart_counts[phase] = STATE.restart_counts.get(phase, 0) + 1
    if phase == "DEPLOY":
        STATE.restart_executed = True
        STATE.deploy_phase = PHASE_RESTARTED
        emit("DEPLOY_PHASE", PHASE_RESTARTED)
        emit("RESTART_EXECUTED", "YES")
        emit("DEPLOY_RESTART_COUNT", 1)
    else:
        STATE.recovery_restart_executed = True
        emit("RECOVERY_RESTART_EXECUTED", "YES")
        emit("RECOVERY_RESTART_COUNT", 1)
    emit("RESTART_COUNT_%s" % phase, STATE.restart_counts[phase])


def readiness_poll_timeout_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_TIMEOUT_S") or "").strip()
        if raw:
            return float(raw)
    return float(READINESS_POLL_TIMEOUT_S)


def readiness_poll_interval_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_INTERVAL_S") or "").strip()
        if raw:
            return float(raw)
    return float(READINESS_POLL_INTERVAL_S)


def readiness_http_timeout_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_HTTP_TIMEOUT_S") or "").strip()
        if raw:
            return float(raw)
    return float(READINESS_HTTP_TIMEOUT_S)


def readiness_max_attempts() -> int:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_MAX_ATTEMPTS") or "").strip()
        if raw:
            return int(raw)
    return int(READINESS_MAX_ATTEMPTS)


def _unit_ready(unit: dict[str, str]) -> bool:
    load = str(unit.get("LoadState") or "")
    active = str(unit.get("ActiveState") or "")
    pid = str(unit.get("MainPID") or "0")
    try:
        pid_ok = int(pid) > 0
    except ValueError:
        pid_ok = False
    return load == "loaded" and active == "active" and pid_ok


def probe_readiness_health() -> tuple[str, int | None]:
    STATE.readiness_probe_count += 1
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_READINESS_NEVER") or "").strip() == "1":
        return "HTTP_FAIL", None
    fail_n_raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_FAIL_COUNT") or "").strip() if test_mode() else ""
    fail_n = int(fail_n_raw) if fail_n_raw else 0
    if test_mode() and fail_n > 0 and STATE.readiness_probe_count <= fail_n:
        return "HTTP_FAIL", None
    url = localhost_ai("/health")
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_HTTP") or "").strip() == "1":
        st, health, _c, _f = _http_fixture(url, "GET")
        ok = st == 200 and isinstance(health, dict) and str(health.get("status") or "") == "ok"
        return ("PASS" if ok else "HEALTH_FAIL"), st
    timeout_s = min(readiness_http_timeout_s(), max(0.5, deadline().remaining() - 1.0))
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = read_limited(resp, HTTP_MAX_INTERNAL_HEALTH_BYTES, CLASS_INTERNAL_HEALTH)
            status = int(resp.getcode() or 0)
    except Halt:
        raise
    except urllib.error.HTTPError as exc:
        status = int(exc.code or 0)
        raw = read_limited(exc, HTTP_MAX_INTERNAL_HEALTH_BYTES, CLASS_INTERNAL_HEALTH) if exc.fp else b""
        try:
            health = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            health = {}
        ok = status == 200 and isinstance(health, dict) and str(health.get("status") or "") == "ok"
        return ("PASS" if ok else "HEALTH_FAIL"), status
    except Exception:
        return "HTTP_FAIL", None
    try:
        health = json.loads(raw.decode("utf-8")) if raw else {}
    except Exception:
        return "HEALTH_FAIL", status
    ok = status == 200 and isinstance(health, dict) and str(health.get("status") or "") == "ok"
    return ("PASS" if ok else "HEALTH_FAIL"), status


def wait_until_ready() -> None:
    timeout_s = readiness_poll_timeout_s()
    interval_s = readiness_poll_interval_s()
    max_attempts = readiness_max_attempts()
    emit("READINESS_POLL_TIMEOUT_S", timeout_s)
    emit("READINESS_POLL_INTERVAL_S", interval_s)
    emit("READINESS_HTTP_TIMEOUT_S", readiness_http_timeout_s())
    emit("READINESS_MAX_ATTEMPTS", max_attempts)
    emit("READINESS_SINGLE_SHOT", "NO")
    emit("READINESS_ARBITRARY_SLEEP_ONLY", "NO")
    deadline().require(min(timeout_s, 5.0), "INSUFFICIENT_TIME_READINESS")
    started = time.monotonic()
    attempt = 0
    last_health = "NONE"
    last_status: int | None = None
    last_unit: dict[str, str] = {}
    while attempt < max_attempts:
        if (time.monotonic() - started) >= timeout_s:
            break
        if deadline().remaining() < 1.0:
            raise Halt("INSUFFICIENT_TIME_READINESS")
        attempt += 1
        emit("READINESS_ATTEMPT", attempt)
        unit = snapshot_unit(after_restart=True)
        last_unit = unit
        load = str(unit.get("LoadState") or "")
        active = str(unit.get("ActiveState") or "")
        pid = str(unit.get("MainPID") or "")
        emit("READINESS_UNIT_LOADSTATE", load)
        emit("READINESS_UNIT_ACTIVESTATE", active)
        emit("READINESS_UNIT_MAINPID", pid)
        if active == "failed":
            emit("READINESS_OK", "NO")
            emit("READINESS_OUTCOME", "FAIL")
            raise Halt("READINESS_UNIT_FAIL")
        health_outcome, status = probe_readiness_health()
        last_health = health_outcome
        last_status = status
        emit("READINESS_HEALTH_OUTCOME", health_outcome)
        emit("READINESS_HEALTH_STATUS", status if status is not None else "NONE")
        if _unit_ready(unit) and health_outcome == "PASS":
            emit("READINESS_OK", "YES")
            emit("READINESS_OUTCOME", "PASS")
            emit("READINESS_ELAPSED_S", "%.3f" % (time.monotonic() - started))
            return
        elapsed = time.monotonic() - started
        remaining_poll = timeout_s - elapsed
        if remaining_poll <= 0:
            break
        time.sleep(min(interval_s, remaining_poll))
    emit("READINESS_OK", "NO")
    emit("READINESS_OUTCOME", "TIMEOUT")
    emit("READINESS_ELAPSED_S", "%.3f" % (time.monotonic() - started))
    emit("READINESS_LAST_HEALTH_OUTCOME", last_health)
    emit("READINESS_LAST_HEALTH_STATUS", last_status if last_status is not None else "NONE")
    emit("READINESS_LAST_UNIT_ACTIVESTATE", str(last_unit.get("ActiveState") or ""))
    raise Halt("READINESS_TIMEOUT")


def maybe_recovery_restart() -> None:
    if STATE.restored and (STATE.restart_executed or STATE.restart_outcome == "UNKNOWN"):
        restart_once("RECOVERY")
    else:
        emit("RECOVERY_RESTART_EXECUTED", "NO")
        emit("RECOVERY_RESTART_COUNT", 0)


def class_for_path(path: str, public: bool, method: str = "GET") -> str:
    if method == "POST":
        return CLASS_DISABLED_POST
    if public:
        if path in PUBLIC_STATIC_PATHS:
            return CLASS_PUBLIC_HTML
        return CLASS_PUBLIC_JSON
    if path == "/health" or path.endswith("/health"):
        return CLASS_INTERNAL_HEALTH
    if path == "/v1/predictions":
        return CLASS_INTERNAL_LIST
    if path.startswith("/v1/predictions/"):
        return CLASS_INTERNAL_DETAIL
    return CLASS_INTERNAL_HEALTH


def cap_for_class(endpoint_class: str) -> int:
    return {
        CLASS_INTERNAL_HEALTH: HTTP_MAX_INTERNAL_HEALTH_BYTES,
        CLASS_INTERNAL_LIST: HTTP_MAX_INTERNAL_LIST_BYTES,
        CLASS_INTERNAL_DETAIL: HTTP_MAX_INTERNAL_DETAIL_BYTES,
        CLASS_PUBLIC_JSON: HTTP_MAX_PUBLIC_JSON_BYTES,
        CLASS_PUBLIC_HTML: HTTP_MAX_PUBLIC_HTML_BYTES,
        CLASS_DISABLED_POST: HTTP_MAX_INTERNAL_HEALTH_BYTES,
    }[endpoint_class]


def read_limited(fp: object, max_bytes: int, endpoint_class: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        piece = fp.read(65536)  # type: ignore[attr-defined]
        if not piece:
            break
        total += len(piece)
        if total > max_bytes:
            emit("HTTP_ENDPOINT_CLASS", endpoint_class)
            emit("HTTP_BYTES_READ_AT_LEAST", total)
            emit("HTTP_LIMIT_BYTES", max_bytes)
            raise Halt("HTTP_BODY_OVERSIZED")
        chunks.append(piece)
    return b"".join(chunks)


def _parse_json_or_halt(raw: bytes) -> object:
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        raise Halt("HTTP_JSON_PARSE_FAIL")


def localhost_ai(path: str) -> str:
    return "http://127.0.0.1:%d%s" % (int(STATE.ai_port or 8000), path)


def ai_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if STATE.ai_key:
        headers["X-AI-Key"] = STATE.ai_key
    return headers


def redact_path(path: str) -> str:
    return path.split("?")[0]


def http_timeout_s(public: bool) -> float:
    base = float(HTTP_PUBLIC_TIMEOUT_S if public else HTTP_LOCAL_TIMEOUT_S)
    return min(base, max(1.0, deadline().remaining() - 1.0))


def _http_fixture(url: str, method: str) -> tuple[int, object, str, str]:
    parsed = urlparse(url)
    path = parsed.path or "/"
    final = url
    fail = test_fail_mode()
    if method == "POST":
        if path != "/v1/prediction-runs":
            raise Halt("POST_REFUSED")
        if fail == "post_enabled":
            return 200, {"ok": True}, "application/json", final
        return 503, {"error": {"code": "PREDICTION_RUNS_DISABLED", "message": "PREDICTION_RUNS_ENABLED is not 1"}}, "application/json", final
    if path == "/health":
        return 200, {"status": "ok", "db": "test", "fallback_reasons": [], "result_automation": {}}, "application/json", final
    if path == "/v1/predictions":
        raw = os.environ.get("OWNER_DEPLOY_TEST_GET_JSON") or '{"ok":true,"data":[{"race_id":"20260719_hanshin_11"}],"meta":{"count":1}}'
        return 200, json.loads(raw), "application/json", final
    if path.startswith("/v1/predictions/"):
        return 200, {"ok": True, "data": {}, "meta": {}}, "application/json", final
    if path == "/v1/conversation/health":
        return 200, {"ok": True, "data": {"status": "ok"}, "meta": {"service": "ConversationObservability"}}, "application/json", final
    if path == "/v1/challenge/active":
        status = int((os.environ.get("OWNER_DEPLOY_TEST_CHALLENGE_STATUS") or "401").strip() or "401")
        return status, {"ok": False, "error": {"code": "UNAUTHORIZED"}}, "application/json", final
    if path == "/v1/admin/results/status":
        return 200, {"ok": True, "data": {}, "meta": {}}, "application/json", final
    if path == "/api/health":
        return 200, json.loads(DEFAULT_BFF_HEALTH_JSON), "application/json", final
    if path in ("/", "/race.html", "/races.html"):
        return 200, DEFAULT_STATIC_HTML.encode("utf-8"), "text/html; charset=utf-8", final
    if path == "/api/predictions":
        return 503, json.loads(DEFAULT_BFF_PREDICTIONS_CLOSED_JSON), "application/json", final
    raise Halt("HTTP_FIXTURE_UNKNOWN_PATH")


def http_call(url: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[int, object, str, str]:
    parsed = urlparse(url)
    path = parsed.path or "/"
    host = parsed.netloc.split(":")[0] if parsed.netloc else "127.0.0.1"
    public = host in ALLOWED_PUBLIC_HOSTS
    if method not in ("GET", "POST"):
        raise Halt("HTTP_METHOD_REFUSED")
    if method == "POST" and path != "/v1/prediction-runs":
        raise Halt("POST_REFUSED")
    if method == "GET" and path == "/v1/prediction-runs":
        raise Halt("GET_PREDICTION_RUNS_REFUSED")
    deadline().require(1.0, "INSUFFICIENT_TIME_HTTP")
    hdrs = dict(headers or {})
    hdrs.pop("Authorization", None)
    hdrs.pop("authorization", None)
    label = "%s %s" % (method, ("%s://%s%s" % (parsed.scheme or "http", parsed.netloc, redact_path(path))) if parsed.netloc else redact_path(path))
    STATE.http_calls.append((method, label))
    emit("HTTP_CALL", label)
    endpoint_class = class_for_path(path, public, method)
    max_bytes = cap_for_class(endpoint_class)
    emit("HTTP_ENDPOINT_CLASS", endpoint_class)
    emit("HTTP_LIMIT_BYTES", max_bytes)
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_HTTP") or "").strip() == "1":
        return _http_fixture(url, method)
    allowed = ALLOWED_PUBLIC_HOSTS if public else ("127.0.0.1", "localhost")
    if public and host not in allowed:
        raise Halt("HTTP_HOST_REFUSED")
    req = urllib.request.Request(url, data=body if method == "POST" else None, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=http_timeout_s(public)) as resp:
            raw = read_limited(resp, max_bytes, endpoint_class)
            ctype = str(resp.headers.get("Content-Type") or "")
            final = str(resp.geturl() or url)
            status = int(resp.getcode() or 0)
    except Halt:
        raise
    except urllib.error.HTTPError as exc:
        raw = read_limited(exc, max_bytes, endpoint_class) if exc.fp else b""
        ctype = str(exc.headers.get("Content-Type") if exc.headers else "")
        final = str(exc.geturl() if hasattr(exc, "geturl") else url)
        status = int(exc.code or 0)
    except Exception:
        raise Halt("HTTP_FAIL")
    wants_json = path.startswith("/api/") or path.startswith("/v1/") or path == "/health" or method == "POST"
    if wants_json:
        payload = _parse_json_or_halt(raw)
        return status, payload, ctype or "application/json", final
    if path in PUBLIC_STATIC_PATHS:
        return status, raw, ctype, final
    return status, raw, ctype, final


def first_list_race_id(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    if not isinstance(first, dict):
        return None
    rid = first.get("race_id") or first.get("id")
    if rid is None or str(rid) == "":
        return None
    return str(rid)


def row_delta_or_halt(src: Path, before: int, label: str) -> None:
    after = pred_row_count_ro(src)
    delta = after - before
    emit("%s_PRED_ROW_DELTA" % label, delta)
    if delta != 0:
        raise Halt("PRED_ROW_DELTA_NONEZERO")


def check_internal_regression(src: Path) -> None:
    before = pred_row_count_ro(src)
    emit("REGRESSION_PRED_ROW_BEFORE", before)
    st, health, _c, _f = http_call(localhost_ai("/health"), headers={"Accept": "application/json"})
    emit("HEALTH_STATUS", st)
    emit("HEALTH_OK", "YES" if st == 200 and isinstance(health, dict) and str(health.get("status") or "") == "ok" else "NO")
    if st != 200 or not isinstance(health, dict) or str(health.get("status") or "") != "ok":
        raise Halt("HEALTH_FAIL")
    row_delta_or_halt(src, before, "HEALTH")
    st, listing, _c, _f = http_call(localhost_ai("/v1/predictions"), headers=ai_headers())
    emit("GET_LIST_STATUS", st)
    if st != 200 or not isinstance(listing, dict) or listing.get("ok") is not True:
        raise Halt("GET_PREDICTIONS_FAIL")
    row_delta_or_halt(src, before, "GET_LIST")
    rid = first_list_race_id(listing)
    if not rid:
        emit("DETAIL_GET", "SKIPPED_EMPTY_LIST")
    else:
        st, detail, _c, _f = http_call(localhost_ai("/v1/predictions/%s" % rid), headers=ai_headers())
        emit("DETAIL_GET_STATUS", st)
        if st != 200 or not isinstance(detail, dict) or detail.get("ok") is not True:
            raise Halt("DETAIL_GET_FAIL")
        row_delta_or_halt(src, before, "GET_DETAIL")
    st, conv, _c, _f = http_call(localhost_ai("/v1/conversation/health"), headers=ai_headers())
    emit("CONVERSATION_HEALTH_STATUS", st)
    if st != 200:
        raise Halt("CONVERSATION_FAIL")
    row_delta_or_halt(src, before, "CONVERSATION")
    st, _ch, _c, _f = http_call(localhost_ai("/v1/challenge/active"), headers=ai_headers())
    emit("CHALLENGE_STATUS", st)
    if st not in (200, 401, 403):
        raise Halt("CHALLENGE_FAIL")
    row_delta_or_halt(src, before, "CHALLENGE")
    st, _ra, _c, _f = http_call(localhost_ai("/v1/admin/results/status"), headers=ai_headers())
    emit("RA_STATUS", st)
    if st not in (200, 401, 403):
        raise Halt("RA_FAIL")
    row_delta_or_halt(src, before, "RA")
    st, body, _c, _f = http_call(
        localhost_ai("/v1/prediction-runs"),
        method="POST",
        body=b'{"race_id":"20260719_hanshin_11"}',
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    emit("POST_PREDICTION_RUNS_PROBE", "YES")
    emit("POST_PREDICTION_RUNS_STATUS", st)
    code = ""
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        code = str(body["error"].get("code") or "")
    emit("POST_PREDICTION_RUNS_ERROR_CODE", code)
    if st != 503 or code != "PREDICTION_RUNS_DISABLED":
        raise Halt("POST_NOT_DISABLED")
    row_delta_or_halt(src, before, "DISABLED_POST")
    emit("PRED_ROW_DELTA_TOTAL", 0)
    forbidden = [c for c in STATE.http_calls if c[0] == "POST" and "/v1/prediction-runs" not in c[1]]
    if forbidden:
        raise Halt("POST_REFUSED")
    emit("POST_WRITE", "NO")
    emit("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED", "UNCHECKED")
    emit("INTERNAL_REGRESSION_PASS", "YES")


def can_run_public_smoke() -> bool:
    if test_mode():
        return (os.environ.get("OWNER_DEPLOY_TEST_PUBLIC_SMOKE") or "").strip() == "1"
    return True


def run_public_smoke() -> None:
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    if not can_run_public_smoke():
        emit("PUBLIC_SMOKE", "SKIPPED")
        emit("PENDING_PUBLIC_SMOKE", "YES")
        return
    for origin in PUBLIC_ORIGINS:
        for path in PUBLIC_STATIC_PATHS + PUBLIC_API_PATHS:
            url = origin + path
            st, payload, ctype, _f = http_call(url, headers={"Accept": "*/*"})
            if path in PUBLIC_STATIC_PATHS:
                if st != 200 or "html" not in (ctype or "").lower():
                    raise Halt("PUBLIC_SMOKE_FAIL")
                text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else str(payload)
                if not all(token in text for token in SITE_IDENTIFIERS):
                    raise Halt("PUBLIC_STATIC_IDENTITY_FAIL")
            elif path == "/api/health":
                if st != 200 or not isinstance(payload, dict) or payload.get("ok") is not True:
                    raise Halt("PUBLIC_SMOKE_FAIL")
            elif path == "/api/predictions":
                if st not in (200, 503):
                    raise Halt("PUBLIC_SMOKE_FAIL")
    emit("PUBLIC_SMOKE", "PASS")
    emit("PENDING_PUBLIC_SMOKE", "NO")


def verify_ops_unchanged(root: Path) -> None:
    for item in OPS_TARGETS:
        dest = lexical_join(root, item["rel"])
        got = file_sha_nofollow(dest)
        if got != STATE.ops_sha.get(item["rel"]):
            raise Halt("OPS_CHANGED")
    emit("OPS_UNCHANGED", "YES")


def fail_closed(code: str) -> int:
    try:
        if STATE.files_replaced and not STATE.restored:
            restore_code_only()
            maybe_recovery_restart()
    except Halt as inner:
        emit("RESTORE_HALT", inner.code)
    emit("SCHEMA_ROLLBACK", "NO")
    emit("MIGRATE", "NO")
    emit("022_REAPPLY", "NO")
    emit("ENV_CHANGED", "NO")
    emit("SYSTEMD_CHANGED", "NO")
    emit("DEPLOY_EXECUTED", "YES" if STATE.files_replaced and not STATE.restored else "NO")
    emit("FILES_REPLACED", STATE.files_replaced)
    emit("RESTART_EXECUTED", STATE.restart_executed)
    emit("RECOVERY_RESTART_EXECUTED", STATE.recovery_restart_executed)
    emit("CODE_RESTORED", STATE.restored)
    emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
    emit("OWNER_DEPLOY_APPROVED", "NO")
    emit("PRODUCTION_CODE_DEPLOY_ALLOWED", "NO")
    emit("OWNER_DEPLOY_STATUS", "FAIL")
    emit("HALT_REASON", code)
    emit("AUDIT_CLOSED", "YES")
    STATE.audit_closed = True
    return 2


def run() -> int:
    STATE.deadline = Deadline(remote_hard_deadline_s())
    emit("PACK", PACK)
    emit("KIND", "OWNER_STEP1_CODE_DEPLOY_EXECUTION_V3")
    emit("PACK_VERSION", "v3")
    emit("ROOT_CAUSE_ADDRESSED", "POST_RESTART_STARTUP_WAIT_INSUFFICIENT")
    emit("V1_OWNER_DEPLOY_PS1_RERUN_ALLOWED", "NO")
    emit("V2_OWNER_DEPLOY_PS1_RERUN_ALLOWED", "NO")
    emit("HUNK_ONLY_V3_ZIP_SHA256", HUNK_ONLY_V3_ZIP_SHA256)
    emit("MAIN_PY_CANDIDATE_SHA256", MAIN_PY_CANDIDATE_SHA256)
    emit("WHOLESALE_MAIN_PY_REPLACE", "NO")
    emit("MIGRATE", "NO")
    emit("022_REAPPLY", "NO")
    emit("022_SQL_FILE_DEPLOY", "NO")
    emit("POST_WRITE", "NO")
    emit("SCHEMA_ROLLBACK", "NO")
    emit("SUDO_USED", "PAYLOAD_SUDO_N_RESTART_ONLY")
    emit("SCP_USED", "NO")
    emit("ENV_CHANGED", "NO")
    emit("SYSTEMD_CHANGED", "NO")
    emit("LIVE_OPS_DEPLOY", "NO")
    emit("REMOTE_HARD_DEADLINE_S", int(deadline().hard_s) if not test_mode() else deadline().hard_s)
    emit("WRAPPER_TIMEOUT_MS", WRAPPER_TIMEOUT_MS)
    emit("HTTP_MAX_INTERNAL_HEALTH_BYTES", HTTP_MAX_INTERNAL_HEALTH_BYTES)
    emit("HTTP_MAX_INTERNAL_LIST_BYTES", HTTP_MAX_INTERNAL_LIST_BYTES)
    emit("HTTP_MAX_INTERNAL_DETAIL_BYTES", HTTP_MAX_INTERNAL_DETAIL_BYTES)
    emit("HTTP_MAX_PUBLIC_JSON_BYTES", HTTP_MAX_PUBLIC_JSON_BYTES)
    emit("HTTP_MAX_PUBLIC_HTML_BYTES", HTTP_MAX_PUBLIC_HTML_BYTES)
    emit("READINESS_POLL_TIMEOUT_S", READINESS_POLL_TIMEOUT_S)
    emit("READINESS_POLL_INTERVAL_S", READINESS_POLL_INTERVAL_S)
    emit("READINESS_HTTP_TIMEOUT_S", READINESS_HTTP_TIMEOUT_S)
    emit("READINESS_MAX_ATTEMPTS", READINESS_MAX_ATTEMPTS)
    emit("DEPLOY_PHASE", PHASE_NOT_STARTED)
    emit("DEPLOY_EXECUTED", "NO")
    emit("RESTART_EXECUTED", "NO")
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    emit("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED", "UNCHECKED")
    emit("PRODUCTION_CODE_DEPLOY_ALLOWED", "NO")
    emit("OWNER_DEPLOY_APPROVED", "NO")
    emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
    if not wrapper_budget_ok():
        raise Halt("WRAPPER_TIMEOUT_SHORTER_THAN_REMOTE")
    refuse_unapproved()
    STATE.deploy_phase = PHASE_PRECHECKS
    emit("DEPLOY_PHASE", PHASE_PRECHECKS)
    collect_production_env(after=False)
    root = win5_root()
    emit("WIN5_ROOT", str(root))
    src = canonical_source()
    if (not test_mode()) and str(src.resolve()) != CANONICAL_SOURCE:
        raise Halt("REFUSED_NON_CANONICAL_SOURCE")
    if not src.is_file():
        raise Halt("SOURCE_MISSING")
    verify_schema_readonly(src, prefix="PRE_")
    verify_ops_live(root)
    verify_must_absent(root)
    verify_preconditions(root)
    candidates = extract_candidates()
    backup_targets(root)
    stage_replace(root, candidates)
    verify_schema_readonly(src, prefix="POST_REPLACE_")
    verify_ops_unchanged(root)
    collect_production_env(after=True)
    restart_once("DEPLOY")
    if test_fail_mode() == "after_restart":
        raise Halt("INJECTED_AFTER_RESTART")
    wait_until_ready()
    verify_schema_readonly(src, prefix="POST_")
    check_internal_regression(src)
    run_public_smoke()
    collect_production_env(after=True)
    verify_ops_unchanged(root)
    STATE.deploy_phase = PHASE_VERIFIED
    emit("DEPLOY_PHASE", PHASE_VERIFIED)
    emit("DEPLOY_EXECUTED", "YES")
    emit("FILES_REPLACED", "YES")
    emit("RESTART_EXECUTED", "YES")
    emit("DEPLOY_RESTART_COUNT", 1)
    emit("RECOVERY_RESTART_COUNT", 0)
    public_pending = (not can_run_public_smoke()) or (
        test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_PUBLIC_SMOKE") or "").strip() != "1"
    )
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_PUBLIC_SMOKE") or "").strip() != "1":
        emit("POST_DEPLOY_REGRESSION_PASS", "PENDING_PUBLIC_SMOKE")
        emit("OWNER_DEPLOY_STATUS", "PENDING_PUBLIC_SMOKE")
        emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
        emit("AUDIT_CLOSED", "YES")
        STATE.audit_closed = True
        return 0
    emit("POST_DEPLOY_REGRESSION_PASS", "YES")
    emit("OWNER_DEPLOY_STATUS", "SUCCESS")
    emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
    emit("PRODUCTION_CODE_DEPLOY_ALLOWED", "NO")
    emit("OWNER_DEPLOY_APPROVED", "NO")
    emit("AUDIT_CLOSED", "YES")
    STATE.audit_closed = True
    return 0 if not public_pending else 0


def main() -> int:
    try:
        return run()
    except Halt as exc:
        return fail_closed(exc.code)


if __name__ == "__main__":
    raise SystemExit(main())
