import os
import re
import subprocess
from datetime import datetime
from urllib.parse import urlparse

import requests


def _run_git(args: list[str], repo_path: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )


def _repo_name_from_url(repo_url: str) -> str:
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


def _sanitize_branch_fragment(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._/-]+", "-", text.strip().lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-/.")
    return cleaned or "autofix"


def _github_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set in environment.")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }


def _configure_git_identity(repo_path: str):
    name = os.environ.get("GIT_AUTHOR_NAME", "AIDE Bot")
    email = os.environ.get("GIT_AUTHOR_EMAIL", "aide-bot@users.noreply.github.com")

    _run_git(["config", "user.name", name], repo_path)
    _run_git(["config", "user.email", email], repo_path)


def _authenticated_repo_url(repo_url: str) -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token or "github.com" not in repo_url:
        return repo_url

    parsed = urlparse(repo_url)
    path = parsed.path.lstrip("/")
    return f"https://x-access-token:{token}@github.com/{path}"


def clone_repo(repo_url: str, base_dir: str = "repos") -> str:
    """
    Clone a GitHub repo locally. Skips if already exists.
    Returns path to cloned repo.
    """
    os.makedirs(base_dir, exist_ok=True)

    repo_name = _repo_name_from_url(repo_url)
    repo_path = os.path.join(base_dir, repo_name)

    if os.path.exists(repo_path):
        print(f"Repo already exists at {repo_path}")
        return repo_path

    print(f"Cloning {repo_url}...")
    try:
        _run_git(["clone", _authenticated_repo_url(repo_url), repo_path])
        print("Clone successful!")
        return repo_path
    except subprocess.CalledProcessError as e:
        print(f"Clone failed:\n{e.stderr}")
        raise


def create_branch(
    repo_path: str,
    base_branch: str = "main",
    branch_name: str | None = None,
    issue_number: int | None = None,
) -> str:
    """
    Create and checkout a new git branch for the fix.
    Returns the branch name.
    """
    if branch_name is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        issue_fragment = f"issue-{issue_number}" if issue_number else "issue"
        branch_name = f"aide/{issue_fragment}-{timestamp}"

    branch_name = _sanitize_branch_fragment(branch_name)

    try:
        _run_git(["fetch", "origin", base_branch], repo_path)
        _run_git(["checkout", base_branch], repo_path)
        _run_git(["pull", "origin", base_branch], repo_path)
        _run_git(["checkout", "-b", branch_name], repo_path)
        print(f"Created branch: {branch_name}")
        return branch_name
    except subprocess.CalledProcessError as e:
        print(f"Branch creation failed:\n{e.stderr}")
        raise


def comment_on_issue(
    repo_owner: str,
    repo_name: str,
    issue_number: int,
    message: str,
) -> dict:
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
    response = requests.post(
        url,
        json={"body": message},
        headers=_github_headers(),
        timeout=30,
    )
    if response.status_code == 201:
        return response.json()
    return {"error": response.text, "status_code": response.status_code}


def commit_and_push(
    repo_path: str,
    branch_name: str,
    message: str,
    changed_files: list[str] | None = None,
) -> dict:
    """
    Stage all changes, commit, and push to origin.
    """
    try:
        status = _run_git(["status", "--porcelain"], repo_path)
        if not status.stdout.strip():
            return {"success": False, "error": "No file changes detected to commit."}

        files_to_stage = [
            path for path in (changed_files or [])
            if path and not path.startswith(".aide_index")
        ]
        if files_to_stage:
            _run_git(["add", "--", *files_to_stage], repo_path)
        else:
            _run_git(["add", "-A"], repo_path)

        _run_git(["reset", "HEAD", "--", ".aide_index.faiss", ".aide_index.meta.pkl"], repo_path)
        staged = _run_git(["diff", "--cached", "--name-only"], repo_path)
        if not staged.stdout.strip():
            return {"success": False, "error": "No eligible file changes detected to commit."}

        _configure_git_identity(repo_path)
        _run_git(["commit", "-m", message], repo_path)
        _run_git(["push", "--set-upstream", "origin", branch_name], repo_path)
        print(f"Pushed branch: {branch_name}")
        return {"success": True}
    except subprocess.CalledProcessError as e:
        print(f"Push failed:\n{e.stderr}")
        return {"success": False, "error": e.stderr.strip() or str(e)}


def create_pull_request(
    repo_owner: str,
    repo_name: str,
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main",
    draft: bool = True,
) -> dict:
    """
    Create a GitHub Pull Request via the REST API.
    Returns PR data on success, or {"error": ...} on failure.
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
    payload = {
        "title": title,
        "body": body,
        "head": branch_name,
        "base": base_branch,
        "draft": draft,
    }

    response = requests.post(url, json=payload, headers=_github_headers(), timeout=30)

    if response.status_code == 201:
        pr = response.json()
        print(f"PR created: {pr['html_url']}")
        return pr

    try:
        error = response.json()
    except ValueError:
        error = response.text
    print(f"PR creation failed: {error}")
    return {"error": error, "status_code": response.status_code}


def full_pr_workflow(
    repo_path: str,
    repo_owner: str,
    repo_name: str,
    fix_description: str,
    changed_files: list[str],
    base_branch: str = "main",
    issue_number: int | None = None,
    branch_name: str | None = None,
    draft: bool = True,
) -> dict:
    """
    End-to-end on an already-prepared repo: branch, commit, push, create PR.
    """
    branch_name = create_branch(
        repo_path=repo_path,
        base_branch=base_branch,
        branch_name=branch_name,
        issue_number=issue_number,
    )

    commit_msg = f"fix: {fix_description[:72]}"
    push_result = commit_and_push(
        repo_path,
        branch_name,
        commit_msg,
        changed_files=changed_files,
    )

    if not push_result.get("success"):
        return {"error": push_result.get("error", "Failed to push branch.")}

    issue_line = f"Closes #{issue_number}\n\n" if issue_number else ""
    pr_body = (
        f"## AIDE Automated Fix\n\n"
        f"{issue_line}"
        f"**Issue Summary:** {fix_description}\n\n"
        f"**Files changed:** {', '.join(changed_files)}\n\n"
        f"*Generated by Autonomous AI Engineer (AIDE)*"
    )

    pr = create_pull_request(
        repo_owner=repo_owner,
        repo_name=repo_name,
        branch_name=branch_name,
        title=f"[AIDE] {fix_description[:60]}",
        body=pr_body,
        base_branch=base_branch,
        draft=draft,
    )
    pr["branch_name"] = branch_name
    return pr
