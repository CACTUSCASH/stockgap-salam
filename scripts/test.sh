#!/bin/sh
set -eu
stockgap_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$stockgap_root"
sh scripts/build.sh
# Salam shares one temporary build directory: compile and execute sequentially.
for stockgap_suite in numbers planning load summary; do
    "${SALAM_BIN:-salam}" build "tests/$stockgap_suite.salam" --output="build/test-$stockgap_suite" --backend=c --cc="${STOCKGAP_CC:-cc}" --log-level=error
    "build/test-$stockgap_suite"
done
python3 tests/cli.py
