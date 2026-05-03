import os
import hmac
import hashlib
import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

os.environ["WATCHFILES_IGNORE_PATHS"] = "repos"
load_dotenv()

jobs: dict = {}
executor = ThreadPoolExecutor(max_workers=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("AIDE API starting up...")
    yield
    print("AIDE API shutting down...")


app = FastAPI(
    title="Autonomous AI Engineer",
    description="Automatically fixes GitHub issues and opens Draft Pull Requests.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    repo_url: str
    issue: str
    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None
    base_branch: str = "main"
    issue_number: Optional[int] = None
    branch_name: Optional[str] = None
    draft_pr: bool = True


def _build_pr_config(request: AnalyzeRequest) -> Optional[dict]:
    if not request.repo_owner or not request.repo_name:
        return None

    return {
        "repo_owner": request.repo_owner,
        "repo_name": request.repo_name,
        "base_branch": request.base_branch,
        "issue_number": request.issue_number,
        "branch_name": request.branch_name,
        "draft": request.draft_pr,
    }


def _comment_job_result(request: AnalyzeRequest, job_id: str, result: dict | None, error: str | None = None):
    if not request.repo_owner or not request.repo_name or not request.issue_number:
        return

    from backend.services.repo_service import comment_on_issue

    if error:
        message = (
            f"Automated fix job `{job_id}` failed.\n\n"
            f"Error:\n```\n{error}\n```"
        )
    else:
        pr = (result or {}).get("pr") or {}
        pr_url = pr.get("html_url")
        changed = [
            item["file"]
            for item in (result or {}).get("results", [])
            if item.get("result", {}).get("status") == "success"
        ]

        if pr_url:
            message = (
                f"Automated fix job `{job_id}` is ready.\n\n"
                f"Draft PR: {pr_url}\n"
                f"Files touched: {', '.join(changed) if changed else 'unknown'}"
            )
        else:
            message = (
                f"Automated fix job `{job_id}` finished, but no draft PR was created.\n\n"
                f"Changed files: {', '.join(changed) if changed else 'none'}\n"
                f"Reason: {_result_failure_reason(result)}"
            )

    comment_on_issue(
        repo_owner=request.repo_owner,
        repo_name=request.repo_name,
        issue_number=request.issue_number,
        message=message,
    )


def _result_failure_reason(result: dict | None) -> str:
    if not result:
        return "No result was produced."

    pr = result.get("pr")
    if isinstance(pr, dict) and pr.get("error"):
        return str(pr["error"])

    if result.get("error"):
        return str(result["error"])

    failed_results = [
        item.get("result", {}).get("error")
        for item in result.get("results", [])
        if item.get("result", {}).get("error")
    ]
    if failed_results:
        return str(failed_results[0])

    if not pr:
        return "No pull request was created."

    return "Unknown failure."


def run_aide_job(job_id: str, request: AnalyzeRequest):
    try:
        jobs[job_id]["status"] = "running"

        from backend.rag.parser import CodeParser
        from backend.rag.vector_store import VectorStore
        from backend.agents.graph import AIAgentSystem
        from backend.services.repo_service import clone_repo

        repo_path = clone_repo(
            request.repo_url,
            base_dir=os.path.join("repos", "jobs", job_id),
        )

        index_dir = os.path.join("repos", "indexes", job_id)
        os.makedirs(index_dir, exist_ok=True)
        index_path = os.path.join(index_dir, "code")
        store = VectorStore()

        if os.path.exists(f"{index_path}.faiss"):
            store.load(index_path)
        else:
            parser = CodeParser(language="python")
            parsed = parser.parse_repository(repo_path)
            print(f"Parsed {len(parsed)} chunks")
            store.build_index(parsed)
            store.save(index_path)

        agent = AIAgentSystem(store, repo_path)
        pr_config = _build_pr_config(request)
        result = agent.run(
            issue=request.issue,
            create_pr=bool(pr_config),
            pr_config=pr_config,
        )

        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = result
        _comment_job_result(request, job_id, result=result)

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        _comment_job_result(request, job_id, result=None, error=str(e))
        print(f"Job {job_id} failed: {e}")


@app.get("/api/status")
def health_check():
    return {
        "status": "ok",
        "service": "AIDE — Autonomous Issue-Driven Engineer",
        "version": "1.0.0",
        "active_jobs": sum(1 for j in jobs.values() if j["status"] == "running"),
    }


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "pending", "result": None, "error": None}
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, run_aide_job, job_id, request)
    return {"job_id": job_id, "status": "pending", "result": None, "error": None}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job.get("status", "pending"),
        "result": job.get("result"),
        "error": job.get("error"),
    }


@app.get("/api/jobs")
def list_jobs():
    return [
        {"job_id": jid, "status": j["status"]}
        for jid, j in jobs.items()
    ]


@app.post("/api/webhook/github")
async def github_webhook(request: Request):
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    body = await request.body()

    if secret:
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            key=secret.encode(), msg=body, digestmod=hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, sig_header):
            raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    payload = json.loads(body)
    event = request.headers.get("X-GitHub-Event", "")

    if event != "issues" or payload.get("action") != "opened":
        return {"message": "Event ignored.", "event": event}

    issue = payload["issue"]
    repo = payload["repository"]
    issue_number = issue["number"]
    owner = repo["owner"]["login"]
    name = repo["name"]

    # Comment on issue immediately
    from backend.services.repo_service import comment_on_issue
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "pending", "result": None, "error": None}

    comment_on_issue(
        repo_owner=owner,
        repo_name=name,
        issue_number=issue_number,
        message=(
            f"**AIDE is on it!**\n\n"
            f"Analyzing the codebase and generating a fix.\n\n"
            f"**Job ID:** `{job_id}`\n\n"
            f"_I'll comment here again once the fix is ready._"
        )
    )

    req = AnalyzeRequest(
        repo_url=repo["clone_url"],
        issue=f"{issue['title']}\n\n{issue.get('body', '')}",
        repo_owner=owner,
        repo_name=name,
        base_branch=repo.get("default_branch", "main"),
        issue_number=issue_number,
        branch_name=f"aide/issue-{issue_number}",
        draft_pr=True,
    )

    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, run_aide_job, job_id, req)

    print(f"Webhook: Issue #{issue_number} -> job {job_id} queued")
    return {"message": "Job queued.", "job_id": job_id}
