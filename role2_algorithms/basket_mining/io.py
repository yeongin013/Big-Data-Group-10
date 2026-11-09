"""File adapters only. CSV is order-line format: basket_id,product_id."""
import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .models import BasketDataset


def load_dataset(path):
    path = Path(path)
    if path.suffix.lower() == ".json":
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(rows, list):
            raise ValueError("JSON must contain a list of baskets")
    elif path.suffix.lower() == ".csv":
        baskets = defaultdict(list)
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not {"basket_id", "product_id"} <= set(reader.fieldnames or []):
                raise ValueError("CSV needs basket_id and product_id columns")
            for row in reader:
                if not row["basket_id"].strip():
                    raise ValueError("Blank basket_id")
                baskets[row["basket_id"]].append(row["product_id"])
        rows = baskets.values()
    elif path.suffix.lower() == ".txt":
        # Plain FIMI-style itemset lines, NOT SPMF sequences or utility records.
        rows = []
        for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith(("#", "%", "@")):
                continue
            if ":" in line or any(x in {"-1", "-2"} for x in line.split()):
                raise ValueError(f"Line {number}: sequential/utility format requires a separate adapter")
            rows.append(line.split())
    else:
        raise ValueError("Supported formats: .json, .csv, .txt")
    return BasketDataset.from_rows(rows)


def input_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_mining_output(directory, result, rules, metadata):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"algorithm": result.algorithm, "n_baskets": result.n_baskets,
               "min_count": result.min_count, "max_size": result.max_size,
               "stats": asdict(result.stats), "metadata": metadata,
               "itemsets": [{"items": list(items), "count": count, "support": count / result.n_baskets}
                            for items, count in sorted(result.frequent_itemsets.items(), key=lambda x: (len(x[0]), x[0]))]}
    (directory / "itemsets.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (directory / "rules.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["antecedent", "consequent", "count", "support", "confidence", "lift"])
        writer.writeheader()
        for rule in rules:
            row = asdict(rule)
            for side in ("antecedent", "consequent"):
                row[side] = json.dumps(row[side], ensure_ascii=False)
            writer.writerow(row)
