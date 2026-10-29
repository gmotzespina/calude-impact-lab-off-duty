# Off-Duty — Bio-Boundary & Shutdown Engine

> **For Engineers & Knowledge Workers:** Off-Duty eases **AI compression burnout** by fusing **Official Idea #1 (A Workload Tracker)** and **Official Idea #3 (A Shutdown Command)** with science-backed physiological recovery and circadian boundaries.

---

## Why Off-Duty Exists (The Compression Burnout Problem)

AI coding agents and parallel workflows eliminate natural cognitive pauses. Instead of waiting for builds or searching documentation, engineers now context-switch across multiple repositories and agent sessions simultaneously—frequently bleeding past **8:00 PM**, starting before **6:00 AM**, and working through **weekends**.

**Off-Duty** obeys the event's One Rule: *"It has to give people time back, not help them do even more."*
- **Zero Prompts / Zero New Work:** It never asks you to type status updates or fill out journals.
- **100% Real Host Telemetry:** On first launch, it inspects your Mac's hardware idle timer, power logs, shell history, active `.git` repositories, and `~/.claude` sessions with zero mocked data.
- **Gives Time & Attention Back:** It offloads your working memory automatically into a cognitive breadcrumb, guides 5-minute physiological resets, and executes a one-click evening shutdown that writes `TOMORROW.md`, pauses active AI agents (`SIGSTOP`), and locks your workspace until 6:00 AM.

---

## 30-Second Quickstart (macOS)

```bash
python3 -m venv venv && source venv/bin/activate
pip install flask
python3 app.py
```

Then open **http://127.0.0.1:5050** in your browser.

---

## How It Works End-to-End (Zero Mocks)

### 1. Live Workload & 7-Day Circadian Audit (Official Idea #1)
- **Hardware Idle & Continuous Streak (`ioreg -c IOHIDSystem`):** Reads macOS `HIDIdleTime` in nanoseconds and tracks your continuous active work streak in `~/.offduty_state.json` (resetting only when you step away for $\ge 300$ seconds or trigger a reset).
- **Juggling & Context-Switching Load:** Scans your workspace and parent directories for `.git` repositories modified today (`git status --porcelain`, `git log --since="24 hours ago"`) and counts today's session turns in `~/.claude`.
- **7-Day Circadian & Weekend Audit:** Parses macOS power management logs (`pmset -g log`), shell history timestamps (`~/.zsh_history`, `~/.bash_history`), `~/.claude` logs, and git commit timestamps over the past 7 days to flag **Pre-6:00 AM starts**, **Post-8:00 PM nights**, and **Weekend work sessions**.

### 2. Zero-Prompt Cognitive Breadcrumb + 5-Minute Science Reset
- Clicking **"Take 5-Min Science Reset Now"** automatically snapshots your active branch, uncommitted files, and latest commit into a visible **Cognitive Breadcrumb** so you can let go of your train of thought immediately.
- Launches a calm full-screen 5:00 countdown featuring your enabled physiological protocols:
  - **Hydration & Osmotic Reset:** 300ml water to prevent mild dehydration-induced prefrontal fatigue.
  - **Posture Switch & Hip Unloading:** Half-kneeling couch stretch to reverse iliopsoas shortening.
  - **Thoracic Extension & Scapular Unloading:** C7–T12 open-book rotations and wall slides.
  - **20-20-20 Visual Reset + Physiological Sigh:** 20-foot gaze to relax ciliary muscle spasm + Huberman double-inhale + extended exhale to activate parasympathetic vagal tone.
- Includes a one-click hardware screen sleep action (`pmset displaysleepnow`).

### 3. The One-Click Evening Shutdown Command (Official Idea #3)
- Clicking **"Execute Evening Shutdown (Write TOMORROW.md & Lock)"** (or working past your 8:00 PM curfew in Hard-Core Mode):
  1. Writes a real **`TOMORROW.md`** file in the project root (and `~/Desktop/TOMORROW.md`) containing your shutdown timestamp, hours reclaimed, open `.git` status (`git diff --stat`), and the concrete first file to open at 9:00 AM tomorrow.
  2. Detects running `claude` CLI agent processes (`pgrep -fl claude`), pauses them safely with `SIGSTOP`, and generates an executable **`morning_resume.sh`** (`SIGCONT`) so agents stop spinning overnight.
  3. Engages the **Full-Screen Hard-Core Curfew Overlay** with a live countdown until 6:00 AM tomorrow.

---

## Project Structure

```text
.
├── app.py                 # Flask backend + real macOS telemetry & shutdown engine
├── templates/
│   └── index.html         # Single-file Vanilla JS + Tailwind editorial UI
├── requirements.txt       # Lightweight dependency (Flask>=3.0.0)
└── README.md              # Documentation & 3-command quickstart
```
