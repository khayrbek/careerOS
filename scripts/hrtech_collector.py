#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сбор вакансий из публичного TG-канала HR-Tech.Карьера (t.me/HRTech_Jobs)."""
import re, json, html as H, subprocess, os, sys
from datetime import datetime

CHANNEL = "HRTech_Jobs"
STATE_FILE = "/root/.hermes/hrtech_jobs_state.json"
OUT_FILE = "/root/.hermes/hrtech_jobs_latest.json"

# Ключевые слова релевантности под профиль Хайрбека (HR IT / архитектура / проекты / продукт)
RELEVANT = [
    "архитектор", "architecture", "solution architect",
    "руководитель проект", "менеджер проект", "руководитель направлен", "руководитель ит", "руководитель ии",
    "product manager", "product owner", "менеджер продукт", "владелец продукт", "директор по продукт",
    "1с", "зуп", "sap", "hcm", "кэдо", "lms", "ats", "hris", "hcm",
    "интеграц", "hr-систем", "hr систем", "hr-tech", "hr tech", "hrtech",
    "бизнес-аналитик", "системный аналитик", "автоматизац",
    "erp", "цифров", "трансформац", "change",
]
# Явные исключения (не его профиль)
EXCLUDE = [
    "рекрутер", "подбор персонала", "кадровое администр", "менеджер по персоналу",
    "продаж", "маркетолог", "бухгалтер", "охрана труда", "логист", "водитель",
    "юрист", "финансовый директор", "экономист по труд",
]


def fetch_channel():
    url = f"https://t.me/s/{CHANNEL}"
    r = subprocess.run(["curl", "-s", "-L", url,
                        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"],
                       capture_output=True, text=True)
    return r.stdout


def parse_posts(raw):
    blocks = re.split(r'(?=<div class="tgme_widget_message[^"]*" data-post=)', raw)
    posts = []
    for b in blocks:
        m = re.search(r'data-post="([^"]+)"', b)
        if not m:
            continue
        post_id = m.group(1)
        tm = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*(?:<div|<a)', b, re.DOTALL)
        if not tm:
            tm = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', b, re.DOTALL)
        if not tm:
            continue
        text = re.sub(r'<br\s*/?>', '\n', tm.group(1))
        text = re.sub(r'<[^>]+>', '', text)
        text = H.unescape(text).strip()
        if not text:
            continue
        dt = re.search(r'<time datetime="([^"]+)"', b)
        date = dt.group(1) if dt else ""
        posts.append({
            "post_id": post_id,
            "num": int(post_id.split("/")[-1]) if "/" in post_id else 0,
            "date": date,
            "text": text,
            "url": f"https://t.me/{post_id}",
            "closed": text.strip().startswith("❌") or "Вакансия закрыта" in text,
        })
    posts.sort(key=lambda x: x["num"])
    return posts


def parse_vacancy(text):
    """Извлекает заголовок (должность + компания)."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # Если первая строка — пометка о закрытии, берём следующую
    if lines and ("Вакансия закрыта" in lines[0] or lines[0].strip().startswith("❌")):
        first = lines[1] if len(lines) > 1 else lines[0]
    else:
        first = lines[0] if lines else ""
    first = re.sub(r'^❌\s*Вакансия закрыта!?\s*', '', first).strip()
    # Формат: "Должность в компанию X" / "Должность в X"
    m = re.match(r'^(.*?)\s+в\s+(?:компанию\s+|компанию |)(.+)$', first)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return first, ""


def relevance(text):
    low = text.lower()
    score = 0
    hits = []
    for kw in RELEVANT:
        if kw in low:
            score += 1
            hits.append(kw)
    for kw in EXCLUDE:
        if kw in low:
            score -= 2
            hits.append(f"-{kw}")
    return score, hits


def main():
    raw = fetch_channel()
    posts = parse_posts(raw)
    print(f"Загружено постов: {len(posts)}")

    state = {}
    if os.path.exists(STATE_FILE):
        state = json.load(open(STATE_FILE))

    results = []
    for p in posts:
        role, comp = parse_vacancy(p["text"])
        score, hits = relevance(p["text"])
        results.append({
            "id": p["post_id"],
            "num": p["num"],
            "date": p["date"],
            "role": role,
            "company": comp,
            "url": p["url"],
            "closed": p["closed"],
            "score": score,
            "hits": hits,
            "text": p["text"],
        })

    results.sort(key=lambda x: x["num"], reverse=True)
    json.dump(results, open(OUT_FILE, "w"), ensure_ascii=False, indent=2)
    json.dump({"last_num": results[0]["num"] if results else 0}, open(STATE_FILE, "w"))

    print(f"\n{'ОТКР':4} {'РЕЛ':4} {'ID':6} ДОЛЖНОСТЬ — КОМПАНИЯ")
    print("-" * 90)
    for r in results:
        flag = "✗" if r["closed"] else "✓"
        mark = "🔥" if r["score"] >= 3 else ("•" if r["score"] >= 1 else " ")
        print(f"{flag:4} {r['score']:>3}  {r['num']:6} {r['role'][:45]:45} — {r['company'][:30]}  {mark}")

    rel = [r for r in results if r["score"] >= 2 and not r["closed"]]
    print(f"\n🔥 Релевантных открытых: {len(rel)}")
    for r in rel:
        print(f"   • {r['role']} — {r['company']} ({r['url']})")


if __name__ == "__main__":
    main()
