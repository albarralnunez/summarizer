import pulumi_cloudflare as cloudflare
from config import cloudflare_api_token

cloudflare_provider = cloudflare.Provider(
    "cloudflare-provider", api_token=cloudflare_api_token
)
