import os
import pulumi
from pulumi_digitalocean import Provider
from config import do_token, do_spaces_access_id, do_spaces_secret_key

do_provider = Provider(
    "do-provider",
    token=do_token,
    spaces_access_id=do_spaces_access_id,
    spaces_secret_key=do_spaces_secret_key,
)
