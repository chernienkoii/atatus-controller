from kubernetes import client, config
from kubernetes.stream import stream
import time, os
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

LICENSED_ANNOTATION = os.getenv('LICENSED_ANNOTATION')
LICENSED_PODS_LIMIT = int(os.getenv('LICENSED_PODS_LIMIT'))
INTERVAL_SECONDS = int(os.getenv('INTERVAL_SECONDS'))
NAMESPACE = os.getenv('NAMESPACE')
NODE_NAME = os.getenv('NODE_NAME')


def list_pods(api_instance):
    pods = api_instance.list_namespaced_pod(NAMESPACE).items
    for pod in pods:
        if (pod.metadata.labels.get("app.kubernetes.io/name") == "app" and
            pod.spec.node_name == NODE_NAME and (pod.metadata.annotations is None or pod.metadata.annotations.get(LICENSED_ANNOTATION) != "true")):
            return pod.metadata.name
    return None

def count_total_pods(api_instance):
    total_pods = 0
    pods = api_instance.list_namespaced_pod(NAMESPACE).items
    for pod in pods:
        if pod.metadata.labels.get("app.kubernetes.io/name") == "app":
            total_pods += 1
    return total_pods


def count_licensed_pods(api_instance):
    licensed_pods = 0
    pods = api_instance.list_namespaced_pod(NAMESPACE).items
    for pod in pods:
        annotations = pod.metadata.annotations
        if (annotations and annotations.get(LICENSED_ANNOTATION) == "true" and
                pod.spec.node_name == NODE_NAME and
                pod.metadata.owner_references):
            licensed_pods += 1
    return licensed_pods


def exec_command(api_instance, pod_name, command):
    exec_command = [
        "/bin/sh",
        "-c",
        command
    ]
    resp = stream(api_instance.connect_get_namespaced_pod_exec, pod_name, NAMESPACE,
                  command=exec_command,
                  container="app",
                  stderr=True, stdin=False,
                  stdout=False, tty=False)
    print("Response: " + resp)

    try:
        pod = api_instance.read_namespaced_pod(name=pod_name, namespace=NAMESPACE)
        if pod.metadata.annotations is None or pod.metadata.annotations.get(LICENSED_ANNOTATION) != "true":
            pod.metadata.annotations = {}
        pod.metadata.annotations[LICENSED_ANNOTATION] = "true"
        api_instance.patch_namespaced_pod(name=pod_name, namespace=NAMESPACE, body=pod)
        print(bcolors.OKGREEN + f"Annotation '{LICENSED_ANNOTATION}' added to pod '{pod_name}' with value 'true'" + bcolors.ENDC)
    except Exception as e:
        print(bcolors.FAIL + f"Failed to add annotation to pod '{pod_name}': {str(e)}" + bcolors.ENDC)


def main():
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    while True:
        pod_name = list_pods(v1)
        total_pods_count = count_total_pods(v1)
        licensed_pods_count = count_licensed_pods(v1)
        print(bcolors.UNDERLINE + f"                   " + bcolors.ENDC)
        print(bcolors.OKBLUE + f"The total number of pods from the deployment: {total_pods_count}" + bcolors.ENDC)
        print(bcolors.OKBLUE + f"Number of licensed pods: {licensed_pods_count} on node {NODE_NAME}" + bcolors.ENDC)
        if licensed_pods_count >= LICENSED_PODS_LIMIT:
            print(bcolors.WARNING + f"The limit licensed pods has been reached ({LICENSED_PODS_LIMIT}). Waiting..." + bcolors.ENDC)
            time.sleep(INTERVAL_SECONDS)
            continue
        if pod_name is None:
            print(bcolors.WARNING + "There are no pods available for licensing. Waiting..." + bcolors.ENDC)
            time.sleep(INTERVAL_SECONDS)
            continue
        elif pod_name is not None:
            print(bcolors.OKCYAN + f"Find pod  {pod_name}" + bcolors.ENDC)
        print(bcolors.UNDERLINE + f"                   " + bcolors.ENDC)

        command = 'wget https://s3.amazonaws.com/atatus-artifacts/atatus-php/downloads/atatus-php-1.15.1-x64-musl.tar.gz && \
        tar -xzvf atatus-php-1.15.1-x64-musl.tar.gz && \
        cd atatus-php-1.15.1-x64-musl && \
        ash install.sh && \
        kill -USR2 1'

        exec_command(v1, pod_name, command)

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
