# StockGap

An offline inventory reorder planner built with the [Salam Programming Language](https://github.com/SalamLang/Salam).

Development is in progress. The first increment provides the native CLI entry point. Following increments will add strict TSV input validation, case-pack planning, supplier totals and executable checks. No real stock or customer information is used.

Requires Salam 0.4.8 and a C compiler. Build the CLI:

```sh
salam build src/main.salam --output=build/stockgap --backend=c --cc=cc
build/stockgap --help
```

This project is developed with an AI assistant for the Salam community application challenge. An advertised reward is conditional on maintainer acceptance; nothing has been awarded or paid.
