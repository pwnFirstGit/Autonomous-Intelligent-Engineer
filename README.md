## 🚀 Autonomous AI Engineer

AI agent that automatically fixes GitHub issues and opens pull requests.

## 🧠 Tech Stack
FastAPI • Streamlit • RAG • LLM Agents • Docker • GitHub API

## 🔥 Demo
- Input: GitHub Issue
- Output: Auto-generated fix + Draft PR

## 📸 Demo Walkthrough

### 1. Github File Error(Syntax erro in line 5, 10 and 13)
![Error File](assets/Image1.png)

### 2. Issue Input
![Issue](assets/Image2.png)

### 3. Agent Planning
![Plan](assets/Image3.png)

### 4. Code Fix
![Fixing](assets/Image4.png)

### 5. PR Creation
![PR](assets/Image5.png)

### 6. Fixed Code Review
![Code Review](assets/Image6.png)

### 7. Merged PR and Issue Closed
![Merged PR](assets/Image7.png)

### 8. Fixed Code Task Complete
![Fixed Code](assets/Image8.png)

### 9. Optional(Also fix bugs manually from Streamlit UI without GitHub issues)
![UI](assets/Image9.png)

## ✨ Key Features

- 🔍 Intelligent code retrieval using RAG
- 🤖 Autonomous agent loop (plan → edit → validate)
- 🔧 Automatic bug fixing from GitHub issues
- 🔁 Draft PR generation with commits
- ⚡ Supports multiple LLM providers

## 💡 Why This Project?

Modern software development is moving towards AI-assisted workflows.
This project demonstrates how LLM agents can:
- Understand large codebases
- Fix real-world issues
- Integrate with developer tools like GitHub

## What It Does

The live GitHub flow looks like this:

1. A developer opens a GitHub issue.
2. GitHub sends an `issues` webhook to AIDE.
3. AIDE clones the repository locally.
4. AIDE parses the repository and builds a retrieval index.
5. AIDE finds relevant files and creates a repair plan.
6. AIDE edits the likely file(s), validates syntax, and runs tests when present.
7. AIDE creates a branch, pushes the fix, and opens a draft PR.
8. AIDE comments back on the issue with the result.

You can also run AIDE manually from the Streamlit UI without GitHub webhooks.

## Project Structure

```text
api/                    FastAPI app and GitHub webhook entrypoint
backend/agents/         Planner, retriever, fixer, critic, orchestration
backend/rag/            Parser, retriever, vector store
backend/services/       LLM, git/GitHub, execution helpers
frontend/               Streamlit UI
scripts/                Manual test and exploration scripts
tests/                  Automated tests for the live autonomous flow
repos/                  Cloned target repositories and job workspaces
```

## Requirements

Before running the project, make sure you have:

- Python 3.10+ recommended
- Git installed and available in `PATH`
- a GitHub token with repository write access
- an LLM provider configured
- optionally Docker Desktop if you want to run with containers

If you want to use the default local LLM mode, also install:

- Ollama

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Autonomous-AI-Engineer
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .newvenv
.\.newvenv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .newvenv
source .newvenv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
pip install ollama  # If you want to use Ollama as your LLM provider
```

## Environment Variables

Create a root `.env` file in the project directory. This file stores private configuration such as your GitHub token, webhook secret, and LLM settings.

```env
GITHUB_TOKEN=your_github_token
GITHUB_WEBHOOK_SECRET=your_random_webhook_secret

LLM_PROVIDER=Your chosen provider, e.g. ollama, gemini, openai, etc.
LLM_MODEL=Your chosen model name for that provider, e.g. qwen2.5-coder:7b
LLM_API_KEY=your_llm_api_key (If you are using a provider that requires an API key, e.g. OpenAI)
```

### What each value means

- `GITHUB_TOKEN`: a GitHub access token AIDE uses to clone repositories, comment on issues, push fix branches, and open pull requests.
- `GITHUB_WEBHOOK_SECRET`: a random secret string shared between GitHub and AIDE so AIDE can verify webhook requests are really from GitHub.
- `LLM_PROVIDER`: which model provider to use. The default is `ollama`.
- `LLM_MODEL`: the model name for the selected provider.
- `LLM_API_KEY`: the API key for the selected provider (if required).

### Supported LLM providers

The project supports:

- `ollama`
- `gemini`
- `groq`
- `anthropic`
- `openai`
- `grok`

### How to create a GitHub token

Use a fine-grained personal access token.

1. Open GitHub in your browser.
2. Click your profile picture in the top-right.
3. Go to `Settings`.
4. In the left sidebar, open `Developer settings`.
5. Open `Personal access tokens`.
6. Select `Fine-grained tokens`.
7. Click `Generate new token`.
8. Give it a clear name, for example `AIDE Local Bot`.
9. Choose an expiration date.
10. Under `Resource owner`, select the account or organization that owns the repository.
11. Under `Repository access`, choose either:
    - `Only select repositories` and select the repo AIDE should work on
    - `All repositories` if you want AIDE to work across all repos you own
12. Under `Repository permissions`, add:
    - `Contents` -> `Read and write`
    - `Issues` -> `Read and write`
    - `Pull requests` -> `Read and write`
13. Generate the token.
14. Copy the token immediately. GitHub will not show it again.
15. Paste it into `.env`:

```env
GITHUB_TOKEN=github_pat_your_real_token_here
```
### How to create a webhook secret

The webhook secret is not given by GitHub. You create it yourself.

Generate a strong random value with Python:
Example output:
```text
7f3c91b2a8e44f2fa1c5d9e6a0b7c124b2e1a9f0d8c7b6a5e4d3c2b1a0f9e8d7
```

Put that value in `.env`:

```env
GITHUB_WEBHOOK_SECRET=7f3c91b2a8e44f2fa1c5d9e6a0b7c124b2e1a9f0d8c7b6a5e4d3c2b1a0f9e8d7
```

Later, when you create the GitHub webhook, paste the exact same value into the webhook `Secret` field.

## How To Run Autonomous AI Engineer

AIDE can run in two ways. The recommended path is Docker because it keeps the backend and frontend setup reproducible. If you prefer direct Python development, use the non-Docker path.

- Option 1: run with Docker Compose
- Option 2: run without Docker, directly with Python

Both options support the same product workflows:

- Manual fixing without PR: AIDE analyzes and fixes code from the Streamlit UI, then you review the local job output yourself.
- Manual fixing with draft PR: AIDE analyzes and fixes code from the Streamlit UI, then pushes a branch and opens a draft PR.
- GitHub webhook automation: AIDE reacts automatically when a new GitHub issue is opened, fixes the code, and opens a draft PR.

## Option 1: Run With Docker

Use this path if you want the easiest repeatable setup. Docker Compose starts both services:

- FastAPI backend on `http://localhost:8000`
- Streamlit frontend on `http://localhost:18601`

Ollama is expected to run on your host machine, not inside Docker. If you use a different LLM provider such as OpenAI, Groq, Gemini, Anthropic, or Grok, you can skip the Ollama step and configure that provider in `.env` instead.

### 1. Start Ollama on the host

Skip this step if you are not using `LLM_PROVIDER=ollama`.

```bash
ollama serve
```

If the model is not installed yet:

```bash
ollama pull qwen2.5-coder:7b
```

### 2. Build and start Autonomous AI Engineer

From the project root:

```bash
docker compose build
docker compose up
```

Open the services:

- API health check: `http://localhost:8000/api/status`
- Streamlit UI: `http://localhost:18601`

The frontend container still runs Streamlit on port `8501` internally, but Docker exposes it on host port `18601` to avoid conflicts with locally running Streamlit apps or Windows-reserved ports.

### 3. Manual fixing without PR in Docker

Use this when you want Autonomous AI Engineer to fix code locally but you do not want it to push a branch or open a PR.

1. Open `http://localhost:18601`.
2. Paste the GitHub repository URL.
3. Describe the issue clearly.
4. Leave `Open a draft Pull Request if the fix succeeds` unchecked.
5. Click `Run AIDE`.
6. Review the plan, files, and diff in the UI.

### 4. Manual fixing with draft PR in Docker

Use this when you want to manually submit a problem from the UI and have AIDE open a draft PR after a successful fix.

1. Open `http://localhost:18601`.
2. Paste the GitHub repository URL.
3. Describe the issue clearly.
4. Check `Open a draft Pull Request if the fix succeeds`.
5. Confirm repository owner, repository name, and base branch.
6. Click `Run AIDE`.

This uses `GITHUB_TOKEN` from `.env` inside the API container. The token must have repository write permissions.

### 5. GitHub webhook automation with Docker

Use this when you want new GitHub issues to trigger AIDE automatically.

Keep Docker Compose running:

```bash
docker compose up
```

In another terminal, expose the API with a tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

Cloudflare will print a URL like:

```text
https://your-random-name.trycloudflare.com
```

Your GitHub webhook payload URL is:

```text
https://your-random-name.trycloudflare.com/api/webhook/github
```

In the target GitHub repository, go to `Settings -> Webhooks -> Add webhook` and use:

- Payload URL: `https://your-random-name.trycloudflare.com/api/webhook/github`
- Content type: `application/json`
- Secret: same value as `GITHUB_WEBHOOK_SECRET` in `.env`
- Events: select `Issues`
- Active: enabled

Then open a brand-new GitHub issue. Only newly opened issues trigger the current webhook flow.

Example issue:

- Title: `Fix syntax errors in helper.py`
- Body: `Only fix helper.py. There is a syntax error preventing execution.`

Expected result:

- AIDE comments that it started
- AIDE fixes the code
- AIDE opens a draft PR
- AIDE comments the PR link back on the issue

## Option 2: Run Without Docker

Use this path if you want to develop directly with Python and your local virtual environment.

### 1. Start Ollama

Skip this step if you are not using `LLM_PROVIDER=ollama`.

```bash
ollama serve
```

If the model is not installed yet:

```bash
ollama pull qwen2.5-coder:7b
```

### 2. Start the backend API

In one terminal:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Health check:

```text
http://localhost:8000/api/status
```

Expected response:

```json
{"status":"ok","service":"Autonomous AI Engineer","version":"1.0.0","active_jobs":0}
```

### 3. Start the Streamlit frontend

In another terminal:

```bash
streamlit run frontend/app.py
```

Open:

```text
http://localhost:8501
```

The frontend talks to the API at `http://localhost:8000` by default.

### 4. Manual fixing without PR without Docker

1. Open `http://localhost:8501`.
2. Paste the GitHub repository URL.
3. Describe the issue clearly.
4. Leave `Open a draft Pull Request if the fix succeeds` unchecked.
5. Click `Run AIDE`.
6. Review the local job output yourself.

### 5. Manual fixing with draft PR without Docker

1. Open `http://localhost:8501`.
2. Paste the GitHub repository URL.
3. Describe the issue clearly.
4. Check `Open a draft Pull Request if the fix succeeds`.
5. Confirm repository owner, repository name, and base branch.
6. Click `Run AIDE`.

This requires `GITHUB_TOKEN` in `.env` with repository write permissions.

### 6. GitHub webhook automation without Docker

Keep the backend API running:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

In another terminal, expose it with Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

Use the generated tunnel URL as your GitHub webhook payload URL with `/api/webhook/github` appended.

Example:

```text
https://your-random-name.trycloudflare.com/api/webhook/github
```

Then configure the GitHub webhook with:

- Content type: `application/json`
- Secret: same value as `GITHUB_WEBHOOK_SECRET` in `.env`
- Events: select `Issues`
- Active: enabled

Open a new GitHub issue to trigger AIDE.

## Future Improvements

- Multi-file reasoning improvements
- Better test generation
- CI/CD integration
- Performance optimization for large repos

## License

This project is licensed under the MIT License.
