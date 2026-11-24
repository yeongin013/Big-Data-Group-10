"""H4 job server: SQLite queue, one worker thread, exact mining in a separate Python process.

    POST /api/jobs                 {"dataset", "support", "memory_budget_bytes", "strategy", "deadline"?}
    GET  /api/jobs/{id}            status and selection history
    GET  /api/jobs/{id}/results    frequent pairs as JSON, or CSV with ?format=csv

The routes live in src/api.py. Jobs run one at a time in submission order. The worker builds the
profile, lets src.mining_selection choose a setting, then starts `python -m src.jobs --mine ...`
for the full count. If that process fails and the strategy allows it, the worker reselects once.
Only aggregate profile and pilot numbers go to Solar (src.mining_selection).
"""
import csv
import functools
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

from src import clean
from src.mining_job import SETTINGS, MiningJob
from src.mining_selection import MiningSelector

DB = clean.ROOT / "data" / "jobs" / "jobs.sqlite"  # data/ is not committed
STRATEGIES = ("rules", "solar_once", "solar_pilot")
DATASETS = {"y1": "year 1 (2009-12..2010-11)", "all": "both years (2009-12..2011-11)"}
MAX_BUDGET = 64 * 1024 ** 3
MINE_TIMEOUT_S = 600
# ponytail: one worker and FIFO order. Deadline-first scheduling is extension scope; deadline is stored only.
_wake = threading.Event()


class JobError(ValueError):
    """Bad request (400) or unknown job (404)."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT NOT NULL, dataset TEXT, support REAL,
        memory_budget_bytes INTEGER, strategy TEXT, deadline TEXT, created_at TEXT, started_at TEXT,
        finished_at TEXT, setting TEXT, message TEXT, history TEXT NOT NULL DEFAULT '[]', stats TEXT)""")
    return con


def _update(job_id, **fields):
    with _db() as con:
        con.execute(f"UPDATE jobs SET {', '.join(k + ' = ?' for k in fields)} WHERE id = ?", (*fields.values(), job_id))


def _add_event(job_id, event):
    with _db() as con:
        history = json.loads(con.execute("SELECT history FROM jobs WHERE id = ?", (job_id,)).fetchone()["history"])
        history.append(event)
        con.execute("UPDATE jobs SET history = ? WHERE id = ?", (json.dumps(history), job_id))


def _result_path(job_id):
    return DB.parent / f"job_{job_id}.csv"


@functools.cache
def baskets(dataset):
    """Registered datasets. JOBS_DATASET_FILE='name=path.json' adds one basket file (a JSON list of lists)."""
    extra = os.environ.get("JOBS_DATASET_FILE", "")
    if extra.partition("=")[0] == dataset:
        with open(extra.partition("=")[2], encoding="utf-8") as f:
            return [tuple(sorted(set(t))) for t in json.load(f)]
    b = clean.load_baskets()
    if dataset == "y1":
        return b[b.year == 1]["items"].tolist()
    if dataset == "all":
        return b[b.year > 0]["items"].tolist()
    raise JobError(400, f"dataset must be one of {sorted(dataset_names())}")


def dataset_names():
    extra = os.environ.get("JOBS_DATASET_FILE", "").partition("=")[0]
    return set(DATASETS) | ({extra} if extra else set())


# ---------- API side ----------

def submit(body):
    dataset, strategy = body.get("dataset"), body.get("strategy", "solar_pilot")
    support, budget, deadline = body.get("support"), body.get("memory_budget_bytes"), body.get("deadline")
    if dataset not in dataset_names():
        raise JobError(400, f"dataset must be one of {sorted(dataset_names())}")
    if strategy not in STRATEGIES:
        raise JobError(400, f"strategy must be one of {list(STRATEGIES)}")
    if type(support) not in (int, float) or not 0 < support <= 1:
        raise JobError(400, "support must be a number in (0, 1]")
    if type(budget) is not int or not 0 < budget <= MAX_BUDGET:
        raise JobError(400, "memory_budget_bytes must be a positive integer")
    if deadline is not None:
        try:
            datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
        except ValueError:
            raise JobError(400, "deadline must be an ISO 8601 time")
    with _db() as con:
        job_id = con.execute("INSERT INTO jobs (status, dataset, support, memory_budget_bytes, strategy, deadline, "
                             "created_at) VALUES ('queued', ?, ?, ?, ?, ?, ?)",
                             (dataset, float(support), budget, strategy, deadline, _now())).lastrowid
    _wake.set()
    return get(job_id)


def get(job_id):
    with _db() as con:
        row = con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise JobError(404, f"no job {job_id}")
    job = dict(row)
    job["history"] = json.loads(job["history"])
    job["stats"] = json.loads(job["stats"]) if job["stats"] else None
    return job


def recent(limit=20):
    """Newest jobs first, without the history (the list view does not need it)."""
    with _db() as con:
        rows = con.execute("SELECT id, status, dataset, support, memory_budget_bytes, strategy, setting, message, "
                           "created_at, finished_at FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


@functools.cache
def _names(dataset):
    """Product code -> name for the registered datasets. A basket file added for a test has no names."""
    return clean.descriptions() if dataset in DATASETS else {}


def results(job_id):
    """(job, rows) for a completed job. rows: [{"a", "a_name", "b", "b_name", "count"}] sorted by count."""
    job = get(job_id)
    if job["status"] != "completed":
        raise JobError(409, f"job {job_id} is {job['status']}, results exist only for completed jobs")
    names = _names(job["dataset"])
    with open(_result_path(job_id), newline="", encoding="utf-8") as f:
        return job, [{"a": r["a"], "a_name": str(names.get(r["a"], "")).strip(), "b": r["b"],
                      "b_name": str(names.get(r["b"], "")).strip(), "count": int(r["count"])} for r in csv.DictReader(f)]


# ---------- worker side ----------

def _mine(job, setting):
    """Run the exact count in a separate process. Returns its stats dict, or raises RuntimeError with the reason."""
    cmd = [sys.executable, "-m", "src.jobs", "--mine", job["dataset"], repr(job["support"]), setting,
           str(_result_path(job["id"]))]
    try:
        p = subprocess.run(cmd, cwd=clean.ROOT, capture_output=True, text=True, timeout=MINE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"mining process timed out after {MINE_TIMEOUT_S} s")
    if p.returncode != 0:
        raise RuntimeError(f"mining process exit {p.returncode}: {p.stderr.strip()[-300:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def process(job_id):
    """Select a setting and run one job to the end. Every outcome is written to the job row."""
    job = get(job_id)
    _update(job_id, status="running", started_at=_now())
    try:
        mining = MiningJob(baskets(job["dataset"]), job["support"], job["memory_budget_bytes"])
        selector = MiningSelector(mining, job["strategy"], emit=lambda e: _add_event(job_id, e))
        t0 = time.perf_counter()
        setting = selector.select()  # profile + choice (+ Solar calls and pilot)
        select_s = time.perf_counter() - t0
        try:
            stats = _mine(job, setting)
        except RuntimeError as e:
            _add_event(job_id, {"event": "mining_failed", "setting": setting, "reason": str(e)})
            if job["strategy"] != "solar_pilot":
                raise
            t0 = time.perf_counter()
            setting = selector.reselect(setting, str(e))  # at most once
            select_s += time.perf_counter() - t0
            stats = _mine(job, setting)
        finished = _now()
        total_s = (datetime.fromisoformat(finished) - datetime.fromisoformat(job["created_at"])).total_seconds()
        stats.update(select_seconds=select_s, total_seconds=total_s,
                     modeled_memory_bytes=mining.profile()["settings"][setting]["modeled_memory_bytes"])
        _update(job_id, status="completed", finished_at=finished, setting=setting, stats=json.dumps(stats),
                message=f"{stats['n_frequent_pairs']} frequent pairs with {setting}")
    except Exception as e:  # the worker must survive any job
        _update(job_id, status="failed", finished_at=_now(), message=str(e)[:500])


def _work():
    while True:
        with _db() as con:
            row = con.execute("SELECT id FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1").fetchone()
        if row is None:
            _wake.wait(timeout=5)
            _wake.clear()
            continue
        process(row["id"])


def start_worker():
    """Start the worker thread once. Jobs left running by an earlier server are marked failed."""
    with _db() as con:
        con.execute("UPDATE jobs SET status = 'failed', message = 'server restarted while the job was running', "
                    "finished_at = ? WHERE status = 'running'", (_now(),))
    if not any(t.name == "job-worker" for t in threading.enumerate()):
        threading.Thread(target=_work, name="job-worker", daemon=True).start()


# ---------- mining process ----------

def _peak_rss():
    """Peak resident memory of this process in bytes (None on Windows: no resource module)."""
    try:
        import resource
    except ImportError:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024  # macOS reports bytes, Linux kilobytes


def mine(dataset, support, setting, out):
    """Count the full input with one setting, write the pairs CSV, and return stats (pass 1 + pass 2 time)."""
    if setting not in SETTINGS:
        raise SystemExit(f"unknown setting {setting}")
    job = MiningJob(baskets(dataset), support, MAX_BUDGET)  # the budget was checked by the worker
    before = _peak_rss()
    t0 = time.perf_counter()
    result = job._run(setting, job._baskets, job._threshold)  # no second profile here: only the count is timed
    seconds = time.perf_counter() - t0
    pairs = sorted(result["pairs"].items(), key=lambda kv: (-kv[1], kv[0]))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["a", "b", "count"])
        w.writerows((a, b, c) for (a, b), c in pairs)
    return {"setting": setting, "n_frequent_pairs": len(pairs), "n_candidates": result["n_candidates"],
            "mining_seconds": seconds, "rss_before_mining_bytes": before, "peak_rss_bytes": _peak_rss()}


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--mine":
        print(json.dumps(mine(sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5])))
    else:
        raise SystemExit("usage: python -m src.jobs --mine DATASET SUPPORT SETTING OUT.csv")
