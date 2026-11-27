#!/usr/bin/env python3
"""Refresh Amazing Oriental offers and Almere store hours from official HTML.

Downloads https://amazingoriental.com/aanbiedingen/ and the Almere store page,
parses product cards from HTML (not Markdown), and writes data/offers.json.
"""

from __future__ import annotations

import html as htmllib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OFFERS_URL = "https://amazingoriental.com/aanbiedingen/"
STORE_URL = "https://amazingoriental.com/Location/winkels-almere/"
STORE_NAME = "Amazing Oriental Almere"
STORE_ADDRESS = "Metropolestraat 64"
AMSTERDAM = ZoneInfo("Europe/Amsterdam")
USER_AGENT = "Mozilla/5.0 (compatible; OrientalOffersBot/1.0)"

SECTIONS = [
    ("weekly-specials", "Weekly Deals", "weekly", "本周特价"),
    ("amazingdeals", "Amazing Deals", "amazing", "Amazing Deals"),
    ("megadeals", "Mega Deals", "mega", "Mega Deals"),
    ("vis-en-vlees", "Vis en vlees", "meat", "鱼和肉"),
]

DUTCH_MONTHS = {
    "januari": 1,
    "februari": 2,
    "maart": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "augustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}

DUTCH_WEEKDAYS = {
    "maandag": "Monday",
    "dinsdag": "Tuesday",
    "woensdag": "Wednesday",
    "donderdag": "Thursday",
    "vrijdag": "Friday",
    "zaterdag": "Saturday",
    "zondag": "Sunday",
}

WEEKDAY_ZH = {
    "Monday": "星期一",
    "Tuesday": "星期二",
    "Wednesday": "星期三",
    "Thursday": "星期四",
    "Friday": "星期五",
    "Saturday": "星期六",
    "Sunday": "星期日",
}

WEEKDAY_ZH_SHORT = {
    "Monday": "周一",
    "Tuesday": "周二",
    "Wednesday": "周三",
    "Thursday": "周四",
    "Friday": "周五",
    "Saturday": "周六",
    "Sunday": "周日",
}

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def load_translations() -> dict:
    path = ROOT / "data" / "translations.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    names = {(item["brand"], item["name"]): item["nameZh"] for item in raw.get("names", [])}
    return {
        "names": names,
        "packages": raw.get("packages", {}),
        "packageByUrl": raw.get("packageByUrl", {}),
        "prep": raw.get("prep", {}),
    }


def fetch_text(url: str, label: str, attempts: int = 3) -> str:
    last_error: Exception | None = None
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "nl,en;q=0.8,zh;q=0.7",
        },
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise RuntimeError(f"{label} failed: HTTP {status}")
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as error:
            last_error = error
            print(f"{label} attempt {attempt}/{attempts} failed: {error}", file=sys.stderr)
            time.sleep(0.5 * attempt)
    raise RuntimeError(f"{label} unavailable: {last_error}") from last_error


def clean(text: str | None) -> str | None:
    if not text:
        return None
    text = htmllib.unescape(re.sub(r"<br\s*/?>", " ", text, flags=re.I))
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    text = text.strip().replace("\xa0", " ").replace("€", "").strip()
    if not text:
        return None
    if re.search(r"\d+\.\d{3}", text) and "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def resolve_date(day: int, month: int, today: date, previous: date | None = None) -> date:
    def make(year: int) -> date | None:
        try:
            return date(year, month, day)
        except ValueError:
            return None

    if previous is not None:
        candidate = make(previous.year)
        if candidate is None or candidate < previous:
            candidate = make(previous.year + 1)
        if candidate is None:
            raise ValueError(f"Cannot resolve date {day:02d}-{month:02d} after {previous.isoformat()}")
        return candidate
    candidates = [item for item in (make(today.year - 1), make(today.year), make(today.year + 1)) if item]
    return min(candidates, key=lambda item: abs((item - today).days))


def parse_loose_date(text: str, today: date, previous: date | None = None) -> date | None:
    text = clean(text) or ""
    text = text.lower().replace("\xa0", " ")
    numeric = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", text)
    if numeric:
        day, month, year = int(numeric.group(1)), int(numeric.group(2)), numeric.group(3)
        if year:
            try:
                return date(int(year), month, day)
            except ValueError:
                return None
        return resolve_date(day, month, today, previous)
    named = re.search(r"\b(\d{1,2})\s+([a-zë]+)\b", text)
    if not named:
        return None
    month = DUTCH_MONTHS.get(named.group(2))
    if not month:
        return None
    return resolve_date(int(named.group(1)), month, today, previous)


def parse_validity_window(text: str | None, today: date) -> tuple[str | None, str | None, str | None, str | None]:
    raw = clean(text)
    if not raw:
        return None, None, None, None
    match = re.search(r"geldig\s+van\s+(.+?)\s+t/?m\s+(.+)$", raw, flags=re.I)
    if not match:
        return None, None, raw, None
    start = parse_loose_date(match.group(1), today)
    end = parse_loose_date(match.group(2), today, start)
    if not start or not end:
        return None, None, raw, None
    validity_zh = (
        f"有效期为{start.month}月{start.day}日{WEEKDAY_ZH[start.strftime('%A')]}"
        f"至{end.month}月{end.day}日{WEEKDAY_ZH[end.strftime('%A')]}"
    )
    return start.isoformat(), end.isoformat(), raw, validity_zh


def section_html(raw: str, sec_id: str) -> str:
    match = re.search(rf'id="{re.escape(sec_id)}"', raw)
    if not match:
        return ""
    start = match.start()
    end = len(raw)
    for other, *_ in SECTIONS:
        if other == sec_id:
            continue
        found = re.search(rf'id="{re.escape(other)}"', raw)
        if found and found.start() > start:
            end = min(end, found.start())
    return raw[start:end]


def package_zh(package: str, url: str, translations: dict) -> str:
    extra = translations["packageByUrl"].get(url)
    key = package.lower()
    zh = translations["packages"].get(key, package)
    if extra and extra not in zh:
        zh = f"{zh} {extra}" if zh else extra
    return zh


def unit_price(sale: float | None, package: str) -> float | None:
    if sale is None:
        return None
    key = package.lower()
    if key in {"per kilo"}:
        return round(sale, 2)
    if key in {"per 500g", "500g"}:
        return round(sale * 2, 2)
    return None


def discount_percent(sale: float | None, original: float | None) -> int | None:
    if sale is None or original is None or original <= 0 or sale >= original:
        return None
    return int(round((original - sale) / original * 100))


def advice_for(item: dict) -> str:
    parts: list[str] = []
    promo = item.get("promo")
    sale, original = item.get("sale"), item.get("original")
    if promo and sale is None:
        parts.append(f"官网活动为「{promo}」。")
        if original is not None:
            parts.append(f"页上单件标价 €{original:.2f}。".replace(".", ","))
        parts.append("没有单独现价，不把自行换算的价格写成折扣价。")
    elif original is None:
        parts.append("页面没有划掉原价，不当折扣。")
    elif sale is not None:
        off = original - sale
        pct = item.get("discountPercent")
        if pct:
            parts.append(f"现价比标出的原价少 €{off:.2f}，折扣 {pct}%。".replace(".", ","))
        else:
            parts.append(f"现价 €{sale:.2f}，原价 €{original:.2f}。".replace(".", ","))
    prep = item.get("prep")
    if prep:
        parts.append(prep + "。")
    return "".join(parts)


def is_section_promo(promo: str | None) -> bool:
    if not promo:
        return True
    if promo in {"Amazing Deals", "Mega Deals", "Weekly Deals", "Vis en vlees"}:
        return True
    if promo.startswith("Weekly "):
        return True
    return False


def parse_items(raw: str, today: date) -> list[dict]:
    parsed = []
    for sec_id, sec_name, sec_key, sec_zh in SECTIONS:
        block = section_html(raw, sec_id)
        date_m = re.search(r'class="se-date">([^<]+)', block)
        valid_from, valid_to, validity_nl, validity_zh = parse_validity_window(
            date_m.group(1) if date_m else None, today
        )
        for ib in re.findall(r'<div class="item">(.*?)</a></div>', block, flags=re.S):
            href = re.search(r'href="(https://amazingoriental.com/product/[^"]+)"', ib)
            if not href:
                continue
            url = href.group(1)
            webp = re.search(r'data-bg="(https://amazingoriental.com/wp-content/uploads/[^"]+\.webp)"', ib)
            png = re.search(r'data-bg="(https://amazingoriental.com/wp-content/uploads/[^"]+\.png)"', ib)
            brand_m = re.search(r'<span class="brand">(.*?)</span>', ib)
            title = re.search(r"<h4>(.*?)</h4>", ib)
            orig_m = re.search(r'original-price[^"]*">\s*([^<]*)', ib)
            sale_m = re.search(r'new-price">\s*([^<]+)', ib)
            label_m = re.search(r'<span class="label">([^<]*)</span>', ib)
            promo_m = re.search(r'<span class="promo">(.*?)</span>', ib)
            promo = clean(promo_m.group(1) if promo_m else "")
            if is_section_promo(promo):
                promo = None
            orig_raw = orig_m.group(1).strip() if orig_m else ""
            name = clean(title.group(1) if title else "") or ""
            if not name:
                print(f"warning: missing product name for {url}", file=sys.stderr)
            parsed.append(
                {
                    "category": sec_name,
                    "categoryKey": sec_key,
                    "categoryZh": sec_zh,
                    "validFrom": valid_from,
                    "validTo": valid_to,
                    "validityNl": validity_nl,
                    "validityZh": validity_zh,
                    "name": name,
                    "brand": clean(brand_m.group(1) if brand_m else "") or "",
                    "sale": parse_price(sale_m.group(1) if sale_m else None),
                    "original": parse_price(orig_raw) if orig_raw else None,
                    "package": clean(label_m.group(1) if label_m else "") or "",
                    "promo": promo,
                    "imageUrl": (webp.group(1) if webp else None) or (png.group(1) if png else None),
                    "productUrl": url,
                }
            )
    return parsed


def merge_unique(items: list[dict], translations: dict) -> list[dict]:
    by_url: dict[str, dict] = {}
    order: list[str] = []
    for item in items:
        url = item["productUrl"]
        if url not in by_url:
            rec = dict(item)
            rec["categories"] = [item["category"]]
            rec["categoryKeys"] = [item["categoryKey"]]
            rec["categoriesZh"] = [item["categoryZh"]]
            by_url[url] = rec
            order.append(url)
        else:
            rec = by_url[url]
            if item["category"] not in rec["categories"]:
                rec["categories"].append(item["category"])
                rec["categoryKeys"].append(item["categoryKey"])
                rec["categoriesZh"].append(item["categoryZh"])
    offers = []
    missing = []
    prep_map = translations["prep"]
    for url in order:
        rec = by_url[url]
        brand, name = rec["brand"], rec["name"]
        name_zh = translations["names"].get((brand, name))
        if not name_zh:
            missing.append((brand, name, url))
            name_zh = name
        rec["nameZh"] = name_zh
        rec["packageZh"] = package_zh(rec["package"], url, translations)
        rec["unitPrice"] = unit_price(rec["sale"], rec["package"])
        rec["discountPercent"] = discount_percent(rec["sale"], rec["original"])
        rec["prep"] = prep_map.get(name_zh) or prep_map.get(f"{brand} {name_zh}")
        rec["advice"] = advice_for(rec)
        rec["displayCategory"] = " · ".join(rec["categoriesZh"])
        offers.append(rec)
    if missing:
        print("Missing translations (kept official names):", file=sys.stderr)
        for brand, name, url in missing:
            print(f"  {brand!r} | {name!r} | {url}", file=sys.stderr)
    return offers


def parse_hours_label(label: str) -> tuple[str | None, str | None, bool]:
    text = clean(label) or ""
    if re.search(r"gesloten", text, flags=re.I):
        return None, None, True
    match = re.search(r"([0-2]\d:[0-5]\d)\s*[-–—]\s*([0-2]\d:[0-5]\d)", text)
    if not match:
        return None, None, False
    return match.group(1), match.group(2), False


def parse_store_hours(html: str, today: date) -> dict:
    rows = re.findall(
        r'<div class="item[^"]*">\s*'
        r'<span class="column"><span>([^<]+)</span></span>\s*'
        r'<span class="column">([^<]+)</span>\s*'
        r'<span class="column">([^<]+)</span>\s*'
        r'</div>',
        html,
        flags=re.I,
    )
    upcoming: list[dict] = []
    previous: date | None = None
    for weekday_nl, date_label, hours_label in rows:
        weekday_nl = (clean(weekday_nl) or "").lower()
        date_label = clean(date_label) or ""
        hours_label = clean(hours_label) or ""
        weekday = DUTCH_WEEKDAYS.get(weekday_nl)
        row_date = parse_loose_date(date_label, today, previous)
        if not weekday or not row_date:
            print(f"warning: skipped store hours row {(weekday_nl, date_label, hours_label)!r}", file=sys.stderr)
            continue
        opens_at, closes_at, closed = parse_hours_label(hours_label)
        if not closed and not closes_at:
            print(f"warning: no opening hours in row {(weekday_nl, date_label, hours_label)!r}", file=sys.stderr)
        upcoming.append(
            {
                "date": row_date.isoformat(),
                "weekday": weekday,
                "weekdayNl": weekday_nl,
                "weekdayZh": WEEKDAY_ZH[weekday],
                "opensAt": opens_at,
                "closesAt": closes_at,
                "closed": closed,
                "label": hours_label,
            }
        )
        previous = row_date

    if not upcoming:
        raise RuntimeError(f"Could not parse opening hours from {STORE_URL}")

    by_date = {row["date"]: row for row in upcoming}
    today_row = by_date.get(today.isoformat())

    weekly_hours = []
    for weekday in WEEKDAY_ORDER:
        # Prefer the current/next occurrence of this weekday from the official table.
        match = next((row for row in upcoming if row["weekday"] == weekday and row["date"] >= today.isoformat()), None)
        if match is None:
            match = next((row for row in reversed(upcoming) if row["weekday"] == weekday), None)
        if match is None:
            continue
        weekly_hours.append(
            {
                "weekday": weekday,
                "weekdayNl": match["weekdayNl"],
                "weekdayZh": match["weekdayZh"],
                "opensAt": match["opensAt"],
                "closesAt": match["closesAt"],
                "closed": match["closed"],
            }
        )

    if today_row is None:
        fallback = next((row for row in weekly_hours if row["weekday"] == today.strftime("%A")), None)
        if fallback:
            today_row = {
                **fallback,
                "date": today.isoformat(),
                "label": "gesloten" if fallback["closed"] else f"{fallback['opensAt']} - {fallback['closesAt']}",
            }

    if today_row is None or (not today_row.get("closed") and not today_row.get("closesAt")):
        raise RuntimeError(
            f"Could not parse today's closing time for {STORE_NAME} on {today.isoformat()} from {STORE_URL}"
        )

    hours_note = build_hours_note(weekly_hours, today_row)
    postal = "Metropolestraat 64, 1315 KM Almere"
    postal_m = re.search(r"Metropolestraat 64[,\s]+1315\s*KM\s*Almere", html, flags=re.I)
    if postal_m:
        postal = re.sub(r"\s+", " ", postal_m.group(0)).replace("1315KM", "1315 KM")

    return {
        "name": STORE_NAME,
        "address": STORE_ADDRESS,
        "postalAddress": postal,
        "url": STORE_URL,
        "hoursSourceUrl": STORE_URL,
        "timezone": "Europe/Amsterdam",
        "opensAt": None if today_row["closed"] else today_row.get("opensAt"),
        "closesAt": None if today_row["closed"] else today_row.get("closesAt"),
        "closedToday": bool(today_row["closed"]),
        "hoursNote": hours_note,
        "weeklyHours": weekly_hours,
        "upcomingHours": upcoming,
    }


def build_hours_note(weekly_hours: list[dict], today_row: dict) -> str:
    groups: list[tuple[list[str], str]] = []
    for row in weekly_hours:
        label = "休息" if row["closed"] else (
            f"{row['opensAt']}–{row['closesAt']}" if row.get("opensAt") and row.get("closesAt") else "营业时间待确认"
        )
        if groups and groups[-1][1] == label:
            groups[-1][0].append(row["weekday"])
        else:
            groups.append(([row["weekday"]], label))

    parts = []
    for weekdays, label in groups:
        names = [WEEKDAY_ZH_SHORT[day] for day in weekdays]
        if len(names) == 1:
            span = names[0]
        elif len(names) == 2 and WEEKDAY_ORDER.index(weekdays[1]) == WEEKDAY_ORDER.index(weekdays[0]) + 1:
            span = f"{names[0]}至{names[1]}"
        elif all(
            WEEKDAY_ORDER.index(weekdays[index]) == WEEKDAY_ORDER.index(weekdays[0]) + index
            for index in range(len(weekdays))
        ):
            span = f"{names[0]}至{names[-1]}"
        else:
            span = "、".join(names)
        parts.append(f"{span} {label}" if label == "休息" else f"{span} {label}")

    if today_row["closed"]:
        today_text = "今日休息"
    else:
        today_text = f"今日 {today_row['opensAt']}–{today_row['closesAt']}"
    summary = "；".join(parts)
    return f"{today_text}（欧洲/阿姆斯特丹）。按星期：{summary}。来源：官方店页。"


def build_validity_summary(offers: list[dict]) -> dict:
    def first(key: str) -> dict | None:
        return next((item for item in offers if key in item.get("categoryKeys", [])), None)

    weekly = first("weekly")
    amazing = first("amazing")
    mega = first("mega")
    meat = first("meat")

    weekly_zh = weekly["validityZh"] if weekly and weekly.get("validityZh") else None
    weekly_nl = weekly["validityNl"] if weekly and weekly.get("validityNl") else None
    if weekly_zh:
        weekly_zh = f"Weekly Deals {weekly_zh}"

    same_window = []
    for item, label in ((amazing, "Amazing Deals"), (mega, "Mega Deals"), (meat, "鱼和肉")):
        if item and item.get("validFrom") and item.get("validTo"):
            same_window.append((label, item["validFrom"], item["validTo"], item.get("validityNl"), item.get("validityZh")))

    amazing_nl = amazing["validityNl"] if amazing else None
    amazing_zh = None
    if same_window:
        windows = {(item[1], item[2], item[4]) for item in same_window}
        if len(windows) == 1:
            labels = "、".join(item[0] for item in same_window)
            if len(same_window) > 1:
                head = "、".join(item[0] for item in same_window[:-1])
                labels = f"{head} 与{same_window[-1][0]}"
            zh = same_window[0][4] or ""
            amazing_zh = f"{labels}{zh}" if zh else labels
            amazing_nl = same_window[0][3]
        else:
            bits_zh = []
            bits_nl = []
            for label, _start, _end, nl, zh in same_window:
                if zh:
                    bits_zh.append(f"{label} {zh}")
                if nl:
                    bits_nl.append(f"{label}: {nl}")
            amazing_zh = "；".join(bits_zh) or None
            amazing_nl = " · ".join(bits_nl) or amazing_nl

    return {
        "weeklyNl": weekly_nl,
        "weeklyZh": weekly_zh,
        "amazingNl": amazing_nl,
        "amazingZh": amazing_zh,
    }


def main() -> None:
    translations = load_translations()
    now = datetime.now(AMSTERDAM)
    today = now.date()
    offers_html = fetch_text(OFFERS_URL, "Amazing Oriental offers HTML")
    store_html = fetch_text(STORE_URL, "Amazing Oriental Almere store HTML")
    offers = merge_unique(parse_items(offers_html, today), translations)
    if not offers:
        raise SystemExit("Parsed 0 offers from the official aanbiedingen page.")
    store = parse_store_hours(store_html, today)
    data = {
        "generatedAt": now.isoformat(timespec="seconds"),
        "sourceUrl": OFFERS_URL,
        "store": store,
        "validity": build_validity_summary(offers),
        "note": "优惠来自全连锁官网，Almere 分店有没有货要到店才知道。",
        "offers": offers,
    }
    out = ROOT / "data" / "offers.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cats = Counter(tuple(item["categories"]) for item in offers)
    print(f"wrote {out} ({len(offers)} unique offers)")
    print(f"generatedAt {data['generatedAt']}")
    print(f"store closesAt {store.get('closesAt')} closedToday {store.get('closedToday')} source {store['hoursSourceUrl']}")
    print("category combos:", dict(cats))
    print("with original", sum(1 for item in offers if item["original"] is not None))
    print("no original", sum(1 for item in offers if item["original"] is None))
    print("promo only", sum(1 for item in offers if item["sale"] is None))


if __name__ == "__main__":
    main()
