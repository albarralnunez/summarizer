import pulumi
import os


# Shared Configuration
config = pulumi.Config()
cloudflare_config = pulumi.Config("cloudflare")
digitalocean_config = pulumi.Config("digitalocean")

project_name = os.getenv("REPOSITORY_NAME", "summarizer")
region = config.get("region") or "nyc3"
environment = config.get("environment") or "production"
domain = config.require("domain")

# DigitalOcean
do_token = digitalocean_config.require("token")
do_spaces_access_id = digitalocean_config.require("spacesAccessKeyId")
do_spaces_secret_key = digitalocean_config.require("spacesSecretAccessKey")

# Cloudflare
cloudflare_zone_id = cloudflare_config.require("zoneId")
cloudflare_api_token = cloudflare_config.require("apiToken")

# Frontend
frontend_host = os.getenv("FRONTEND_HOST")
