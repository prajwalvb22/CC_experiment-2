import re
import glob
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # saves the image without needing a display
import matplotlib.pyplot as plt

RAW_DIRS = {
    "VM": "results/raw/memory/vm",
    "Container": "results/raw/memory/container",
}
CSV_PATH = "results/processed/memory_results.csv"
FIG_PATH = "results/figures/memory_performance.png"


def parse_run(path):
    """Read one sysbench memory output file and return its numbers."""
    text = open(path).read()

    ops = re.search(r"Total operations:\s*\d+\s*\(\s*([\d.]+)\s*per second\)", text)
    mib = re.search(r"\(\s*([\d.]+)\s*MiB/sec\)", text)
    lat = re.search(r"avg:\s*([\d.]+)", text)

    if not (ops and mib and lat):
        print(f"WARNING: could not read numbers from {path}")
        return None

    return {
        "operations_per_second": float(ops.group(1)),
        "mib_per_sec": float(mib.group(1)),
        "avg_latency_ms": float(lat.group(1)),
    }


# 1. Build the CSV from the raw files
rows = []
for env, folder in RAW_DIRS.items():
    files = sorted(
        glob.glob(f"{folder}/run*.txt"),
        key=lambda p: int(re.search(r"run(\d+)", p).group(1)),
    )
    if not files:
        print(f"WARNING: no run files found in {folder}")
    for f in files:
        result = parse_run(f)
        if result:
            run_no = int(re.search(r"run(\d+)", f).group(1))
            rows.append({"environment": env, "run": run_no, **result})

df = pd.DataFrame(rows)
if df.empty:
    raise SystemExit("No data found. Check the results/raw/memory folders.")

df.to_csv(CSV_PATH, index=False)
print(f"Saved {CSV_PATH}\n")
print(df)

# 2. Statistics
summary = df.groupby("environment")["operations_per_second"].agg(
    ["mean", "median", "min", "max", "std"]
)
print("\nOperations per second:")
print(summary)

# 3. Graph
summary["mean"].plot(kind="bar", title="Average Memory Performance")
plt.ylabel("Operations per Second")
plt.xlabel("Environment")
plt.tight_layout()
plt.savefig(FIG_PATH, dpi=300)
print(f"\nSaved {FIG_PATH}")

# 4. Performance difference (throughput formula from Section 24 of the manual)
if "VM" in summary.index and "Container" in summary.index:
    vm = summary.loc["VM", "mean"]
    container = summary.loc["Container", "mean"]
    difference = ((container - vm) / vm) * 100
    print(f"\nVM mean:        {vm:.2f} ops/sec")
    print(f"Container mean: {container:.2f} ops/sec")
    print(f"Throughput difference: {difference:.2f}%")
