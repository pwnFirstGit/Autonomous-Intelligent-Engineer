import unittest
from unittest.mock import patch
import hashlib
import hmac
import os
import sys
import types

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import api.main as main
from backend.rag.retriever import CodeRetriever
import backend.services.repo_service as repo_service


class AutonomousFlowTests(unittest.TestCase):
    def test_retriever_prioritizes_explicit_file_mentions(self):
        class FakeVectorStore:
            metadata = [
                {"file": "app.py", "start_line": 0, "end_line": 10, "code": "app"},
                {"file": "preprocessor.py", "start_line": 0, "end_line": 10, "code": "broken"},
            ]

            def search(self, query, top_k):
                return [{"file": "app.py", "start_line": 0, "end_line": 10, "code": "app"}]

        retriever = CodeRetriever(FakeVectorStore())
        results = retriever.retrieve("Fix syntax error in preprocessor.py", top_k=2)

        self.assertEqual(results[0]["file"], "preprocessor.py")

    def test_full_pr_workflow_creates_draft_pr(self):
        captured = {}

        def fake_create_branch(repo_path, base_branch, branch_name, issue_number):
            captured["create_branch"] = {
                "repo_path": repo_path,
                "base_branch": base_branch,
                "branch_name": branch_name,
                "issue_number": issue_number,
            }
            return branch_name

        def fake_commit_and_push(repo_path, branch_name, message, changed_files=None):
            captured["commit"] = {
                "repo_path": repo_path,
                "branch_name": branch_name,
                "message": message,
                "changed_files": changed_files,
            }
            return {"success": True}

        def fake_create_pull_request(repo_owner, repo_name, branch_name, title, body, base_branch, draft):
            captured["pr"] = {
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "branch_name": branch_name,
                "title": title,
                "body": body,
                "base_branch": base_branch,
                "draft": draft,
            }
            return {"html_url": "https://github.com/acme/demo/pull/1"}

        with patch.object(repo_service, "create_branch", side_effect=fake_create_branch), \
             patch.object(repo_service, "commit_and_push", side_effect=fake_commit_and_push), \
             patch.object(repo_service, "create_pull_request", side_effect=fake_create_pull_request):
            result = repo_service.full_pr_workflow(
                repo_path="repos/jobs/job-1/demo",
                repo_owner="acme",
                repo_name="demo",
                fix_description="Fix failing parser edge case",
                changed_files=["parser.py"],
                base_branch="develop",
                issue_number=42,
                branch_name="aide/issue-42",
                draft=True,
            )

        self.assertTrue(result["html_url"].endswith("/pull/1"))
        self.assertEqual(result["branch_name"], "aide/issue-42")
        self.assertEqual(captured["create_branch"]["base_branch"], "develop")
        self.assertEqual(captured["create_branch"]["issue_number"], 42)
        self.assertEqual(captured["commit"]["changed_files"], ["parser.py"])
        self.assertTrue(captured["pr"]["draft"])
        self.assertIn("Closes #42", captured["pr"]["body"])

    def test_commit_and_push_configures_git_identity(self):
        calls = []

        class FakeCompletedProcess:
            def __init__(self, stdout=""):
                self.stdout = stdout

        def fake_run_git(args, repo_path=None):
            calls.append(args)
            if args == ["status", "--porcelain"]:
                return FakeCompletedProcess(stdout=" M preprocessor.py\n")
            if args == ["diff", "--cached", "--name-only"]:
                return FakeCompletedProcess(stdout="preprocessor.py\n")
            return FakeCompletedProcess()

        with patch.object(repo_service, "_run_git", side_effect=fake_run_git):
            result = repo_service.commit_and_push(
                "repo",
                "aide/issue-1",
                "fix: syntax",
                changed_files=["preprocessor.py"],
            )

        self.assertTrue(result["success"])
        self.assertIn(["config", "user.name", "AIDE Bot"], calls)
        self.assertIn(["config", "user.email", "aide-bot@users.noreply.github.com"], calls)
        self.assertIn(["commit", "-m", "fix: syntax"], calls)

    def test_run_aide_job_posts_completion_comment(self):
        fake_parser_module = types.ModuleType("backend.rag.parser")
        fake_vector_store_module = types.ModuleType("backend.rag.vector_store")
        fake_graph_module = types.ModuleType("backend.agents.graph")

        class FakeParser:
            def __init__(self, language):
                self.language = language

            def parse_repository(self, repo_path):
                return [{"file": "bug.py", "code": "print('x')"}]

        class FakeVectorStore:
            def load(self, index_path):
                self.index_path = index_path

            def build_index(self, parsed):
                self.parsed = parsed

            def save(self, index_path):
                self.saved_index_path = index_path

        class FakeAgent:
            def __init__(self, store, repo_path):
                self.repo_path = repo_path

            def run(self, issue, create_pr, pr_config):
                self.issue = issue
                self.create_pr = create_pr
                self.pr_config = pr_config
                return {
                    "plan": {"problem": issue, "files_likely": ["bug.py"]},
                    "results": [{"file": "bug.py", "result": {"status": "success", "diff": "patch"}}],
                    "pr": {"html_url": "https://github.com/acme/demo/pull/2"},
                }

        fake_parser_module.CodeParser = FakeParser
        fake_vector_store_module.VectorStore = FakeVectorStore
        fake_graph_module.AIAgentSystem = FakeAgent

        comments = []
        job_id = "job-2"
        main.jobs[job_id] = {"status": "pending", "result": None, "error": None}
        request = main.AnalyzeRequest(
            repo_url="https://github.com/acme/demo.git",
            issue="Fix parser failure",
            repo_owner="acme",
            repo_name="demo",
            issue_number=7,
            branch_name="aide/issue-7",
        )

        with patch.dict(
                 sys.modules,
                 {
                     "backend.rag.parser": fake_parser_module,
                     "backend.rag.vector_store": fake_vector_store_module,
                     "backend.agents.graph": fake_graph_module,
                 },
             ), \
             patch("backend.services.repo_service.clone_repo", lambda repo_url, base_dir="repos": "repos/jobs/job-2/demo"), \
             patch(
                 "backend.services.repo_service.comment_on_issue",
                 lambda repo_owner, repo_name, issue_number, message: comments.append(message) or {"id": 1},
             ):
            main.run_aide_job(job_id, request)

        self.assertEqual(main.jobs[job_id]["status"], "done")
        self.assertTrue(main.jobs[job_id]["result"]["pr"]["html_url"].endswith("/pull/2"))
        self.assertTrue(any("Draft PR: https://github.com/acme/demo/pull/2" in comment for comment in comments))

    def test_github_webhook_queues_autonomous_job(self):
        queued = {}
        body = (
            '{"action":"opened","issue":{"number":9,"title":"Bug report","body":"traceback here"},'
            '"repository":{"name":"demo","clone_url":"https://github.com/acme/demo.git",'
            '"default_branch":"develop","owner":{"login":"acme"}}}'
        )

        class FakeLoop:
            def run_in_executor(self, executor, fn, job_id, request):
                queued["job_id"] = job_id
                queued["fn"] = fn
                queued["request"] = request

        secret = main.os.environ.get("GITHUB_WEBHOOK_SECRET", "")
        headers = {"X-GitHub-Event": "issues"}
        if secret:
            digest = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Hub-Signature-256"] = f"sha256={digest}"

        with patch.object(main.asyncio, "get_event_loop", return_value=FakeLoop()), \
             patch(
                 "backend.services.repo_service.comment_on_issue",
                 lambda repo_owner, repo_name, issue_number, message: {"id": 123},
             ):
            client = TestClient(main.app)
            response = client.post(
                "/api/webhook/github",
                headers=headers,
                content=body,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIs(queued["fn"], main.run_aide_job)
        self.assertEqual(queued["request"].repo_owner, "acme")
        self.assertEqual(queued["request"].repo_name, "demo")
        self.assertEqual(queued["request"].base_branch, "develop")
        self.assertEqual(queued["request"].branch_name, "aide/issue-9")


if __name__ == "__main__":
    unittest.main()
