"""
Compare two sets of pytest-benchmark runs (baseline vs branch) and fail
when a benchmark has regressed.

Single benchmark runs are too noisy to gate on: process-level effects
(hash randomization, memory layout, CPU frequency, runner load) shift
individual timings by 20-40% between runs of identical code. Instead of
comparing one run against one run, this script expects several
interleaved runs per side and only reports a regression when the branch
is *consistently* slower than the baseline:

    fail if min(branch medians) > max(baseline medians) * (1 + threshold)

i.e. the fastest branch run must be slower than the slowest baseline
run by more than the threshold. A whole-process outlier on either side
then can't produce a false positive, because the comparison always uses
the branch's luckiest run against the baseline's unluckiest run.

Even that gate has a noise floor: on shared CI runners, whole runs of
identical code have been observed to differ by 10-30%. The threshold
therefore has to sit above that floor, which makes this a tripwire for
gross accidental regressions rather than a precision instrument --
changes too small to trip it should be measured with deliberate
repeated local runs instead.

Usage:

    python bench/compare_runs.py \
        --baseline '.benchmarks/*/*_master?.json' \
        --branch '.benchmarks/*/*_branch?.json' \
        --threshold 0.25
"""

import argparse
import glob
import json
import os
import sys
from statistics import median


def load_runs(pattern):
    """Load benchmark stats from every file matching the glob pattern.

    Returns a list of runs, each a dict mapping benchmark name to its
    median timing in seconds.
    """
    runs = []
    for path in sorted(glob.glob(pattern)):
        with open(path) as fh:
            data = json.load(fh)
        runs.append({b["name"]: b["stats"]["median"] for b in data["benchmarks"]})
    return runs


def format_time(seconds):
    for unit, factor in [("s", 1), ("ms", 1e3), ("us", 1e6), ("ns", 1e9)]:
        if seconds * factor >= 1:
            return f"{seconds * factor:,.1f}{unit}"
    return f"{seconds * 1e9:.2f}ns"


def compare(baseline_runs, branch_runs, threshold):
    """Compare runs and return (rows, failed_names)."""
    baseline_names = set().union(*(r.keys() for r in baseline_runs))
    branch_names = set().union(*(r.keys() for r in branch_runs))

    rows = []
    failed = []
    for name in sorted(branch_names):
        if name not in baseline_names:
            rows.append((name, None, None, None, "new"))
            continue
        base = [r[name] for r in baseline_runs if name in r]
        branch = [r[name] for r in branch_runs if name in r]
        # Estimated change, for reporting only: middle-of-the-road runs
        # on both sides.
        change = (median(branch) - median(base)) / median(base)
        # Gate: the fastest branch run against the slowest baseline run.
        excess = (min(branch) - max(base)) / max(base)
        if excess > threshold:
            verdict = "FAIL"
            failed.append(name)
        else:
            verdict = ""
        rows.append((name, base, branch, change, verdict))
    for name in sorted(baseline_names - branch_names):
        rows.append((name, None, None, None, "removed"))
    return rows, failed


def render_table(rows, markdown=False):
    header = ["benchmark", "baseline medians", "branch medians", "change", ""]
    body = []
    for name, base, branch, change, verdict in rows:
        body.append(
            [
                name,
                " / ".join(format_time(t) for t in sorted(base)) if base else "-",
                " / ".join(format_time(t) for t in sorted(branch)) if branch else "-",
                f"{change:+.1%}" if change is not None else "-",
                verdict,
            ]
        )
    if markdown:
        lines = [
            "| " + " | ".join(header) + " |",
            "|" + "|".join("---" for _ in header) + "|",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in body)
        return "\n".join(lines)
    widths = [max(len(row[i]) for row in [header, *body]) for i in range(len(header))]
    lines = [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in [header, *body]
    ]
    lines.insert(1, "-" * max(len(line) for line in lines))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="glob for baseline runs")
    parser.add_argument("--branch", required=True, help="glob for branch runs")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.25,
        help="max allowed consistent slowdown, as a fraction (default: 0.25)",
    )
    args = parser.parse_args(argv)

    baseline_runs = load_runs(args.baseline)
    branch_runs = load_runs(args.branch)

    if not branch_runs:
        print(f"error: no branch runs match {args.branch!r}")
        return 2
    if not baseline_runs:
        # The baseline couldn't run at all (e.g. the branch's benchmarks
        # exercise APIs that don't exist on the baseline yet); there is
        # nothing to compare against, so pass.
        print(f"warning: no baseline runs match {args.baseline!r}, skipping compare")
        return 0

    rows, failed = compare(baseline_runs, branch_runs, args.threshold)
    print(
        f"Comparing {len(branch_runs)} branch run(s) against "
        f"{len(baseline_runs)} baseline run(s), threshold {args.threshold:.0%}:\n"
    )
    print(render_table(rows))

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as fh:
            fh.write("## Benchmark comparison\n\n")
            if failed:
                fh.write(f"**{len(failed)} benchmark(s) regressed.**\n\n")
            fh.write(render_table(rows, markdown=True))
            fh.write("\n")

    if failed:
        print(
            f"\n{len(failed)} benchmark(s) consistently slower than baseline "
            f"by more than {args.threshold:.0%}:"
        )
        for name in failed:
            print(f"  {name}")
        return 1
    print("\nNo benchmark consistently regressed beyond the threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
