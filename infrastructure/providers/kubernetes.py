from pulumi_kubernetes import Provider as K8sProvider


def create_k8s_provider(cluster):
    return K8sProvider("k8s-provider", kubeconfig=cluster.kube_configs[0].raw_config)
