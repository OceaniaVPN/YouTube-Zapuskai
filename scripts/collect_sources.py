#!/usr/bin/env python3
"""Collect public news mentions of Russian mobile-internet whitelists.
Automatic matches are candidates only; confirmed/none statuses require manual review.
"""
import json, os, re, time, html
from datetime import datetime, timezone, timedelta, date
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)
QUERIES = [
    '"белый список" "мобильный интернет" Россия',
    '"белые списки" мобильный интернет регионы',
    '"ограничение мобильного интернета" регион белый список',
]
REGIONS = {
    "Республика Адыгея":["Адыгея"], "Республика Алтай":["Республика Алтай"],
    "Алтайский край":["Алтайский край"], "Амурская область":["Амурская область"],
    "Архангельская область":["Архангельская область"], "Астраханская область":["Астраханская область"],
    "Республика Башкортостан":["Башкортостан"], "Белгородская область":["Белгородская область"],
    "Брянская область":["Брянская область"], "Республика Бурятия":["Бурятия"],
    "Владимирская область":["Владимирская область"], "Волгоградская область":["Волгоградская область"],
    "Вологодская область":["Вологодская область"], "Воронежская область":["Воронежская область"],
    "Республика Дагестан":["Дагестан"], "Еврейская автономная область":["Еврейская автономная область"],
    "Забайкальский край":["Забайкальский край"], "Ивановская область":["Ивановская область"],
    "Республика Ингушетия":["Ингушетия"], "Иркутская область":["Иркутская область"],
    "Кабардино-Балкарская Республика":["Кабардино-Балкария"], "Калининградская область":["Калининградская область"],
    "Республика Калмыкия":["Калмыкия"], "Калужская область":["Калужская область"],
    "Камчатский край":["Камчатский край"], "Карачаево-Черкесская Республика":["Карачаево-Черкесия"],
    "Республика Карелия":["Карелия"], "Кемеровская область":["Кемеровская область","Кузбасс"],
    "Хабаровский край":["Хабаровский край"], "Республика Хакасия":["Хакасия"],
    "Ханты-Мансийский автономный округ":["Ханты-Мансийский автономный округ","ХМАО"],
    "Чукотский автономный округ":["Чукотский автономный округ","Чукотка"],
    "Челябинская область":["Челябинская область"], "Чеченская Республика":["Чечня"],
    "Чувашская Республика":["Чувашия"], "Чукотский автономный округ":["Чукотка"],
    "Республика Крым":["Республика Крым","Крым"], "Республика Коми":["Коми"],
    "Костромская область":["Костромская область"], "Краснодарский край":["Краснодарский край","Кубань"],
    "Красноярский край":["Красноярский край"], "Курганская область":["Курганская область"],
    "Курская область":["Курская область"], "Ленинградская область":["Ленинградская область"],
    "Липецкая область":["Липецкая область"], "Магаданская область":["Магаданская область"],
    "Республика Марий Эл":["Марий Эл"], "Республика Мордовия":["Мордовия"],
    "Москва":["Москва","Москве"], "Московская область":["Московская область","Подмосковье"],
    "Мурманская область":["Мурманская область"], "Ненецкий автономный округ":["Ненецкий автономный округ"],
    "Нижегородская область":["Нижегородская область"], "Новгородская область":["Новгородская область"],
    "Новосибирская область":["Новосибирская область"], "Омская область":["Омская область"],
    "Оренбургская область":["Оренбургская область","Оренбург"], "Орловская область":["Орловская область"],
    "Пензенская область":["Пензенская область"], "Пермский край":["Пермский край"],
    "Приморский край":["Приморский край"], "Псковская область":["Псковская область"],
    "Ростовская область":["Ростовская область"], "Рязанская область":["Рязанская область"],
    "Самарская область":["Самарская область","Самаре"], "Санкт-Петербург":["Санкт-Петербург","Петербург","Петербурге"],
    "Саратовская область":["Саратовская область"], "Республика Саха (Якутия)":["Якутия"],
    "Сахалинская область":["Сахалинская область"], "Свердловская область":["Свердловская область"],
    "Севастополь":["Севастополь"], "Смоленская область":["Смоленская область"],
    "Ставропольский край":["Ставропольский край"], "Тамбовская область":["Тамбовская область"],
    "Республика Татарстан":["Татарстан"], "Тверская область":["Тверская область"],
    "Томская область":["Томская область"], "Тульская область":["Тульская область"],
    "Республика Тыва":["Тыва","Тува"], "Тюменская область":["Тюменская область"],
    "Удмуртская Республика":["Удмуртия"], "Ульяновская область":["Ульяновская область"],
    "Херсонская область":["Херсонская область"], "Запорожская область":["Запорожская область"],
    "Ярославская область":["Ярославская область"], "Ямало-Ненецкий автономный округ":["Ямало-Ненецкий автономный округ","ЯНАО"]
}

def clean(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip()

def fetch(query):
    url = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=ru&gl=RU&ceid=RU:ru"
    req = Request(url, headers={"User-Agent":"Mozilla/5.0 (compatible; RegionMonitor/1.0)"})
    with urlopen(req, timeout=25) as response:
        root = ET.fromstring(response.read())
    out = []
    for item in root.findall(".//item"):
        title = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        desc = clean(item.findtext("description"))
        date = clean(item.findtext("pubDate"))
        source_el = item.find("source")
        source = clean(source_el.text if source_el is not None else "")
        text = (title + " " + desc).lower().replace("ё", "е")
        if not any(x in text for x in ("белый список", "белые списки", "белого списка", "белым списком", "whitelist")):
            continue
        matched = []
        normalized = re.sub(r"\s+", " ", text)
        for region, aliases in REGIONS.items():
            for alias in aliases:
                if alias.lower().replace("ё", "е") in normalized:
                    matched.append(region)
                    break
        out.append({"title":title, "url":link, "date":date, "source":source or "Google News RSS", "regions":sorted(set(matched)), "summary":desc[:500]})
    return out


def fetch_json(url):
    req = Request(url, headers={"User-Agent":"WhitelistRFMonitor/1.0 (+https://whitelist-rf.apruxdomain.space)"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def fetch_text(url):
    req = Request(url, headers={"User-Agent":"WhitelistRFMonitor/1.0 (+https://whitelist-rf.apruxdomain.space)"})
    with urlopen(req, timeout=12) as response:
        return response.read().decode("utf-8", "replace")


def parse_monitor_runet_page(page):
    text = clean(re.sub(r"<[^>]+>", " ", page))
    text = re.sub(r"\s+", " ", text)
    restrictions = re.search(r"(\d{1,2})\s+из\s+14\s+дней\s+с\s+ограничениями", text, re.I)
    whitelist_days = re.search(
        r"белые списки\s*[—–:-]\s*(\d{1,2})\s+дн|"
        r"(\d{1,2})\s+из\s+14\s+дней\s+с\s+белыми списками",
        text, re.I
    )
    if not restrictions and not whitelist_days:
        return None
    last_day = re.search(r"последний отмеченный день\s*[—:]\s*(\d{1,2}\s+[а-яё]+)", text, re.I)
    last_noted_date = None
    if last_day:
        months = {
            "января":1, "февраля":2, "марта":3, "апреля":4, "мая":5, "июня":6,
            "июля":7, "августа":8, "сентября":9, "октября":10, "ноября":11, "декабря":12
        }
        parts = last_day.group(1).lower().split()
        try:
            day_number, month_number = int(parts[0]), months[parts[1]]
            today = datetime.now(timezone.utc).date()
            year = today.year
            candidate = date(year, month_number, day_number)
            if (candidate - today).days > 1:
                candidate = date(year - 1, month_number, day_number)
            last_noted_date = candidate.isoformat()
        except (ValueError, KeyError, IndexError):
            last_noted_date = None
    return {
        "restrictionDays": int(restrictions.group(1)) if restrictions else None,
        "periodDays": 14 if restrictions else 14 if whitelist_days else None,
        "whitelistDays": int(whitelist_days.group(1) or whitelist_days.group(2)) if whitelist_days else None,
        "lastNotedDay": last_day.group(1) if last_day else None,
        "lastNotedDate": last_noted_date
    }


def parse_taucloud_page(page):
    plain = clean(re.sub(r"<[^>]+>", " ", page))
    plain = re.sub(r"\s+", " ", plain)
    stamp = re.search(r"Данные на\s+(\d{1,2}:\d{2})\s+МСК,\s+(\d{1,2})\s+([а-яё]+)\s+(\d{4})\s*г", plain, re.I)
    checked_at = None
    if stamp:
        months = {
            "января":1, "февраля":2, "марта":3, "апреля":4, "мая":5, "июня":6,
            "июля":7, "августа":8, "сентября":9, "октября":10, "ноября":11, "декабря":12
        }
        try:
            hour, minute = map(int, stamp.group(1).split(":"))
            checked_at = datetime(
                int(stamp.group(4)), months[stamp.group(3).lower()], int(stamp.group(2)),
                hour, minute, tzinfo=timezone(timedelta(hours=3))
            )
        except (ValueError, KeyError):
            checked_at = None

    districts = {}
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.I | re.S)
    header = None
    for row in rows:
        cells = [clean(cell) for cell in re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row, re.I | re.S)]
        if not cells:
            continue
        if cells[0].strip().lower().startswith("оператор") and all(d in cells for d in ("ЦФО","СЗФО","ЮФО","СКФО","ПФО","УФО","СФО","ДФО")):
            header = cells
            continue
        if header and len(cells) >= len(header):
            for idx, district in enumerate(header[1:], start=1):
                if district not in TAUCLOUD_DISTRICTS:
                    continue
                value = cells[idx].lower()
                entry = districts.setdefault(district, {"enabled":0, "disabled":0})
                if "включены" in value:
                    entry["enabled"] += 1
                elif "выключены" in value:
                    entry["disabled"] += 1

    for district in TAUCLOUD_DISTRICTS:
        # Prefer the publisher's own aggregate percentage from the map summary.
        # The operator table is a fallback; its display may omit rows with no data.
        short = "KGD" if district == "Калининград" else district
        match = re.search(r"(?<![A-Za-zА-Яа-я])" + re.escape(short) + r"\s+(\d{1,3})%", plain, re.I)
        if match:
            districts[district] = {
                "percentage": int(match.group(1)),
                "enabled": None,
                "disabled": None,
                "measuredOperators": None,
                "percentageSource": "publisher summary"
            }

    if not checked_at or not districts:
        raise ValueError("Не удалось разобрать дату или таблицу замеров Taucloud")
    for district, value in districts.items():
        if value.get("percentage") is None:
            measured = value["enabled"] + value["disabled"]
            value["measuredOperators"] = measured
            value["percentage"] = round(value["enabled"] * 100 / measured) if measured else None
        else:
            value["measuredOperators"] = None
        value["status"] = (
            "confirmed" if value.get("percentage") == 100 else
            "none" if value.get("percentage") == 0 else
            "possible" if value.get("percentage") is not None else "unknown"
        )
    return {
        "checkedAt": checked_at.astimezone(timezone.utc).isoformat(timespec="minutes"),
        "url": "https://taucloud.ru/belye-spiski/karta",
        "districts": districts
    }


def norm_region(value):
    return re.sub(r"[^a-zа-я0-9]+", " ", (value or "").lower().replace("ё", "е")).strip()

REGION_FD = {
    "Москва":"ЦФО", "Московская область":"ЦФО", "Белгородская область":"ЦФО",
    "Брянская область":"ЦФО", "Владимирская область":"ЦФО", "Воронежская область":"ЦФО",
    "Ивановская область":"ЦФО", "Калужская область":"ЦФО", "Костромская область":"ЦФО",
    "Курская область":"ЦФО", "Липецкая область":"ЦФО", "Орловская область":"ЦФО",
    "Рязанская область":"ЦФО", "Смоленская область":"ЦФО", "Тамбовская область":"ЦФО",
    "Тверская область":"ЦФО", "Тульская область":"ЦФО", "Ярославская область":"ЦФО",
    "Санкт-Петербург":"СЗФО", "Ленинградская область":"СЗФО", "Архангельская область":"СЗФО",
    "Вологодская область":"СЗФО", "Мурманская область":"СЗФО", "Новгородская область":"СЗФО",
    "Псковская область":"СЗФО", "Республика Карелия":"СЗФО", "Республика Коми":"СЗФО",
    "Ненецкий автономный округ":"СЗФО",
    "Республика Адыгея":"ЮФО", "Республика Калмыкия":"ЮФО", "Краснодарский край":"ЮФО",
    "Астраханская область":"ЮФО", "Волгоградская область":"ЮФО", "Ростовская область":"ЮФО",
    "Республика Крым":"Крым", "Севастополь":"Крым", "Калининградская область":"Калининград",
    "Республика Дагестан":"СКФО", "Республика Ингушетия":"СКФО",
    "Кабардино-Балкарская Республика":"СКФО", "Карачаево-Черкесская Республика":"СКФО",
    "Чеченская Республика":"СКФО", "Ставропольский край":"СКФО",
    "Республика Башкортостан":"ПФО", "Республика Марий Эл":"ПФО", "Республика Мордовия":"ПФО",
    "Республика Татарстан":"ПФО", "Удмуртская Республика":"ПФО", "Чувашская Республика":"ПФО",
    "Пермский край":"ПФО", "Нижегородская область":"ПФО", "Оренбургская область":"ПФО",
    "Пензенская область":"ПФО", "Самарская область":"ПФО", "Саратовская область":"ПФО",
    "Ульяновская область":"ПФО",
    "Курганская область":"УФО", "Свердловская область":"УФО", "Тюменская область":"УФО",
    "Челябинская область":"УФО", "Ханты-Мансийский автономный округ":"УФО",
    "Ямало-Ненецкий автономный округ":"УФО",
    "Республика Алтай":"СФО", "Алтайский край":"СФО", "Кемеровская область":"СФО",
    "Красноярский край":"СФО", "Новосибирская область":"СФО", "Омская область":"СФО",
    "Томская область":"СФО", "Республика Хакасия":"СФО", "Республика Тыва":"СФО",
    "Иркутская область":"СФО",
    "Республика Бурятия":"ДФО", "Забайкальский край":"ДФО", "Республика Саха (Якутия)":"ДФО",
    "Амурская область":"ДФО", "Еврейская автономная область":"ДФО", "Камчатский край":"ДФО",
    "Магаданская область":"ДФО", "Приморский край":"ДФО", "Сахалинская область":"ДФО",
    "Хабаровский край":"ДФО", "Чукотский автономный округ":"ДФО"
}
TAUCLOUD_DISTRICTS = ("ЦФО","СЗФО","ЮФО","СКФО","ПФО","УФО","СФО","ДФО","Калининград","Крым")

def main():
    collected = {}
    errors = []
    successful_sources = 0
    api_ok = False
    api_generated = None
    api_region_statuses = {}
    items = []
    api_region_total = 0
    runet_region_data = {}
    runet_region_statuses = {}
    runet_regions_with_whitelist = set()
    runet_pages_total = 0
    runet_pages_ok = 0
    runet_page_errors = 0
    taucloud_data = None

    # Primary structured source: shutdown.fyi public API (CC BY 4.0).
    try:
        payload = fetch_json("https://shutdown.fyi/api/status.json")
        items = payload.get("items")
        if not isinstance(items, list):
            raise ValueError("В ответе API отсутствует массив items")
        api_region_total = sum(1 for item in items if item.get("kind") == "region")
        api_ok = True
        successful_sources += 1
        api_generated = payload.get("generatedAt")

        aliases = {}
        for canonical, names in REGIONS.items():
            aliases[norm_region(canonical)] = canonical
            for alias in names:
                aliases[norm_region(alias)] = canonical

        for item in items:
            if item.get("kind") != "region":
                continue
            api_name = item.get("name") or item.get("slug") or ""
            canonical = aliases.get(norm_region(api_name))
            if not canonical:
                continue
            state = item.get("status")
            score = item.get("score")
            confidence = item.get("confidence")
            # shutdown.fyi reports anomalies/outages, not an official declaration
            # of a whitelist. Therefore API signals can only create "possible".
            if state in ("degraded", "down") and (confidence is None or confidence >= 0.15):
                api_region_statuses[canonical.lower()] = "possible"
                url = item.get("url") or ("https://shutdown.fyi/api/status/region/" + item.get("slug", "") + ".json")
                collected["api:" + canonical.lower()] = {
                    "title": "Сигнал по региону: " + canonical,
                    "url": url,
                    "date": item.get("computedAt") or item.get("changedAt") or api_generated or "",
                    "source": "shutdown.fyi API (CC BY 4.0)",
                    "regions": [canonical],
                    "summary": "Статус: " + str(state) +
                               "; индекс: " + str(score if score is not None else "н/д") +
                               "; уверенность: " + str(confidence if confidence is not None else "н/д") +
                               "; жалобы за час: " + str(item.get("reports1h", "н/д")) +
                               ". Это сигнал мониторинга, не официальное подтверждение белого списка."
                }
    except Exception as exc:
        errors.append("shutdown.fyi API: " + type(exc).__name__ + ": " + str(exc))
        print("API error:", errors[-1])

    # Region pages publish the separate 14-day "Монитор Рунета" observations.
    # Pace requests below the documented API limit of 60 requests per minute.
    if api_ok:
        region_items = [x for x in items if x.get("kind") == "region"]
        runet_pages_total = len(region_items)
        for region_item in region_items:
            canonical = aliases.get(norm_region(region_item.get("name") or ""))
            slug = region_item.get("slug")
            if not canonical or not slug:
                continue
            page_url = "https://shutdown.fyi/kogda-vklyuchat-internet/" + quote(str(slug), safe="-") + "/"
            try:
                page_html = fetch_text(page_url)
                runet_pages_ok += 1
                page_data = parse_monitor_runet_page(page_html)
                if page_data:
                    page_data["url"] = page_url
                    runet_region_data[canonical.lower()] = page_data
                    white_days = page_data.get("whitelistDays")
                    restriction_days = page_data.get("restrictionDays")
                    last_date = page_data.get("lastNotedDate")
                    fresh = False
                    if last_date:
                        try:
                            age_days = (datetime.now(timezone.utc).date() - date.fromisoformat(last_date)).days
                            fresh = 0 <= age_days <= 3
                        except ValueError:
                            fresh = False
                    if fresh and white_days is not None and white_days > 0:
                        # Red: the source explicitly records whitelist use in the 14-day window.
                        runet_region_statuses[canonical.lower()] = "confirmed"
                        runet_regions_with_whitelist.add(canonical)
                    elif fresh and restriction_days is not None and restriction_days > 0:
                        # Yellow: restrictions were recorded, but whitelist days are zero/unspecified.
                        runet_region_statuses[canonical.lower()] = "possible"
                    elif fresh and restriction_days == 0 and white_days == 0:
                        # Green only when the source explicitly reports both counters as zero.
                        runet_region_statuses[canonical.lower()] = "none"
            except Exception as exc:
                runet_page_errors += 1
                print("Monitor Runeta page failed:", slug, type(exc).__name__)
            time.sleep(1.1)

        if runet_pages_ok:
            successful_sources += 1
        if runet_page_errors:
            errors.append("Монитор Рунета: недоступно страниц " + str(runet_page_errors) + " из " + str(runet_pages_total))

    # Independent current modem measurements from Taucloud, by operator and federal district.
    try:
        taucloud_page = fetch_text("https://taucloud.ru/belye-spiski/karta")
        taucloud_data = parse_taucloud_page(taucloud_page)
        age_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(taucloud_data["checkedAt"])).total_seconds()
        if age_seconds < -300 or age_seconds > 6 * 3600:
            raise ValueError("Замеры Taucloud устарели или имеют некорректную дату")
        successful_sources += 1
    except Exception as exc:
        taucloud_data = None
        errors.append("Taucloud: " + type(exc).__name__ + ": " + str(exc))
        print("Taucloud error:", errors[-1])

    # Recent incident feed is supplementary; API status remains usable if it fails.
    try:
        incidents_payload = fetch_json("https://shutdown.fyi/api/incidents.json")
        incidents = incidents_payload.get("incidents", [])
        if isinstance(incidents, list):
            successful_sources += 1
            for incident in incidents:
                entity = incident.get("entity", "")
                if not entity.startswith("region:"):
                    continue
                slug = entity.split(":", 1)[1]
                region_item = next((x for x in (items if api_ok else []) if x.get("kind") == "region" and x.get("slug") == slug), None)
                region_name = (region_item or {}).get("name") or slug
                canonical = next((v for k, v in REGIONS.items() if norm_region(k) == norm_region(region_name)), None)
                if not canonical:
                    continue
                key = "incident:" + str(incident.get("id", slug))
                collected[key] = {
                    "title": incident.get("title") or ("Инцидент: " + canonical),
                    "url": incident.get("url") or "https://shutdown.fyi/",
                    "date": incident.get("startedAt") or incidents_payload.get("generatedAt", ""),
                    "source": "shutdown.fyi · инциденты (CC BY 4.0)",
                    "regions": [canonical],
                    "summary": "Серьёзность: " + str(incident.get("severity", "н/д")) +
                               ". Сигнал мониторинга; не официальное подтверждение белого списка."
                }
    except Exception as exc:
        errors.append("shutdown.fyi incidents: " + type(exc).__name__ + ": " + str(exc))
        print("Incident API error:", errors[-1])

    # RSS/news remains an additional source, never the only source of regional status.
    for query in QUERIES:
        try:
            for item in fetch(query):
                if item.get("url"):
                    collected[item["url"]] = item
            successful_sources += 1
        except Exception as exc:
            message = f"{query}: {type(exc).__name__}: {exc}"
            errors.append(message)
            print("RSS error:", message)

    monitor_path = os.path.join(DATA, "monitor.json")
    try:
        with open(monitor_path, encoding="utf-8") as f:
            monitor = json.load(f)
    except (OSError, ValueError):
        monitor = {}

    try:
        with open(os.path.join(DATA, "reports.json"), encoding="utf-8") as f:
            previous_reports = json.load(f).get("reports", [])
    except (OSError, ValueError):
        previous_reports = []

    try:
        with open(os.path.join(DATA, "statuses.json"), encoding="utf-8") as f:
            previous_statuses = json.load(f).get("regions", {})
    except (OSError, ValueError):
        previous_statuses = {}

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if successful_sources == 0:
        monitor.update({
            "status": "error", "lastAttemptAt": now,
            "error": "Не удалось получить данные ни из одного источника.",
            "details": errors, "successfulFeeds": 0,
            "totalFeeds": 7, "reportsFound": 0
        })
        with open(monitor_path, "w", encoding="utf-8") as f:
            json.dump(monitor, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("All sources failed; previous data preserved")
        return

    # Retain old records when a source temporarily returns an empty response.
    merged = {r.get("url"): r for r in previous_reports if r.get("url")}
    merged.update({r.get("url"): r for r in collected.values() if r.get("url")})
    reports = sorted(merged.values(), key=lambda x: x.get("date", ""), reverse=True)[:150]

    preserve_previous = (not api_ok) or (
        runet_pages_total > 0 and len(runet_region_data) < max(1, runet_pages_total // 2)
    )
    candidates = dict(previous_statuses) if preserve_previous else {}
    if api_ok:
        candidates.update(api_region_statuses)
    candidates.update(runet_region_statuses)

    # Fresh district-level modem results are the current status layer.
    # Region-level 14-day Monitor Runeta history remains in the popup for context.
    taucloud_regions = {}
    if taucloud_data:
        taucloud_checked = datetime.fromisoformat(taucloud_data["checkedAt"])
        tau_fresh = (datetime.now(timezone.utc) - taucloud_checked).total_seconds() <= 6 * 3600
        if tau_fresh:
            for region, district in REGION_FD.items():
                district_data = taucloud_data["districts"].get(district)
                if not district_data:
                    continue
                measured = district_data.get("measuredOperators")
                pct = district_data.get("percentage")
                if pct is None or (measured is not None and measured < 2):
                    continue
                entry = {
                    "status": district_data["status"], "district": district,
                    "percentage": pct,
                    "activeOperators": district_data.get("enabled"),
                    "disabledOperators": district_data.get("disabled"),
                    "measuredOperators": measured,
                    "checkedAt": taucloud_data["checkedAt"],
                    "url": taucloud_data["url"],
                    "level": "district"
                }
                taucloud_regions[region.lower()] = entry
                candidates[region.lower()] = entry["status"]


    # Add orange candidates only for recent regional reports that explicitly
    # connect whitelist language with mobile-internet restrictions/outages.
    # A generic story about a service being added to the federal whitelist
    # must not be mistaken for a regional mobile-internet restriction.
    aliases = {}
    for canonical, names in REGIONS.items():
        aliases[norm_region(canonical)] = canonical
        for alias in names:
            aliases[norm_region(alias)] = canonical

    whitelist_pattern = re.compile(r"бел\w*\s+списк\w*|white[\s-]?list", re.I)
    mobile_context_pattern = re.compile(
        r"мобильн\w*\s+интернет|интернет.{0,70}(?:отключ|огранич|не работает)|"
        r"(?:отключ|огранич).{0,70}интернет|бел\w*\s+списк\w*.{0,100}(?:мобильн|отключ|огранич)|"
        r"(?:мобильн|отключ|огранич).{0,100}бел\w*\s+списк",
        re.I
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    region_report_names = set()
    for report in collected.values():
        story_text = (report.get("title", "") + " " + report.get("summary", "")).lower().replace("ё", "е")
        if not whitelist_pattern.search(story_text) or not mobile_context_pattern.search(story_text):
            continue
        published = None
        raw_date = report.get("date", "")
        try:
            published = parsedate_to_datetime(raw_date)
        except (TypeError, ValueError, OverflowError):
            try:
                published = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except (TypeError, ValueError, AttributeError):
                published = None
        if published is None:
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published < cutoff:
            continue
        for reported_region in report.get("regions", []):
            canonical = aliases.get(norm_region(reported_region))
            if not canonical:
                continue
            key = canonical.lower()
            if candidates.get(key) not in ("confirmed", "none"):
                candidates[key] = "possible"
            region_report_names.add(canonical)

    manual_path = os.path.join(DATA, "manual-statuses.json")
    try:
        with open(manual_path, encoding="utf-8") as f:
            manual = json.load(f).get("regions", {})
    except (OSError, ValueError):
        manual = {}
    for region, status in manual.items():
        if status in ("confirmed", "possible", "none"):
            candidates[region.lower()] = status

    monitor.update({
        "status": "ok" if not errors else "partial",
        "lastAttemptAt": now,
        "lastSuccessAt": now,
        "error": None if not errors else "Часть источников недоступна; успешные источники сохранены.",
        "details": errors,
        "successfulFeeds": successful_sources,
        "totalFeeds": 7,
        "reportsFound": len(collected),
        "shutdownApiOk": api_ok,
        "shutdownApiUpdatedAt": api_generated,
        "shutdownApiRegionsTotal": api_region_total,
        "shutdownApiRegionsWithSignals": len(api_region_statuses),
        "monitorRunetPagesFetched": runet_pages_ok,
        "monitorRunetPagesTotal": runet_pages_total,
        "monitorRunetRegionsWithData": len(runet_region_data),
        "monitorRunetRegionsWithWhitelist": len(runet_regions_with_whitelist),
        "taucloudOk": bool(taucloud_data),
        "taucloudCheckedAt": taucloud_data.get("checkedAt") if taucloud_data else None,
        "taucloudMeasuredDistricts": len(taucloud_data.get("districts", {})) if taucloud_data else 0,
        "taucloudRegionsMapped": len(taucloud_regions),
        "monitorRunetRegionsConfirmedNoRestriction": sum(
            1 for key, data in runet_region_data.items()
            if data.get("lastNotedDate") and
            (datetime.now(timezone.utc).date() - date.fromisoformat(data["lastNotedDate"])).days in range(0, 4) and
            data.get("restrictionDays") == 0 and data.get("whitelistDays") == 0
        ),
        "regionReportsFound": len(region_report_names | runet_regions_with_whitelist),
        "attribution": "shutdown.fyi / Монитор Рунета — На связи"
    })
    with open(os.path.join(DATA, "reports.json"), "w", encoding="utf-8") as f:
        json.dump({"updatedAt": now, "reports": reports}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(DATA, "statuses.json"), "w", encoding="utf-8") as f:
        json.dump({"updatedAt": now, "regions": candidates, "monitorRunet": runet_region_data, "taucloud": {"checkedAt": taucloud_data.get("checkedAt"), "url": taucloud_data.get("url"), "districts": taucloud_data.get("districts"), "regions": taucloud_regions} if taucloud_data else {}}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(monitor_path, "w", encoding="utf-8") as f:
        json.dump(monitor, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Saved", len(reports), "reports and", len(candidates), "region candidates;", len(region_report_names), "recent region reports; API regions:", api_region_total)

if __name__ == "__main__":
    main()
