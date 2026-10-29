#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py
"""
import json
from datetime import datetime
from decimal import Decimal


def parse_ts(value):
    # "2026-09-21T15:30:26Z" -> aware datetime, so ordering is by time, not by file position
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_amount(value):
    # Amounts arrive as numbers or as strings with thousands separators ("4,804.15").
    # Decimal avoids float drift when summing ~23k payments.
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    return Decimal(str(value))


# The export is not in chronological order, so keep the latest attempt per txn_id by ts.
latest = {}

with open("payments.jsonl", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)  # truncated/corrupt lines are skipped
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        txn_id = event.get("txn_id")
        if not txn_id:  # events without a txn_id are ignored
            continue
        try:
            ts = parse_ts(event["ts"])
        except (KeyError, ValueError, AttributeError):
            continue
        current = latest.get(txn_id)
        if current is None or ts > current[0]:
            latest[txn_id] = (ts, event)

total = Decimal("0")
count = 0

# A payment is collected only if its latest attempt succeeded.
for ts, event in latest.values():
    if event.get("status") == "success":
        total += parse_amount(event["amount"])
        count += 1

with open("expected.txt") as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")
