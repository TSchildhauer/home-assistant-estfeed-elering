#!/usr/bin/env python3
"""
Fetch electricity meter data from the Elering Estfeed customer portal.

Authenticates using OAuth2 client credentials (client_id + client_secret)
from ~/.elering/Elering API Key.

API endpoint:
  POST https://estfeed.elering.ee/api/v1/metering-data
    ?startDateTime=2025-01-01T00:00:00.000Z
    &endDateTime=2025-01-31T23:59:59.999Z
    &resolution=one_day
  Body: ["38ZEE-00652265-8"]   (array of EIC codes)

Resolution options: fifteen_minutes, one_hour, one_day, one_week, one_month

Usage:
  python fetch_meter_data.py --start 2025-01-01 --end 2025-01-31
  python fetch_meter_data.py --start 2025-01-01 --end 2025-01-31 --resolution one_hour
  python fetch_meter_data.py --start 2025-01-01 --end 2025-01-31 --output data.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://estfeed.elering.ee"
TOKEN_URL = "https://kc.elering.ee/realms/elering-sso/protocol/openid-connect/token"
DEFAULT_CREDENTIALS = Path.home() / ".elering" / "Elering API Key"

RESOLUTIONS = ["fifteen_minutes", "one_hour", "one_day", "one_week", "one_month"]


def load_credentials(path: Path) -> dict:
    """Parse the key file: title line, then alternating label / value lines."""
    lines = [l.rstrip() for l in path.read_text().splitlines() if l.strip()]
    mapping = {}
    i = 1  # skip title line "Elering API Key"
    while i < len(lines) - 1:
        label = lines[i].lower()
        value = lines[i + 1]
        if "eic" in label:
            mapping["eic"] = value
        elif "client id" in label:
            mapping["client_id"] = value
        elif "client secret" in label:
            mapping["client_secret"] = value
        i += 2
    missing = [k for k in ("eic", "client_id", "client_secret") if k not in mapping]
    if missing:
        print(f"Error: could not find {missing} in {path}", file=sys.stderr)
        sys.exit(1)
    return mapping


def get_access_token(client_id: str, client_secret: str) -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    if not response.ok:
        print(f"Authentication failed ({response.status_code}): {response.text}", file=sys.stderr)
        sys.exit(1)
    return response.json()["access_token"]


def to_iso(date_str: str) -> str:
    """Accept YYYY-MM-DD or full ISO datetime and return UTC ISO-8601 with milliseconds."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except ValueError:
            continue
    return date_str


def fetch_metering_data(token: str, eic: str, start: str, end: str, resolution: str) -> list:
    response = requests.post(
        f"{BASE_URL}/api/v1/metering-data",
        params={
            "startDateTime": start,
            "endDateTime": end,
            "resolution": resolution,
        },
        json=[eic],
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "If-Modified-Since": "Mon, 26 Jul 1997 05:00:00 GMT",
        },
        timeout=30,
    )
    if response.status_code in (401, 403):
        print(f"Error {response.status_code} — check your client_id and client_secret.", file=sys.stderr)
        sys.exit(1)
    if not response.ok:
        print(f"Error {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)
    return response.json()


def print_summary(data: list) -> None:
    for mp in data:
        print(f"\nMetering point : {mp['meteringPointEic']}")
        print(f"  Requested res  : {mp.get('requestedResolution')}")
        print(f"  Actual res     : {mp.get('actualResolution')}")
        interval = mp.get("timeInterval", {})
        print(f"  Time interval  : {interval.get('from')} → {interval.get('to')}")
        intervals = mp.get("accountingIntervals", [])
        print(f"  Intervals      : {len(intervals)}")
        for iv in intervals:
            consumption = iv.get("consumptionKwh", "—")
            production  = iv.get("productionKwh",  "—")
            price       = iv.get("marketPrice", {}).get("centsPerKwh", "—")
            print(f"    {iv['fromDateTime']}  consumption={consumption} kWh  production={production} kWh  price={price} c/kWh")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch your electricity meter data from Elering Estfeed."
    )
    parser.add_argument("--start", required=True, help="Period start date (YYYY-MM-DD or ISO datetime)")
    parser.add_argument("--end", required=True, help="Period end date (YYYY-MM-DD or ISO datetime)")
    parser.add_argument(
        "--resolution",
        default="one_day",
        choices=RESOLUTIONS,
        help="Data resolution (default: one_day)",
    )
    parser.add_argument(
        "--credentials",
        default=str(DEFAULT_CREDENTIALS),
        help=f"Path to credentials file (default: {DEFAULT_CREDENTIALS})",
    )
    parser.add_argument("--output", help="Save JSON result to this file (default: print to stdout)")
    args = parser.parse_args()

    creds = load_credentials(Path(args.credentials))
    start = to_iso(args.start)
    end   = to_iso(args.end)

    print("Authenticating...", file=sys.stderr)
    token = get_access_token(creds["client_id"], creds["client_secret"])
    print("Token obtained.", file=sys.stderr)
    print(f"EIC:        {creds['eic']}", file=sys.stderr)
    print(f"Period:     {start} → {end}", file=sys.stderr)
    print(f"Resolution: {args.resolution}", file=sys.stderr)

    data = fetch_metering_data(token, creds["eic"], start, end, args.resolution)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to {args.output}", file=sys.stderr)

    print_summary(data)


if __name__ == "__main__":
    main()
