# Off-Duty — AI Context Decompression & Bio-Boundary Engine

> **For Engineers & Knowledge Workers:** Screen blockers only track hours. **Off-Duty** cures **AI compression burnout** by fusing **Official Idea #1 (A Live Workload & Open-Loop Tracker)** and **Official Idea #3 (A One-Click Evening Shutdown Command)**—parking your open Git diffs and Claude loops to disk so your brain can actually let go.

---

## Why Off-Duty Exists (The AI Compression Problem)

AI coding agents and parallel workflows eliminated natural cognitive pauses (waiting for builds, searching docs). Engineers now context-switch across multiple repositories and Claude sessions simultaneously—frequently bleeding past **8:00 PM**, starting before **6:00 AM**, and working through **weekends**. Traditional screen blockers fail because locking a screen while 14 uncommitted files sit in working memory triggers anxiety rather than rest.

**Off-Duty** obeys the event's One Rule: *"It has to give people time back, not help them do even more."*
- **Zero Prompts / Zero New Work:** Never asks you to type status updates, fill out journals, or maintain timers.
- **100% Real macOS Host Telemetry:** On launch, inspects your Mac's hardware idle timer (`IOHIDSystem`), power logs (`pmset`), shell history, active `.git` repositories (`~/Dev`, `~/Projects`, `~/Code`, `~/Desktop`), and `~/.claude` sessions with zero mocked data.
- **Active Context Decompression:** Parks individual open workstreams (or your entire workday) into a live `TOMORROW.md` handoff file with 1-click resume in **Cursor / VS Code**, guides single-activity 5-minute physiological resets, pauses spinning Claude agents (`SIGSTOP`), and enforces an overnight circadian curfew until **6:00 AM**.

---

## 30-Second Quickstart (macOS)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

*(Note: `app.py` also includes a built-in zero-dependency stdlib `ThreadingHTTPServer` fallback if run directly with system `python3 app.py` before installing Flask.)*

- **Live Dashboard:** Open **http://127.0.0.1:5050**
- **5-Slide User Journey Pitch Deck:** Open **http://127.0.0.1:5050/slides#1** (click left/right sides of the screen, use the `←` / `→` buttons, or press Left/Right arrow keys to navigate `#1` through `#5`)

---

## 5-Slide User Journey Pitch (`/slides#1` → `/slides#5`)

Visit **http://127.0.0.1:5050/slides#1** (or click **`📽️ 5-Slide Pitch →`** in the dashboard header) to walk through the 5-slide narrative user journey:

1. **`#1` • 07:45 PM — The AI Compression Trap:** Why hours-only screen timers fail when parallel Git repos and Claude loops stay stuck in working memory.
2. **`#2` • 03:15 PM — Zero-Prompt Live Telemetry (Official Idea #1):** Real-time macOS hardware idle (`HIDIdleTime`), multi-repo uncommitted `git diff -U1` scanner, `~/.claude` session counter, and 7-day circadian audit.
3. **`#3` • 03:20 PM — 1-Click Spot Save & 5-Min Bio-Reset:** Snapshots a 1-line Cognitive Breadcrumb (`✓ Spot Saved`) and presents **1 single non-repeating physical protocol** per break with 1-click display sleep (`pmset displaysleepnow`).
4. **`#4` • 08:00 PM — The Evening Shutdown Command (Official Idea #3):** Atomic 1-click shutdown that writes `TOMORROW.md`, suspends live `claude` CLI PIDs via `SIGSTOP`, generates `./morning_resume.sh`, and engages the 6:00 AM curfew lockout.
5. **`#5` • 09:00 AM — 10-Second Morning Unpack:** Wakes paused agents (`SIGCONT`), opens the exact last-edited file in Cursor/VS Code, and returns **10h/night** of protected sleep plus **~23m/repo** of morning ramp-up time.

---

## How It Works End-to-End (Zero Mocks)

### 1. Live Workload, Open Code Loops & 7-Day Circadian Audit (Official Idea #1)
- **Hardware Idle & Continuous Streak (`ioreg -c IOHIDSystem`):** Reads macOS `HIDIdleTime` in nanoseconds and tracks your continuous active work streak in `~/.offduty_state.json` (resetting only when you step away for $\ge 300$ seconds or trigger a bio-reset).
- **Open Loops Board ("Open Loops Holding Your Brain Hostage"):** Scans your workspace and common macOS dev directories for `.git` repositories modified today (`git status --porcelain`, `git diff -U1`, `git log --since="24 hours ago"`) and counts today's session turns and live PIDs in `~/.claude` (`pgrep -fl claude`).
- **1-Click Per-Repo Spot Parking (`/api/park-context`):** Click **`📌 Save My Spot (Close Tab Safely)`** on any active repo to snapshot its branch, uncommitted file list, diff preview, and 9:00 AM resume command directly into `TOMORROW.md` (+23 mins working memory saved per repo).
- **7-Day Circadian & Weekend Audit:** Parses macOS power management logs (`pmset -g log`), shell history timestamps (`~/.zsh_history`, `~/.bash_history`, `~/.zsh_sessions`), `~/.claude` logs, and git commit timestamps over the past 7 days to flag **Pre-6:00 AM starts**, **Post-8:00 PM nights**, and **Weekend work sessions** (with sub-15ms cached polling).

### 2. Zero-Prompt Cognitive Breadcrumb + Single-Activity 5-Minute Bio-Reset
- **Automatic 60-Minute Background Watcher & Native Alerts:** A background thread monitors your continuous active streak every 60 seconds and triggers a native macOS notification (`osascript`) and browser `Notification` when a break is due (testable anytime via **`🔔 Test 60m Alert`**).
- **1-Line Cognitive Breadcrumb:** Clicking **`Start 5-Min Bio-Reset`** automatically snapshots your active branch, uncommitted files, and latest commit so you can drop your train of thought immediately.
- **Single Rotating Science Protocol (No Repeats):** Launches a clean full-screen `05:00` countdown featuring **one** rotating protocol at a time (with a `↻ Try next activity` button):
  1. **💧 Hydration Reset (1 min):** Full glass of water standing to reverse 1% dehydration prefrontal fatigue.
  2. **🧍 Posture & Hip Unload (90 sec):** Half-kneeling hip flexor stretch to reverse sitting-induced iliopsoas shortening.
  3. **🔄 Thoracic Spine Release (90 sec):** Open-book upper-back extensions to unload 45 lbs of forward-head neck tension.
  4. **🌬️ 20-20-20 + Physiological Sigh (1 min):** 20-foot gaze to relax ciliary muscle spasm + double-inhales with slow mouth exhales to activate vagal tone.
- **Hardware Display Sleep:** One-click `pmset displaysleepnow` action to physically darken the Mac screen.

### 3. The One-Click Evening Shutdown Command & Morning Unpack (Official Idea #3)
- Clicking **`End Workday: Park All, Pause Claude & Lock`** (`/api/shutdown`):
  1. Writes a real **`TOMORROW.md`** file in the project root (and `~/Desktop/TOMORROW.md`) containing your shutdown timestamp, hours protected, open `.git` status (`git diff --stat`), and the concrete first file to open at 9:00 AM tomorrow.
  2. Detects running `claude` CLI agent processes (`pgrep -fl claude`), pauses them safely with `SIGSTOP`, and generates executable **`morning_resume.sh`** and **`resume_agents.sh`** (`SIGCONT`) scripts.
  3. Engages the **Full-Screen Hard-Core Curfew Lockout Overlay** with a live countdown until 06:00 AM and a *"Time & Attention Returned To You"* receipt.
- **☀ Morning Unpack (`/api/resume-morning` & `/api/open-workspace`):** Next morning, one click sends `SIGCONT` to paused agents, copies your primary resume command, or opens your parked repository and latest file directly in **Cursor** or **VS Code**.

---

## Project Structure

```text
.
├── app.py                 # Flask backend + macOS telemetry, notifier & shutdown engine
├── templates/
│   ├── index.html         # Main dashboard (4 telemetry cards, Open Loops board, overlays)
│   └── slides.html        # 5-slide User Journey pitch deck (/slides#1 .. /slides#5)
├── TOMORROW.md            # Live auto-generated morning handoff & parked workstreams
├── morning_resume.sh      # Auto-generated executable script to SIGCONT paused Claude PIDs
├── resume_agents.sh       # Alias resume script generated on evening shutdown
├── requirements.txt       # Lightweight dependency (Flask>=3.0.0)
└── README.md              # Documentation & quickstart
```
