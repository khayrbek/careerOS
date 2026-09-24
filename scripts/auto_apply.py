#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Авто-отклики на hh.ru (режим C): очередь -> роль -> резюме -> письмо -> отклик -> CRM.

Запуск:  auto_apply.py [--max N] [--dry-run]
Предохранители: лимит откликов/день, паузы, порог релевантности, стоп при капче.
"""
import json, subprocess, time, random, os, datetime, re, sys

HOME = "/root/.hermes"
PY = "/usr/local/lib/hermes-agent/venv/bin/python3"
APPLY = f"{HOME}/scripts/hh_apply2.py"
CFG = json.load(open(f"{HOME}/role_matrix.json"))
QUEUE = f"{HOME}/apply_queue.json"
COUNTER = f"{HOME}/apply_counter.json"
LOG = f"{HOME}/apply_log.txt"
COVERS = f"{HOME}/covers"
GAPI = ["python", f"{HOME}/skills/productivity/google-workspace/scripts/google_api.py"]
SHEET = "1cNzjNK8gZMwag8TbJ1SmwNViaIlRDzDfS4EGNWf-kvY"
MAXBUF = f"{HOME}/max_vacancies.json"

MAXN = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 1
DRY = "--dry-run" in sys.argv


def today():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")


def load_json(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def save_json(p, d):
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)


def counter():
    d = load_json(COUNTER, {})
    if d.get("date") != today():
        d = {"date": today(), "count": 0, "seen": d.get("seen", [])}
    d.setdefault("seen", [])
    return d


def classify(title, desc):
    text = (str(title) + " " + str(desc)).lower()
    if any(k.lower() in text for k in CFG.get("skip_keywords", [])):
        return None, 0
    for r in sorted(CFG["roles"], key=lambda x: x["priority"]):
        for kw in r["keywords"]:
            if kw in text:
                return r, 8
    return None, 0


def make_cover(role, position, company):
    tpl = open(CFG["cover_template_file"], encoding="utf-8").read()
    ai = ""
    if role.get("ai_paragraph"):
        ai = ("Отдельно развиваю экспертизу в GenAI/LLM: RAG, AI-агенты, function calling, "
              "контекстный инжиниринг — реализовал ИИ-ассистента, финансового ассистента "
              "и автоматизацию бизнес-процессов.\n\n")
    txt = tpl.replace("{position}", position or "руководителя проектов").replace("{company}", company or "вашей компании").replace("{ai_paragraph}", ai)
    return re.sub(r"\n{3,}", "\n\n", txt)


def enqueue_from_max():
    """Добавляем в очередь релевантные вакансии из буфера MAX."""
    q = load_json(QUEUE, {"items": []})
    have = {i["url"] for i in q["items"]}
    added = 0
    for v in load_json(MAXBUF, []):
        url = (v.get("url") or "").split("?")[0]
        if not url or url in have or "hh.ru/vacancy" not in url:
            continue
        raw_title = v.get("title") or ""
        m = re.search(r"работа в компании (.+)$", raw_title)
        company = m.group(1).strip() if m else ""
        title = raw_title.replace("Вакансия ", "")
        title = re.split(r" в Москве| в Санкт| в ", title)[0].strip()
        desc = v.get("short_desc") or v.get("desc") or ""
        role, score = classify(title, desc)
        if not role or not role.get("resume"):
            continue
        if score < CFG["limits"]["min_score"]:
            continue
        q["items"].append({"url": url, "title": title, "company": company, "role": role["name"], "resume": role["resume"], "score": score, "added": today()})
        have.add(url)
        added += 1
    save_json(QUEUE, q)
    return added


def crm_add(url, title, company, role, resume, score, status, comment=""):
    row = json.dumps([[today(), company, title, url, "авто-отклик", "", "", str(score), status, resume, "Отправлено (авто)", today(), "Ждать ответа", comment]], ensure_ascii=False)
    subprocess.run(GAPI + ["sheets", "append", SHEET, "Вакансии!A:N", "--values", row], capture_output=True, text=True)


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} {msg}\n")


def main():
    n_enq = enqueue_from_max()
    c = counter()
    q = load_json(QUEUE, {"items": []})
    if not q["items"]:
        return
    done = []
    for item in list(q["items"]):
        if c["count"] >= CFG["limits"]["max_per_day"]:
            print(f"⛔ Достигнут дневной лимит ({CFG['limits']['max_per_day']}) — стоп.")
            break
        if len(done) >= MAXN:
            break
        url, title, company, resume = item["url"], item["title"], item.get("company", ""), item["resume"]
        if url in c["seen"]:
            q["items"].remove(item)
            continue
        role = next((r for r in CFG["roles"] if r["name"] == item["role"]), {"name": item["role"]})
        cover = make_cover(role, title, company)
        cpath = f"{COVERS}/auto_{re.sub(r'[^0-9]', '', url)}.txt"
        open(cpath, "w", encoding="utf-8").write(cover)

        if DRY:
            print(f"[dry-run] {title} | {company} | резюме: {resume} | письмо: {len(cover)} зн.")
            done.append(item); q["items"].remove(item); continue

        r = subprocess.run([PY, APPLY, url, resume, cpath], capture_output=True, text=True, timeout=300)
        out = (r.stdout or "") + (r.stderr or "")
        if "отклик отправлен" in out.lower():
            c["count"] += 1
            c["seen"].append(url)
            status = "Отклик отправлен"
            crm_add(url, title, company, item["role"], resume, item["score"], status)
            log(f"OK {url} | {title} | {resume}")
            print(f"✅ Отклик: {title} — {company or '?'} (резюме: {resume})")
            done.append(item)
        elif "уже есть отклик" in out.lower():
            c["seen"].append(url)
            log(f"SKIP(already) {url}")
        elif "captcha" in out.lower() or "проверк" in out.lower():
            log(f"CAPTCHA-STOP {url}")
            print("🛑 Похоже на капчу/проверку hh — остановись, нужен ручной вход.")
            break
        else:
            log(f"FAIL {url} | {out.strip()[:200]}")
            print(f"⚠️ Не отправлено: {title} — {out.strip()[:120]}")
        q["items"].remove(item)
        save_json(QUEUE, q)
        save_json(COUNTER, c)
        time.sleep(random.randint(*CFG["limits"]["pause_between_sec"]))

    save_json(QUEUE, q)
    save_json(COUNTER, c)
    if done:
        print(f"\nИтого: откликов сегодня {c['count']}/{CFG['limits']['max_per_day']}, в очереди осталось {len(q['items'])}.")


if __name__ == "__main__":
    main()
