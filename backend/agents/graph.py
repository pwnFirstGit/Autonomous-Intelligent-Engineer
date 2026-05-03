from backend.agents.planner import PlannerAgent
from backend.agents.retriever_agent import RetrieverAgent
from backend.agents.self_healing import SelfHealingAgent
from backend.services.repo_service import full_pr_workflow


class AIAgentSystem:
    """
    Main orchestrator for the Autonomous AI Engineer pipeline:
    Issue → Retrieve context → Plan → Fix → (PR)
    """

    def __init__(self, vector_store, repo_path: str):
        self.retriever = RetrieverAgent(vector_store)
        self.planner = PlannerAgent()
        self.healer = SelfHealingAgent(repo_path)
        self.repo_path = repo_path

    def run(self, issue: str, create_pr: bool = False, pr_config: dict = None) -> dict:
        """
        Run the full fix pipeline for a given issue.

        Args:
            issue: Natural language description of the bug/issue.
            create_pr: If True, open a GitHub PR with the fixes.
            pr_config: Dict with keys: repo_url, repo_owner, repo_name, base_branch

        Returns:
            {
                "plan": {...},
                "results": [{"file": str, "result": {...}}, ...],
                "pr": {...} or None
            }
        """
        print(f"\n🔍 Retrieving context for: {issue}")
        context = self.retriever.run(issue)

        if not context:
            return {
                "plan": {},
                "results": [],
                "error": "No relevant context found in the repository.",
            }

        print(f"📋 Planning fix...")
        plan = self.planner.run(issue, context)

        if "error" in plan:
            return {"plan": plan, "results": [], "error": plan["error"]}

        if "files_likely" not in plan or not plan["files_likely"]:
            return {
                "plan": plan,
                "results": [],
                "error": "Planner did not identify any files to fix.",
            }

        results = []
        changed_files = []

        for file_name in plan["files_likely"]:
            print(f"\n🔧 Fixing: {file_name}")
            result = self.healer.fix_code(file_name, plan.get("problem", issue))
            results.append({"file": file_name, "result": result})

            if result.get("status") == "success" and result.get("diff"):
                changed_files.append(file_name)

        pr_result = None
        if create_pr and changed_files and pr_config:
            print(f"\n🚀 Creating Pull Request...")
            pr_result = full_pr_workflow(
                repo_path=self.repo_path,
                repo_owner=pr_config["repo_owner"],
                repo_name=pr_config["repo_name"],
                fix_description=plan.get("problem", issue),
                changed_files=changed_files,
                base_branch=pr_config.get("base_branch", "main"),
                issue_number=pr_config.get("issue_number"),
                branch_name=pr_config.get("branch_name"),
                draft=pr_config.get("draft", True),
            )

        return {
            "plan": plan,
            "results": results,
            "pr": pr_result,
        }
