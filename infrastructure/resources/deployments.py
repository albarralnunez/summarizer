import pulumi
from pulumi_kubernetes import core, apps
from pulumi_docker_build import Image
from config import environment, project_name
import os


def create_app_image(registry_info, registry, registry_credentials, nginx_chart):
    return Image(
        f"{project_name}-app-image",
        tags=[
            pulumi.Output.concat(
                registry.endpoint,
                f"/{project_name}-app:",
                "prod" if environment == "production" else "dev",
            )
        ],
        dockerfile={
            "location": "../server/python.Dockerfile",
        },
        context={
            "location": "../server",
        },
        platforms=["linux/amd64"],
        push=True,
        registries=[
            {
                "address": registry_info["server"],
                "password": registry_info["password"],
                "username": registry_info["username"],
            }
        ],
        build_on_preview=False,
        opts=pulumi.ResourceOptions(
            depends_on=[registry, registry_credentials, nginx_chart]
        ),
    )


def create_scheduler_deployment(
    namespace, app_image, config_map, registry_secret, nginx_chart, k8s_provider
):
    scheduler_deployment = apps.v1.Deployment(
        "scheduler-deployment",
        metadata={
            "name": f"{project_name}-scheduler",
            "namespace": namespace.metadata["name"],
        },
        spec={
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": f"{project_name}-scheduler",
                },
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": f"{project_name}-scheduler",
                    },
                },
                "spec": {
                    "containers": [
                        {
                            "name": "scheduler",
                            "image": app_image.ref,
                            "args": [
                                "dask",
                                "scheduler",
                                "--host",
                                "0.0.0.0",
                                "--port",
                                "8786",
                                "--dashboard-address",
                                "0.0.0.0:8787",
                                "--protocol",
                                "tcp://",
                                "--no-show",
                            ],
                            "ports": [
                                {"containerPort": 8786},
                                {"containerPort": 8787},
                            ],
                            "envFrom": [
                                {
                                    "configMapRef": {
                                        "name": config_map.metadata["name"],
                                    },
                                }
                            ],
                            "lifecycle": {
                                "preStop": {
                                    "exec": {"command": ["/bin/sh", "-c", "sleep 30"]}
                                }
                            },
                        }
                    ],
                    "imagePullSecrets": [
                        {
                            "name": registry_secret.metadata["name"],
                        }
                    ],
                },
            },
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_chart]),
    )

    scheduler_service = core.v1.Service(
        "scheduler-service",
        metadata={
            "name": f"{project_name}-scheduler",
            "namespace": namespace.metadata["name"],
        },
        spec={
            "type": "ClusterIP",
            "ports": [
                {
                    "name": "dask-scheduler",
                    "port": 8786,
                    "targetPort": 8786,
                },
                {
                    "name": "dask-dashboard",
                    "port": 8787,
                    "targetPort": 8787,
                },
            ],
            "selector": {
                "app": f"{project_name}-scheduler",
            },
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_chart]),
    )

    return scheduler_deployment, scheduler_service


def create_worker_deployment(
    namespace, app_image, config_map, registry_secret, nginx_chart, k8s_provider
):
    return apps.v1.Deployment(
        "worker-deployment",
        metadata={
            "name": f"{project_name}-worker",
            "namespace": namespace.metadata["name"],
        },
        spec={
            "replicas": 4 if environment == "production" else 2,
            "selector": {
                "matchLabels": {
                    "app": f"{project_name}-worker",
                },
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": f"{project_name}-worker",
                    },
                },
                "spec": {
                    "containers": [
                        {
                            "name": "worker",
                            "image": app_image.ref,
                            "args": [
                                "dask",
                                "worker",
                                "tcp://summarizer-scheduler:8786",
                                "--nthreads",
                                "2",
                                "--memory-limit",
                                "4GB",
                                "--no-dashboard",
                            ],
                            "envFrom": [
                                {
                                    "configMapRef": {
                                        "name": config_map.metadata["name"],
                                    },
                                }
                            ],
                            "lifecycle": {
                                "preStop": {
                                    "exec": {"command": ["/bin/sh", "-c", "sleep 30"]}
                                }
                            },
                        }
                    ],
                    "imagePullSecrets": [
                        {
                            "name": registry_secret.metadata["name"],
                        }
                    ],
                },
            },
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_chart]),
    )


def create_app_deployment(
    namespace, app_image, config_map, registry_secret, nginx_chart, k8s_provider
):
    app_deployment = apps.v1.Deployment(
        "app-deployment",
        metadata={
            "name": f"{project_name}-app",
            "namespace": namespace.metadata["name"],
        },
        spec={
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": f"{project_name}-app",
                    "environment": environment,
                },
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": f"{project_name}-app",
                        "environment": environment,
                    },
                },
                "spec": {
                    "containers": [
                        {
                            "name": "summarizer-app",
                            "image": app_image.ref,
                            "ports": [
                                {
                                    "containerPort": 8888,
                                }
                            ],
                            "envFrom": [
                                {
                                    "configMapRef": {
                                        "name": config_map.metadata["name"],
                                    },
                                }
                            ],
                        }
                    ],
                    "imagePullSecrets": [
                        {
                            "name": registry_secret.metadata["name"],
                        }
                    ],
                },
            },
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_chart]),
    )

    # Create a service for the app
    app_service = core.v1.Service(
        "app-service",
        metadata={
            "name": f"{project_name}-app",
            "namespace": namespace.metadata["name"],
        },
        spec={
            "type": "ClusterIP",
            "ports": [
                {
                    "port": 8888,
                    "targetPort": 8888,
                    "protocol": "TCP",
                }
            ],
            "selector": {
                "app": f"{project_name}-app",
            },
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_chart]),
    )

    return app_deployment, app_service


def create_frontend_deployment(namespace, k8s_provider):
    # Create Nginx ConfigMap first
    nginx_config_map = core.v1.ConfigMap(
        "nginx-config-frontend",
        metadata={
            "name": "nginx-config-frontend",
            "namespace": namespace.metadata["name"],
        },
        data={
            "default.conf": pulumi.Output.concat(
                "server {\n",
                "    listen 80;\n",
                "    location / {\n",
                "        return 301 /",
                project_name,
                "/;\n",
                "    }\n",
                "    location /",
                project_name,
                " {\n",
                "        proxy_pass https://",
                os.getenv("FRONTEND_HOST"),
                "/",
                project_name,
                "/;\n",
                "        proxy_set_header Host ",
                os.getenv("FRONTEND_HOST"),
                ";\n",
                "        proxy_set_header X-Forwarded-Proto https;\n",
                "        proxy_set_header Origin ",
                os.getenv("FRONTEND_HOST"),
                ";\n",
                "        proxy_set_header X-Real-IP $remote_addr;\n",
                "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n",
                "    }\n",
                "}\n",
            )
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    frontend_deployment = apps.v1.Deployment(
        "frontend-deployment",
        metadata={
            "name": "nginx-frontend",
            "namespace": namespace.metadata["name"],
        },
        spec={
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": "nginx-frontend",
                },
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "nginx-frontend",
                    },
                },
                "spec": {
                    "containers": [
                        {
                            "name": "nginx",
                            "image": "nginx:latest",
                            "ports": [
                                {
                                    "containerPort": 80,
                                }
                            ],
                            "volumeMounts": [
                                {
                                    "name": "nginx-config-frontend",
                                    "mountPath": "/etc/nginx/conf.d",
                                }
                            ],
                        }
                    ],
                    "volumes": [
                        {
                            "name": "nginx-config-frontend",
                            "configMap": {
                                "name": "nginx-config-frontend",
                            },
                        }
                    ],
                },
            },
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    # Create a service for the frontend
    frontend_service = core.v1.Service(
        "frontend-service",
        metadata={
            "name": "nginx-frontend",
            "namespace": namespace.metadata["name"],
        },
        spec={
            "type": "ClusterIP",
            "ports": [
                {
                    "port": 80,
                    "targetPort": 80,
                    "protocol": "TCP",
                }
            ],
            "selector": {
                "app": "nginx-frontend",
            },
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    return frontend_deployment, frontend_service, nginx_config_map
