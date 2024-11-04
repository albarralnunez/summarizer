import pulumi
from pulumi_kubernetes import core
from providers.digitalocean import do_provider
from providers.kubernetes import create_k8s_provider
from providers.cloudflare import cloudflare_provider
from resources.registry import setup_registry
from resources.cluster import create_cluster
from resources.deployments import (
    create_app_image,
    create_scheduler_deployment,
    create_worker_deployment,
    create_app_deployment,
    create_frontend_deployment,
)
from resources.networking import (
    setup_nginx_ingress,
    create_dns_record,
    create_ingresses,
    get_nginx_external_ip,
)
from config import project_name, environment, region

# Setup core infrastructure
registry, registry_credentials, registry_info = setup_registry(do_provider)
cluster = create_cluster(do_provider)
k8s_provider = create_k8s_provider(cluster)

# Setup Nginx Ingress
nginx_chart, nginx_namespace = setup_nginx_ingress(k8s_provider, cluster)

# Create namespace and config
namespace = core.v1.Namespace(
    f"{environment}-namespace",
    metadata={
        "name": f"summarizer-app-{environment}",
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_chart]),
)

# Create registry secret and config map
registry_secret = core.v1.Secret(
    "registry-secret",
    metadata={
        "name": "registry-secret",
        "namespace": namespace.metadata["name"],
    },
    type="kubernetes.io/dockerconfigjson",
    string_data={
        ".dockerconfigjson": registry_credentials.docker_credentials,
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider),
)

config_map = core.v1.ConfigMap(
    "app-config",
    metadata={
        "name": "summarizer-config",
        "namespace": namespace.metadata["name"],
    },
    data={
        "ENVIRONMENT": environment,
        "REGION": region,
        "LOG_LEVEL": "INFO" if environment == "production" else "DEBUG",
        "PYTHONUNBUFFERED": "1",
        "DASK_SCHEDULER_HOST": "summarizer-scheduler",
        "DASK_SCHEDULER_PORT": "8786",
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider),
)

# Create deployments and services
app_image = create_app_image(registry_info, registry, registry_credentials, nginx_chart)
scheduler_deployment, _ = create_scheduler_deployment(
    namespace, app_image, config_map, registry_secret, nginx_chart, k8s_provider
)

# Create app deployment and service
app_deployment, app_service = create_app_deployment(
    namespace, app_image, config_map, registry_secret, nginx_chart, k8s_provider
)

# Create worker deployment
worker_deployment = create_worker_deployment(
    namespace, app_image, config_map, registry_secret, nginx_chart, k8s_provider
)

# Create frontend deployment and service
frontend_deployment, frontend_service, nginx_config_map = create_frontend_deployment(
    namespace, k8s_provider
)

# Create services and networking
nginx_external_ip = get_nginx_external_ip(nginx_chart, k8s_provider)
dns_record = create_dns_record(nginx_external_ip, cloudflare_provider, nginx_chart)
api_ingress, frontend_ingress = create_ingresses(
    namespace, app_service, frontend_service, nginx_chart, dns_record, k8s_provider
)

# Exports
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("registry_endpoint", registry.server_url)
pulumi.export("kubeconfig", cluster.kube_configs)
pulumi.export("nginx_external_ip", nginx_external_ip)
pulumi.export("dns_record_name", dns_record.name)
pulumi.export("frontend_service_endpoint", frontend_service.spec.cluster_ip)
