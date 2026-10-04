# StockGap

An offline inventory reorder planner built with the [Salam Programming Language](https://github.com/SalamLang/Salam).

StockGap turns a small stock export into proposed reorder quantities, supplier totals, a budget check and warnings about shortages before deliveries arrive. It runs locally, reads one file and prints a TSV report. The example data is synthetic.

Requires [Salam 0.4.8](https://github.com/SalamLang/Salam/releases/tag/v0.4.8) and a C compiler (`cc`, Clang or GCC). Verification was performed on macOS ARM64. The file-opening helper also targets Linux x86-64/ARM64, which has not been tested. Other platforms are unsupported. No network connection is used by the application.

From the repository root:

```sh
sh scripts/build.sh
build/stockgap --help
build/stockgap examples/stock.tsv 7 50000
```

If Salam is not on your PATH, set `SALAM_BIN=/absolute/path/to/salam`. Set `STOCKGAP_CC` to choose a C compiler. Build artifacts stay in `build/` and `.salam-build/`.

The arguments are the input path, review interval in days and total budget in integer cents. Budget and unit costs must use the same currency. The example proposes 42 units from PANTRY costing 5250 cents and 36 units from CLEAN costing 9000 cents, for a total of 14250 cents. With a 50000-cent budget, the status is `WITHIN`.

Exit status is 0 within budget, 1 over budget, or 2 for invalid input. Invalid input produces an error on stderr and no report on stdout. A budget shortfall retains all proposed quantities in the report: StockGap does not choose which items to omit. It places no orders.

The TSV header must match exactly, with literal tabs:

```text
sku	supplier	on_hand	reserved	daily_demand	lead_days	safety_days	pack_size	min_order	unit_cost_cents
```

| Field | Accepted values |
| --- | --- |
| `sku`, `supplier` | 1–64 ASCII characters; first character a letter or digit; remaining characters letters, digits, `.`, `_`, `-` |
| `on_hand`, `reserved` | 0–1000000000; reserved cannot exceed on hand |
| `daily_demand` | 0–1000000 units per day |
| `lead_days`, `safety_days`, CLI review days | 0–365 |
| `pack_size` | 1–1000000 units |
| `min_order` | 0–1000000 units |
| `unit_cost_cents` | 0–1000000 |
| CLI budget cents | 0–1000000000000000 |

Numeric fields accept 1–16 ASCII decimal digits, including leading zeros. Signs, whitespace and fractions are rejected. Identifiers are case-sensitive, and SKUs must be unique. Supplier values are identifiers rather than display names.

Input must contain 1–1000 data rows and be at most 512000 bytes. LF and CRLF line endings are accepted; the final newline is optional. Blank rows, extra or missing columns, NUL bytes and a header without data are rejected. Use a stable, ordinary disk file. Non-seekable pipes are rejected without waiting for a writer.

For each item:

```text
available = on_hand - reserved
target = daily_demand * (lead_days + safety_days + review_days)
shortage = max(0, target - available)
order_qty = 0 if shortage == 0
            else round_up_to_pack(max(shortage, min_order))
cost_cents = order_qty * unit_cost_cents
arrival_gap = max(0, daily_demand * lead_days - available)
```

This assumes constant daily demand and deterministic lead times. It omits open purchase orders, taxes, shipping, discounts, forecast uncertainty and supplier capacity. Arrival gaps indicate a potential shortage before the proposed delivery; ordering more does not resolve that timing gap. Minimum orders apply only when an item has a shortage.

The report includes every item and aggregates suppliers with nonzero proposed orders in their first appearance order. `TOTAL_CENTS`, `BUDGET_STATUS`, `ORDERED_SKUS` and `ARRIVAL_GAP_SKUS` summarize the result. Costs use exact signed 64-bit integer arithmetic; the accepted limits keep the maximum 1000-row aggregate below its capacity.

Run the checks with Python 3 available for the black-box test runner:

```sh
sh scripts/test.sh
```

Native Salam suites check parsing, planning and aggregation. The Python runner invokes the compiled application to check malformed input, no partial output, line endings, duplicate SKUs, budget equality, pipe rejection and maximum row/arithmetic boundaries. Python is not required to run StockGap.

Implementation is split across `src/main.salam`, `number.salam`, `inventory.salam`, `inputfile.salam`, `item.salam`, `planner.salam`, `totals.salam` and `report.salam`. Application logic is written in Salam; the nonblocking file helper calls the operating system's C library.

Developed with an AI assistant for the [Salam community application challenge](https://github.com/SalamLang/Salam/issues/1713). This disclosure does not imply challenge acceptance or payment. License: GNU GPL version 3; see `LICENSE`.
