import os

from backend.services.execution_service import ExecutionService
from backend.agents.code_agent import CodeAgent
from backend.agents.critic import CriticAgent


class SelfHealingAgent:
    """
    Iteratively fixes a file: modify → execute → check → repeat.
    Uses CriticAgent for a pre-flight static review before execution.
    """

    def __init__(self, repo_path: str, model: str = None):
        self.executor = ExecutionService(repo_path)
        self.code_agent = CodeAgent(repo_path, model)
        self.critic = CriticAgent(model)

    def fix_code(self, file_name: str, instruction: str, max_attempts: int = 3) -> dict:
        file_name = os.path.normpath(file_name)
        last_diff = ""
        last_error = ""

        for attempt in range(1, max_attempts + 1):
            print(f"\n🔁 Attempt {attempt}/{max_attempts} — {file_name}")

            # Step 1: LLM modifies the code
            modify_result = self.code_agent.modify_code(file_name, instruction)

            if "error" in modify_result:
                last_error = modify_result["error"]
                print(f"❌ Code modification failed: {last_error}")
                continue

            last_diff = modify_result["diff"]
            updated_code = modify_result["updated_code"]

            if not last_diff.strip():
                last_error = "The previous attempt did not change the file."
                instruction = (
                    f"{last_error}\n\n"
                    f"Apply a concrete code change that addresses this task:\n{instruction}"
                )
                continue

            # Step 2: Critic review
            review = self.critic.review(updated_code)
            print(f"🔍 Critic: {review[:120]}")

            if "valid" not in review.lower():
                last_error = review
                instruction = (
                    f"Fix the following issues:\n{review}\n\nOriginal task:\n{instruction}"
                )
                continue

            syntax_check = self.executor.validate_python_file(file_name)
            if not syntax_check["success"]:
                last_error = syntax_check["stderr"]
                instruction = (
                    f"The updated file still fails validation:\n{last_error}\n\n"
                    f"Original task:\n{instruction}"
                )
                continue

            test_result = self.executor.run_tests_if_present()
            if not test_result["success"]:
                last_error = test_result["stderr"] or test_result["stdout"]
                instruction = (
                    f"The repository tests are failing after the change:\n{last_error}\n\n"
                    f"Original task:\n{instruction}"
                )
                continue

            print("✅ Validation approved!")
            return {
                "status": "success",
                "attempts": attempt,
                "diff": last_diff,
                "output": test_result["stdout"] or syntax_check["stdout"],
            }

            instruction = (
                f"Fix the following issues:\n{last_error}\n\nOriginal task:\n{instruction}"
            )

        return {
            "status": "failed",
            "attempts": max_attempts,
            "diff": last_diff,
            "error": last_error,
        }
