import pulumi
from pulumi_kubernetes import core
from pulumi_kubernetes.networking.v1 import Ingress
from pulumi_kubernetes.helm.v4 import Chart, RepositoryOptsArgs
import pulumi_cloudflare as cloudflare
from config import environment, frontend_host, cloudflare_zone_id, domain


def setup_nginx_ingress(k8s_provider, cluster):
    nginx_namespace = "ingress-nginx"

    ingress_nginx_namespace = core.v1.Namespace(
        "ingress-nginx-namespace",
        metadata={
            "name": nginx_namespace,
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    nginx_chart = Chart(
        "summarizer-app-ingress",
        chart="ingress-nginx",
        namespace=nginx_namespace,
        version="4.12.0-beta.0",
        repository_opts=RepositoryOptsArgs(
            repo="https://kubernetes.github.io/ingress-nginx"
        ),
        values={
            "controller": {
                "admissionWebhooks": {
                    "enabled": False,
                    "patch": {
                        "enabled": False,
                    },
                }
            }
        },
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=[ingress_nginx_namespace, cluster]
        ),
    )

    return nginx_chart, nginx_namespace


def create_dns_record(nginx_external_ip, cloudflare_provider, nginx_chart):
    return cloudflare.Record(
        "summarizer-dns-record",
        zone_id=cloudflare_zone_id,
        name=domain,
        type="A",
        content=nginx_external_ip,
        ttl=1,
        proxied=True,
        opts=pulumi.ResourceOptions(
            provider=cloudflare_provider, depends_on=[nginx_chart]
        ),
    )


def create_ingresses(
    namespace, app_service, frontend_service, nginx_chart, dns_record, k8s_provider
):
    api_ingress = Ingress(
        "api-ingress",
        metadata={
            "name": "api-ingress",
            "namespace": namespace.metadata["name"],
            "annotations": {
                "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
                "nginx.ingress.kubernetes.io/ssl-redirect": "true",
            },
        },
        spec={
            "ingressClassName": "nginx",
            "rules": [
                {
                    "host": domain,
                    "http": {
                        "paths": [
                            {
                                "path": "/api(/|$)(.*)",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": app_service.metadata["name"],
                                        "port": {
                                            "number": 8888,
                                        },
                                    },
                                },
                            }
                        ],
                    },
                }
            ],
        },
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=[nginx_chart, dns_record]
        ),
    )

    frontend_ingress = Ingress(
        "frontend-ingress",
        metadata={
            "name": "frontend-ingress",
            "namespace": namespace.metadata["name"],
            "annotations": {
                "nginx.ingress.kubernetes.io/rewrite-target": "/$1",
                "nginx.ingress.kubernetes.io/ssl-redirect": "true",
            },
        },
        spec={
            "ingressClassName": "nginx",
            "rules": [
                {
                    "host": domain,
                    "http": {
                        "paths": [
                            {
                                "path": "/(.*)",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": frontend_service.metadata["name"],
                                        "port": {
                                            "number": 80,
                                        },
                                    },
                                },
                            }
                        ],
                    },
                }
            ],
        },
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=[nginx_chart, dns_record, api_ingress]
        ),
    )

    return api_ingress, frontend_ingress


def get_nginx_external_ip(nginx_chart, k8s_provider):
    """
    Get the external IP of the Nginx ingress controller.

    Args:
        nginx_chart: The deployed Nginx ingress controller Helm chart
        k8s_provider: The Kubernetes provider instance

    Returns:
        The external IP address of the Nginx ingress controller
    """
    nginx_controller_service = core.v1.Service.get(
        "nginx-controller-service",
        f"ingress-nginx/summarizer-app-ingress-ingress-nginx-controller",
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_chart]),
    )

    return nginx_controller_service.status.apply(
        lambda status: (
            status.load_balancer.ingress[0].ip if status.load_balancer.ingress else None
        )
    )
