#!/bin/sh
set -eu
stockgap_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$stockgap_root"
mkdir -p build
"${SALAM_BIN:-salam}" build src/main.salam --output=build/stockgap --backend=c --cc="${STOCKGAP_CC:-cc}" --log-level=error
