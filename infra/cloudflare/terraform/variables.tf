variable "account_id" {
  type        = string
  description = "Cloudflare Account ID"
}

variable "zone_id" {
  type        = string
  description = "Zone ID（独自ドメイン利用時）。pages.dev のみの場合は空文字可"
  default     = ""
}

variable "environment" {
  type        = string
  description = "development | staging | production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "environment must be development, staging, or production."
  }
}

variable "pages_hostnames" {
  type        = list(string)
  description = "Access で保護するホスト（例: keiba-single-ai.pages.dev, expect.example.com）"
}

variable "allowed_emails" {
  type        = list(string)
  description = "β許可メール（email ポリシー）。空なら email 条件は作らない"
  default     = []
}

variable "allowed_email_domains" {
  type        = list(string)
  description = "許可メールドメイン（例: example.com）。空可"
  default     = []
}

variable "require_warp" {
  type        = bool
  description = "true のとき WARP 接続を Access ポリシーに含める"
  default     = true
}

variable "ai_tunnel_name" {
  type        = string
  description = "Python AI 用 Tunnel 名"
  default     = "expect-win5-ai"
}

variable "ai_private_hostname" {
  type        = string
  description = "BFF が使う AI ホスト名（Access Service Auth 付き）。公開 DNS には載せない運用を推奨"
  default     = "ai-internal.expect-beta.local"
}

variable "ai_origin_service" {
  type        = string
  description = "cloudflared が転送するローカル Origin（Python）"
  default     = "http://127.0.0.1:8000"
}

variable "session_duration" {
  type        = string
  description = "Access セッション長"
  default     = "24h"
}

variable "create_dns_for_ai_hostname" {
  type        = bool
  description = "true かつ zone_id があるときだけ AI ホスト用 CNAME を作成（通常は false＝非公開運用）"
  default     = false
}
