"""
Add two huge files of numbers line by line and write the totals to a third file,
three ways: single-threaded, multithreaded and multiprocessing.

Each line i of totalfile.txt = line i of hugefile1.txt + line i of hugefile2.txt.
The files are too large to load into memory, so everything streams.

How the parallel versions split the work:
  * Each worker gets a range of LINES, found by scanning byte offsets of line starts
    once (cheap compared to parsing) so both files stay aligned line for line.
  * Each worker writes its own part file; parts are concatenated in order at the
    end, so the output order is always correct.

Usage:
    python sum_files.py --mode single
    python sum_files.py --mode threads --workers 4
    python sum_files.py --mode processes --workers 8
    python sum_files.py --mode all      # run all three and verify outputs match
"""
import argparse
import hashlib
import multiprocessing as mp
import os
import shutil
import threading
import time

FILE1, FILE2, OUTPUT = "hugefile1.txt", "hugefile2.txt", "totalfile.txt"
BUFFER = 8 * 1024 * 1024


def run_single(out_path=OUTPUT):
    with open(FILE1) as f1, open(FILE2) as f2, open(out_path, "w", buffering=BUFFER) as out:
        for a, b in zip(f1, f2):
            out.write(f"{int(a) + int(b)}\n")


def line_offsets(path, n_chunks):
    """Byte offsets where each of n_chunks equal line ranges begins, plus total lines."""
    with open(path, "rb") as f:
        total = sum(buf.count(b"\n") for buf in iter(lambda: f.read(BUFFER), b""))
    per_chunk = -(-total // n_chunks)
    targets = {i * per_chunk for i in range(n_chunks)}
    offsets, line_no, pos = [], 0, 0
    with open(path, "rb") as f:
        for line in f:
            if line_no in targets:
                offsets.append(pos)
            pos += len(line)
            line_no += 1
    offsets.append(pos)
    counts = [min(per_chunk, total - i * per_chunk) for i in range(len(offsets) - 1)]
    return offsets, counts


def process_chunk(args):
    """Sum `count` lines starting at the given byte offsets and write a part file."""
    off1, off2, count, part_path = args
    with open(FILE1, "rb") as f1, open(FILE2, "rb") as f2, \
         open(part_path, "w", buffering=BUFFER) as out:
        f1.seek(off1)
        f2.seek(off2)
        for _ in range(count):
            out.write(f"{int(f1.readline()) + int(f2.readline())}\n")
    return part_path


def build_tasks(workers):
    offs1, counts = line_offsets(FILE1, workers)
    offs2, _ = line_offsets(FILE2, workers)
    return [(offs1[i], offs2[i], counts[i], f"{OUTPUT}.part{i:02d}") for i in range(len(counts))]


def merge(parts, out_path):
    with open(out_path, "wb") as out:
        for p in parts:
            with open(p, "rb") as f:
                shutil.copyfileobj(f, out, BUFFER)
            os.remove(p)


def run_threads(workers, out_path=OUTPUT):
    tasks = build_tasks(workers)
    threads = [threading.Thread(target=process_chunk, args=(t,)) for t in tasks]
    for t in threads:
        t.start()
    for t in threads:          # join every thread, not just the last one
        t.join()
    merge([t[3] for t in tasks], out_path)


def run_processes(workers, out_path=OUTPUT):
    tasks = build_tasks(workers)
    with mp.Pool(workers) as pool:
        parts = pool.map(process_chunk, tasks)
    merge(parts, out_path)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for buf in iter(lambda: f.read(BUFFER), b""):
            h.update(buf)
    return h.hexdigest()


def timed(label, fn, *args):
    start = time.perf_counter()
    fn(*args)
    elapsed = time.perf_counter() - start
    print(f"{label:<28}{elapsed:8.2f} s")
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["single", "threads", "processes", "all"], default="all")
    parser.add_argument("--workers", type=int, default=os.cpu_count())
    args = parser.parse_args()

    if args.mode == "single":
        timed("Single-threaded:", run_single)
    elif args.mode == "threads":
        timed(f"Multithreaded ({args.workers}):", run_threads, args.workers)
    elif args.mode == "processes":
        timed(f"Multiprocessing ({args.workers}):", run_processes, args.workers)
    else:
        print(f"Workers: {args.workers} | CPU cores: {os.cpu_count()}")
        t1 = timed("Single-threaded:", run_single, "total_single.txt")
        t2 = timed(f"Multithreaded ({args.workers}):", run_threads, args.workers, "total_threads.txt")
        t3 = timed(f"Multiprocessing ({args.workers}):", run_processes, args.workers, "total_processes.txt")
        same = sha256("total_single.txt") == sha256("total_threads.txt") == sha256("total_processes.txt")
        print(f"\nAll three outputs identical: {same}")
        print(f"Multithreading speedup:   {t1 / t2:.2f}x")
        print(f"Multiprocessing speedup:  {t1 / t3:.2f}x")


if __name__ == "__main__":
    main()
