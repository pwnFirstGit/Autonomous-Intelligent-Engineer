import os
import difflib
from backend.services.llm_service import LLMService


class CodeAgent:
    """
    Modifies source files using an LLM based on a natural language instruction.
    """

    def __init__(self, repo_path: str, model: str = None):
        self.repo_path = repo_path
        self.llm = LLMService(model=model)

    def modify_code(self, file_name: str, instruction: str) -> dict:
        """
        Read a file, apply the instruction via LLM, save updated code.
        Returns: {"file", "diff", "updated_code"} or {"error": str}
        """
        file_path = os.path.join(self.repo_path, file_name)

        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        with open(file_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        prompt = f"""You are an expert Python developer performing automated code repair.

STRICT OUTPUT RULES:
- Return ONLY raw Python code.
- NO explanations, NO markdown, NO triple backticks.
- The output must be a complete, valid Python file.

INSTRUCTION:
{instruction}

CURRENT CODE:
{original_code}
"""

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            updated_code = response["message"]["content"]
        except Exception as e:
            return {"error": f"LLM call failed: {e}"}

        updated_code = self._strip_markdown(updated_code)

        if not updated_code.strip():
            return {"error": "LLM returned empty code."}

        diff = list(
            difflib.unified_diff(
                original_code.splitlines(),
                updated_code.splitlines(),
                fromfile=f"a/{file_name}",
                tofile=f"b/{file_name}",
                lineterm="",
            )
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_code)

        return {
            "file": file_name,
            "diff": "\n".join(diff),
            "updated_code": updated_code,
        }

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove markdown code fences the LLM might add despite instructions."""
        text = text.strip()
        if text.startswith("```python"):
            text = text[len("```python"):].strip()
        elif text.startswith("```"):
            text = text[3:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        return text