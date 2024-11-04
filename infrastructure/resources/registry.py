import pulumi
from pulumi_digitalocean import ContainerRegistry, ContainerRegistryDockerCredentials
import base64
import json
from config import project_name


def setup_registry(provider):
    registry = ContainerRegistry(
        "registry",
        name=f"{project_name}-registry-{pulumi.get_stack()}",
        subscription_tier_slug="basic",
        opts=pulumi.ResourceOptions(provider=provider),
    )

    registry_credentials = ContainerRegistryDockerCredentials(
        "registry-credentials",
        registry_name=registry.name,
        write=True,
        opts=pulumi.ResourceOptions(provider=provider),
    )

    registry_info = pulumi.Output.all(
        registry_credentials.docker_credentials, registry.server_url
    ).apply(
        lambda args: {
            "server": args[1],
            "username": (
                lambda auth: (decoded := base64.b64decode(auth).decode()).split(":")[0]
            )(json.loads(args[0])["auths"][args[1]]["auth"]),
            "password": (
                lambda auth: (decoded := base64.b64decode(auth).decode()).split(":")[1]
            )(json.loads(args[0])["auths"][args[1]]["auth"]),
        }
    )

    return registry, registry_credentials, registry_info
