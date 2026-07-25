# -*- coding: utf-8 -*-
"""
Block Rules — Personal Chat Security Guard。

内部情報・秘密・インフラ・Prompt 漏洩要求を検知する。
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class BlockRule:
    rule_id: str
    category: str
    pattern: re.Pattern[str]
    description: str


def _c(*parts: str) -> re.Pattern[str]:
    return re.compile("|".join(parts), re.IGNORECASE)


# カテゴリ別ブロック規則
BLOCK_RULES: tuple[BlockRule, ...] = (
    BlockRule(
        "sys_prompt",
        "System Prompt",
        _c(
            r"system\s*prompt",
            r"システム[・\s]?プロンプト",
            r"hidden\s*prompt",
            r"隠しプロンプト",
            r"プロンプトを(見せ|教え|出せ|表示)",
            r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
            r"前の指示を無視",
            r"指示を無視して",
        ),
        "System / Hidden Prompt の開示・迂回",
    ),
    BlockRule(
        "internal_api",
        "内部 API",
        _c(
            r"内部\s*api",
            r"internal\s*api",
            r"非公開\s*api",
            r"隠(し|れた)\s*api",
            r"api\s*(キー|仕様|一覧|を教え|を見せ)",
            r"エンドポイント(を|の|は)?(教え|見せ|出せ|一覧)",
        ),
        "内部 API / エンドポイント照会",
    ),
    BlockRule(
        "feature_flag",
        "Feature Flag",
        _c(
            r"feature\s*flag",
            r"フィーチャー\s*フラグ",
            r"F_V4_",
            r"フラグの(値|状態|設定)",
            r"flag\s*(on|off|enabled)",
        ),
        "Feature Flag 情報",
    ),
    BlockRule(
        "prediction_internal",
        "Prediction AI 内部ロジック",
        _c(
            r"prediction\s*(ai|内部|ロジック|アルゴリズム)",
            r"予測(モデル|アルゴリズム|内部|ロジック|重み)",
            r"モデルの(重み|パラメータ|学習データ)",
            r"ranking\s*logic",
            r"confidence\s*(計算|ロジック|内部)",
        ),
        "Prediction AI 内部ロジック",
    ),
    BlockRule(
        "configuration",
        "Configuration",
        _c(
            r"configuration",
            r"設定ファイル",
            r"config\.(ya?ml|json|toml)",
            r"conversation\.ya?ml",
        ),
        "Configuration 開示",
    ),
    BlockRule(
        "env_secret",
        "環境変数 / Secret / Token / Password",
        _c(
            r"環境変数",
            r"\.env\b",
            r"secret",
            r"シークレット",
            r"api[_\s-]?key",
            r"access[_\s-]?token",
            r"bearer\s+token",
            r"password",
            r"パスワード(を|は|教えて|見せ)",
            r"認証トークン",
        ),
        "Secret / Token / Password / Env",
    ),
    BlockRule(
        "infra",
        "Server / Database",
        _c(
            r"サーバー(構成|設定|IP|アドレス|内部)",
            r"\bdatabase\b",
            r"データベース(構成|接続|中身|スキーマ)",
            r"\bsqlite\b",
            r"\bpostgres",
            r"接続文字列",
            r"connection\s*string",
        ),
        "Server / Database",
    ),
    BlockRule(
        "admin_debug",
        "管理情報 / デバッグ",
        _c(
            r"管理(者|画面|情報|API)",
            r"\badmin\b",
            r"デバッグ情報",
            r"\bdebug\b",
            r"stack\s*trace",
            r"スタックトレース",
            r"ログを(全部|見せ|出せ)",
        ),
        "管理・デバッグ情報",
    ),
    BlockRule(
        "internal_path",
        "内部パス",
        _c(
            r"内部パス",
            r"ソースコード(を|の|は)?(見せ|教え|出せ|表示|読め)",
            r"app[/\\]conversation",
            r"services[/\\]win5-ai",
            r"[A-Za-z]:\\Users\\",
            r"/etc/passwd",
            r"\bfilepath\b",
        ),
        "内部パス / ソース開示",
    ),
)


def match_block_rules(text: str) -> BlockRule | None:
    raw = str(text or "")
    if not raw.strip():
        return None
    for rule in BLOCK_RULES:
        if rule.pattern.search(raw):
            return rule
    return None
