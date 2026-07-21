# -----------------------------------------------------------------------------
# Cloudflare Tunnel — Python AI（インターネットにポート公開しない）
# Origin: 127.0.0.1:8000 ← cloudflared のみが到達
# BFF は Access Service Token 付きで hostname へアクセス
# -----------------------------------------------------------------------------

resource "random_id" "tunnel_secret" {
  byte_length = 32
}

resource "cloudflare_tunnel" "ai" {
  account_id = var.account_id
  name       = "${var.ai_tunnel_name}-${var.environment}"
  secret     = random_id.tunnel_secret.b64_std
}

resource "cloudflare_tunnel_config" "ai" {
  account_id = var.account_id
  tunnel_id  = cloudflare_tunnel.ai.id

  config {
    # ワイルドカード catch-all は 404（誤公開防止）
    ingress_rule {
      hostname = var.ai_private_hostname
      service  = var.ai_origin_service
      origin_request {
        no_tls_verify = true
        connect_timeout = "10s"
      }
    }

    ingress_rule {
      service = "http_status:404"
    }
  }
}

# 独自ゾーンへ載せる場合のみ（既定 false）
resource "cloudflare_record" "ai_cname" {
  count   = var.create_dns_for_ai_hostname && var.zone_id != "" ? 1 : 0
  zone_id = var.zone_id
  name    = var.ai_private_hostname
  type    = "CNAME"
  content = "${cloudflare_tunnel.ai.id}.cfargotunnel.com"
  proxied = true
  comment = "Phase9-A AI Tunnel (${var.environment}) — Access 必須"
}

output "tunnel_id" {
  value       = cloudflare_tunnel.ai.id
  description = "cloudflared 用 Tunnel ID"
}

output "tunnel_token" {
  value       = cloudflare_tunnel.ai.tunnel_token
  sensitive   = true
  description = "cloudflared tunnel run 用トークン（ホストにだけ渡す）"
}

output "tunnel_cname_target" {
  value       = "${cloudflare_tunnel.ai.id}.cfargotunnel.com"
  description = "DNS CNAME 先（create_dns_for_ai_hostname=true のとき）"
}
