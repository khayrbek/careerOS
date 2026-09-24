#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Авто-отклик с генерацией письма на YandexGPT-5-pro (один отклик за запуск).

Пайплайн: prep_next (вакансия+требования) -> gen_cover (YandexGPT) -> hh_apply2 (отклик) -> prep_next done.
Тихий режим: если нечего делать — stdout пустой (cron no_agent не доставляет сообщение).
"""
import json, subprocess, sys, os, datetime

HOME = "/root/.hermes"
PY = "/usr/local/lib/hermes-agent/venv/bin/python3"
PREP = f"{HOME}/scripts/prep_next.py"
GEN = f"{HOME}/scripts/gen_cover.py"
APPLY = f"{HOME}/scripts/hh_apply2.py"
COVERS = f"{HOME}/covers"

def run(cmd, timeout=240):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr

def main():
    # 1) берём следующую вакансию
    out = run([PY, PREP, "next"], timeout=120)
    try:
        data = json.loads(out.strip().split("\n", 1)[-1] if out.strip().startswith("{") else out[out.index("{"):])
    except Exception:
        try:
            data = json.loads(out[out.index("{"):out.rindex("}")+1])
        except Exception:
            print("ERR: не удалось разобрать prep_next:", out[:300]); return
    st = data.get("status")
    if st != "ok":
        return  # limit_reached / queue_empty -> тихо
    v = data["vacancy"]
    url = v["url"]
    title = v.get("title","")
    company = v.get("company","")
    resume = v.get("resume","")
    vid = url.rstrip("/").split("/")[-1]

    # 2) генерируем письмо через YandexGPT-5-pro
    vjson = f"/tmp/vac_{vid}.json"
    json.dump({"title": title, "company": company, "description": v.get("description","")},
              open(vjson, "w"), ensure_ascii=False)
    cover = f"{COVERS}/auto_{vid}.txt"
    gen_out = run([PY, GEN, vjson, cover], timeout=180)
    if not os.path.exists(cover) or os.path.getsize(cover) < 200:
        run([PY, PREP, "skip", url])
        print(f"⚠️ Не сгенерировалось письмо для «{title}» ({company}) — пропуск")
        return

    # 3) откликаемся
    app_out = run([PY, APPLY, url, resume, cover], timeout=300)
    if "отклик отправлен" in app_out.lower():
        run([PY, PREP, "done", url], timeout=60)
        # тихо: успешные отклики идут в утренний дайджест, не в чат
        return
    else:
        run([PY, PREP, "skip", url], timeout=60)
        if "капч" in app_out.lower() or "captcha" in app_out.lower():
            print(f"🔴 hh требует проверку (капча) — остановился. Вакансия: {title}")
        return

main()
