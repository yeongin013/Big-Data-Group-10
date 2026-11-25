"""H4 comparison experiment: three selection strategies under the same conditions (plan/selection_compare.md).

    python scripts/run_selection_compare.py                    # 5 repeats, writes results/selection_compare.csv
    python scripts/run_selection_compare.py --repeats 1 --out /tmp/try.csv --strategies rules

Each row is one job: condition x strategy x repeat. Jobs go through src.jobs (SQLite row, selection,
mining in a separate process), one at a time, so t_total_s has no queue wait. Rows with strategy
"fixed:<setting>" run one setting without selection: they give the reference pairs and the fastest
setting per condition (best_ok). solar_once and solar_pilot call Solar: the script stops at the start
if UPSTAGE_API_KEY is missing. A Solar failure during the run falls back to the rule baseline and the
row says source rules_fallback. Within each repeat the strategies run one after another, and the
starting strategy rotates, so a change in Solar latency over the run does not land on one strategy.
Jobs are stored in data/jobs/selection_compare/ (--db), apart from the jobs of the demo page.
Times depend on the machine and on Solar latency. Run it on the reference machine only.
"""
import argparse
import csv
import datetime
import json
import platform
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import agent, jobs  # noqa: E402
from src.mining_job import SETTINGS, MiningJob  # noqa: E402
from src.mining_selection import valid_settings  # noqa: E402

MIB = 1024 ** 2
# name, dataset, support, memory budget in bytes (reviews/h4_progress.md, decisions A, B, D)
CONDITIONS = [("B0", "y1", 0.01, 64 * MIB), ("B1", "y1", 0.01, int(3.5 * MIB)),
              ("B0.25", "y1", 0.0025, 6 * MIB), ("B0.25-all", "all", 0.0025, 6 * MIB)]
COLUMNS = ["condition", "dataset", "support", "memory_budget_bytes", "strategy", "repeat", "status", "selected", "source",
           "pairs_ok", "best_ok", "t_profile_s", "t_pilot_s", "t_select_s", "t_mining_s",
           "t_pcy_pass1_s", "t_pcy_pass2_s", "t_total_s",
           "mem_model_bytes", "mem_peak_bytes", "mem_mining_increase_bytes", "n_solar_calls", "n_pilots", "failures", "job_id",
           "run_at", "commit", "solar_model", "python", "machine"]


def failures(history):
    """Failure classes of plan/selection_compare.md section 4, from the job history."""
    found = []
    for e in history:
        reason = str(e.get("reason", ""))
        if e["event"] == "failed":
            found.append("no_feasible")
        elif e["event"] == "invalid_tool_call":
            found.append("invalid_call")
        elif e["event"] == "mining_failed":
            found.append("run_failed")
        elif e["event"] == "fallback":
            found.append("no_selection" if "selection" in reason else "solar_error" if "HTTP" in reason else "solar_unreachable")
    return ",".join(dict.fromkeys(found))


def fixed_run(dataset, support, setting):
    """One setting without selection, in its own process. Returns (stats, {pair: count})."""
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "pairs.csv"
        p = subprocess.run([sys.executable, "-m", "src.jobs", "--mine", dataset, repr(support), setting, str(out)],
                           cwd=ROOT, capture_output=True, text=True, check=True)
        with open(out, newline="", encoding="utf-8") as f:
            pairs = {(r["a"], r["b"]): int(r["count"]) for r in csv.DictReader(f)}
    return json.loads(p.stdout.strip().splitlines()[-1]), pairs


def provenance():
    """Same for every row of one run: when, which code, which Solar model, which machine."""
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()  # noqa: E731
    return {"run_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "commit": git("rev-parse", "--short", "HEAD") + ("-dirty" if git("status", "--porcelain") else ""),
            "solar_model": agent.MODEL,  # the model requested
            "python": platform.python_version(), "machine": f"{platform.system()} {platform.machine()}"}


def run(repeats, strategies, conditions):
    rows = []
    for name, dataset, support, budget in conditions:
        base = {"condition": name, "dataset": dataset, "support": support, "memory_budget_bytes": budget}
        mining = MiningJob(jobs.baskets(dataset), support, budget)
        feasible = valid_settings(mining)
        times, reference = {}, None
        for setting in feasible:  # fixed runs: reference pairs and the fastest feasible setting
            runs = [fixed_run(dataset, support, setting) for _ in range(repeats)]
            reference = reference or runs[0][1]
            assert all(pairs == reference for _, pairs in runs), f"{name}: {setting} differs from the reference pairs"
            times[setting] = statistics.median(s["mining_seconds"] for s, _ in runs)
            for k, (s, _) in enumerate(runs, 1):
                rows.append({**base, "strategy": f"fixed:{setting}", "repeat": k, "status": "completed", "selected": setting,
                             "source": "fixed", "pairs_ok": True, "t_mining_s": s["mining_seconds"],
                             "t_pcy_pass1_s": s.get("pass1_seconds"), "t_pcy_pass2_s": s.get("pass2_seconds"),
                             "mem_model_bytes": mining.profile()["settings"][setting]["modeled_memory_bytes"],
                             "mem_peak_bytes": s["peak_rss_bytes"],
                             "mem_mining_increase_bytes": (s["peak_rss_bytes"] or 0) - (s["rss_before_mining_bytes"] or 0)})
        best = min(times, key=times.get) if times else None
        print(f"{name}: feasible {feasible}, fixed medians {({k: round(v, 3) for k, v in times.items()})}, fastest {best}")
        for k in range(1, repeats + 1):
            for strategy in strategies[(k - 1) % len(strategies):] + strategies[:(k - 1) % len(strategies)]:
                job_id = jobs.submit({"dataset": dataset, "support": support, "memory_budget_bytes": budget,
                                      "strategy": strategy})["id"]
                jobs.process(job_id)
                job = jobs.get(job_id)
                row = {**base, "strategy": strategy, "repeat": k, "status": job["status"], "job_id": job_id,
                       "failures": failures(job["history"])}
                chosen = [e for e in job["history"] if e["event"] == "selected"]
                if chosen:
                    row["source"] = chosen[-1]["source"]
                if job["status"] == "completed":
                    s = job["stats"]
                    _, pairs = jobs.results(job_id)
                    row.update(selected=job["setting"], best_ok=job["setting"] == best,
                               pairs_ok={(r["a"], r["b"]): r["count"] for r in pairs} == reference,
                               t_profile_s=s["profile_seconds"], t_select_s=s["select_seconds"],
                               t_pilot_s=sum(e["result"]["elapsed_s"] for e in job["history"] if e["event"] == "pilot"),
                               t_mining_s=s["mining_seconds"], t_total_s=s["total_seconds"],
                               t_pcy_pass1_s=s.get("pass1_seconds"), t_pcy_pass2_s=s.get("pass2_seconds"),
                               mem_model_bytes=s["modeled_memory_bytes"], mem_peak_bytes=s["peak_rss_bytes"],
                               mem_mining_increase_bytes=(s["peak_rss_bytes"] or 0) - (s["rss_before_mining_bytes"] or 0),
                               n_solar_calls=s["n_solar_calls"], n_pilots=s["n_pilots"])
                rows.append(row)
                print(f"  {strategy} {k}: {job['status']} {job['setting']} total {row.get('t_total_s', 0):.2f} s {row['failures']}")
    return rows


def summary(rows):
    """Median total time and the chosen settings per condition and strategy."""
    keys = dict.fromkeys((r["condition"], r["strategy"]) for r in rows if not r["strategy"].startswith("fixed:"))
    for cond, strategy in keys:
        group = [r for r in rows if (r["condition"], r["strategy"]) == (cond, strategy)]
        done = [r for r in group if r["status"] == "completed"]
        total = statistics.median(r["t_total_s"] for r in done) if done else float("nan")
        print(f"{cond:10} {strategy:12} completed {len(done)}/{len(group)}  median total {total:6.2f} s  "
              f"selected {sorted({r['selected'] for r in done})}  pairs_ok {all(r['pairs_ok'] for r in done)}  "
              f"best_ok {sum(bool(r['best_ok']) for r in done)}/{len(done)}")


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--repeats", type=int, default=5)
    a.add_argument("--strategies", nargs="+", default=list(jobs.STRATEGIES), choices=jobs.STRATEGIES)
    a.add_argument("--conditions", nargs="+", default=[c[0] for c in CONDITIONS], choices=[c[0] for c in CONDITIONS])
    a.add_argument("--out", default=str(ROOT / "results" / "selection_compare.csv"))
    a.add_argument("--db", default=str(jobs.DB.parent / "selection_compare" / "jobs.sqlite"),
                   help="job store of this run (job_id refers to it)")
    args = a.parse_args()
    assert set(SETTINGS) == {"apriori", "pcy_small", "pcy_large"}
    if set(args.strategies) - {"rules"}:
        agent.api_key()  # stops here without a key, before any job runs
    jobs.DB = Path(args.db)
    stamp = provenance()
    result = [{**r, **stamp} for r in
              run(args.repeats, args.strategies, [c for c in CONDITIONS if c[0] in args.conditions])]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(result)
    print(f"\nWrote {len(result)} rows to {args.out}")
    summary(result)
