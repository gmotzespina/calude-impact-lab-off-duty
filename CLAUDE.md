# CLAUDE.md — Claude Code Instructions for Off-Duty

This file configures **Claude Code** (`claude`) to both maintain the **Off-Duty** codebase and act as a burnout-aware pair programmer that integrates with the local Off-Duty engine (`http://127.0.0.1:5050`).

---

## 1. Quick Commands

```bash
# Run the Off-Duty server (works with Flask or stdlib fallback on port 5050)
python3 app.py

# Run end-to-end API smoke test
python3 -c "import app; c = app.app.test_client(); assert c.get('/').status_code == 200; assert c.get('/api/telemetry').status_code == 200; print('OK')"
```

---

## 2. How Claude Code Should Interact With Off-Duty For the User

1. **On Session Start — Check `TOMORROW.md` First:**
   - Before asking the user *"What would you like to work on?"*, check if `./TOMORROW.md` exists in the working directory.
   - If `./TOMORROW.md` exists, read it silently to restore the user's parked git branch, uncommitted file list, and **9:00 AM First Step**.
2. **When the User Says "Park this" / "Save my spot" / "I'm stopping for tonight":**
   - Do **not** ask the user to write a summary.
   - Call the local Off-Duty shutdown or park endpoint directly:
     - **Park single repo:** `curl -s -X POST http://127.0.0.1:5050/api/park-context -H "Content-Type: application/json" -d "{\"repo_path\": \"$(pwd)\"}"`
     - **Full evening shutdown:** `curl -s -X POST http://127.0.0.1:5050/api/shutdown -H "Content-Type: application/json" -d '{"pause_agents": false}'` *(Note: pass `"pause_agents": false` if calling from inside your own Claude process so you don't `SIGSTOP` yourself before printing the confirmation!)*
3. **Respect Circadian & Break Boundaries:**
   - Query `curl -s http://127.0.0.1:5050/api/telemetry` when starting long tasks. If `break_due` is `true`, suggest the user click **Card #1 (Take a Bio-Reset now)** for a 5-minute non-repeating physical reset (`water`, `posture`, `mobility`, `breathwork`) while you finish running commands.

---

## 3. Engineering Rules When Editing This Repo

- **Zero Fake/Mocked Data:** Every number displayed in the UI must originate from real macOS telemetry in [`app.py`](./app.py):
  - Hardware idle time: `ioreg -c IOHIDSystem` (`HIDIdleTime` nanoseconds → seconds)
  - 7-day circadian window: `pmset -g log`, `~/.zsh_history`, `~/.bash_history`, `~/.claude`, and `git log --since="7 days ago"`
  - Open code loops: `git status --porcelain`, `git diff -U1`, `git log -1 --oneline`
- **Sub-30ms Responsiveness:** Preserve `_SNAPSHOT_CACHE` and `iter_shallow_files()` in [`app.py`](./app.py) so directory scans never traverse `node_modules` or `.venv`.
- **Calm Editorial UI:** In [`templates/index.html`](./templates/index.html), maintain the 4-card top row (`#EDEAE2` background, `#F9F7F2` cards, 5px colored top bars in Terracotta `#D46A43`, Periwinkle `#7C72B8`, Sage `#578E7E`, and Charcoal `#191918`). Never add pop-up forms, chat widgets, or text walls inside the 5-minute break overlay.
