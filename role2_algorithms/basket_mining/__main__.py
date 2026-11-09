"""명령행 실행: python -m basket_mining --help"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from . import mine_apriori, mine_pcy, support_to_count, generate_rules
from .benchmark import compare, save_report
from .io import load_dataset, input_sha256, write_mining_output


def main():
    parser = argparse.ArgumentParser(description="Role 2: independent frequent itemset mining")
    commands = parser.add_subparsers(dest="command", required=True)
    mining = commands.add_parser("mine")
    mining.add_argument("--algorithm", choices=["apriori", "pcy"], required=True)
    mining.add_argument("--input", type=Path, required=True)
    threshold = mining.add_mutually_exclusive_group(required=True)
    threshold.add_argument("--min-count", type=int)
    threshold.add_argument("--min-support")
    mining.add_argument("--buckets", type=int, default=65_521)
    mining.add_argument("--max-size", type=int, choices=[2, 3], default=2)
    mining.add_argument("--min-confidence", type=float, default=0.5)
    mining.add_argument("--min-lift", type=float, default=1.0)
    mining.add_argument("--out", type=Path, required=True)
    bench = commands.add_parser("benchmark")
    bench.add_argument("--input", type=Path, required=True)
    bench.add_argument("--supports", nargs="+", default=["0.02", "0.01", "0.005", "0.0025"])
    bench.add_argument("--buckets", type=int, nargs="+", default=[65_521, 1_048_573])
    bench.add_argument("--max-size", type=int, choices=[2, 3], default=2)
    bench.add_argument("--repeats", type=int, default=3)
    bench.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        dataset = load_dataset(args.input)
        metadata = {"input": str(args.input.resolve()), "input_sha256": input_sha256(args.input), "n_items": dataset.n_items}
        if args.command == "mine":
            threshold = args.min_count if args.min_count is not None else support_to_count(len(dataset), args.min_support)
            if args.algorithm == "apriori":
                result = mine_apriori(dataset, threshold, args.max_size)
            else:
                result = mine_pcy(dataset, threshold, args.buckets, args.max_size)
            rules = generate_rules(result, args.min_confidence, args.min_lift)
            metadata.update(min_confidence=args.min_confidence, min_lift=args.min_lift, min_support=args.min_support)
            write_mining_output(args.out, result, rules, metadata)
            print(json.dumps({"algorithm": result.algorithm, "baskets": len(dataset),
                              "pairs": len(result.of_size(2)), "triples": len(result.of_size(3)),
                              "rules": len(rules), "stats": asdict(result.stats)}, ensure_ascii=False, indent=2))
        else:
            rows = compare(dataset, args.supports, args.buckets, args.repeats, args.max_size)
            save_report(args.out, rows, {**metadata, "repeats": args.repeats})
            print(f"Verified equal itemsets; saved {len(rows)} comparison rows to {args.out}")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
