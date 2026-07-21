# -----------------------------------------------------------------------------
# Cloudflare Access
# 1) Pages/BFF — エンドユーザー（WARP / メール）のみ到達
# 2) AI hostname — Service Token のみ（BFF 用）。一般ユーザーは不可
# -----------------------------------------------------------------------------

locals {
  app_name_pages = "expect-pages-${var.environment}"
  app_name_ai    = "expect-ai-${var.environment}"
}

# --- Pages / BFF（人間向け） ---
resource "cloudflare_access_application" "pages" {
  account_id                = var.account_id
  name                      = local.app_name_pages
  domain                    = var.pages_hostnames[0]
  type                      = "self_hosted"
  session_duration          = var.session_duration
  auto_redirect_to_identity = false
  # 追加ホストは self_hosted_domains で拡張（provider バージョンによりフィールド名が異なる場合あり）
}

resource "cloudflare_access_policy" "pages_allow" {
  application_id = cloudflare_access_application.pages.id
  account_id     = var.account_id
  name           = "beta-allow-${var.environment}"
  precedence     = 1
  decision       = "allow"

  dynamic "include" {
    for_each = length(var.allowed_emails) > 0 ? [1] : []
    content {
      email = var.allowed_emails
    }
  }

  dynamic "include" {
    for_each = length(var.allowed_email_domains) > 0 ? [1] : []
    content {
      email_domain = var.allowed_email_domains
    }
  }

  # メール条件が無い場合のフォールバック（管理者が後から締める前提）
  dynamic "include" {
    for_each = length(var.allowed_emails) == 0 && length(var.allowed_email_domains) == 0 ? [1] : []
    content {
      everyone = true
    }
  }

  # WARP 必須は Device Posture ルール ID がチーム依存のため Terraform では付けない。
  # require_warp=true のときは apply 後、ダッシュボードで本ポリシーに
  # 「Require → WARP」を追加すること（docs/phase9-a-access-infrastructure.md §3）。
}

resource "cloudflare_access_policy" "pages_deny" {
  application_id = cloudflare_access_application.pages.id
  account_id     = var.account_id
  name           = "deny-all-${var.environment}"
  precedence     = 1000
  decision       = "deny"

  include {
    everyone = true
  }
}

# --- AI Tunnel hostname（Service Token のみ） ---
resource "cloudflare_access_application" "ai" {
  account_id       = var.account_id
  name             = local.app_name_ai
  domain           = var.ai_private_hostname
  type             = "self_hosted"
  session_duration = "24h"
}

resource "cloudflare_access_service_token" "bff_to_ai" {
  account_id = var.account_id
  name       = "expect-bff-ai-${var.environment}"
}

resource "cloudflare_access_policy" "ai_service_token" {
  application_id = cloudflare_access_application.ai.id
  account_id     = var.account_id
  name           = "bff-service-token-${var.environment}"
  precedence     = 1
  decision       = "non_identity"

  include {
    service_token = [cloudflare_access_service_token.bff_to_ai.id]
  }
}

resource "cloudflare_access_policy" "ai_deny" {
  application_id = cloudflare_access_application.ai.id
  account_id     = var.account_id
  name           = "ai-deny-all-${var.environment}"
  precedence     = 1000
  decision       = "deny"

  include {
    everyone = true
  }
}

output "pages_access_app_id" {
  value = cloudflare_access_application.pages.id
}

output "ai_access_app_id" {
  value = cloudflare_access_application.ai.id
}

output "bff_access_client_id" {
  value       = cloudflare_access_service_token.bff_to_ai.client_id
  sensitive   = true
  description = "Pages Secret: CF_ACCESS_CLIENT_ID"
}

output "bff_access_client_secret" {
  value       = cloudflare_access_service_token.bff_to_ai.client_secret
  sensitive   = true
  description = "Pages Secret: CF_ACCESS_CLIENT_SECRET"
}

output "ai_base_url_suggested" {
  value       = "https://${var.ai_private_hostname}"
  description = "Pages Secret: AI_BASE_URL（末尾スラッシュなし）"
}
