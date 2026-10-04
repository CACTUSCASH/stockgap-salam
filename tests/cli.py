#!/usr/bin/env python3
"""Black-box checks for the compiled native CLI; Python is only a test runner."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build/stockgap"
HEADER = b"sku\tsupplier\ton_hand\treserved\tdaily_demand\tlead_days\tsafety_days\tpack_size\tmin_order\tunit_cost_cents"
ROW = b"A\tS\t0\t0\t1\t1\t0\t12\t25\t100"
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


def run(args):
    return subprocess.run([str(BIN), *map(str, args)], capture_output=True, timeout=5)


with tempfile.TemporaryDirectory(prefix="stockgap-test-") as folder:
    path = Path(folder) / "input.tsv"

    def fixture(data, review="0", budget="999999999999999"):
        path.write_bytes(data)
        return run([path, review, budget])

    def rejected(data, review="0", budget="999999999999999"):
        result = fixture(data, review, budget)
        check(result.returncode == 2, f"invalid input accepted: {data[:160]!r}")
        check(result.stdout == b"", "invalid input emitted a partial report")
        check(bool(result.stderr), "invalid input did not explain rejection")

    for args in [[], ["--unknown"], [path], [path, "0"], [path, "0", "1", "extra"]]:
        result = run(args)
        check(result.returncode == 2 and not result.stdout, "bad CLI arity")
    for flag, text in [("--help", b"No orders are placed"), ("--version", b"StockGap 0.1.0")]:
        result = run([flag])
        check(result.returncode == 0 and text in result.stdout, flag)

    sample = run([ROOT / "examples/stock.tsv", "7", "50000"])
    check(sample.returncode == 0 and not sample.stderr, "sample failed")
    check(b"TOTAL_CENTS\t14250\n" in sample.stdout, "sample total")
    check(b"SUPPLIER\tPANTRY\t42\t5250\n" in sample.stdout, "PANTRY total")
    check(b"SUPPLIER\tCLEAN\t36\t9000\n" in sample.stdout, "CLEAN total")
    check(b"ARRIVAL_GAP_SKUS\t2\n" in sample.stdout, "arrival gaps")
    same = run([ROOT / "examples/stock.tsv", "7", "50000"])
    check(sample.stdout == same.stdout, "report is not deterministic")
    for budget, code, status in [("14249", 1, b"OVER"), ("14250", 0, b"WITHIN")]:
        result = run([ROOT / "examples/stock.tsv", "7", budget])
        check(result.returncode == code, "budget boundary exit")
        check(b"BUDGET_STATUS\t" + status + b"\n" in result.stdout, "budget status")
        check(b"TOTAL_CENTS\t14250\n" in result.stdout, "budget changed proposed orders")

    valid = HEADER + b"\n" + ROW
    for data in [valid, valid + b"\n", valid.replace(b"\n", b"\r\n") + b"\r\n"]:
        result = fixture(data)
        check(result.returncode == 0, "valid line endings rejected")
        check(b"ITEM\tA\tS\t0\t1\t1\t36\t3600\t1\n" in result.stdout, "minimum order rounding")
    zero = HEADER + b"\n" + b"Z\tS\t1\t0\t1\t1\t0\t12\t25\t100"
    result = fixture(zero)
    check(b"ORDERED_SKUS\t0\n" in result.stdout and b"SUPPLIER\t" not in result.stdout, "minimum forced unnecessary order")

    for data in [b"", HEADER, HEADER + b"\n", b"bad\n" + ROW, valid + b"\n\n",
                 valid + b"\n" + ROW, valid + b"\t", valid.replace(b"\t100", b""),
                 valid.replace(b"A\tS", b"-A\tS"), valid.replace(b"A\tS", b"A\tS P"),
                 valid.replace(b"A\tS", b"A\t" + b"S" * 65),
                 valid.replace(b"\n", b"\r"), valid + b"\x00", valid + b"\n\x00hidden",
                 valid.replace(b"\t12\t", b"\t0\t"), valid.replace(b"\t0\t0\t", b"\t0\t1\t")]:
        rejected(data)
    for token in [b"-1", b"+1", b"1.0", b"1x", b" 1", b"1 ", b"", "１".encode(), b"0" * 17]:
        rejected(HEADER + b"\n" + ROW.replace(b"\t100", b"\t" + token))
    limits = [1000000000, 1000000000, 1000000, 365, 365, 1000000, 1000000, 1000000]
    for index, maximum in enumerate(limits):
        fields = ROW.split(b"\t")
        fields[index + 2] = str(maximum + 1).encode()
        rejected(HEADER + b"\n" + b"\t".join(fields))
    for review in ["-1", "366", "1.0", "１", "0" * 17]:
        rejected(valid, review=review)
    for budget in ["-1", "1000000000000001", "1x", "0" * 17]:
        rejected(valid, budget=budget)
    result = fixture(valid, "0000000000000365", "1000000000000000")
    check(result.returncode == 0, "maximum CLI bounds rejected")
    missing = run([Path(folder) / "absent", "0", "0"])
    check(missing.returncode == 2 and not missing.stdout, "missing file accepted")
    directory = run([folder, "0", "0"])
    check(directory.returncode == 2 and not directory.stdout, "directory accepted")
    if hasattr(os, "mkfifo"):
        fifo = Path(folder) / "pipe"
        os.mkfifo(fifo)
        result = run([fifo, "0", "0"])
        check(result.returncode == 2 and not result.stdout, "empty FIFO was opened")
    rejected(b"X" * 512001)

    maximal_rows = [f"K{i}\tS\t1000000000\t1000000000\t1000000\t365\t365\t999999\t1000000\t1000000".encode() for i in range(1000)]
    maximal = HEADER + b"\n" + b"\n".join(maximal_rows)
    result = fixture(maximal, "365", "1000000000000000")
    quantity = ((1095000000 + 999998) // 999999) * 999999
    total = quantity * 1000000 * 1000
    check(result.returncode == 1, "1000 maximal rows should exceed budget")
    check(f"TOTAL_CENTS\t{total}\n".encode() in result.stdout, "64-bit aggregate overflow")
    check(f"SUPPLIER\tS\t{quantity * 1000}\t{total}\n".encode() in result.stdout, "supplier conservation")
    check(result.stdout.count(b"ITEM\t") == 1000, "1000 row boundary")
    rejected(maximal + b"\n" + ROW)

print(f"CLI: {checks} checks passed")
