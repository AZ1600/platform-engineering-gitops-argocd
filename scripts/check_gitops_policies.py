"""Repository-specific safety checks for the NGINX GitOps demo.

These checks run offline and complement schema validation; they are not
Kubernetes admission policies or proof of runtime cluster security.
"""

from pathlib import Path
import re
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/AZ1600/platform-engineering-gitops-argocd.git"
FILES = (
    "manifests/deployment.yaml",
    "manifests/service.yaml",
    "argocd/application.yaml",
    "argocd/project.yaml",
)


def load_documents(root=ROOT):
    """Read the manifests that this repository currently deploys."""
    return {name: yaml.safe_load((Path(root) / name).read_text()) for name in FILES}


def nested(value, *keys):
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        elif isinstance(value, list) and isinstance(key, int) and 0 <= key < len(value):
            value = value[key]
        else:
            return None
    return value


def validate_documents(documents):
    """Report unsafe or widened configuration without contacting a cluster."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    deploy = documents.get("manifests/deployment.yaml")
    service = documents.get("manifests/service.yaml")
    app = documents.get("argocd/application.yaml")
    project = documents.get("argocd/project.yaml")

    pod = nested(deploy, "spec", "template", "spec") or {}
    security = nested(pod, "securityContext") or {}
    containers = nested(pod, "containers") or []

    require(nested(deploy, "kind") == "Deployment", "expected NGINX Deployment")
    require(nested(pod, "automountServiceAccountToken") is False,
            "disable automatic ServiceAccount token mounting")
    require(nested(pod, "hostNetwork") is not True, "host networking must stay disabled")
    require(nested(pod, "hostPID") is not True, "host PID namespace must stay disabled")
    require(nested(security, "runAsNonRoot") is True, "workload must run as non-root")
    uid = nested(security, "runAsUser")
    require(type(uid) is int and uid > 0, "workload must declare a non-root UID")
    require(nested(security, "seccompProfile", "type") == "RuntimeDefault",
            "retain RuntimeDefault seccomp")
    for volume in nested(pod, "volumes") or []:
        require("hostPath" not in volume, "hostPath volumes are not allowed")

    require(isinstance(containers, list) and len(containers) == 1,
            "expected exactly one NGINX container")
    for container in containers if isinstance(containers, list) else []:
        image = container.get("image", "") if isinstance(container, dict) else ""
        require(isinstance(image, str) and re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", image),
                "container image must be pinned to a SHA256 digest")
        sc = container.get("securityContext", {}) if isinstance(container, dict) else {}
        require(sc.get("allowPrivilegeEscalation") is False,
                "container privilege escalation must be disabled")
        require(sc.get("privileged") is not True, "privileged containers are not allowed")
        require(sc.get("readOnlyRootFilesystem") is True,
                "container root filesystem must be read-only")
        require("ALL" in nested(sc, "capabilities", "drop") if isinstance(nested(sc, "capabilities", "drop"), list) else False,
                "container must drop all Linux capabilities")
        require(bool(nested(container, "readinessProbe")), "readiness probe required")
        require(bool(nested(container, "livenessProbe")), "liveness probe required")
        require(bool(nested(container, "resources", "requests")), "resource requests required")
        require(bool(nested(container, "resources", "limits")), "resource limits required")

    labels = nested(deploy, "spec", "template", "metadata", "labels") or {}
    selector = nested(deploy, "spec", "selector", "matchLabels") or {}
    service_selector = nested(service, "spec", "selector") or {}
    require(bool(selector) and all(labels.get(k) == v for k, v in selector.items()),
            "Deployment selector must match pod labels")
    require(bool(service_selector) and all(labels.get(k) == v for k, v in service_selector.items()),
            "Service selector must match pod labels")
    require(nested(service, "spec", "type") == "ClusterIP",
            "NGINX service must remain internal ClusterIP")

    require(nested(app, "spec", "project") == "gitops-demo",
            "Argo CD Application must stay in restricted project")
    require(nested(app, "spec", "source", "repoURL") == REPOSITORY,
            "Argo CD source repository must not change")
    require(nested(app, "spec", "source", "targetRevision") == "main",
            "Argo CD must track reviewed main branch")
    require(nested(app, "spec", "source", "path") == "manifests",
            "Argo CD must deploy only manifests/")
    expected_destination = {"server": "https://kubernetes.default.svc", "namespace": "nginx"}
    require(nested(app, "spec", "destination") == expected_destination,
            "Argo CD Application destination must remain nginx namespace in-cluster")
    require(nested(app, "spec", "syncPolicy", "automated", "allowEmpty") is False,
            "Argo CD must not prune on an empty desired state")

    require(nested(project, "spec", "sourceRepos") == [REPOSITORY],
            "AppProject must allow only the approved repository")
    require(nested(project, "spec", "destinations") == [expected_destination],
            "AppProject must allow only the nginx namespace in-cluster")
    resources = nested(project, "spec", "namespaceResourceWhitelist") or []
    cluster_resources = nested(project, "spec", "clusterResourceWhitelist") or []
    def kinds(rows):
        return {(r.get("group"), r.get("kind")) for r in rows if isinstance(r, dict)}
    require(kinds(resources) == {("apps", "Deployment"), ("", "Service")}
            and len(resources) == 2, "AppProject namespace resource allowlist widened")
    require(kinds(cluster_resources) == {("", "Namespace")}
            and len(cluster_resources) == 1, "AppProject cluster resource allowlist widened")

    return errors


if __name__ == "__main__":
    try:
        violations = validate_documents(load_documents())
    except (OSError, yaml.YAMLError) as exc:
        print(f"FAIL: could not read GitOps manifests: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if violations:
        for violation in violations:
            print(f"FAIL: {violation}", file=sys.stderr)
        raise SystemExit(1)
    print("PASS: GitOps workload and Argo CD policy baseline")
