#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Наполнение очереди авто-откликов из избранного hh (лайкнутые).
enqueue_fav.py [--limit N]
"""
import json, re, subprocess, sys, html as H

HOME = "/root/.hermes"
CFG = json.load(open(f"{HOME}/role_matrix.json"))
QUEUE = f"{HOME}/apply_queue.json"

SKIP_WORDS = ["junior", "стажер", "стажёр", "интерн", "стажировк", "ассистент", "помощник"]

def load(p, d):
    try: return json.load(open(p))
    except Exception: return d

def fetch(url):
    try:
        r = subprocess.run(["curl","-s","-L","--max-time","25",url,
            "-H","User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"],
            capture_output=True, text=True, timeout=35)
        html = r.stdout
    except Exception:
        return None, None, ""
    title = company = ""
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    if m:
        try:
            d = json.loads(H.unescape(m.group(1)))
            title = d.get("title","").replace("Вакансия ","").split(" в ")[0].strip()
            org = d.get("hiringOrganization") or {}
            company = org.get("name","") if isinstance(org, dict) else ""
            desc = re.sub(r"<[^>]+>"," ", d.get("description",""))
            desc = re.sub(r"\s+"," ", H.unescape(desc)).strip()
        except Exception:
            desc = ""
    else:
        desc = ""
    return title, company, desc

AI_RE = re.compile(r'(?i)(?:\bии\b|\bai\b|llm|genai|\bgpt\b|нейросет|\bагент)')

def classify(title, desc):
    t = title.lower()
    if any(w in t for w in SKIP_WORDS):
        return None
    # 0) ИИ-роли — высший приоритет (regex по заголовку, затем описанию)
    ai_role = next((r for r in CFG["roles"] if r.get("priority") == 1), None)
    if ai_role and (AI_RE.search(title) or AI_RE.search(desc[:1500])):
        return ai_role
    # 1) матч по заголовку
    for r in sorted(CFG["roles"], key=lambda x: x.get("priority", 99)):
        for kw in r["keywords"]:
            if kw in t:
                return r
    # 2) fallback по описанию — только для явных HR/продуктовых ролей
    d = desc.lower()
    for r in sorted(CFG["roles"], key=lambda x: x.get("priority", 99)):
        if 2 <= r.get("priority", 99) <= 3:
            for kw in r["keywords"]:
                if kw in d:
                    return r
    return None

def main():
    limit = 18
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit")+1])
    links = load("/tmp/fav_links.json", [])
    q = load(QUEUE, {"items": []})
    have = {x["url"] for x in q["items"]}
    added = 0
    for it in links:
        if added >= limit: break
        url = it["url"]
        if url in have: continue
        title, company, desc = fetch(url)
        if not title:
            continue
        role = classify(title, desc)
        if not role or not role.get("resume"):
            continue
        q["items"].append({"url": url, "title": title, "company": company,
                           "role": role["name"], "resume": role["resume"],
                           "score": 9, "source": "fav", "added": "2026-09-23"})
        have.add(url); added += 1
        print(f"+ {title} — {company} -> {role['resume']}")
    # приоритет: сначала ИИ/HR-tech×ИИ
    def prio(x):
        r = x.get("role","").lower()
        if "ии" in r or "ai" in r: return 0
        if "hr" in r: return 1
        return 2
    q["items"].sort(key=prio)
    json.dump(q, open(QUEUE,"w"), ensure_ascii=False, indent=1)
    print(f"\nВ очереди: {len(q['items'])}")

main()
