#!/usr/bin/env python3
"""Collect public news mentions of Russian mobile-internet whitelists.
Automatic matches are candidates only; confirmed/none statuses require manual review.
"""
import json, os, re, time, html
from datetime import datetime, timezone
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
    "Москва":["Москва"], "Московская область":["Московская область","Подмосковье"],
    "Мурманская область":["Мурманская область"], "Ненецкий автономный округ":["Ненецкий автономный округ"],
    "Нижегородская область":["Нижегородская область"], "Новгородская область":["Новгородская область"],
    "Новосибирская область":["Новосибирская область"], "Омская область":["Омская область"],
    "Оренбургская область":["Оренбургская область"], "Орловская область":["Орловская область"],
    "Пензенская область":["Пензенская область"], "Пермский край":["Пермский край"],
    "Приморский край":["Приморский край"], "Псковская область":["Псковская область"],
    "Ростовская область":["Ростовская область"], "Рязанская область":["Рязанская область"],
    "Самарская область":["Самарская область"], "Санкт-Петербург":["Санкт-Петербург"],
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

def main():
    collected = {}
    for query in QUERIES:
        try:
            for item in fetch(query):
                if item.get("url"):
                    collected[item["url"]] = item
        except Exception as exc:
            print("Feed error:", query, str(exc))
    reports = sorted(collected.values(), key=lambda x: x.get("date",""), reverse=True)[:100]
    manual_path = os.path.join(DATA, "manual-statuses.json")
    try:
        with open(manual_path, encoding="utf-8") as f:
            manual = json.load(f).get("regions", {})
    except (OSError, ValueError):
        manual = {}
    candidates = {}
    for report in reports:
        for region in report.get("regions", []):
            candidates[region.lower()] = "possible"
    # Manual reviewed values override automated candidate flags.
    for region, status in manual.items():
        if status in ("confirmed", "possible", "none"):
            candidates[region.lower()] = status
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(os.path.join(DATA, "reports.json"), "w", encoding="utf-8") as f:
        json.dump({"updatedAt":now,"reports":reports}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(DATA, "statuses.json"), "w", encoding="utf-8") as f:
        json.dump({"updatedAt":now,"regions":candidates}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Saved", len(reports), "reports and", len(candidates), "region candidates")

if __name__ == "__main__":
    main()
