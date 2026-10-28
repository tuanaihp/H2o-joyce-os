"""Do xen ke chi phi nap main cho nhieu phien ban. python bench_import.py <n> <ten=thu_muc_server> ..."""
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

n = int(sys.argv[1])
vers = [a.split("=", 1) for a in sys.argv[2:]]
codes = ("pass", "import fastapi", "import main")
res = {v: {c: [] for c in codes} for v, _ in vers}
rc = {v: set() for v, _ in vers}
for i in range(n):
    for v, d in vers:
        for c in codes:
            env = dict(os.environ, JOYCE_STATE_DIR=tempfile.mkdtemp(prefix="joyce-bench-"))
            t = time.perf_counter()
            p = subprocess.run([sys.executable, "-c", c], cwd=d, capture_output=True, env=env)
            res[v][c].append((time.perf_counter() - t) * 1000)
            rc[v].add(p.returncode)
            if p.returncode != 0 and c == "import main":
                print("LOI", v, p.stderr.decode("utf-8", "replace")[-300:])
out = {}
for v, _ in vers:
    r = res[v]
    base = min(r["pass"])
    fa = min(r["import fastapi"]) - base
    ma = min(r["import main"]) - base
    mm = [x - statistics.median(r["pass"]) for x in r["import main"]]
    out[v] = {"exit_codes": sorted(rc[v]), "interp": round(base), "fastapi": round(fa), "main_min": round(ma),
              "ratio_min": round(ma / fa, 2), "main_median": round(statistics.median(mm)),
              "main_p95": round(sorted(mm)[int(0.95 * (len(mm) - 1))]), "raw": {c: [round(x) for x in r[c]] for c in codes}}
print(json.dumps(out, indent=1))
