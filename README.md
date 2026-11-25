# Processing huge files in parallel: threads vs processes

Two text files each hold one number per line. The job: add them line by line and write the totals to a third file. The original assignment used 1 billion lines per file (about 10 GB each), far too big to load into memory, so everything has to stream.

This project compares three ways to do it in Python:

1. **Single-threaded**, the baseline
2. **Multithreaded**, several threads in one process
3. **Multiprocessing**, several separate processes, one per CPU core

## Results

<!-- Replace this table with results from your own machine: python sum_files.py --mode all -->

20 million lines per file, 2 CPU cores:

| Method | Time | Speedup |
|---|---|---|
| Single-threaded | 6.51 s | 1.00x |
| Multithreaded (2 threads) | 9.57 s | 0.68x (slower) |
| Multiprocessing (2 processes) | 6.10 s | 1.07x |

All three produce byte-for-byte identical output, which the script checks with a SHA-256 hash.

**Why threads made it slower:** Python's Global Interpreter Lock (GIL) lets only one thread run Python code at a time. Parsing and adding numbers is CPU work, so threads just take turns and add coordination overhead. Separate processes each get their own interpreter and run truly in parallel, so multiprocessing scales with the number of cores.

## What I fixed from the first version

I first built this for a graduate operating systems course. Reviewing it later, I found bugs that made the original timing comparison unreliable:

- The single-threaded version added `line1 + line1` instead of `line1 + line2`, so its output was wrong.
- The multithreaded version used line numbers as byte offsets in `seek()`, so threads read from the wrong positions. All threads also appended to the same output file at once, scrambling the order.
- The join loop reused the variable name (`for threads in threads: thread.join()`), so it only waited for the last thread. The timer stopped before the work finished, which made threads look faster than they were.

This version fixes all three. Each worker gets an exact line range found by scanning line-start byte offsets, writes its own part file, and the parts are merged in order. Every run now verifies that all three methods produce the same output.

## Run it

```bash
python generate_data.py --lines 20000000      # creates hugefile1.txt and hugefile2.txt
python sum_files.py --mode all                # runs all three and verifies the output
python sum_files.py --mode processes --workers 8
```

No third-party packages needed. The generated files are about 140 MB each at 20 million lines.

## Built with

Python standard library: multiprocessing, threading, hashlib
