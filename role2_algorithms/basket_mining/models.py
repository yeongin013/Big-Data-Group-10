"""Data contracts only. Algorithms, file formats, and presentation stay elsewhere."""
from dataclasses import dataclass, field
from itertools import chain

Itemset = tuple[str, ...]


@dataclass(frozen=True)
class BasketDataset:
    baskets: tuple[Itemset, ...]

    def __post_init__(self):
        if not isinstance(self.baskets, tuple):
            raise ValueError("Use BasketDataset.from_rows() to normalize baskets")
        for basket in self.baskets:
            if not isinstance(basket, tuple):
                raise ValueError("Use BasketDataset.from_rows() to normalize baskets")
            if any(not isinstance(x, str) or not x.strip() for x in basket):
                raise ValueError("Items must be non-empty strings")
            if tuple(sorted(set(basket))) != basket:
                raise ValueError("Baskets must be sorted and deduplicated")

    @classmethod
    def from_rows(cls, rows):
        """One row = one basket. Counts presence, not quantity. Empty baskets remain."""
        baskets = []
        for row in rows:
            if isinstance(row, (str, bytes)):
                raise ValueError("A basket must be a sequence of items, not a string")
            items = set()
            for item in row:
                if isinstance(item, bool) or not isinstance(item, (str, int)):
                    raise ValueError("Item IDs must be strings or integers")
                value = str(item).strip()
                if not value:
                    raise ValueError("Blank item ID")
                items.add(value)
            baskets.append(tuple(sorted(items)))
        return cls(tuple(baskets))

    def __len__(self):
        return len(self.baskets)

    @property
    def n_items(self):
        return len(set(chain.from_iterable(self.baskets)))


@dataclass
class MiningStats:
    # Identical definitions for both algorithms, including sparse counting storage.
    frequent_singletons: int = 0
    possible_frequent_item_pairs: int = 0
    pair_candidates_observed: int = 0  # distinct pairs actually inserted into pair counter
    pair_occurrences_examined: int = 0  # frequent-item pair occurrences tested in pass 2
    pair_count_updates: int = 0  # occurrences counted after filtering
    bucket_count: int | None = None
    frequent_bucket_ratio: float | None = None
    bucket_counter_bytes: int | None = None  # array payload only, not peak RAM
    bitmap_payload_bytes: int | None = None
    triple_candidates: int = 0
    triple_count_updates: int = 0


@dataclass
class MiningResult:
    algorithm: str
    n_baskets: int
    min_count: int
    max_size: int
    item_counts: dict[str, int]
    frequent_itemsets: dict[Itemset, int]
    stats: MiningStats = field(default_factory=MiningStats)
    bucket_counts: tuple[int, ...] | None = None  # optional teaching diagnostics; excluded from benchmarks

    def of_size(self, size):
        return {items: count for items, count in self.frequent_itemsets.items() if len(items) == size}
