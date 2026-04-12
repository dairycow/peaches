---
description: List stocks within 3% of their 52-week high
agent: build
---

List all ordinary stocks currently trading within 3% of their 52-week high, excluding options, warrants, and indices.

Run the following Python script against the trading database at `/home/hf/peaches/data-prod/trading.db`:

```bash
uv run python << 'PYEOF'
import sqlite3, re

OPTION_SUFFIX = r"(SO|KO|WO|JO|IO|MO|LO|DO|GO|PO|TO|NO|RO|BO|CO|HO|VO|QO|UO|XO|YO|ZO|EO|FO)[A-Z0-9]{1,2}$"
INDEX_PREFIX = r"^X[A-Z]{2}"

conn = sqlite3.connect("/home/hf/peaches/data-prod/trading.db")
conn.create_function("REGEXP", 2, lambda p, s: 1 if re.search(p, s) else 0)
cursor = conn.cursor()
cursor.execute(
    """
    WITH latest AS (
        SELECT symbol, close_price, datetime,
               ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY datetime DESC) as rn
        FROM dbbardata WHERE interval = 'd'
    ),
    high52 AS (
        SELECT symbol, MAX(high_price) as high_52w
        FROM dbbardata
        WHERE interval = 'd'
          AND datetime >= date('now', '-365 days')
        GROUP BY symbol
    )
    SELECT l.symbol, l.close_price, h.high_52w,
           ROUND((l.close_price - h.high_52w) / h.high_52w * 100, 2) as pct_from_high,
           l.datetime
    FROM latest l
    JOIN high52 h ON l.symbol = h.symbol
    WHERE l.rn = 1
      AND h.high_52w > 0
      AND l.close_price >= h.high_52w * 0.97
      AND l.symbol NOT REGEXP ?
      AND l.symbol NOT REGEXP ?
    ORDER BY pct_from_high DESC
""",
    (OPTION_SUFFIX, INDEX_PREFIX),
)
rows = cursor.fetchall()
if not rows:
    print("No stocks found within 3% of their 52-week high.")
else:
    print(f"Found {len(rows)} stocks within 3% of their 52-week high:")
    print()
    header = f"{'Symbol':<10} {'Close':>10} {'52W High':>10} {'% From High':>12} {'Date':<12}"
    print(header)
    print("-" * 56)
    for row in rows:
        print(f"{row[0]:<10} {row[1]:>10.3f} {row[2]:>10.3f} {row[3]:>11.2f}% {row[4]:<12}")
conn.close()
PYEOF
```

Display the results as-is. If the user asks for a different threshold, adjust the `0.97` multiplier (e.g., `0.95` for 5%, `0.90` for 10%).

The query excludes:
- Options and warrants (symbols ending in SO/KO/WO/JO/IO/MO/LO/DO/GO/PO/TO/NO/RO/BO/CO/HO/VO suffixes + series identifier)
- Indices (symbols starting with X followed by 2 letters, e.g. XJO, XAO)
