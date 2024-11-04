import pulumi
from pulumi_digitalocean import KubernetesCluster
from config import project_name, region


def create_cluster(provider):
    return KubernetesCluster(
        project_name,
        name=project_name,
        region=region,
        version="1.31.1-do.3",
        auto_upgrade=True,
        ha=False,
        node_pool={
            "name": "worker-pool",
            "size": "s-2vcpu-4gb",
            "auto_scale": False,
            "node_count": 1,
            "labels": {
                "service": "summarizer-app",
            },
        },
        maintenance_policy={
            "day": "sunday",
            "start_time": "04:00",
        },
        opts=pulumi.ResourceOptions(provider=provider),
    )
