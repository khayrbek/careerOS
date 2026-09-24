#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сбор данных для утреннего дайджеста по поиску работы.
Выводит готовый текст сводки (используется cron-задачей no_agent)."""
import json, os, datetime, subprocess

HOME = "/root/.hermes"
QUEUE = f"{HOME}/apply_queue.json"
COUNTER = f"{HOME}/apply_counter.json"
LOG = f"{HOME}/apply_log.txt"
MAXBUF = f"{HOME}/max_vacancies.json"
GAPI = ["python", f"{HOME}/skills/productivity/google-workspace/scripts/google_api.py"]
SHEET = "1cNzjNK8gZMwag8TbJ1SmwNViaIlRDzDfS4EGNWf-kvY"


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def today_dot():
    return datetime.datetime.utcnow().strftime("%d.%m.%Y")


def main():
    lines = []
    lines.append("📊 СВОДКА ПО ПОИСКУ РАБОТЫ — " + today_dot())
    lines.append("")

    # --- Отклики за сегодня (из лога) ---
    done, skip = [], []
    if os.path.exists(LOG):
        for ln in open(LOG):
            parts = ln.split()
            if len(parts) >= 3 and parts[0] == today_dot():
                if parts[1] == "DONE":
                    done.append(parts[2] if len(parts) > 2 else "")
                elif parts[1] == "SKIP":
                    skip.append(parts[2] if len(parts) > 2 else "")
    c = load(COUNTER, {})
    lines.append(f"✉️ Отклики сегодня: {c.get('count', 0)} / 10")
    if done:
        lines.append(f"   ссылки: {', '.join(x.rsplit('/',1)[-1] for x in done[:12])}")
    if skip:
        lines.append(f"⚠️ Пропущено (форма/дубль): {len(skip)}")

    # --- Очередь ---
    q = load(QUEUE, {"items": []})
    lines.append("")
    lines.append(f"📋 В очереди на отклик: {len(q['items'])}")
    for it in q["items"][:5]:
        lines.append(f"   • {it.get('title','')[:50]} — {it.get('company','')[:25]}")

    # --- Новые вакансии из MAX ---
    mx = load(MAXBUF, [])
    lines.append("")
    lines.append(f"📡 Новые вакансии (MAX): {len(mx)}")
    for v in mx[:5]:
        lines.append(f"   • {v.get('title','')[:70]}")

    # --- Вакансии из TG-канала ---
    try:
        r = subprocess.run(["/usr/local/lib/hermes-agent/venv/bin/python3",
                            f"{HOME}/scripts/hrtech_collector.py"],
                           capture_output=True, text=True, timeout=120)
        tg = [l.strip() for l in r.stdout.split("\n") if l.strip() and "vacancy" in l]
        if tg:
            lines.append("")
            lines.append(f"📨 TG @HRTech_Jobs — вакансий в ленте: {len(tg)}")
            for l in tg[:5]:
                lines.append("   • " + l[:80])
    except Exception:
        pass

    # --- CRM: итоги ---
    try:
        r = subprocess.run(GAPI + ["sheets", "get", SHEET, "Вакансии!A1:N"],
                           capture_output=True, text=True, timeout=60)
        rows = json.loads(r.stdout)
        total = len(rows) - 1
        from collections import Counter
        st = Counter((row[8] if len(row) > 8 else "") for row in rows[1:])
        lines.append("")
        lines.append(f"🗂 База (CRM): {total} записей")
        for k, v in st.most_common():
            if k:
                lines.append(f"   • {k}: {v}")
    except Exception as e:
        lines.append(f"(CRM недоступна: {str(e)[:60]})")

    print("\n".join(lines))


main()
