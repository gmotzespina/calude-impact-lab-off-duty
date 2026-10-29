# AGENTS.md — Instructions for AI Coding Agents Working With Off-Duty

> **Core Rule:** Off-Duty exists to **give engineers and knowledge workers time and attention back** from AI compression burnout. Never add prompts, questionnaires, or mocked telemetry.

---

## 1. How AI Agents Should Use Off-Duty During a Coding Session

If the Off-Duty server is running locally (`http://127.0.0.1:5050`), you can query and trigger it directly via `curl` so the human never has to context-switch or type status notes:

### A. Morning Startup / Session Resume (Read Before Asking the User What to Do)
1. Check if `./TOMORROW.md` or `~/Desktop/TOMORROW.md` exists.
2. If present, read `TOMORROW.md` first to see the user's parked repositories, active branch, uncommitted files, and **9:00 AM Immediate Action**—then offer to pick up right where they left off without making them re-explain context.
3. To unpack parked workstreams and resume any `SIGSTOP`-paused agent processes:
   ```bash
   curl -s -X POST http://127.0.0.1:5050/api/resume-morning
   ```

### B. Check the User's Live Burnout & Juggling Telemetry
Before starting a large multi-file refactor after hours or during a long streak, you can inspect the host's live cognitive and circadian load:
```bash
curl -s http://127.0.0.1:5050/api/telemetry
```
- If `break_due` is `true` (`continuous_work_minutes >= break_interval_minutes`), gently remind the user they can take a 5-minute bio-reset while you run tests or background tasks.
- If `curfew_status.in_curfew_window` is `true` (past 8:00 PM or before 6:00 AM), offer to park the current repo to `TOMORROW.md` so they can rest.

### C. Park Current Repo Context ("Save My Spot")
When the user says *"save my spot"*, *"park this repo"*, or switches to another task:
```bash
curl -s -X POST http://127.0.0.1:5050/api/park-context \
  -H "Content-Type: application/json" \
  -d "{\"repo_path\": \"$(pwd)\", \"unpark\": false}"
```

### D. Trigger a 5-Minute Bio-Reset
When the user says *"I need a break"*:
```bash
curl -s -X POST http://127.0.0.1:5050/api/trigger-break \
  -H "Content-Type: application/json" \
  -d '{"sleep_display": false}'
```

### E. Execute Full Evening Shutdown
When the user says *"I'm done for today"*, *"shut down"*, or *"wrap up for tomorrow"*:
```bash
curl -s -X POST http://127.0.0.1:5050/api/shutdown \
  -H "Content-Type: application/json" \
  -d '{"pause_agents": true, "sleep_display": false}'
```

---

## 2. Codebase Architecture & Development Guardrails

- **[`app.py`](./app.py):** Single-file Python backend (Flask with a built-in `ThreadingHTTPServer` stdlib fallback so `python3 app.py` runs even before `pip install flask`).
  - **Zero Mocks Policy:** All metrics must come from real host macOS commands (`ioreg -c IOHIDSystem`, `pmset -g log`, `~/.zsh_history`, `~/.claude`, `pgrep -fl claude`, and `git status`/`git diff`/`git log`).
  - **Performance Policy:** Never use unbounded `rglob("*")` on user directories. Always use `iter_shallow_files()` (which skips `node_modules`, `.venv`, `.git`, `dist`, `build`) and `_SNAPSHOT_CACHE` so `/api/telemetry` responds in `< 30ms`.
- **[`templates/index.html`](./templates/index.html):** Single-file Vanilla JS + Tailwind CSS editorial UI.
  - Warm stone aesthetic (`#EDEAE2` canvas, `#F9F7F2` cards, `Newsreader` display serif numerals, `Plus Jakarta Sans` body).
  - Keep the 4 top cards clean and keep advanced settings / raw telemetry inside progressive-disclosure drawers.
- **Persistent State:** Stored in `~/.offduty_state.json` (with fallback to `./.offduty_state.json`).
