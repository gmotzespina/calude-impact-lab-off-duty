# GEMINI.md — Gemini & Antigravity Agent Instructions for Off-Duty

This document guides **Gemini / Antigravity** agents on how to operate, extend, and integrate with **Off-Duty (AI Context Decompression & Bio-Boundary Engine)**.

---

## 1. Project Purpose & Philosophy

**Off-Duty** solves **AI compression burnout** for engineers and knowledge workers.
- **Why Screen-Time Blockers Fail Engineers:** Apps like Jomo or macOS Screen Time only measure *hours* and block the screen mid-thought, causing open-loop anxiety (*Zeigarnik effect*) when uncommitted code and AI sessions are left hanging.
- **How Off-Duty Works:** It reads live macOS hardware idle state (`ioreg`), 7-day power/shell/agent logs (`pmset`, `~/.zsh_history`, `~/.claude`), and open `.git` working trees to:
  1. Guide a **5-minute non-repeating physical Bio-Reset** every 60 minutes (Card #1).
  2. Extract live **Open Code Loops** (uncommitted files + code diff previews + 9:00 AM resume commands) so users can **Save Their Spot (`TOMORROW.md`)** and close tabs safely.
  3. Execute a **1-Click Evening Shutdown** that writes `TOMORROW.md`, pauses background CLI agents (`SIGSTOP`), and locks the workspace until 6:00 AM, paired with a **1-Click Morning Resume (`POST /api/open-workspace` & `POST /api/resume-morning`)** that reopens the user's editor (`Cursor` / `VS Code`) directly to the file they were editing.

---

## 2. API Reference for Agent Automation (`http://127.0.0.1:5050`)

Agents can interact with the running Off-Duty server on behalf of the user:

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/api/telemetry` | `GET` | Returns live `idle_seconds`, `continuous_work_minutes`, `next_protocol`, `juggling_metrics` (open repos, uncommitted files, live `diff_preview`), `circadian_audit`, and `saved_breadcrumb`. Pass `?force=1` to bypass the 8s/60s cache. |
| `/api/trigger-break` | `POST` | Resets the continuous work streak, increments `breaks_taken_today`, and advances `last_protocol_id` to return the next non-repeating physiological activity (`water`, `posture`, `mobility`, `breathwork`). Pass `{"rotate_only": true}` to cycle the activity without resetting the timer. |
| `/api/park-context` | `POST` | Marks a repo path as parked (`{"repo_path": "/path/to/repo", "unpark": false}`) and immediately syncs `./TOMORROW.md` on disk. |
| `/api/open-workspace` | `POST` | Opens `{"repo_path": "...", "latest_file": "..."}` in `Cursor`, `VS Code`, or macOS Finder and unparks the workstream. |
| `/api/notify` | `POST` | Fires a native macOS Notification banner via `osascript` with the next queued break activity. |
| `/api/shutdown` | `POST` | Parks all active repos, writes `./TOMORROW.md` and `~/Desktop/TOMORROW.md`, generates executable `./morning_resume.sh`, optionally sends `SIGSTOP` to `claude` PIDs, and returns the "Time & Attention Returned" receipt. |
| `/api/resume-morning` | `POST` | Sends `SIGCONT` to paused agent PIDs, clears parked flags, and returns the primary terminal resume command. |

---

## 3. Key Implementation Files

- [`app.py`](./app.py) — Backend telemetry & shutdown engine (Flask + zero-dependency stdlib `ThreadingHTTPServer` fallback + background 60-minute macOS notification daemon).
- [`templates/index.html`](./templates/index.html) — Single-file frontend (Tailwind CSS + Vanilla JS, editorial 4-card layout + Open Loops board + Bio-Reset & Curfew overlays).
- [`README.md`](./README.md) — Quickstart & overview.
