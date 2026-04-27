# Python Script Manager

A professional-grade, real-time dashboard for managing, monitoring, and automating the execution of Python scripts (agents).

![Python Script Manager](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-green?style=for-the-badge&logo=flask)
![APScheduler](https://img.shields.io/badge/Automation-APScheduler-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

## Overview

Python Script Manager provides a modular web interface to manage a fleet of Python agents. It features automated script discovery, real-time log streaming, advanced scheduling, and deep execution analytics.

Designed for operational reliability, it uses a clean architecture with a persistent SQLite backend to ensure your automation workflows remain observable and recoverable.

## Key Features

- **Automated Script Discovery**: Drop any `.py` file into the `tasks/` directory, and it appears on your dashboard instantly.
- **Advanced Automation**:
    - **Interval Scheduling**: Run scripts every X minutes/hours.
    - **Cron Scheduling**: Full cron expression support for complex schedules.
    - **Dynamic Toggles**: Enable or disable schedules at runtime without code changes.
    - **Re-run Support**: One-click re-triggering of finished or failed scripts directly from the dashboard.
- **Real-time Observability**:
    - **Live Log Streaming**: Uses Server-Sent Events (SSE) to stream output directly to the browser.
    - **Live Timers**: Track execution duration in real-time.
- **Deep Analytics & History**: 
    - **Execution Stats**: Track total runs, average duration, max duration, and error rates per script.
    - **Full Audit Trail**: Persistent log files stored on disk (`run_logs/`) and history in **SQLite**.
    - **Run Details**: Detailed drawer showing configuration, environment variables, and last 20 execution logs.

- **Clean UX**:
    - **Search & Filtering**: Quickly find agents by name, description, or category.
    - **Categorical Grouping**: Toggle between a Kanban board and a grouped list view.
    - **Mobile-Responsive**: Optimized for monitoring on the go.

## Security & Reliability

The application implements:

1.  **CSRF Protection**: State-mutating requests are protected by server-issued tokens.
2.  **Rate Limiting**: Integrated protection against automated trigger abuse.
3.  **Strict CSP**: Content Security Policy headers prevent XSS and injection attacks.
4.  **Isolate Execution**: Scripts are executed in their own process with configurable timeouts and resource cleanup.
5.  **Restart-Safe Recovery**: Reconciles state on startup, ensuring "orphaned" tasks are correctly logged.

## Tech Stack

- **Backend**: Python 3.10+, Flask 3.0, APScheduler.
- **Database**: SQLite.
- **Frontend**: Vanilla HTML5/CSS3/JS with a focus on high-performance DOM manipulation.
- **Communication**: Server-Sent Events (SSE).

## Getting Started

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/python-script-manager.git
cd python-script-manager
pip install -r requirements.txt
```

### 2. Configure Your Agents
Add metadata to `script_meta.json` to define schedules and custom parameters:
```json
{
  "report_bot": {
    "display_name": "Daily Reporter",
    "schedule": "cron:0 9 * * *",
    "timeout": 300,
    "env": { "DB_URL": "..." }
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
├── runner.py           # Process management & lifecycle logic
├── scheduler.py        # APScheduler orchestration
├── database.py         # SQLite persistence layer
├── models.py           # Typed DataClasses & Enums
├── config.py           # Centralized configuration
├── utils.py            # Discovery & helper functions
├── static/
│   └── index.html      # Real-time UI
├── tasks/              # Your Python scripts (agents)
└── run_logs/           # Persistent log storage
```

## 📜 License

This project is licensed under the MIT License.
