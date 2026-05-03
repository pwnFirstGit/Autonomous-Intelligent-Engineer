import time
import os
from urllib.parse import urlparse

import requests
import streamlit as st

API_URL = os.environ.get("AIDE_API_URL", "http://localhost:8000")


def parse_github_repo(repo_url: str) -> tuple[str | None, str | None]:
    try:
        parsed = urlparse(repo_url.strip())
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        owner, name = path.split("/", 1)
        return owner or None, name or None
    except ValueError:
        return None, None

st.set_page_config(
    page_title="Autonomous AI Engineer",
    page_icon="🤖",
    layout="wide",
)

st.markdown("""
<style>
    .diff-add    { color: #3fb950; font-family: monospace; }
    .diff-remove { color: #f85149; font-family: monospace; }
    .diff-meta   { color: #8b949e; font-family: monospace; }
    .badge { display:inline-block; padding:2px 12px; border-radius:12px; font-size:13px; font-weight:600; }
    .done    { background:#1a4731; color:#3fb950; }
    .running { background:#1c2d3a; color:#58a6ff; }
    .failed  { background:#3d1c1c; color:#f85149; }
    .pending { background:#2d2208; color:#d29922; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🤖 Autonomous AI Engineer")
st.markdown("*Paste a GitHub repo URL and describe the issue — AIDE will fix it.*")
st.divider()

# ── API health ────────────────────────────────────────────────────────────────
try:
    health = requests.get(f"{API_URL}/api/status", timeout=3).json()
    st.success(f"✅ API connected — {health['active_jobs']} active job(s)")
except Exception:
    st.error("❌ API not running. Start it with: `uvicorn api.main:app --port 8000`")
    st.stop()

# ── Input ─────────────────────────────────────────────────────────────────────
repo_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/username/repo")
issue = st.text_area("Describe the Issue", placeholder="e.g. fix syntax error in helper.py", height=120)
create_pr = st.checkbox(
    "Open a draft Pull Request if the fix succeeds",
    value=False,
    help="Requires GITHUB_TOKEN with Contents, Issues, and Pull requests read/write permissions.",
)

repo_owner, repo_name = parse_github_repo(repo_url) if repo_url else (None, None)
base_branch = "main"

if create_pr:
    with st.expander("Pull Request settings", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            repo_owner = st.text_input("Repository owner", value=repo_owner or "")
        with col2:
            repo_name = st.text_input("Repository name", value=repo_name or "")
        with col3:
            base_branch = st.text_input("Base branch", value="main")
submit = st.button("🚀 Run AIDE", type="primary", use_container_width=True)

if submit:
    if not repo_url or not issue:
        st.warning("Please fill in both fields.")
    elif create_pr and (not repo_owner or not repo_name or not base_branch):
        st.warning("Please fill in repository owner, repository name, and base branch to create a PR.")
    else:
        payload = {
            "repo_url": repo_url,
            "issue": issue,
        }

        if create_pr:
            payload.update({
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "base_branch": base_branch,
                "draft_pr": True,
            })

        resp = requests.post(f"{API_URL}/api/analyze", json=payload).json()
        st.session_state["job_id"] = resp["job_id"]
        st.success(f"✅ Job submitted! ID: `{resp['job_id']}`")

# ── Results ───────────────────────────────────────────────────────────────────
if "job_id" in st.session_state:
    job_id = st.session_state["job_id"]
    st.divider()
    st.markdown(f"### Job `{job_id}`")

    status_box = st.empty()

    with st.spinner("AIDE is working..."):
        waited = 0
        while waited < 300:
            job = requests.get(f"{API_URL}/api/jobs/{job_id}").json()
            status = job.get("status", "pending")
            status_box.markdown(
                f'<span class="badge {status}">{status.upper()}</span>',
                unsafe_allow_html=True,
            )
            if status in ("done", "failed"):
                break
            time.sleep(3)
            waited += 3

    if status == "failed":
        st.error(f"❌ {job.get('error')}")

    elif status == "done":
        result = job["result"]
        plan = result.get("plan", {})
        results = result.get("results", [])
        pr = result.get("pr")

        if pr and pr.get("html_url"):
            st.success("Draft Pull Request created.")
            st.markdown(f"**PR:** [{pr['html_url']}]({pr['html_url']})")
        elif pr and pr.get("error"):
            st.warning("AIDE fixed code, but Pull Request creation failed.")
            st.code(str(pr["error"]), language="bash")

        # Plan summary
        with st.expander("📋 Plan", expanded=True):
            st.markdown(f"**Problem:** {plan.get('problem', 'N/A')}")
            st.markdown(f"**Files:** {', '.join(plan.get('files_likely', []))}")
            for i, step in enumerate(plan.get("steps", []), 1):
                st.markdown(f"{i}. {step}")

        # Per-file diffs
        for r in results:
            fix = r["result"]
            fix_status = fix.get("status", "unknown")
            icon = "✅" if fix_status == "success" else "❌"

            with st.expander(f"{icon} {r['file']} — {fix_status} ({fix.get('attempts', '?')} attempt(s))"):
                if fix.get("diff"):
                    lines = fix["diff"].split("\n")
                    rendered = []
                    for line in lines:
                        if line.startswith("+") and not line.startswith("+++"):
                            rendered.append(f'<span class="diff-add">{line}</span>')
                        elif line.startswith("-") and not line.startswith("---"):
                            rendered.append(f'<span class="diff-remove">{line}</span>')
                        elif line.startswith("@@"):
                            rendered.append(f'<span class="diff-meta">{line}</span>')
                        else:
                            rendered.append(line)
                    st.markdown("<pre>" + "\n".join(rendered) + "</pre>", unsafe_allow_html=True)

                if fix.get("error"):
                    st.code(fix["error"], language="bash")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📜 Job History")
    st.button("🔄 Refresh")
    try:
        all_jobs = requests.get(f"{API_URL}/api/jobs", timeout=3).json()
        if not all_jobs:
            st.caption("No jobs yet.")
        for j in reversed(all_jobs):
            badge = {"done": "🟢", "running": "🔵", "pending": "🟡", "failed": "🔴"}.get(j["status"], "⚪")
            if st.button(f"{badge} `{j['job_id']}` — {j['status']}", key=j["job_id"]):
                st.session_state["job_id"] = j["job_id"]
    except Exception:
        st.caption("Could not load jobs.")
