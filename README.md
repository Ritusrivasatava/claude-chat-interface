# Claude Chat UI

A secure, locally-hosted web interface for Claude AI models, designed to mimic the Claude.ai experience with persistent chat history, multi-model support, and file upload capabilities. Communicates directly with the Anthropic Claude API.

Unlike cloud-hosted chat interfaces, **your conversation history never leaves your machine** — it is stored in a local SQLite database that no third party can access. The underlying LLM does not retain or log user data between requests, meaning this self-hosted setup gives you a significantly more private and secure way to interact with AI models compared to using a company-operated chat platform.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Option A — Docker (Recommended)](#option-a--docker-recommended)
- [Option B — Local Python](#option-b--local-python)
- [Using the App](#using-the-app)
- [Data & Backups](#data--backups)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Only for local dev (Option B) |
| Docker Desktop | Latest | Required for Option A |
| Anthropic API Key | — | Direct API key from [console.anthropic.com](https://console.anthropic.com) |

---

## Project Structure

```
claude-chat-interface/
├── streamlit_claude_app.py   # Main UI — Streamlit interface, CSS, session state
├── claude_client.py          # ClaudeClient — Anthropic API client
├── chat_history.py           # ChatHistoryManager — SQLite-backed persistence
├── requirements_claude.txt   # Python dependencies
├── Dockerfile                # Container image definition
├── docker-compose.yml        # Multi-container orchestration
├── docker_helper.sh          # Convenience wrapper around docker compose
└── .env                      # Your secrets & config (create this — see below)
```

---

## Configuration

Create a `.env` file in the project root. This file is loaded by both the local dev server and the Docker container.

```bash
# .env

# Required — your Anthropic API key from console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...

# Optional — default model on startup
# Options: claude-sonnet-latest, claude-opus-latest, claude-haiku-latest
MODEL_NAME=claude-sonnet-latest
```

> The `.env` file is mounted read-only into the Docker container and is never copied into the image. Keep it out of version control.

---

## Docker based deployment

This is the simplest way to run the app. Docker handles all dependencies and data persistence.

### 1. Ensure Docker Desktop is running

```bash
docker info
```

### 2. Create your `.env` file

See [Configuration](#configuration) above.

### 3. Make the helper script executable (first time only)

```bash
chmod +x docker_helper.sh
```

### 4. Build and start

```bash
./docker_helper.sh up
```

This builds the image and starts the container in the background. On first run the image build takes 1–2 minutes.

### 5. Open the app

Navigate to **http://localhost:8501** in your browser.

### Common Docker commands

| Command | Description |
|---|---|
| `./docker_helper.sh up` | Build (if needed) and start |
| `./docker_helper.sh down` | Stop the container |
| `./docker_helper.sh restart` | Restart without rebuilding |
| `./docker_helper.sh rebuild` | Force a clean image rebuild |
| `./docker_helper.sh logs` | Tail live logs |
| `./docker_helper.sh status` | Show container health |
| `./docker_helper.sh test` | Run HTTP health check |
| `./docker_helper.sh stats` | Show CPU/memory usage |
| `./docker_helper.sh shell` | Open a shell inside the container |


---

## Using the App

- **New Chat** — Click "＋ New Chat" in the sidebar to start a fresh conversation.
- **Model selector** — Switch between Claude Sonnet, Opus, and Haiku from the sidebar dropdown.
- **File uploads** — Attach images or text files to any message using the upload button.
- **Chat history** — All sessions are persisted to SQLite. Previous chats appear in the sidebar grouped by date.
- **Delete a chat** — Click the ✕ icon next to a session and confirm.

---

## Data & Backups

Chat history is stored in a SQLite database (`data/chat.db`).

- **Docker**: data lives in the named Docker volume `claude_data`, which survives container restarts and rebuilds.
- **Local dev**: data lives in `./data/chat.db` relative to the project root.

### Backup

```bash
./docker_helper.sh backup
# Creates ./backups/<timestamp>.tar.gz
```

### Restore

```bash
./docker_helper.sh restore ./backups/claude_data_20260101_120000.tar.gz
```

### ⚠ Delete all data

```bash
./docker_helper.sh clean
# Removes containers AND the claude_data volume — this is irreversible
```

---

## Troubleshooting

### App shows "ANTHROPIC_API_KEY not found"
Ensure `.env` exists in the project root and contains `ANTHROPIC_API_KEY=...`. For Docker, verify the `env_file` path in `docker-compose.yml` is correct.

### Cannot connect to the Anthropic API
- Confirm your API key is valid and has sufficient credits at [console.anthropic.com](https://console.anthropic.com).
- Check that outbound HTTPS traffic to `api.anthropic.com` is not blocked by a firewall or corporate proxy.

### Port 8501 already in use
Either stop the conflicting process or change the host port in `docker-compose.yml`:
```yaml
ports:
  - "8502:8501"   # map container port 8501 to host port 8502
```
Then access the app at **http://localhost:8502**.

### Container exits immediately
Check logs for the error:
```bash
./docker_helper.sh logs
```

