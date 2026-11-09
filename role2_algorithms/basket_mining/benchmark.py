"""시간 측정과 메모리 측정을 나눠 실행한다."""
import csv
import gc
import json
import platform
import statistics
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path

from .algorithms import apriori, pcy
from .thresholds import support_to_count


def measure(fn, repeats):
    fn()  # same explicit warm-up policy for both algorithms
    timings = []
    for _ in range(repeats):
        gc.collect()
        start = time.perf_counter()
        result = fn()
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
        del result
    gc.collect()
    tracemalloc.start()
    try:
        result = fn()
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    return result, {"median_seconds": statistics.median(timings), "min_seconds": min(timings),
                    "max_seconds": max(timings), "tracemalloc_peak_bytes": peak}


def compare(dataset, supports, bucket_sizes, repeats=3, max_size=2):
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    supports, bucket_sizes = list(supports), list(bucket_sizes)
    if not supports or not bucket_sizes:
        raise ValueError("At least one support and bucket size are required")
    rows = []
    for support in supports:
        threshold = support_to_count(len(dataset), support)
        expected, timing = measure(lambda: apriori.mine(dataset, threshold, max_size), repeats)
        rows.append(_row(expected, support, timing))
        for buckets in bucket_sizes:
            result, timing = measure(lambda: pcy.mine(dataset, threshold, buckets, max_size), repeats)
            if result.frequent_itemsets != expected.frequent_itemsets:
                raise AssertionError("PCY and A-Priori disagree")
            rows.append(_row(result, support, timing))
    return rows


def _row(result, support, timing):
    return {"algorithm": result.algorithm, "min_support": str(support), "min_count": result.min_count,
            "max_size": result.max_size, "n_baskets": result.n_baskets,
            "frequent_pairs": len(result.of_size(2)), "frequent_triples": len(result.of_size(3)),
            **asdict(result.stats), **timing}


def save_report(directory, rows, metadata):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "comparison.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    info = {"python": platform.python_version(), "platform": platform.platform(),
            "processor": platform.processor(), "timing": "1 warm-up; repeated timings; separate tracemalloc run",
            "memory_scope": "tracked allocations during miner call; excludes preloaded input; not process RSS",
            "comparison": "sparse pair counters in both implementations; timing includes miner setup and optional triples",
            **metadata}
    (directory / "environment.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
