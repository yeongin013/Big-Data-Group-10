"""PCY: pair hashing in pass 1, packed bitmap filtering in pass 2, exact final counts."""
from array import array
from collections import Counter
from itertools import combinations

from ..models import BasketDataset, MiningResult, MiningStats
from ..thresholds import validate_min_count
from ..extensions.triples import extend_triples

HASH_MULTIPLIER = 1_000_003


def bucket_index(i: int, j: int, n_buckets: int) -> int:
    """IDs must satisfy i < j. Integer arithmetic gives a reproducible hash."""
    return (i * HASH_MULTIPLIER + j) % n_buckets


def pack_frequent_buckets(counts, min_count):
    bits = bytearray((len(counts) + 7) // 8)
    n_frequent = 0
    for bucket, count in enumerate(counts):
        if count >= min_count:
            bits[bucket // 8] |= 1 << (bucket % 8)
            n_frequent += 1
    return bits, n_frequent


def is_frequent_bucket(bits, bucket):
    return bool(bits[bucket // 8] & (1 << (bucket % 8)))


def mine(dataset: BasketDataset, min_count: int, n_buckets: int = 65_521, max_size: int = 2,
         *, capture_buckets: bool = False) -> MiningResult:
    validate_min_count(min_count)
    if isinstance(n_buckets, bool) or not isinstance(n_buckets, int) or n_buckets < 1:
        raise ValueError("n_buckets must be a positive integer")
    if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size not in (2, 3):
        raise ValueError("max_size must be 2 or 3")
    # Stable integer IDs are local to this run; original item IDs are returned unchanged.
    codes = sorted({item for basket in dataset.baskets for item in basket})
    ids = {item: i for i, item in enumerate(codes)}
    item_counts = Counter()
    bucket_counts = array("Q", [0]) * n_buckets

    # Pass 1 must hash ALL pairs, including items not yet known to be frequent.
    for basket in dataset.baskets:
        item_counts.update(basket)
        for a, b in combinations(basket, 2):
            bucket_counts[bucket_index(ids[a], ids[b], n_buckets)] += 1

    frequent = {item for item, count in item_counts.items() if count >= min_count}
    m = len(frequent)
    bitmap, n_frequent_buckets = pack_frequent_buckets(bucket_counts, min_count)
    payload = bucket_counts.itemsize * len(bucket_counts)
    diagnostic_counts = tuple(bucket_counts) if capture_buckets else None
    del bucket_counts  # Only the packed bitmap is needed in pass 2.
    stats = MiningStats(
        frequent_singletons=m, possible_frequent_item_pairs=m * (m - 1) // 2,
        bucket_count=n_buckets, frequent_bucket_ratio=n_frequent_buckets / n_buckets,
        bucket_counter_bytes=payload, bitmap_payload_bytes=len(bitmap),
    )

    # A frequent bucket is only a necessary condition. Count surviving pairs exactly.
    pair_counts = Counter()
    for basket in dataset.baskets:
        retained = [item for item in basket if item in frequent]
        for a, b in combinations(retained, 2):
            stats.pair_occurrences_examined += 1
            bucket = bucket_index(ids[a], ids[b], n_buckets)
            if is_frequent_bucket(bitmap, bucket):
                pair_counts[(a, b)] += 1
                stats.pair_count_updates += 1
    stats.pair_candidates_observed = len(pair_counts)
    itemsets = {(item,): item_counts[item] for item in sorted(frequent)}
    itemsets.update({pair: count for pair, count in sorted(pair_counts.items()) if count >= min_count})
    result = MiningResult("pcy", len(dataset), min_count, max_size, dict(item_counts), itemsets, stats)
    result.bucket_counts = diagnostic_counts
    if max_size == 3:
        extend_triples(dataset, result)
    return result
