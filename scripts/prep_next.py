#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подготовка/завершение авто-отклика (режим C, LLM-генерация письма).

  prep_next.py next        -> выводит следующую вакансию из очереди + её требования (JSON)
  prep_next.py done <url> [--resume X] [--cover-file Y] -> убирает из очереди, пишет в CRM
  prep_next.py skip <url>  -> убирает из очереди без отклика
"""
import json, sys, subprocess, re, html as H, os, datetime

HOME = "/root/.hermes"
QUEUE = f"{HOME}/apply_queue.json"
COUNTER = f"{HOME}/apply_counter.json"
LOG = f"{HOME}/apply_log.txt"
GAPI = ["python", f"{HOME}/skills/productivity/google-workspace/scripts/google_api.py"]
SHEET = "1cNzjNK8gZMwag8TbJ1SmwNViaIlRDzDfS4EGNWf-kvY"

def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default

def save(p, d):
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)

def today():
    return datetime.datetime.utcnow().strftime("%d.%m.%Y")

def today_key():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")

def fetch_desc(url):
    """Выгружает требования вакансии с hh (JSON-LD + текст)."""
    try:
        r = subprocess.run(["curl","-s","-L","--max-time","30",url,
            "-H","User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"],
            capture_output=True, text=True, timeout=40)
        html = r.stdout
    except Exception as e:
        return "", ""
    desc = ""
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    if m:
        try:
            d = json.loads(H.unescape(m.group(1)))
            desc = re.sub(r"<[^>]+>", " ", d.get("description",""))
            desc = H.unescape(desc)
            desc = re.sub(r"\s+", " ", desc).strip()
        except Exception:
            pass
    if not desc:
        m2 = re.search(r'data-qa="vacancy-description"(.*?)</div>', html, re.S)
        if m2:
            desc = re.sub(r"<[^>]+>", " ", m2.group(1))
            desc = re.sub(r"\s+", " ", H.unescape(desc)).strip()
    return desc[:4000], html

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "next"
    q = load(QUEUE, {"items": []})

    if cmd == "next":
        c = load(COUNTER, {})
        if c.get("date") != today_key():
            c = {"date": today_key(), "count": 0}
        if c.get("count", 0) >= 10:
            print(json.dumps({"status": "limit_reached", "count": c.get("count")}, ensure_ascii=False))
            return
        if not q["items"]:
            print(json.dumps({"status": "queue_empty"}, ensure_ascii=False))
            return
        v = q["items"][0]
        desc, _ = fetch_desc(v["url"])
        v["description"] = desc
        print(json.dumps({"status": "ok", "vacancy": v, "left": len(q["items"]),
                          "today": c.get("count", 0)}, ensure_ascii=False, indent=1))
        return

    if cmd in ("done", "skip"):
        url = sys.argv[2] if len(sys.argv) > 2 else ""
        item = next((x for x in q["items"] if x["url"] == url), None)
        q["items"] = [x for x in q["items"] if x["url"] != url]
        save(QUEUE, q)
        if cmd == "done":
            c = load(COUNTER, {})
            if c.get("date") != today_key():
                c = {"date": today_key(), "count": 0}
            c["count"] = c.get("count", 0) + 1
            save(COUNTER, c)
            if item:
                row = [[today(), item.get("company",""), item.get("title",""), url,
                        "hh.ru", "", "", str(item.get("score","")), "Отклик отправлен",
                        item.get("resume",""), "LLM-генерация", today(), "Ждать ответа", "авто"]]
                try:
                    subprocess.run(GAPI + ["sheets","append",SHEET,"Вакансии!A:N","--values",json.dumps(row, ensure_ascii=False)],
                                   capture_output=True, text=True, timeout=60)
                except Exception as e:
                    print("CRM warn:", str(e)[:80], file=sys.stderr)
            with open(LOG, "a") as f:
                f.write(f"{today()} DONE {url} {item.get('title','') if item else ''}\n")
            print(json.dumps({"status":"done","count":c["count"],"left":len(q["items"])}, ensure_ascii=False))
        else:
            with open(LOG, "a") as f:
                f.write(f"{today()} SKIP {url}\n")
            print(json.dumps({"status":"skipped","left":len(q["items"])}, ensure_ascii=False))
        return

    print("usage: prep_next.py next|done <url>|skip <url>")

main()
