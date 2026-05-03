import subprocess
import sys
import os

class ExecutionService:
    """
    Safely executes Python files in a subprocess and captures output.
    """

    def __init__(self, repo_path: str, timeout: int = 15):
        self.repo_path = repo_path
        self.timeout = timeout
        # Use the same Python interpreter running this process
        self.python_exec = sys.executable

    def run_python_file(self, file_name: str) -> dict:
        """
        Run a Python file and return success/stdout/stderr.
        """
        file_path = os.path.join(self.repo_path, file_name)

        if not os.path.exists(file_path):
            return {
                "success": False,
                "stdout": "",
                "stderr": f"File not found: {file_path}",
            }

        try:
            result = subprocess.run(
                [self.python_exec, file_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.repo_path,  # run from repo root so relative imports work
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {self.timeout}s",
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
            }

    def validate_python_file(self, file_name: str) -> dict:
        """
        Compile a Python file to catch syntax errors without executing it.
        """
        file_path = os.path.join(self.repo_path, file_name)

        if not os.path.exists(file_path):
            return {
                "success": False,
                "stdout": "",
                "stderr": f"File not found: {file_path}",
            }

        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                source = handle.read()
            compile(source, file_path, "exec")
            return {"success": True, "stdout": "Syntax check passed.", "stderr": ""}
        except SyntaxError as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"SyntaxError: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
            }

    def run_tests_if_present(self) -> dict:
        """
        Run pytest only when the repository already contains tests.
        """
        has_tests = False
        for root, _, files in os.walk(self.repo_path):
            if any(name.startswith("test_") and name.endswith(".py") for name in files):
                has_tests = True
                break

        if not has_tests:
            return {
                "success": True,
                "stdout": "No repository tests were found; skipped pytest.",
                "stderr": "",
            }

        return self.run_tests()

    def run_tests(self, test_pattern: str = "test_*.py") -> dict:
        """
        Run pytest on the repo and return results.
        """
        try:
            result = subprocess.run(
                [self.python_exec, "-m", "pytest", test_pattern, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.repo_path,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Test run timed out.",
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
            }
