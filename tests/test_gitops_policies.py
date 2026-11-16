"""Regression tests proving the GitOps baseline detects unsafe changes."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_gitops_policies import load_documents, validate_documents


class GitOpsPolicyTests(unittest.TestCase):
    def setUp(self):
        self.docs = copy.deepcopy(load_documents())

    def expect_rejected(self, part):
        violations = validate_documents(self.docs)
        self.assertTrue(any(part in x for x in violations), violations)

    def test_current_manifests_pass(self):
        self.assertEqual(validate_documents(self.docs), [])

    def test_rejects_mutable_image_tag(self):
        self.docs["manifests/deployment.yaml"]["spec"]["template"]["spec"]["containers"][0]["image"] = "nginx:latest"
        self.expect_rejected("SHA256 digest")

    def test_rejects_service_account_token_mounting(self):
        self.docs["manifests/deployment.yaml"]["spec"]["template"]["spec"]["automountServiceAccountToken"] = True
        self.expect_rejected("ServiceAccount token")

    def test_rejects_root_execution(self):
        self.docs["manifests/deployment.yaml"]["spec"]["template"]["spec"]["securityContext"]["runAsUser"] = 0
        self.expect_rejected("non-root UID")

    def test_rejects_privilege_escalation(self):
        self.docs["manifests/deployment.yaml"]["spec"]["template"]["spec"]["containers"][0]["securityContext"]["allowPrivilegeEscalation"] = True
        self.expect_rejected("privilege escalation")

    def test_rejects_writable_root_filesystem(self):
        self.docs["manifests/deployment.yaml"]["spec"]["template"]["spec"]["containers"][0]["securityContext"]["readOnlyRootFilesystem"] = False
        self.expect_rejected("read-only")

    def test_rejects_pod_host_network(self):
        self.docs["manifests/deployment.yaml"]["spec"]["template"]["spec"]["hostNetwork"] = True
        self.expect_rejected("host networking")

    def test_rejects_public_service(self):
        self.docs["manifests/service.yaml"]["spec"]["type"] = "LoadBalancer"
        self.expect_rejected("ClusterIP")

    def test_rejects_tracking_unreviewed_branch(self):
        self.docs["argocd/application.yaml"]["spec"]["source"]["targetRevision"] = "development"
        self.expect_rejected("reviewed main")

    def test_rejects_project_wildcard_repo(self):
        self.docs["argocd/project.yaml"]["spec"]["sourceRepos"] = ["*"]
        self.expect_rejected("approved repository")

    def test_rejects_project_wildcard_namespace(self):
        self.docs["argocd/project.yaml"]["spec"]["destinations"][0]["namespace"] = "*"
        self.expect_rejected("nginx namespace")

    def test_rejects_extra_cluster_resource(self):
        self.docs["argocd/project.yaml"]["spec"]["clusterResourceWhitelist"].append({"group": "*", "kind": "*"})
        self.expect_rejected("cluster resource allowlist")


if __name__ == "__main__":
    unittest.main()
