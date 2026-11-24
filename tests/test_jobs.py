"""H4 job server, offline: a tiny basket file, a temporary SQLite file, the real mining subprocess, no Solar.
Run: python -m tests.test_jobs
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src import agent, api, apriori, jobs

BASKETS = [["a", "b", "c"]] * 6 + [["a", "b"]] * 3 + [["c", "d"]] * 2 + [["d"]]  # 12 baskets
BODY = {"dataset": "tiny", "support": 0.25, "memory_budget_bytes": 64 * 1024 ** 2, "strategy": "rules"}


def _choose_first(messages, specs):
    """Scripted Solar: choose the first setting the server lists as feasible."""
    feasible = json.loads(messages[1]["content"])["feasible"]
    return {"role": "assistant", "tool_calls": [{"id": "1", "function": {
        "name": "choose", "arguments": json.dumps({"setting": feasible[0], "reason": "test"})}}]}


def test_job_server():
    with tempfile.TemporaryDirectory() as d:
        data = Path(d) / "tiny.json"
        data.write_text(json.dumps(BASKETS), encoding="utf-8")
        jobs.baskets.cache_clear()
        with patch.object(jobs, "DB", Path(d) / "jobs.sqlite"), \
             patch.dict(os.environ, {"JOBS_DATASET_FILE": f"tiny={data}"}):
            # bad requests and unknown jobs
            for bad in ({**BODY, "dataset": "../etc"}, {**BODY, "support": 0}, {**BODY, "support": "0.1"},
                        {**BODY, "memory_budget_bytes": 1.5}, {**BODY, "strategy": "gpt"}, {**BODY, "deadline": "soon"}):
                try:
                    api.route("POST", "/api/jobs", bad)
                except api.ApiError as e:
                    assert e.status == 400, bad
                else:
                    raise AssertionError(f"accepted {bad}")
            for url, status in (("/api/jobs/999", 404), ("/api/jobs/999/results", 404)):
                try:
                    api.route("GET", url)
                except api.ApiError as e:
                    assert e.status == status
                else:
                    raise AssertionError(url)

            # rules strategy: queued -> completed, pairs equal to the fixed A-Priori run
            job = api.route("POST", "/api/jobs", {**BODY, "deadline": "2026-12-01T09:00:00Z"})
            assert job["status"] == "queued" and job["history"] == []
            try:
                api.route("GET", f"/api/jobs/{job['id']}/results")
            except api.ApiError as e:
                assert e.status == 409
            jobs.process(job["id"])
            done = api.route("GET", f"/api/jobs/{job['id']}")
            assert done["status"] == "completed" and done["setting"] == "apriori", done["message"]
            assert [e["event"] for e in done["history"]] == ["profile", "selected"]
            assert done["stats"]["n_solar_calls"] == 0 and done["stats"]["n_pilots"] == 0 and done["stats"]["profile_seconds"] > 0
            assert done["stats"]["mining_seconds"] > 0 and done["stats"]["total_seconds"] >= done["stats"]["select_seconds"]
            expected = apriori.run([tuple(t) for t in BASKETS], apriori.min_count(len(BASKETS), 0.25))["pairs"]
            res = api.route("GET", f"/api/jobs/{job['id']}/results")
            assert {(r["a"], r["b"]): r["count"] for r in res["pairs"]} == expected and len(expected) == 3
            csv_reply = api.route("GET", f"/api/jobs/{job['id']}/results?format=csv")
            assert isinstance(csv_reply, api.Csv) and csv_reply.raw.decode().splitlines()[0] == "a,a_name,b,b_name,count"
            assert len(csv_reply.raw.decode().splitlines()) == 4
            assert len(api.route("GET", f"/api/jobs/{job['id']}/results?limit=2")["pairs"]) == 2
            listed = api.route("GET", "/api/jobs")["jobs"]
            assert listed[0]["id"] == job["id"] and listed[0]["status"] == "completed" and "history" not in listed[0]

            # Solar unavailable: the rule baseline takes over and the job still completes
            with patch.object(agent, "chat", side_effect=SystemExit("no key")):
                job = api.route("POST", "/api/jobs", {**BODY, "strategy": "solar_once"})
                jobs.process(job["id"])
            done = jobs.get(job["id"])
            assert done["status"] == "completed"
            assert [e["event"] for e in done["history"]] == ["profile", "fallback", "selected"]
            assert done["history"][-1]["source"] == "rules_fallback"

            # mining process fails once: solar_pilot reselects another setting, other strategies fail
            real_mine, attempts = jobs._mine, []

            def fail_once(job, setting):
                attempts.append(setting)
                if len(attempts) == 1:
                    raise RuntimeError("out of memory")
                return real_mine(job, setting)

            with patch.object(agent, "chat", side_effect=_choose_first), \
                 patch.object(jobs, "_mine", side_effect=fail_once) as m:
                job = api.route("POST", "/api/jobs", {**BODY, "strategy": "solar_pilot"})
                jobs.process(job["id"])
                assert m.call_args_list[0].args[1] != m.call_args_list[1].args[1]
            done = jobs.get(job["id"])
            assert done["status"] == "completed" and done["setting"] == "pcy_small"
            assert done["stats"]["n_solar_calls"] == 2  # one choice, then one more after the failure
            assert "mining_failed" in [e["event"] for e in done["history"]]
            assert "reselection" in [e["event"] for e in done["history"]]
            with patch.object(jobs, "_mine", side_effect=RuntimeError("out of memory")):
                job = api.route("POST", "/api/jobs", BODY)
                jobs.process(job["id"])
            assert jobs.get(job["id"])["status"] == "failed"

            # no setting fits the budget
            job = api.route("POST", "/api/jobs", {**BODY, "memory_budget_bytes": 1})
            jobs.process(job["id"])
            failed = jobs.get(job["id"])
            assert failed["status"] == "failed" and "budget" in failed["message"]

            # a job left running by an earlier server is marked failed at start
            job = api.route("POST", "/api/jobs", BODY)
            jobs._update(job["id"], status="running")
            with patch.object(jobs.threading, "Thread"):
                jobs.start_worker()
            assert jobs.get(job["id"])["status"] == "failed"
        jobs.baskets.cache_clear()


if __name__ == "__main__":
    test_job_server()
    print("ok test_job_server")
