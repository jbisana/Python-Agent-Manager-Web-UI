# Python Script Manager

A professional-grade, real-time dashboard for managing, monitoring, and automating the execution of Python scripts (agents).

![Python Script Manager](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-green?style=for-the-badge&logo=flask)
![APScheduler](https://img.shields.io/badge/Automation-APScheduler-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

## Overview

Python Script Manager provides a modular web interface to manage a fleet of Python agents. It features automated script discovery, real-time log streaming, advanced scheduling, and deep execution analytics.

Designed for operational reliability, it uses a clean architecture with a persistent SQLite backend to ensure your automation workflows remain observable and recoverable.

<img width="1274" height="972" alt="Untitled picture" src="https://github.com/user-attachments/assets/77dfcc60-fe0e-4aa5-b872-324e16040741" />

## 🚀 Key Features

- **Automated Script Discovery**: Drop any `.py` file into the `tasks/` directory, and it appears on your dashboard instantly.
- **Advanced Automation**:
    - **Interval & Cron Scheduling**: Full support for interval-based or complex cron expressions.
    - **Dynamic Toggles**: Enable or disable schedules at runtime without code changes.
    - **One-Click Execution**: Manually trigger or stop agents directly from the UI.
- **Real-time Observability**:
    - **Live Log Streaming**: Uses Server-Sent Events (SSE) to stream output directly to the browser.
    - **Resource Telemetry**: Live **CPU %** and **Memory (MB)** tracking for running agents via `psutil`.
- **Isolation & Integration**:
    - **Virtual Environment (vEnv) Isolation**: Run specific agents in their own isolated virtual environments.
    - **Lifecycle Webhooks**: Trigger POST notifications to custom URLs (Slack/Discord) on completion or failure.
    - **Git Integration**: Pull updates and reload tasks/metadata directly from the dashboard.
- **Deep Analytics & History**: 
    - **Execution Stats**: Track total runs, average duration, max duration, and error rates per script.
    - **History Management**: Clear execution history to reset agent status to IDLE.
    - **Persistent Logs**: All output is stored on disk and indexed in **SQLite**.

## 📖 Documentation

- [**GEMINI.md**](GEMINI.md): Behavioral guidelines for coding and maintaining the project (simplicity, surgical changes).
- [**AGENTS.md**](AGENTS.md): Senior-level implementation patterns for developing robust agents (SIGTERM handling, shared state).

## 🛡️ Security & Reliability

1.  **CSRF Protection**: State-mutating requests are protected by server-issued tokens.
2.  **Rate Limiting**: Integrated protection against automated trigger abuse.
3.  **Strict CSP**: Content Security Policy headers prevent XSS and injection attacks.
4.  **Restart-Safe Recovery**: Reconciles state on startup, ensuring "orphaned" tasks are correctly logged.

## 🛠️ Getting Started

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/python-script-manager.git
cd python-script-manager
pip install -r requirements.txt
```

### 2. Configure Your Agents
Define schedules, venvs, and webhooks in `script_meta.json`:
```json
{
  "scrapper_agent": {
    "display_name": "Web Scraper",
    "schedule": "cron:0 */2 * * *",
    "venv_path": "/opt/venvs/scraper",
    "webhook_url": "https://hooks.slack.com/services/...",
    "timeout": 300,
    "env": { "API_KEY": "secret_val" }
  }
}
```

### 3. Run
```bash
python app.py
```
Access the dashboard at `http://127.0.0.1:5000`.

## 📂 Project Structure

```text
├── app.py              # Flask entry point & API routes
├── runner.py           # Process management & resource telemetry
├── scheduler.py        # APScheduler orchestration
├── database.py         # SQLite persistence layer
├── models.py           # Typed DataClasses (Metadata, State)
├── config.py           # Centralized configuration
├── utils.py            # Discovery & helper functions
├── static/
│   └── index.html      # Real-time Vanilla JS Dashboard
├── tasks/              # Your Python agents
└── run_logs/           # Persistent log storage
```

## 📜 License

This project is licensed under the MIT License.
