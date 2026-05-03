import os
import json
import re
from typing import List, Dict
from backend.services.llm_service import LLMService


class LLMPlanner:
    def __init__(self, model: str = None):
        self.llm = LLMService(model=model)

    def _extract_mentioned_files(self, issue: str, valid_files: set) -> list:
        """If user explicitly mentions a filename, prioritize it."""
        mentioned = []
        for f in valid_files:
            basename = os.path.basename(f).lower()
            if basename in issue.lower() or basename.replace(".py", "") in issue.lower():
                mentioned.append(f)
        return mentioned

    def generate_plan(self, issue: str, context: List[Dict]) -> Dict:
        if not context:
            return {"error": "No context retrieved. Cannot generate plan."}

        files = list(set(os.path.basename(c["file"]) for c in context))
        valid_files = set(files)

        # If user explicitly named a file, skip LLM entirely
        mentioned = self._extract_mentioned_files(issue, valid_files)
        if mentioned:
            return {
                "problem": f"Fix issues in {', '.join(mentioned)}: {issue}",
                "files_likely": mentioned,
                "steps": ["analyze the file", "fix the issues", "verify no errors remain"]
            }

        code_context = "\n\n".join(
            f"FILE: {os.path.basename(c['file'])}\n{c['code'][:500]}"
            for c in context
        )

        prompt = f"""You are an expert software engineer performing automated code repair.

IMPORTANT RULES:
- ONLY include files from the "Available files" list below.
- DO NOT invent file names.
- Return ONLY valid JSON — no explanation, no markdown.

Available files:
{json.dumps(files)}

---
ISSUE:
{issue}

---
CODE CONTEXT:
{code_context}

---
Return ONLY this JSON:
{{
  "problem": "one sentence describing the root cause",
  "files_likely": ["only files from Available files"],
  "steps": ["step 1", "step 2", "step 3"]
}}"""

        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return self._parse_plan(response["message"]["content"], valid_files)

    def _parse_plan(self, content: str, valid_files: set) -> Dict:
        cleaned = re.sub(r"```(?:json)?", "", content).strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        cleaned = match.group() if match else cleaned

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            return {"error": f"JSON parse error: {e}. Raw: {content[:300]}"}

        raw_files = parsed.get("files_likely", [])
        filtered = [f for f in raw_files if f in valid_files]
        if not filtered:
            filtered = list(valid_files)[:1]
        parsed["files_likely"] = filtered
        return parsed


class PlannerAgent:
    def __init__(self, model: str = None):
        self.planner = LLMPlanner(model=model)

    def run(self, issue: str, context: List[Dict]) -> Dict:
        return self.planner.generate_plan(issue, context)