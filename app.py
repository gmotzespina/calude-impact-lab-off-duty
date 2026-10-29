import json
import os
import re
import signal
import subprocess
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from flask import Flask, jsonify, render_template, request
except ImportError:
    # Graceful stdlib HTTP fallback if run before `pip install flask`
    class _RequestProxy:
        def __init__(self):
            self._json = None

        def get_json(self, silent=True):
            return self._json

    request = _RequestProxy()

    def jsonify(data):
        return data

    def render_template(template_name):
        tpl_path = Path(__file__).resolve().parent / "templates" / template_name
        return tpl_path.read_text(encoding="utf-8")

    class _TestResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def get_json(self):
            return self._payload if isinstance(self._payload, dict) else json.loads(self._payload)

    class Flask:
        def __init__(self, name):
            self.name = name
            self.routes = {}

        def route(self, path, methods=("GET",)):
            def decorator(fn):
                for m in methods:
                    self.routes[(path, m.upper())] = fn
                return fn
            return decorator

        def test_client(self):
            app_ref = self

            class _Client:
                def get(self, path):
                    fn = app_ref.routes.get((path, "GET"))
                    request._json = None
                    return _TestResponse(200, fn())

                def post(self, path, json=None):
                    fn = app_ref.routes.get((path, "POST"))
                    request._json = json or {}
                    return _TestResponse(200, fn())

            return _Client()

        def run(self, host="127.0.0.1", port=5050, debug=False, **kwargs):
            app_ref = self

            class _Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    path = self.path.split("?")[0]
                    fn = app_ref.routes.get((path, "GET"))
                    if not fn:
                        self.send_response(404)
                        self.end_headers()
                        return
                    request._json = None
                    res = fn()
                    self.send_response(200)
                    if isinstance(res, dict):
                        body = json.dumps(res).encode("utf-8")
                        self.send_header("Content-Type", "application/json")
                    else:
                        body = str(res).encode("utf-8")
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(body)

                def do_POST(self):
                    path = self.path.split("?")[0]
                    fn = app_ref.routes.get((path, "POST"))
                    if not fn:
                        self.send_response(404)
                        self.end_headers()
                        return
                    length = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    try:
                        request._json = json.loads(raw)
                    except Exception:
                        request._json = {}
                    res = fn()
                    body = json.dumps(res).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, fmt, *args):
                    return

            server = ThreadingHTTPServer((host, port), _Handler)
            server.serve_forever()

app = Flask(__name__)
if hasattr(app, "config"):
    app.config["TEMPLATES_AUTO_RELOAD"] = True

PROJECT_ROOT = Path(__file__).resolve().parent
PRIMARY_STATE_PATH = Path.home() / ".offduty_state.json"
FALLBACK_STATE_PATH = PROJECT_ROOT / ".offduty_state.json"

SCIENCE_PROTOCOLS = {
    "water": {
        "id": "water",
        "icon": "💧",
        "short_label": "Drink a glass of water",
        "title": "Hydration Reset",
        "duration_label": "1 min",
        "action": "Walk away from your desk and drink a full glass of water while standing.",
        "why": "Even 1% dehydration drops prefrontal blood flow and spikes cortisol."
    },
    "posture": {
        "id": "posture",
        "icon": "🧍",
        "short_label": "Stand up & stretch hips",
        "title": "Posture & Hip Unload",
        "duration_label": "90 sec",
        "action": "Stand tall and do a 45-second half-kneeling hip flexor stretch on each side.",
        "why": "Sitting locks your hip flexors and reduces lung capacity by up to 20%."
    },
    "mobility": {
        "id": "mobility",
        "icon": "🔄",
        "short_label": "Open-book shoulder rolls",
        "title": "Thoracic Spine Release",
        "duration_label": "90 sec",
        "action": "Clasp hands behind your head, arch gently back, and rotate your torso 8x.",
        "why": "Unloads 45 lbs of forward-head neck tension from staring at code."
    },
    "breathwork": {
        "id": "breathwork",
        "icon": "🌬️",
        "short_label": "20ft gaze + 5 deep sighs",
        "title": "20-20-20 + Physiological Sigh",
        "duration_label": "1 min",
        "action": "Look at a target 20+ feet away and take 5 double-inhales with slow mouth exhales.",
        "why": "Relaxes eye muscle spasm and physically slows heart rate via the vagus nerve."
    }
}

DEFAULT_SETTINGS = {
    "break_interval_minutes": 60,
    "active_break_types": ["water", "posture", "mobility", "breathwork"],
    "curfew_start_hour": 20,
    "curfew_end_hour": 6,
    "max_daily_hours": 8.0,
    "hardcore_mode": True
}


def run_cmd(cmd, cwd=None, timeout=3.0):
    """Run a shell/system command safely and return stdout string."""
    try:
        res = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return res.stdout.strip() if res.returncode == 0 else ""
    except Exception:
        return ""


def get_state_file_path():
    """Return ~/.offduty_state.json if accessible, else local project fallback."""
    try:
        if PRIMARY_STATE_PATH.exists():
            PRIMARY_STATE_PATH.read_text(encoding="utf-8")
            return PRIMARY_STATE_PATH
        PRIMARY_STATE_PATH.touch(exist_ok=True)
        return PRIMARY_STATE_PATH
    except Exception:
        return FALLBACK_STATE_PATH


def load_state():
    """Load persistent state from ~/.offduty_state.json."""
    now = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")
    default_state = {
        "date": today_str,
        "streak_start_epoch": now,
        "last_seen_epoch": now,
        "breaks_taken_today": 0,
        "reclaimed_minutes_today": 0.0,
        "shutdown_executed_today": False,
        "last_shutdown_at": None,
        "last_breadcrumb": None,
        "settings": dict(DEFAULT_SETTINGS)
    }
    path = get_state_file_path()
    try:
        if path.exists():
            raw = path.read_text(encoding="utf-8").strip()
            if raw:
                data = json.loads(raw)
                merged_settings = dict(DEFAULT_SETTINGS)
                if isinstance(data.get("settings"), dict):
                    merged_settings.update(data["settings"])
                data["settings"] = merged_settings
                if data.get("date") != today_str:
                    data["date"] = today_str
                    data["breaks_taken_today"] = 0
                    data["reclaimed_minutes_today"] = 0.0
                    data["shutdown_executed_today"] = False
                return data
    except Exception:
        pass
    save_state(default_state)
    return default_state


def save_state(state):
    """Write persistent state to ~/.offduty_state.json (with local fallback)."""
    payload = json.dumps(state, indent=2)
    for candidate in (PRIMARY_STATE_PATH, FALLBACK_STATE_PATH):
        try:
            candidate.write_text(payload, encoding="utf-8")
            if candidate == PRIMARY_STATE_PATH:
                break
        except Exception:
            continue


def get_hid_idle_seconds():
    """Extract real macOS HIDIdleTime in seconds using ioreg -c IOHIDSystem."""
    output = run_cmd(["ioreg", "-c", "IOHIDSystem"])
    if output:
        matches = re.findall(r'"HIDIdleTime"\s*=\s*(\d+)', output)
        if matches:
            ns = int(matches[0])
            return round(ns / 1_000_000_000.0, 1)
    return 0.0


SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".next", "dist", "build", "target", "vendor", "Pods", ".cache"
}
IGNORED_FILES = {".DS_Store", ".offduty_state.json", "morning_resume.sh", "resume_agents.sh"}

_SNAPSHOT_CACHE = {
    "repos_ts": 0.0,
    "repos_data": [],
    "claude_ts": 0.0,
    "claude_data": None,
    "pmset_ts": 0.0,
    "pmset_events": [],
    "history_ts": 0.0,
    "history_events": [],
    "git7d_ts": 0.0,
    "git7d_events": []
}
_CACHE_LOCK = threading.Lock()


def iter_shallow_files(root_path, max_depth=2):
    """Fast directory walk up to max_depth that strictly prunes heavy build/dependency folders."""
    root_str = str(root_path)
    root_depth = root_str.rstrip(os.sep).count(os.sep)
    try:
        for dirpath, dirnames, filenames in os.walk(root_str):
            dirnames[:] = [
                d for d in dirnames
                if d not in SKIP_DIRS and not d.startswith(".")
            ]
            depth = dirpath.count(os.sep) - root_depth
            if depth >= max_depth:
                dirnames[:] = []
            for fname in filenames:
                if fname in IGNORED_FILES or fname.endswith(".pyc"):
                    continue
                yield Path(dirpath) / fname
    except Exception:
        return


def update_continuous_streak(state, idle_seconds):
    """
    Track continuous active work minutes persistently.
    Resets streak_start_epoch ONLY when idle_seconds >= 300 (5 minutes)
    or when the host was offline/idle for >= 300 seconds between checks.
    """
    now = time.time()
    last_seen = float(state.get("last_seen_epoch", now))
    streak_start = float(state.get("streak_start_epoch", now))

    if abs(now - streak_start) < 2.0 and state.get("breaks_taken_today", 0) == 0:
        earliest_recent = now
        for p in iter_shallow_files(PROJECT_ROOT, max_depth=2):
            try:
                mtime = p.stat().st_mtime
                if 0 < (now - mtime) < 3600:
                    earliest_recent = min(earliest_recent, mtime)
            except Exception:
                pass
        if earliest_recent < now:
            streak_start = earliest_recent

    if idle_seconds >= 300.0:
        streak_start = now
    elif (now - last_seen) >= 300.0 and idle_seconds >= 60.0:
        streak_start = now - max(0.0, 60.0 - idle_seconds)

    state["streak_start_epoch"] = streak_start
    state["last_seen_epoch"] = now
    save_state(state)

    active_seconds = max(0.0, now - streak_start)
    return round(active_seconds / 60.0, 1)


def discover_git_repos(force=False):
    """
    Scan current working directory, parent directories, and common macOS dev roots
    for real .git repositories and inspect their live status & 24h commit history.
    Cached for 8 seconds to keep UI interactions instantaneous.
    """
    now = time.time()
    if not force and _SNAPSHOT_CACHE["repos_data"] and (now - _SNAPSHOT_CACHE["repos_ts"] < 8.0):
        return _SNAPSHOT_CACHE["repos_data"]

    candidate_roots = [
        PROJECT_ROOT,
        PROJECT_ROOT.parent,
        Path.home() / "Dev",
        Path.home() / "Projects",
        Path.home() / "Code",
        Path.home() / "Desktop"
    ]

    git_dirs = []
    seen = set()

    def add_if_repo(path_obj):
        try:
            resolved = path_obj.resolve()
            if str(resolved) in seen:
                return
            if (resolved / ".git").exists():
                seen.add(str(resolved))
                git_dirs.append(resolved)
        except Exception:
            pass

    for root in candidate_roots:
        try:
            if not root.exists():
                continue
            add_if_repo(root)
            for child in root.iterdir():
                if child.is_dir() and not child.name.startswith(".") and child.name not in SKIP_DIRS:
                    add_if_repo(child)
        except Exception:
            continue

    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    repos_info = []

    for repo_path in git_dirs[:15]:
        branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path, timeout=1.2) or "main"
        status_raw = run_cmd(["git", "status", "--porcelain"], cwd=repo_path, timeout=1.5)
        status_lines = [line for line in status_raw.splitlines() if line.strip()]
        modified_files = []
        for line in status_lines:
            parts = line.strip().split(maxsplit=1)
            fname = parts[1] if len(parts) == 2 else (parts[0] if parts else "")
            if not fname:
                continue
            if any(ig in fname for ig in IGNORED_FILES) or "__pycache__" in fname or fname.endswith(".pyc"):
                continue
            modified_files.append(fname)

        commits_24h_raw = run_cmd(
            ["git", "log", "--since=24 hours ago", "--oneline"],
            cwd=repo_path,
            timeout=1.2
        )
        commits_24h = [c.strip() for c in commits_24h_raw.splitlines() if c.strip()]
        last_commit = run_cmd(["git", "log", "-1", "--oneline"], cwd=repo_path, timeout=1.2) or "No commits yet"
        diff_stat = run_cmd(["git", "diff", "--stat"], cwd=repo_path, timeout=1.2)

        latest_mtime = 0.0
        latest_file_name = None

        # Fast check on modified files first, then shallow directory walk
        candidates = [repo_path / mf for mf in modified_files[:10]]
        for item in list(candidates) + list(iter_shallow_files(repo_path, max_depth=2)):
            try:
                if item.is_file() and item.name not in IGNORED_FILES:
                    st = item.stat()
                    if st.st_mtime > latest_mtime:
                        latest_mtime = st.st_mtime
                        latest_file_name = str(item.relative_to(repo_path))
            except Exception:
                continue

        touched_today = (
            len(modified_files) > 0
            or len(commits_24h) > 0
            or latest_mtime >= today_midnight
        )

        # Extract a concise, real code diff or file preview for the latest touched file
        diff_preview = ""
        if latest_file_name:
            raw_diff = run_cmd(
                ["git", "diff", "-U1", "--", latest_file_name],
                cwd=repo_path,
                timeout=1.0
            )
            if raw_diff:
                diff_lines = [
                    ln for ln in raw_diff.splitlines()
                    if (ln.startswith("+") or ln.startswith("-") or ln.startswith("@@"))
                    and not ln.startswith("+++") and not ln.startswith("---")
                ]
                diff_preview = "\n".join(diff_lines[:6])
            else:
                try:
                    target_fp = repo_path / latest_file_name
                    if target_fp.is_file() and target_fp.stat().st_size < 200_000:
                        lines = [ln.rstrip() for ln in target_fp.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
                        diff_preview = "\n".join(lines[:5])
                except Exception:
                    pass

        mins_ago = max(0, int((time.time() - latest_mtime) / 60)) if latest_mtime > 0 else 0
        focus_file = latest_file_name or (modified_files[0] if modified_files else "README.md")
        resume_cmd = f"cd {repo_path} && git status -s && git diff {focus_file}"

        repos_info.append({
            "name": repo_path.name,
            "path": str(repo_path),
            "branch": branch,
            "uncommitted_count": len(modified_files),
            "modified_files": modified_files[:12],
            "commits_today_count": len(commits_24h),
            "commits_today": commits_24h[:5],
            "last_commit": last_commit,
            "diff_stat": diff_stat,
            "diff_preview": diff_preview,
            "latest_mtime": latest_mtime,
            "minutes_ago": mins_ago,
            "latest_file": focus_file,
            "resume_command": resume_cmd,
            "touched_today": touched_today
        })

    if str(PROJECT_ROOT) not in seen:
        recent_files = []
        latest_mtime = 0.0
        latest_file_name = None
        for item in iter_shallow_files(PROJECT_ROOT, max_depth=2):
            try:
                st = item.stat()
                if st.st_mtime >= today_midnight:
                    recent_files.append(str(item.relative_to(PROJECT_ROOT)))
                if st.st_mtime > latest_mtime:
                    latest_mtime = st.st_mtime
                    latest_file_name = str(item.relative_to(PROJECT_ROOT))
            except Exception:
                continue

        if recent_files:
            repos_info.insert(0, {
                "name": PROJECT_ROOT.name + " (workspace)",
                "path": str(PROJECT_ROOT),
                "branch": "working-tree",
                "uncommitted_count": len(recent_files),
                "modified_files": recent_files[:12],
                "commits_today_count": 0,
                "commits_today": [],
                "last_commit": "Active workspace directory (uncommitted files)",
                "diff_stat": f"{len(recent_files)} active file(s) modified today in {PROJECT_ROOT.name}",
                "latest_mtime": latest_mtime,
                "latest_file": latest_file_name,
                "touched_today": True
            })

    repos_info.sort(key=lambda r: (r["touched_today"], r["latest_mtime"]), reverse=True)
    with _CACHE_LOCK:
        _SNAPSHOT_CACHE["repos_ts"] = now
        _SNAPSHOT_CACHE["repos_data"] = repos_info
    return repos_info


def scan_claude_and_agents(force=False):
    """
    Scan ~/.claude (and local agent session logs) for today's session turns and updates,
    plus inspect live running claude CLI processes via pgrep. Cached for 8 seconds.
    """
    now = time.time()
    if not force and _SNAPSHOT_CACHE["claude_data"] and (now - _SNAPSHOT_CACHE["claude_ts"] < 8.0):
        return _SNAPSHOT_CACHE["claude_data"]

    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    seven_days_ago = (datetime.now() - timedelta(days=7)).timestamp()

    claude_roots = [
        Path.home() / ".claude" / "projects",
        Path.home() / ".claude"
    ]

    sessions_touched_today = 0
    log_turns_today = 0
    recent_session_files = []
    timestamps_7d = []
    visited_files = set()

    for root in claude_roots:
        for fpath in iter_shallow_files(root, max_depth=3):
            try:
                resolved_str = str(fpath)
                if resolved_str in visited_files:
                    continue
                visited_files.add(resolved_str)

                st = fpath.stat()
                mtime = st.st_mtime
                if mtime >= seven_days_ago:
                    timestamps_7d.append(mtime)

                if mtime >= today_midnight and fpath.suffix in (".jsonl", ".json", ".log", ".md"):
                    sessions_touched_today += 1
                    recent_session_files.append({
                        "name": fpath.name,
                        "parent": fpath.parent.name,
                        "mtime": datetime.fromtimestamp(mtime).strftime("%H:%M")
                    })
                    if fpath.suffix == ".jsonl" and st.st_size < 5_000_000:
                        try:
                            with fpath.open("r", encoding="utf-8", errors="ignore") as f:
                                log_turns_today += sum(1 for _ in f)
                        except Exception:
                            log_turns_today += 1
                    else:
                        log_turns_today += 1
            except Exception:
                continue

    my_pid = os.getpid()
    running_agents = []
    pgrep_out = run_cmd(["pgrep", "-fl", "claude"], timeout=1.0)
    if pgrep_out:
        for line in pgrep_out.splitlines():
            parts = line.strip().split(maxsplit=1)
            if not parts:
                continue
            try:
                pid = int(parts[0])
                cmd_str = parts[1] if len(parts) > 1 else "claude"
                if pid != my_pid and "pgrep" not in cmd_str:
                    running_agents.append({"pid": pid, "command": cmd_str[:80]})
            except ValueError:
                continue

    result = {
        "sessions_touched_today": sessions_touched_today,
        "log_turns_today": log_turns_today,
        "recent_session_files": recent_session_files[:6],
        "running_agents": running_agents,
        "running_agent_count": len(running_agents),
        "timestamps_7d": timestamps_7d
    }
    with _CACHE_LOCK:
        _SNAPSHOT_CACHE["claude_ts"] = now
        _SNAPSHOT_CACHE["claude_data"] = result
    return result


def compute_circadian_audit(settings, repos_info, claude_data, force=False):
    """
    Perform a 7-Day Circadian & Weekend Audit using real macOS telemetry:
    1. pmset -g log (tail of recent Wake / DarkWake / UserIsActive events, cached 60s)
    2. Shell histories (~/.zsh_history, ~/.bash_history, ~/.zsh_sessions, cached 60s)
    3. ~/.claude & agent log modification timestamps
    4. Git repository commit timestamps & workspace file modifications over last 7 days
    """
    now = time.time()
    now_dt = datetime.now()
    seven_days_ago_dt = (now_dt - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago_ts = seven_days_ago_dt.timestamp()

    curfew_start = int(settings.get("curfew_start_hour", 20))
    curfew_end = int(settings.get("curfew_end_hour", 6))

    events_ts = []
    sources_used = ["IOHIDSystem (HIDIdleTime)"]

    # 1. Parse recent pmset -g log tail (cached for 60s so polling is <15ms)
    if force or (now - _SNAPSHOT_CACHE["pmset_ts"] > 60.0):
        pmset_events = []
        pmset_out = run_cmd(["sh", "-c", "pmset -g log 2>/dev/null | tail -n 2500"], timeout=1.5)
        if pmset_out and "Error -" not in pmset_out:
            ts_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*?(Wake|DarkWake|UserIsActive)")
            for line in pmset_out.splitlines():
                m = ts_pattern.search(line)
                if m:
                    try:
                        dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                        if dt.timestamp() >= seven_days_ago_ts:
                            pmset_events.append(dt.timestamp())
                    except Exception:
                        continue
        with _CACHE_LOCK:
            _SNAPSHOT_CACHE["pmset_ts"] = now
            _SNAPSHOT_CACHE["pmset_events"] = pmset_events

    pmset_cached = _SNAPSHOT_CACHE["pmset_events"]
    if pmset_cached:
        events_ts.extend(pmset_cached)
        sources_used.append(f"pmset ({len(pmset_cached)} power events)")

    # 2. Inspect ~/.zsh_history, ~/.bash_history, ~/.zsh_sessions (cached 60s)
    if force or (now - _SNAPSHOT_CACHE["history_ts"] > 60.0):
        hist_events = []
        for hist_file in [Path.home() / ".zsh_history", Path.home() / ".bash_history"]:
            try:
                if hist_file.exists():
                    st = hist_file.stat()
                    if st.st_mtime >= seven_days_ago_ts:
                        hist_events.append(st.st_mtime)
                    with hist_file.open("rb") as f:
                        # Read only last 256KB of history file for speed
                        f.seek(0, os.SEEK_END)
                        size = f.tell()
                        f.seek(max(0, size - 262144), os.SEEK_SET)
                        tail_text = f.read().decode("utf-8", errors="ignore")
                        for line in tail_text.splitlines():
                            if line.startswith(": "):
                                m = re.match(r"^:\s*(\d{10}):", line)
                                if m:
                                    ts = float(m.group(1))
                                    if ts >= seven_days_ago_ts:
                                        hist_events.append(ts)
            except Exception:
                continue

        zsh_sessions_dir = Path.home() / ".zsh_sessions"
        try:
            if zsh_sessions_dir.exists():
                for sf in zsh_sessions_dir.iterdir():
                    if sf.is_file():
                        mtime = sf.stat().st_mtime
                        if mtime >= seven_days_ago_ts:
                            hist_events.append(mtime)
        except Exception:
            pass

        with _CACHE_LOCK:
            _SNAPSHOT_CACHE["history_ts"] = now
            _SNAPSHOT_CACHE["history_events"] = hist_events

    hist_cached = _SNAPSHOT_CACHE["history_events"]
    if hist_cached:
        events_ts.extend(hist_cached)
        sources_used.append(f"Shell History ({len(hist_cached)} entries)")

    # 3. Include ~/.claude / agent session timestamps
    agent_ts = claude_data.get("timestamps_7d", [])
    if agent_ts:
        events_ts.extend(agent_ts)
        sources_used.append(f"Agent Logs ({len(agent_ts)} files)")

    # 4. Include Git commit timestamps and shallow workspace file mtimes over last 7 days (cached 60s)
    if force or (now - _SNAPSHOT_CACHE["git7d_ts"] > 60.0):
        git_events = []
        for repo in repos_info[:8]:
            repo_path = Path(repo["path"])
            if (repo_path / ".git").exists():
                log_out = run_cmd(["git", "log", "--since=7 days ago", "--format=%ct"], cwd=repo_path, timeout=1.0)
                for line in log_out.splitlines():
                    line = line.strip()
                    if line.isdigit():
                        ts = float(line)
                        if ts >= seven_days_ago_ts:
                            git_events.append(ts)
            if repo.get("latest_mtime", 0) >= seven_days_ago_ts:
                git_events.append(repo["latest_mtime"])
        with _CACHE_LOCK:
            _SNAPSHOT_CACHE["git7d_ts"] = now
            _SNAPSHOT_CACHE["git7d_events"] = git_events

    git_cached = _SNAPSHOT_CACHE["git7d_events"]
    if git_cached:
        events_ts.extend(git_cached)
        sources_used.append(f"Git & Workspace ({len(git_cached)} events)")

    events_ts.append(now_dt.timestamp())

    daily_buckets = {}
    for offset in range(6, -1, -1):
        d = (now_dt - timedelta(days=offset)).date()
        daily_buckets[d.isoformat()] = {
            "date": d.isoformat(),
            "day_label": d.strftime("%a %b %d"),
            "short_day": d.strftime("%a"),
            "is_weekend": d.weekday() in (5, 6),
            "timestamps": []
        }

    for ts in events_ts:
        dt = datetime.fromtimestamp(ts)
        d_key = dt.date().isoformat()
        if d_key in daily_buckets:
            daily_buckets[d_key]["timestamps"].append(dt)

    pre_6am_starts_count = 0
    post_8pm_nights_count = 0
    weekend_active_days_count = 0
    daily_breakdown = []

    for d_key, info in daily_buckets.items():
        dts = sorted(info["timestamps"])
        if not dts:
            daily_breakdown.append({
                "date": d_key,
                "day_label": info["day_label"],
                "short_day": info["short_day"],
                "is_weekend": info["is_weekend"],
                "active": False,
                "earliest": "—",
                "latest": "—",
                "pre_6am": False,
                "post_8pm": False,
                "event_count": 0
            })
            continue

        earliest_dt = dts[0]
        latest_dt = dts[-1]
        is_pre_6am = any(x.hour < curfew_end for x in dts)
        is_post_8pm = any(x.hour >= curfew_start for x in dts)

        if is_pre_6am:
            pre_6am_starts_count += 1
        if is_post_8pm:
            post_8pm_nights_count += 1
        if info["is_weekend"]:
            weekend_active_days_count += 1

        daily_breakdown.append({
            "date": d_key,
            "day_label": info["day_label"],
            "short_day": info["short_day"],
            "is_weekend": info["is_weekend"],
            "active": True,
            "earliest": earliest_dt.strftime("%H:%M"),
            "latest": latest_dt.strftime("%H:%M"),
            "pre_6am": is_pre_6am,
            "post_8pm": is_post_8pm,
            "event_count": len(dts)
        })

    today_key = now_dt.date().isoformat()
    today_entry = next((item for item in daily_breakdown if item["date"] == today_key), None)
    earliest_today = today_entry["earliest"] if today_entry else now_dt.strftime("%H:%M")
    latest_today = today_entry["latest"] if today_entry else now_dt.strftime("%H:%M")

    # Compute overall Burnout Risk verdict from real counts
    violation_points = (
        (post_8pm_nights_count * 2)
        + (pre_6am_starts_count * 2)
        + (weekend_active_days_count * 2)
    )
    if violation_points >= 4:
        verdict = "HIGH RISK — Circadian Compression Detected"
        verdict_level = "high"
    elif violation_points >= 2 or now_dt.hour >= curfew_start or now_dt.hour < curfew_end:
        verdict = "MODERATE — Boundary Drift Active"
        verdict_level = "moderate"
    else:
        verdict = "HEALTHY — Circadian Boundaries Intact"
        verdict_level = "healthy"

    return {
        "pre_6am_starts_count": pre_6am_starts_count,
        "post_8pm_nights_count": post_8pm_nights_count,
        "weekend_active_days_count": weekend_active_days_count,
        "earliest_interaction_today": earliest_today,
        "latest_interaction_today": latest_today,
        "burnout_risk_verdict": verdict,
        "verdict_level": verdict_level,
        "daily_breakdown": daily_breakdown,
        "telemetry_sources": sources_used
    }


def build_cognitive_breadcrumb(repos_info):
    """
    Auto-generate a zero-prompt 'Cognitive Breadcrumb' from the user's open git repo
    and most recently modified files so they never have to type status notes.
    """
    if not repos_info:
        now_str = datetime.now().strftime("%H:%M:%S")
        return {
            "summary": f"Saved your spot at {now_str}: Working in {PROJECT_ROOT.name} ({PROJECT_ROOT}).",
            "repo_name": PROJECT_ROOT.name,
            "repo_path": str(PROJECT_ROOT),
            "branch": "main",
            "modified_files": [],
            "last_commit": "N/A",
            "latest_file": "app.py",
            "first_step_tomorrow": f"Open {PROJECT_ROOT}/app.py and review active session changes.",
            "captured_at": now_str
        }

    primary = repos_info[0]
    mod_files = primary.get("modified_files", [])
    mod_count = primary.get("uncommitted_count", 0)
    latest_file = primary.get("latest_file") or (mod_files[0] if mod_files else "README.md")
    files_preview = ", ".join(mod_files[:4]) if mod_files else latest_file
    if mod_count > 4:
        files_preview += f" (+{mod_count - 4} more)"

    summary = (
        f"Saved your spot: {mod_count} modified file(s) in /{primary['name']} "
        f"({files_preview}) on branch {primary['branch']}. "
        f"Last commit: '{primary['last_commit']}'"
    )
    first_step = (
        f"Resume in `{primary['path']}` on branch `{primary['branch']}` -> "
        f"inspect `{latest_file}` (most recently modified file) and run `git diff`."
    )

    return {
        "summary": summary,
        "repo_name": primary["name"],
        "repo_path": primary["path"],
        "branch": primary["branch"],
        "modified_files": mod_files,
        "uncommitted_count": mod_count,
        "last_commit": primary["last_commit"],
        "diff_stat": primary.get("diff_stat") or "Working tree modifications tracked.",
        "latest_file": latest_file,
        "first_step_tomorrow": first_step,
        "captured_at": datetime.now().strftime("%H:%M:%S")
    }


def compute_curfew_status(settings, continuous_work_minutes):
    """Determine if current local time falls inside the curfew lockout window."""
    now = datetime.now()
    start_h = int(settings.get("curfew_start_hour", 20))
    end_h = int(settings.get("curfew_end_hour", 6))
    max_daily_hours = float(settings.get("max_daily_hours", 8.0))

    in_curfew_hours = (now.hour >= start_h) or (now.hour < end_h)

    # Calculate next 06:00 AM (curfew_end_hour) timestamp for countdown
    if now.hour >= end_h:
        unlock_dt = (now + timedelta(days=1)).replace(hour=end_h, minute=0, second=0, microsecond=0)
    else:
        unlock_dt = now.replace(hour=end_h, minute=0, second=0, microsecond=0)

    seconds_until_unlock = max(0, int((unlock_dt - now).total_seconds()))
    hours_until_unlock = round(seconds_until_unlock / 3600.0, 1)

    return {
        "in_curfew_window": in_curfew_hours,
        "exceeded_daily_limit": (continuous_work_minutes / 60.0) >= max_daily_hours,
        "should_auto_lock": bool(settings.get("hardcore_mode", True) and in_curfew_hours),
        "unlock_iso": unlock_dt.isoformat(),
        "unlock_Time_formatted": unlock_dt.strftime("%I:%M %p"),
        "seconds_until_unlock": seconds_until_unlock,
        "hours_protected_until_morning": hours_until_unlock
    }


def pick_next_protocol(state, advance=False):
    """
    Select ONE activity from the user's enabled break protocols without repeating
    the previous suggestion. Advances `last_protocol_id` when advance=True.
    """
    settings = state.get("settings", DEFAULT_SETTINGS)
    enabled = [
        pid for pid in (settings.get("active_break_types") or [])
        if pid in SCIENCE_PROTOCOLS
    ]
    if not enabled:
        enabled = ["breathwork", "water", "posture", "mobility"]

    last_id = state.get("last_protocol_id")
    if last_id in enabled and len(enabled) > 1:
        next_idx = (enabled.index(last_id) + 1) % len(enabled)
        chosen_id = enabled[next_idx]
    else:
        chosen_id = enabled[0]

    if advance:
        state["last_protocol_id"] = chosen_id

    return SCIENCE_PROTOCOLS[chosen_id]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/slides")
@app.route("/slides/")
def slides():
    return render_template("slides.html")


@app.route("/api/telemetry", methods=["GET"])
def api_telemetry():
    t0 = time.time()
    force = False
    try:
        force = getattr(request, "args", {}).get("force") == "1"
    except Exception:
        pass

    state = load_state()
    settings = state.get("settings", DEFAULT_SETTINGS)

    idle_seconds = get_hid_idle_seconds()
    continuous_work_minutes = update_continuous_streak(state, idle_seconds)

    repos_info = discover_git_repos(force=force)
    active_repos_today = [r for r in repos_info if r.get("touched_today")]
    total_uncommitted = sum(r.get("uncommitted_count", 0) for r in active_repos_today)

    claude_data = scan_claude_and_agents(force=force)
    circadian_audit = compute_circadian_audit(settings, repos_info, claude_data, force=force)
    breadcrumb = build_cognitive_breadcrumb(repos_info)
    curfew_status = compute_curfew_status(settings, continuous_work_minutes)
    next_protocol = pick_next_protocol(state, advance=False)

    state["last_breadcrumb"] = breadcrumb
    parked_map = state.get("parked_repos", {})
    for r in active_repos_today:
        r["is_parked"] = r["path"] in parked_map
        r["parked_at"] = parked_map.get(r["path"])

    save_state(state)

    break_interval = int(settings.get("break_interval_minutes", 60))
    break_due = continuous_work_minutes >= break_interval
    scan_ms = round((time.time() - t0) * 1000.0, 1)

    return jsonify({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_duration_ms": scan_ms,
        "idle_seconds": idle_seconds,
        "continuous_work_minutes": continuous_work_minutes,
        "break_due": break_due,
        "breaks_taken_today": state.get("breaks_taken_today", 0),
        "reclaimed_minutes_today": state.get("reclaimed_minutes_today", 0.0),
        "next_protocol": next_protocol,
        "parked_count": len(parked_map),
        "shutdown_executed_today": state.get("shutdown_executed_today", False),
        "last_shutdown_at": state.get("last_shutdown_at"),
        "juggling_metrics": {
            "active_repos_count": len(active_repos_today),
            "active_repos": active_repos_today,
            "uncommitted_file_count": total_uncommitted,
            "claude_sessions_today": claude_data["sessions_touched_today"],
            "claude_turns_today": claude_data["log_turns_today"],
            "recent_claude_files": claude_data["recent_session_files"],
            "running_agents": claude_data["running_agents"],
            "running_agent_count": claude_data["running_agent_count"]
        },
        "circadian_audit": circadian_audit,
        "saved_breadcrumb": breadcrumb,
        "settings": settings,
        "curfew_status": curfew_status
    })


@app.route("/api/park-context", methods=["POST"])
def api_park_context():
    """
    Park a specific open repository/workstream into TOMORROW.md and ~/.offduty_state.json
    so the engineer can drop that mental thread immediately.
    """
    state = load_state()
    payload = request.get_json(silent=True) or {}
    repo_path = payload.get("repo_path")
    unpark = bool(payload.get("unpark", False))

    parked_map = state.get("parked_repos", {})
    now_str = datetime.now().strftime("%H:%M:%S")

    if repo_path:
        if unpark:
            parked_map.pop(repo_path, None)
        else:
            parked_map[repo_path] = now_str
    state["parked_repos"] = parked_map
    save_state(state)

    # Also refresh TOMORROW.md on disk with all currently parked/open contexts
    repos_info = discover_git_repos()
    breadcrumb = build_cognitive_breadcrumb(repos_info)
    active_repos = [r for r in repos_info if r.get("touched_today")] or repos_info[:1]

    md_lines = [
        "# TOMORROW.md — Parked Workstreams & Morning Handoff",
        "",
        f"- **Last Updated:** {datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p')}",
        f"- **Parked Workstreams:** {len(parked_map)} / {len(active_repos)} active repo(s)",
        "",
        "## Your 9:00 AM First Step",
        f"> **{breadcrumb['summary']}**",
        f"- [ ] {breadcrumb['first_step_tomorrow']}",
        "",
        "## Open & Parked Repositories",
        ""
    ]
    for idx, r in enumerate(active_repos, start=1):
        status_tag = f"PARKED at {parked_map[r['path']]}" if r["path"] in parked_map else "OPEN"
        md_lines.append(f"### {idx}. `{r['name']}` (`{r['branch']}`) — [{status_tag}]")
        md_lines.append(f"- **Resume Command:** `{r.get('resume_command', '')}`")
        md_lines.append(f"- **Last Commit:** `{r['last_commit']}`")
        if r.get("modified_files"):
            md_lines.append(f"- **Uncommitted Files ({r['uncommitted_count']}):** `{', '.join(r['modified_files'])}`")
        md_lines.append("")

    tomorrow_md_content = "\n".join(md_lines) + "\n"
    try:
        (PROJECT_ROOT / "TOMORROW.md").write_text(tomorrow_md_content, encoding="utf-8")
    except Exception:
        pass

    return jsonify({
        "status": "ok",
        "parked_repos": parked_map,
        "parked_count": len(parked_map),
        "tomorrow_md_content": tomorrow_md_content
    })


@app.route("/api/resume-morning", methods=["POST"])
def api_resume_morning():
    """
    Morning Unpack: Sends SIGCONT to any paused Claude agents, clears parked state,
    and returns the primary resume command so the user is back in flow in 10 seconds.
    """
    state = load_state()
    claude_data = scan_claude_and_agents(force=True)
    resumed_pids = []
    for agent in claude_data["running_agents"]:
        try:
            os.kill(agent["pid"], signal.SIGCONT)
            resumed_pids.append(agent["pid"])
        except Exception:
            pass

    repos_info = discover_git_repos()
    breadcrumb = build_cognitive_breadcrumb(repos_info)
    primary_cmd = repos_info[0].get("resume_command") if repos_info else f"cd {PROJECT_ROOT} && git status"

    state["parked_repos"] = {}
    state["shutdown_executed_today"] = False
    state["streak_start_epoch"] = time.time()
    save_state(state)

    return jsonify({
        "status": "ok",
        "resumed_pids": resumed_pids,
        "resume_command": primary_cmd,
        "breadcrumb": breadcrumb
    })


@app.route("/api/settings", methods=["POST"])
def api_settings():
    state = load_state()
    payload = request.get_json(silent=True) or {}
    settings = state.get("settings", dict(DEFAULT_SETTINGS))

    if "break_interval_minutes" in payload:
        settings["break_interval_minutes"] = max(5, min(240, int(payload["break_interval_minutes"])))
    if "active_break_types" in payload and isinstance(payload["active_break_types"], list):
        valid = [b for b in payload["active_break_types"] if b in SCIENCE_PROTOCOLS]
        settings["active_break_types"] = valid or ["breathwork"]
    if "curfew_start_hour" in payload:
        settings["curfew_start_hour"] = max(0, min(23, int(payload["curfew_start_hour"])))
    if "curfew_end_hour" in payload:
        settings["curfew_end_hour"] = max(0, min(23, int(payload["curfew_end_hour"])))
    if "max_daily_hours" in payload:
        settings["max_daily_hours"] = max(1.0, min(16.0, float(payload["max_daily_hours"])))
    if "hardcore_mode" in payload:
        settings["hardcore_mode"] = bool(payload["hardcore_mode"])

    state["settings"] = settings
    save_state(state)
    return jsonify({"status": "ok", "settings": settings})


@app.route("/api/trigger-break", methods=["POST"])
def api_trigger_break():
    state = load_state()
    payload = request.get_json(silent=True) or {}
    rotate_only = bool(payload.get("rotate_only", False))

    repos_info = discover_git_repos()
    breadcrumb = build_cognitive_breadcrumb(repos_info)
    chosen_protocol = pick_next_protocol(state, advance=True)

    # Reset continuous work streak and credit 5 minutes of physiological recovery (unless rotating activity)
    if not rotate_only:
        state["streak_start_epoch"] = time.time()
        state["last_seen_epoch"] = time.time()
        state["breaks_taken_today"] = int(state.get("breaks_taken_today", 0)) + 1
        state["reclaimed_minutes_today"] = round(float(state.get("reclaimed_minutes_today", 0.0)) + 5.0, 1)
    state["last_breadcrumb"] = breadcrumb
    save_state(state)

    display_slept = False
    if payload.get("sleep_display"):
        run_cmd(["pmset", "displaysleepnow"])
        display_slept = True

    return jsonify({
        "status": "ok",
        "duration_seconds": 300,
        "saved_breadcrumb": breadcrumb,
        "protocol": chosen_protocol,
        "breaks_taken_today": state["breaks_taken_today"],
        "reclaimed_minutes_today": state["reclaimed_minutes_today"],
        "display_slept": display_slept
    })


@app.route("/api/sleep-display", methods=["POST"])
def api_sleep_display():
    """Directly trigger macOS hardware display sleep via pmset displaysleepnow."""
    run_cmd(["pmset", "displaysleepnow"])
    return jsonify({"status": "ok", "command": "pmset displaysleepnow"})


@app.route("/api/notify", methods=["POST"])
def api_notify():
    """
    Trigger a native macOS notification banner via osascript.
    Also used by the automatic 60-minute background watcher.
    """
    state = load_state()
    next_proto = pick_next_protocol(state, advance=False)
    title = "Off-Duty — 5-Min Bio-Reset Due"
    subtitle = f"Up next: {next_proto['icon']} {next_proto['short_label']}"
    msg = "Your open code spot is saved. Click to open Off-Duty and step away for 5 minutes."
    apple_script = (
        f'display notification "{msg}" with title "{title}" '
        f'subtitle "{subtitle}" sound name "Glass"'
    )
    run_cmd(["osascript", "-e", apple_script], timeout=2.0)
    return jsonify({
        "status": "ok",
        "title": title,
        "subtitle": subtitle,
        "message": msg,
        "next_protocol": next_proto
    })


@app.route("/api/open-workspace", methods=["POST"])
def api_open_workspace():
    """
    Open a parked repository directly in the user's macOS editor (Cursor / VS Code) or Finder/Terminal
    when they return from a break or start at 9:00 AM.
    """
    payload = request.get_json(silent=True) or {}
    repo_path = payload.get("repo_path") or str(PROJECT_ROOT)
    latest_file = payload.get("latest_file")
    target = str(Path(repo_path) / latest_file) if latest_file else str(repo_path)

    # Try opening in Cursor or VS Code if installed, else fallback to macOS `open`
    opened_with = "macOS open"
    if run_cmd(["which", "cursor"]):
        run_cmd(["cursor", repo_path, target])
        opened_with = "Cursor"
    elif run_cmd(["which", "code"]):
        run_cmd(["code", repo_path, target])
        opened_with = "VS Code"
    else:
        run_cmd(["open", repo_path])

    return jsonify({"status": "ok", "opened_with": opened_with, "repo_path": repo_path})


@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    """
    Execute Official Idea #3: The One-Click Shutdown Command.
    1. Auto-inspects open git repos, branches, uncommitted diffs, and recent files.
    2. Writes a real TOMORROW.md file to project root (and Desktop if permitted).
    3. Detects running `claude` CLI agent processes, optionally pauses them via SIGSTOP,
       and generates executable `morning_resume.sh` / `resume_agents.sh`.
    4. Records reclaimed hours in ~/.offduty_state.json and triggers curfew lockout.
    """
    state = load_state()
    payload = request.get_json(silent=True) or {}
    settings = state.get("settings", dict(DEFAULT_SETTINGS))
    pause_agents = payload.get("pause_agents", True)
    sleep_display = payload.get("sleep_display", False)

    now = datetime.now()
    repos_info = discover_git_repos()
    claude_data = scan_claude_and_agents()
    breadcrumb = build_cognitive_breadcrumb(repos_info)
    curfew_status = compute_curfew_status(settings, 0)

    # Pause running claude processes if requested
    paused_agents = []
    for agent in claude_data["running_agents"]:
        pid = agent["pid"]
        if pause_agents:
            try:
                os.kill(pid, signal.SIGSTOP)
                paused_agents.append({"pid": pid, "command": agent["command"], "status": "SIGSTOP (Paused)"})
            except Exception as exc:
                paused_agents.append({"pid": pid, "command": agent["command"], "status": f"Detected ({exc})"})
        else:
            paused_agents.append({"pid": pid, "command": agent["command"], "status": "Detected (Not paused)"})

    # Write morning_resume.sh and resume_agents.sh
    resume_lines = [
        "#!/usr/bin/env bash",
        f"# Generated by Off-Duty Shutdown Engine at {now.strftime('%Y-%m-%d %H:%M:%S')}",
        "echo '☀️  Good morning! Resuming paused AI agents and displaying TOMORROW.md...'",
    ]
    if paused_agents:
        for pa in paused_agents:
            resume_lines.append(f"kill -CONT {pa['pid']} 2>/dev/null && echo 'Resumed PID {pa['pid']} ({pa['command']})'")
    else:
        resume_lines.append("echo 'No background Claude CLI processes were suspended overnight.'")
    resume_lines.append(f"cat \"{PROJECT_ROOT / 'TOMORROW.md'}\"")
    resume_script_content = "\n".join(resume_lines) + "\n"

    for script_name in ("morning_resume.sh", "resume_agents.sh"):
        script_path = PROJECT_ROOT / script_name
        try:
            script_path.write_text(resume_script_content, encoding="utf-8")
            script_path.chmod(0o755)
        except Exception:
            pass

    # Calculate time & attention returned to the user
    hours_protected = curfew_status["hours_protected_until_morning"]
    # Context-switching offload savings: 23 mins per open repo + break minutes reclaimed
    active_repos = [r for r in repos_info if r.get("touched_today")] or repos_info[:1]
    cognitive_offload_mins = round(len(active_repos) * 23.0 + float(state.get("reclaimed_minutes_today", 0.0)), 0)

    # Build TOMORROW.md
    md_lines = [
        "# TOMORROW.md — Off-Duty Shutdown Handoff",
        "",
        f"- **Shutdown Executed:** {now.strftime('%A, %B %d, %Y at %I:%M:%S %p')}",
        f"- **Circadian Boundary Protected:** Until {curfew_status['unlock_Time_formatted']} tomorrow ({hours_protected} hrs off-grid)",
        f"- **Working Memory Offloaded:** ~{int(cognitive_offload_mins)} mins of context-recovery saved",
        f"- **Active Repos Snapshotted:** {len(active_repos)} | **Claude Turns Today:** {claude_data['log_turns_today']}",
        "",
        "---",
        "",
        "## 1. Your 9:00 AM First Step (Zero-Prompt Breadcrumb)",
        "",
        f"> **{breadcrumb['summary']}**",
        "",
        f"- [ ] **9:00 AM Immediate Action:** {breadcrumb['first_step_tomorrow']}",
        f"- [ ] **Run Morning Resume Script:** `./morning_resume.sh` (resumes any paused agents & prints this brief)",
        "",
        "## 2. Open Git Repositories & Uncommitted State",
        ""
    ]

    for idx, repo in enumerate(active_repos, start=1):
        md_lines.append(f"### {idx}. `{repo['name']}` (`{repo['path']}`)")
        md_lines.append(f"- **Active Branch:** `{repo['branch']}`")
        md_lines.append(f"- **Last Commit:** `{repo['last_commit']}`")
        md_lines.append(f"- **Most Recently Edited File:** `{repo.get('latest_file') or 'N/A'}`")
        if repo.get("modified_files"):
            md_lines.append(f"- **Uncommitted Files ({repo['uncommitted_count']}):**")
            for mf in repo["modified_files"]:
                md_lines.append(f"  - [ ] `{mf}`")
        else:
            md_lines.append("- **Working Tree:** Clean (0 uncommitted files)")
        if repo.get("diff_stat"):
            md_lines.append("- **Diff Stat:**")
            md_lines.append("  ```text")
            for dl in repo["diff_stat"].splitlines():
                md_lines.append(f"  {dl}")
            md_lines.append("  ```")
        md_lines.append("")

    md_lines.extend([
        "## 3. Background AI Agents & Claude Sessions",
        ""
    ])
    if paused_agents:
        for pa in paused_agents:
            md_lines.append(f"- **PID `{pa['pid']}`** (`{pa['command']}`): **{pa['status']}** — resume tomorrow via `./morning_resume.sh`")
    else:
        md_lines.append("- **Live Agent Processes:** 0 active `claude` CLI processes running at shutdown.")
    md_lines.append(f"- **Claude Sessions Updated Today:** {claude_data['sessions_touched_today']} session file(s) ({claude_data['log_turns_today']} logged events)")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("*Generated automatically by Off-Duty (Bio-Boundary & Shutdown Engine). Close the lid—your spot is saved.*")
    tomorrow_md_content = "\n".join(md_lines) + "\n"

    written_paths = []
    primary_md_path = PROJECT_ROOT / "TOMORROW.md"
    primary_md_path.write_text(tomorrow_md_content, encoding="utf-8")
    written_paths.append(str(primary_md_path))

    desktop_md_path = Path.home() / "Desktop" / "TOMORROW.md"
    try:
        desktop_md_path.write_text(tomorrow_md_content, encoding="utf-8")
        written_paths.append(str(desktop_md_path))
    except Exception:
        pass

    parked_map = state.get("parked_repos", {})
    for r in active_repos:
        parked_map[r["path"]] = now.strftime("%H:%M:%S")
    state["parked_repos"] = parked_map
    state["streak_start_epoch"] = time.time()
    state["last_seen_epoch"] = time.time()
    state["shutdown_executed_today"] = True
    state["last_shutdown_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
    state["last_breadcrumb"] = breadcrumb
    save_state(state)

    if sleep_display:
        run_cmd(["pmset", "displaysleepnow"])

    return jsonify({
        "status": "ok",
        "shutdown_at": state["last_shutdown_at"],
        "tomorrow_md_content": tomorrow_md_content,
        "written_paths": written_paths,
        "resume_script_path": str(PROJECT_ROOT / "morning_resume.sh"),
        "paused_agents": paused_agents,
        "saved_breadcrumb": breadcrumb,
        "time_returned": {
            "hours_protected_until_morning": hours_protected,
            "cognitive_offload_minutes": int(cognitive_offload_mins),
            "breaks_taken_today": state.get("breaks_taken_today", 0),
            "reclaimed_break_minutes": state.get("reclaimed_minutes_today", 0.0),
            "unlock_time_formatted": curfew_status["unlock_Time_formatted"],
            "seconds_until_unlock": curfew_status["seconds_until_unlock"]
        }
    })


def _warmup_cache():
    try:
        state = load_state()
        repos = discover_git_repos(force=True)
        claude = scan_claude_and_agents(force=True)
        compute_circadian_audit(state.get("settings", DEFAULT_SETTINGS), repos, claude, force=True)
    except Exception:
        pass


def _background_break_notifier(port):
    """
    Background daemon that checks continuous active work every 60 seconds.
    When the user crosses their break threshold (e.g., 60 mins) without a reset,
    triggers a native macOS notification and can bring http://127.0.0.1:<port> up.
    """
    last_notified_epoch = 0.0
    while True:
        time.sleep(60)
        try:
            state = load_state()
            settings = state.get("settings", DEFAULT_SETTINGS)
            threshold = float(settings.get("break_interval_minutes", 60))
            idle_sec = get_hid_idle_seconds()
            cont_mins = update_continuous_streak(state, idle_sec)
            now = time.time()

            if cont_mins >= threshold and (now - last_notified_epoch) >= 900:
                last_notified_epoch = now
                next_proto = pick_next_protocol(state, advance=False)
                apple_script = (
                    f'display notification "You have been working {int(cont_mins)}m straight. '
                    f'Next reset: {next_proto["short_label"]}" '
                    f'with title "Off-Duty — Time for a 5-Min Bio-Reset" sound name "Glass"'
                )
                run_cmd(["osascript", "-e", apple_script], timeout=2.0)
        except Exception:
            continue


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    threading.Thread(target=_warmup_cache, daemon=True).start()
    threading.Thread(target=_background_break_notifier, args=(port,), daemon=True).start()
    print(
        f"\n🌿 Off-Duty (Bio-Boundary & Shutdown Engine) running at http://127.0.0.1:{port}\n"
        f"📽️  5-Slide User Journey Pitch Deck at http://127.0.0.1:{port}/slides#1\n"
    )
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
