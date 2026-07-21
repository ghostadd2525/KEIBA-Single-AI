terraform {
  required_version = ">= 1.5.0"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.40"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # バックエンドは管理者が設定（例: Terraform Cloud / S3）
  # backend "s3" {}
}

provider "cloudflare" {
  # CLOUDFLARE_API_TOKEN を環境変数で渡す（アカウント変更権限は管理者のみ）
}
