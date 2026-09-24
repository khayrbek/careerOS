#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сбор вакансий из группы MAX «Вакансии» через Bot API.
Забирает новые сообщения (updates), извлекает вакансии hh.ru, копит в буфер.
Тихий режим: при отсутствии новых данных не печатает ничего (для cron no_agent)."""
import json, os, re, subprocess, sys, time

CFG = "/root/.hermes/max_config.json"
STATE = "/root/.hermes/max_state.json"
BUFFER = "/root/.hermes/max_vacancies.json"

cfg = json.load(open(CFG))
TOKEN = cfg["token"]
CHAT_ID = cfg["chat_id"]
API = "https://platform-api.max.ru"


def api_get(path):
    r = subprocess.run(["curl", "-s", "--max-time", "20", "-H", f"Authorization: {TOKEN}", f"{API}{path}"],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    marker = state.get("marker")
    url = f"/updates?timeout=0&limit=100" + (f"&marker={marker}" if marker else "")
    data = api_get(url)
    ups = data.get("updates", [])
    new_marker = data.get("marker")

    buffer = json.load(open(BUFFER)) if os.path.exists(BUFFER) else []
    known = {v.get("vacancy_id") for v in buffer}
    added = []

    for u in ups:
        if u.get("update_type") != "message_created":
            continue
        m = u.get("message", {})
        if m.get("recipient", {}).get("chat_id") != CHAT_ID:
            continue
        body = m.get("body", {})
        text = body.get("text", "") or ""
        sender = m.get("sender", {}).get("name", "")
        ts = m.get("timestamp", 0)

        vid = None
        title = ""
        desc = ""
        # из текста
        mm = re.search(r'hh\.ru/vacancy/(\d+)', text)
        if mm:
            vid = mm.group(1)
        # из вложения
        for att in body.get("attachments", []) or []:
            urlv = (att.get("payload", {}) or {}).get("url", "") or ""
            mm = re.search(r'hh\.ru/vacancy/(\d+)', urlv)
            if mm:
                vid = mm.group(1)
            if att.get("title"):
                title = att["title"]
            if att.get("description"):
                desc = att["description"]

        if not vid:
            continue
        if vid in known:
            continue

        rec = {
            "vacancy_id": vid,
            "url": f"https://hh.ru/vacancy/{vid}",
            "title": title,
            "short_desc": desc,
            "sender": sender,
            "timestamp": ts,
            "source": "MAX: группа «Вакансии»",
        }
        buffer.append(rec)
        known.add(vid)
        added.append(rec)

    json.dump(buffer, open(BUFFER, "w"), ensure_ascii=False, indent=2)
    json.dump({"marker": new_marker}, open(STATE, "w"))

    if added:
        # при добавлении новых — печатаем (для отладки/уведомления)
        print(f"NEW:{len(added)}")
        for a in added:
            print(f"{a['vacancy_id']}|{a['title']}|{a['url']}")


if __name__ == "__main__":
    main()
