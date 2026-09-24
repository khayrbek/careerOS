#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Выгрузка сообщений группы MAX «Вакансии» с пагинацией + извлечение вакансий."""
import json, subprocess, re, csv, time

cfg = json.load(open("/root/.hermes/max_config.json"))
TOKEN = cfg["token"]
CHAT = str(cfg["chat_id"])
BASE = "https://platform-api.max.ru"

def api(path):
    r = subprocess.run(["curl","-s","--max-time","30","-H",f"Authorization: {TOKEN}", BASE+path],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}

all_msgs = []
from_ts = None
for page in range(15):
    url = f"/messages?chat_id={CHAT}&count=100"
    if from_ts:
        url += f"&from={from_ts}"
    data = api(url)
    msgs = data.get("messages", [])
    if not msgs:
        break
    all_msgs.extend(msgs)
    oldest = min(m["timestamp"] for m in msgs)
    if from_ts is not None and oldest >= from_ts:
        break
    from_ts = oldest
    time.sleep(0.5)

# дедуп по mid
seen = {}
for m in all_msgs:
    mid = m.get("body",{}).get("mid")
    if mid:
        seen[mid] = m
msgs = sorted(seen.values(), key=lambda m: m["timestamp"])

print("Всего сообщений:", len(msgs))

# Извлечение вакансий
vacs = []
for m in msgs:
    b = m.get("body", {})
    text = b.get("text", "") or ""
    snd = m.get("sender", {})
    author = snd.get("name") or snd.get("first_name","")
    ts = m["timestamp"]
    for att in b.get("attachments", []):
        if att.get("type") == "share":
            url = (att.get("payload") or {}).get("url","")
            title = att.get("title","")
            desc = att.get("description","")
            if "hh.ru/vacancy" in url or "hh.ru/vacancy" in text:
                vacs.append({"ts": ts, "author": author, "url": url, "title": title, "desc": desc})
                break
    else:
        m2 = re.search(r"hh\.ru/vacancy/(\d+)", text)
        if m2:
            vacs.append({"ts": ts, "author": author, "url": f"https://hh.ru/vacancy/{m2.group(1)}", "title": "", "desc": ""})

print("Вакансий найдено:", len(vacs))

json.dump({"messages": msgs, "vacancies": vacs}, open("/root/.hermes/max_chat_dump.json","w"), ensure_ascii=False, indent=1)

# CSV вакансий
import datetime
with open("/root/.hermes/max_vacancies_export.csv","w",newline="",encoding="utf-8") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Дата","Автор","Компания/Должность","Зарплата/описание","Ссылка"])
    for v in vacs:
        dt = datetime.datetime.utcfromtimestamp(v["ts"]/1000).strftime("%d.%m.%Y %H:%M")
        w.writerow([dt, v["author"], v["title"], v["desc"], v["url"]])

print("Файлы: /root/.hermes/max_chat_dump.json, /root/.hermes/max_vacancies_export.csv")
print("Диапазон:", datetime.datetime.utcfromtimestamp(msgs[0]['timestamp']/1000).strftime('%d.%m.%Y'), "-", datetime.datetime.utcfromtimestamp(msgs[-1]['timestamp']/1000).strftime('%d.%m.%Y'))
