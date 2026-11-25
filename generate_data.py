"""Create two test files of random integers, one per line.

Usage:
    python generate_data.py --lines 20000000
The original assignment used 1,000,000,000 lines per file (about 10 GB each).
"""
import argparse
import random


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lines", type=int, default=20_000_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    chunk = 1_000_000
    for name in ("hugefile1.txt", "hugefile2.txt"):
        with open(name, "w") as f:
            remaining = args.lines
            while remaining:
                n = min(chunk, remaining)
                f.write("\n".join(str(rng.randint(0, 1_000_000)) for _ in range(n)) + "\n")
                remaining -= n
        print(f"Wrote {args.lines:,} lines to {name}")


if __name__ == "__main__":
    main()
