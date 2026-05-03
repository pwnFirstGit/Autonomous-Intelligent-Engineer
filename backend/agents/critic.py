from backend.services.llm_service import LLMService


class CriticAgent:
    """
    Reviews generated code for syntax errors, logical issues,
    and obvious bugs before execution.
    """

    def __init__(self, model: str = None):
        self.llm = LLMService(model=model)

    def review(self, code: str) -> str:
        """
        Returns "valid" if the code looks correct,
        otherwise returns a description of the issues found.
        """
        prompt = f"""You are a senior Python code reviewer performing automated quality checks.

Review the code below for:
1. Syntax errors (invalid Python)
2. Undefined variables or missing imports  
3. Obvious logical bugs (infinite loops, wrong return types, etc.)
4. Security issues (e.g., shell injection, unsafe eval)

RESPONSE RULES:
- If the code is correct: respond with exactly the word "valid"
- If there are issues: list them concisely, one per line

CODE TO REVIEW:
{code}
"""
        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response["message"]["content"].strip()