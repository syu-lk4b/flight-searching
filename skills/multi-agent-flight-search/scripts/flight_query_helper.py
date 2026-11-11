#!/usr/bin/env python3
"""
Reusable Flight Query Helper for multi-agent-flight-search skill.

Commands:
  1. trip_calendar <dep_city> <arr_city> [start_date YYYY-MM-DD] [days_span 90] [dep_weekday 0] [trip_days 5]
     -> Queries Trip.com (hk.trip.com) GetLowPriceInCalender API for round-trip direct lowest tax-inclusive CNY fares.
  2. ch_day <dep_code> <arr_code> <YYYY-MM-DD>
     -> Queries Spring Airlines (hk.ch.com) Flights/SearchByTime API for 9C/IJ direct flights, tax-inclusive CNY fares, tax breakdown, and baggage rules.
  3. gflights <dep_code> <arr_code> <dep_date> [ret_date]
     -> Queries Google Flights (ds:1 JSON) for nonstop flight numbers, times, aircraft, and CNY prices.

Security Notes:
  - Uses only public, unauthenticated read-only flight search endpoints over HTTPS.
  - No API keys, tokens, cookies, or personal identifiers are required or stored.
  - All airport/city IATA codes and date parameters are strictly validated before request construction.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

IATA_RE = re.compile(r"^[A-Za-z]{3}$")


def _validate_iata(code: str, name: str = "airport/city code") -> str:
    cleaned = (code or "").strip().upper()
    if not IATA_RE.match(cleaned):
        raise ValueError(f"Invalid {name}: {code!r} (expected 3-letter IATA code, e.g. PVG, TYO)")
    return cleaned


def _validate_date(date_str: str, name: str = "date") -> str:
    cleaned = (date_str or "").strip()
    try:
        datetime.strptime(cleaned, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Invalid {name}: {date_str!r} (expected YYYY-MM-DD)") from exc
    return cleaned


def get_weekday_pairs(start_date_str: str, span_days: int = 90, dep_weekday: int = 0, trip_days: int = 5):
    """
    Generate (dep_date, ret_date) pairs where dep_date.weekday() == dep_weekday (0=Mon .. 6=Sun)
    and trip length is trip_days (inclusive, e.g., 5 = Mon->Fri +4 days).
    """
    start_clean = _validate_date(start_date_str, "start_date")
    if not (1 <= int(span_days) <= 366):
        raise ValueError("span_days must be between 1 and 366")
    if not (0 <= int(dep_weekday) <= 6):
        raise ValueError("dep_weekday must be between 0 (Monday) and 6 (Sunday)")
    if not (1 <= int(trip_days) <= 60):
        raise ValueError("trip_days must be between 1 and 60")

    d = datetime.strptime(start_clean, "%Y-%m-%d")
    end_d = d + timedelta(days=int(span_days))
    while d.weekday() != int(dep_weekday):
        d += timedelta(days=1)
    pairs = []
    while d <= end_d:
        r = d + timedelta(days=int(trip_days) - 1)
        pairs.append((d.strftime("%Y-%m-%d"), r.strftime("%Y-%m-%d")))
        d += timedelta(days=7)
    return pairs


def trip_calendar(dep_city: str, arr_city: str, pairs=None):
    dep_clean = _validate_iata(dep_city, "dep_city")
    arr_clean = _validate_iata(arr_city, "arr_city")
    url = "https://hk.trip.com/restapi/soa2/14427/GetLowPriceInCalender"
    payload = json.dumps({
        "departCityCode": dep_clean,
        "arriveCityCode": arr_clean,
        "flightWayType": "RT",
        "cabin": "Y",
        "curr": "CNY",
        "isDirectFlight": True,
        "head": {
            "cid": "09031000000000000000",
            "ctok": "",
            "cver": "1.0",
            "lang": "01",
            "sid": "8888",
            "syscode": "09",
            "auth": "",
            "sauth": "",
            "currency": "CNY",
            "locale": "zh-HK"
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=12) as r:
        resp = json.loads(r.read().decode("utf-8", "ignore"))
        prices = {p["departDate"]: p for p in (resp.get("lowPriceInCalenderDtoInfoList") or [])}
        if not pairs:
            return prices
        out = {}
        for m, f in pairs:
            k = f"{m}_{f}"
            if k in prices:
                out[k] = prices[k]["totalPrice"]
        return out


def ch_search_day(dep: str, arr: str, dt: str, retries: int = 2):
    dep_clean = _validate_iata(dep, "dep_code")
    arr_clean = _validate_iata(arr, "arr_code")
    dt_clean = _validate_date(dt, "departure_date")
    url = "https://hk.ch.com/Flights/SearchByTime"
    data = urllib.parse.urlencode({
        "Departure": dep_clean,
        "Arrival": arr_clean,
        "DepartureDate": dt_clean,
        "IsIJFlight": "false",
        "IsBg": "false",
        "Currency": "0",
        "SType": "0",
        "IsReturn": "false"
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://hk.ch.com/flights/{dep_clean}-{arr_clean}.html"
        }
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                resp = json.loads(r.read().decode("utf-8", "ignore"))
                flights = []
                for seg_list in (resp.get("Route") or []):
                    if len(seg_list) == 1:
                        r0 = seg_list[0]
                        cab0 = r0["AircraftCabins"][0]["AircraftCabinInfos"][0]
                        flights.append({
                            "flightNo": r0["No"],
                            "company": r0.get("CompanyName"),
                            "depAirport": r0["DepartureAirportCode"],
                            "depStation": r0.get("DepartureStation"),
                            "depTime": r0["DepartureTime"],
                            "arrAirport": r0["ArrivalAirportCode"],
                            "arrStation": r0.get("ArrivalStation"),
                            "arrTime": r0["ArrivalTime"],
                            "aircraft": r0.get("Type"),
                            "totalPriceCNY": r0["MinCabinPrice"],
                            "taxCNY": r0["RouteTotalTax"],
                            "basePriceCNY": r0["MinCabinPrice"] - r0["RouteTotalTax"],
                            "checkedBaggage": cab0.get("Baggage"),
                            "handBaggage": cab0.get("HandBaggage")
                        })
                if flights or attempt == retries:
                    return flights
        except Exception as e:
            if attempt == retries:
                return [{"error": str(e)}]
        time.sleep(0.8)
    return []


def _fmt_gf_time(arr):
    if not arr:
        return "N/A"
    h = (arr[0] if len(arr) > 0 else 0) or 0
    m = (arr[1] if len(arr) > 1 else 0) or 0
    return f"{h:02d}:{m:02d}"


def gflights_search(dep: str, arr: str, dep_date: str, ret_date: str = None):
    dep_clean = _validate_iata(dep, "dep_code")
    arr_clean = _validate_iata(arr, "arr_code")
    dep_dt_clean = _validate_date(dep_date, "dep_date")
    if ret_date:
        ret_dt_clean = _validate_date(ret_date, "ret_date")
        q_raw = f"nonstop flights from {dep_clean} to {arr_clean} {dep_dt_clean} to {ret_dt_clean}"
    else:
        q_raw = f"nonstop flights from {dep_clean} to {arr_clean} on {dep_dt_clean}"
    q_encoded = urllib.parse.quote_plus(q_raw)
    url = f"https://www.google.com/travel/flights?q={q_encoded}&curr=CNY&hl=zh-CN"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
    )
    with urllib.request.urlopen(req, timeout=12) as r:
        html = r.read().decode("utf-8", "ignore")
        m = re.search(r"key:\s*'ds:1',\s*hash:\s*'\d+',\s*data:(\[.*?\]),\s*sideChannel:", html, re.S)
        if not m:
            return []
        data = json.loads(m.group(1))
        nonstop = []
        for g in [2, 3]:
            if len(data) > g and data[g] and data[g][0]:
                for item in data[g][0]:
                    legs = item[0][2]
                    if len(legs) == 1:
                        l = legs[0]
                        p = item[1][0][1] if item[1] and item[1][0] else None
                        nonstop.append({
                            "flightNo": f"{l[22][0]}{l[22][1]}",
                            "airline": l[22][3],
                            "depAirport": l[3],
                            "depName": l[4],
                            "depTime": _fmt_gf_time(l[8]),
                            "arrAirport": l[6],
                            "arrName": l[5],
                            "arrTime": _fmt_gf_time(l[10]),
                            "durationMin": l[11],
                            "aircraft": l[17],
                            "priceCNY": p
                        })
        return nonstop


def _print_usage():
    print(__doc__.strip())


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        _print_usage()
        sys.exit(0)

    cmd = sys.argv[1]
    try:
        if cmd == "trip_calendar":
            if len(sys.argv) < 4:
                raise ValueError("Usage: trip_calendar <dep_city> <arr_city> [start_date] [span_days] [weekday] [trip_days]")
            dep_city = sys.argv[2]
            arr_city = sys.argv[3]
            start_dt = sys.argv[4] if len(sys.argv) > 4 else datetime.now().strftime("%Y-%m-%d")
            span = int(sys.argv[5]) if len(sys.argv) > 5 else 90
            weekday = int(sys.argv[6]) if len(sys.argv) > 6 else 0
            trip_days = int(sys.argv[7]) if len(sys.argv) > 7 else 5
            pairs = get_weekday_pairs(start_dt, span, weekday, trip_days)
            print(json.dumps(trip_calendar(dep_city, arr_city, pairs), ensure_ascii=False, indent=2))
        elif cmd == "ch_day":
            if len(sys.argv) < 5:
                raise ValueError("Usage: ch_day <dep_code> <arr_code> <YYYY-MM-DD>")
            print(json.dumps(ch_search_day(sys.argv[2], sys.argv[3], sys.argv[4]), ensure_ascii=False, indent=2))
        elif cmd == "gflights":
            if len(sys.argv) < 5:
                raise ValueError("Usage: gflights <dep_code> <arr_code> <dep_date> [ret_date]")
            ret = sys.argv[5] if len(sys.argv) > 5 else None
            print(json.dumps(gflights_search(sys.argv[2], sys.argv[3], sys.argv[4], ret), ensure_ascii=False, indent=2))
        else:
            raise ValueError(f"Unknown command: {cmd!r}. Expected trip_calendar, ch_day, or gflights.")
    except Exception as err:
        print(json.dumps({"error": str(err)}, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)
