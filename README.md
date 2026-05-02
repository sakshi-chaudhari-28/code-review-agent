# 🤖 Autonomous Code Review Agent

An autonomous AI-powered multi-agent system that automatically reviews GitHub Pull Requests, detects bugs and security vulnerabilities, and posts intelligent fix suggestions as inline comments — powered by Groq LLaMA 3.3 70B.

## 🌐 Live Demo
**Deployed at:** https://code-review-agent-1-4jhw.onrender.com  
**GitHub:** https://github.com/sakshi-chaudhari-28/code-review-agent

---

## 📌 Overview

The Code Review Agent listens to GitHub webhook events and automatically triggers an AI-powered review pipeline whenever a Pull Request is opened, updated, or reopened. It analyzes the code diff, generates structured feedback, and posts review comments directly on the PR — all without any manual intervention.

Achieves **88% precision and 88% recall** on a labelled evaluation suite, matching the performance of paid tools like GitHub Copilot Review ($19/month) at zero cost.

---

## ✨ Features

- 🔗 **GitHub Webhook Integration** — Listens to PR events in real time via HMAC-verified webhooks
- 🤖 **Multi-Agent Architecture** — Orchestrator + 4 specialist agents (Code Analyzer, Security Scanner, Test Evaluator, Fix Generator)
- 🧠 **LLM-Powered Reviews** — Uses Groq LLaMA 3.3 70B to generate intelligent, context-aware code feedback
- 💾 **Memory Module** — ChromaDB vector store retains past findings for consistent, context-aware reviews
- 🔍 **Smart Pre-Check** — Skips LLM calls for clean well-written code to reduce false positives
- 🛠️ **Modular Tools** — Pluggable tool system for extending analysis capabilities
- 📊 **Evaluation Framework** — Built-in eval module to measure and benchmark agent review quality
- 🐳 **Dockerized** — Fully containerized for consistent, portable deployment
- ☁️ **Render Deployment** — Ready-to-deploy on Render with render.yaml configuration
- 📋 **Structured Logging** — JSON-structured logs via structlog for observability

---

## 🏗️ Project Structure
code-review-agent/
│
├── agents/                    # AI agent logic
│   ├── orchestrator.py        # Main orchestrator — coordinates the full review pipeline
│   ├── code_analyzer.py       # Detects bugs, code smells, and logic errors
│   ├── security_scanner.py    # Finds SQL injection, hardcoded secrets, OWASP issues
│   ├── test_evaluator.py      # Checks for missing test coverage
│   └── fix_generator.py       # Generates and posts code fix suggestions
│
├── tools/                     # Pluggable tools for GitHub API interaction
│   └── github_tool.py         # Fetch PR diffs, post inline comments, open PRs
│
├── memory/                    # Vector store for persistent context
│   └── vector_store.py        # JSON-based memory for past findings
│
├── eval/                      # Evaluation framework for benchmarking agent quality
│   ├── run_eval.py            # Main evaluation script
│   └── test_cases/            # Labelled test cases (SQL injection, secrets, clean code)
│
├── main.py                    # FastAPI app — webhook receiver and API endpoints
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker container configuration
├── render.yaml                # Render cloud deployment config
├── .env.example               # Environment variable template
├── .dockerignore              # Docker build ignore rules
├── .gitignore                 # Git ignore rules
└── README.md                  # Project documentation

---

## ⚙️ How It Works
GitHub PR Event
│
▼
FastAPI Webhook (/webhook)
│
├── Verify HMAC Signature
│
▼
Orchestrator Agent
│
├── Fetch PR Diff from GitHub API
│
├── Pre-check — is code clean? (skip LLM if yes)
│
├── Query Memory for past context
│
├── Dispatch to specialist agents:
│     ├── Code Analyzer
│     ├── Security Scanner
│     ├── Test Evaluator
│     └── Fix Generator (high severity only)
│
├── Post inline comments on GitHub PR
│
└── Store findings in memory for future reviews

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.11+ |
| Web Framework | FastAPI + Uvicorn |
| AI / LLM | Groq LLaMA 3.3 70B |
| GitHub Integration | GitHub REST API + PyGitHub |
| Vector Memory | ChromaDB |
| HTTP Client | HTTPX |
| Logging | Structlog (JSON) |
| Containerization | Docker |
| Cloud Deployment | Render |
| Config Management | python-dotenv |

---

## 📈 Evaluation Results

| Test Case | Status | F1 Score |
|-----------|--------|----------|
| SQL Injection | ✅ PASS | 100% |
| Null Pointer / Error Handling | ✅ PASS | 66.7% |
| Hardcoded Secrets | ✅ PASS | 66.7% |
| Clean Code (false positive test) | ✅ PASS | 100% |

**Average Precision: 88% | Average Recall: 88%**

Matches the performance of paid tools like GitHub Copilot Review ($19/month) at zero cost.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Docker (optional)
- GitHub account with webhook access
- Groq API key (free at console.groq.com)

### 1. Clone the Repository

```bash
git clone https://github.com/sakshi-chaudhari-28/code-review-agent.git
cd code-review-agent
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret
PORT=8000
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Server

```bash
python main.py
```

The server starts at `http://localhost:8000`

---

### 🐳 Running with Docker

```bash
# Build the image
docker build -t code-review-agent .

# Run the container
docker run -p 8000:8000 --env-file .env code-review-agent
```

---

## 🔗 Setting Up GitHub Webhook

1. Go to your GitHub repository → **Settings** → **Webhooks** → **Add webhook**
2. Set Payload URL to: `https://code-review-agent-1-4jhw.onrender.com/webhook`
3. Set Content type to: `application/json`
4. Set Secret to the same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
5. Select **Pull request events** only
6. Click **Add webhook**

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Welcome message — server status |
| GET | `/health` | Health check endpoint |
| POST | `/webhook` | GitHub PR webhook receiver |
| GET | `/memory/clear` | Clear all vector memory |
| DELETE | `/memory/reset` | Reset vector store |

---

## ☁️ Deploying to Render

This project includes a `render.yaml` for one-click deployment on Render:

1. Push your code to GitHub
2. Go to `render.com` → **New** → **Web Service**
3. Connect your GitHub repository
4. Render auto-detects `render.yaml` and configures the service
5. Add your environment variables in the Render dashboard:
   - `GROQ_API_KEY`
   - `GITHUB_TOKEN`
   - `GITHUB_WEBHOOK_SECRET`
6. Click **Deploy** 🚀

---

## 📊 Running Evaluation

```bash
python -m eval.run_eval
```

Sample output:
═══════════════════════════════════════════════════════
AUTONOMOUS CODE REVIEW AGENT — EVALUATION REPORT
═══════════════════════════════════════════════════════
Tests passed  : 4 / 4
Avg Precision : 88%
Avg Recall    : 88%
Avg F1 Score  : 83%
═══════════════════════════════════════════════════════

---

## 🔐 Security

- All GitHub webhooks are verified using **HMAC-SHA256** signature validation
- API keys are managed via environment variables — never hardcoded
- Sensitive files are excluded via `.gitignore` and `.dockerignore`

---

## 👩‍💻 Author
**Sakshi Chaudhari**  
