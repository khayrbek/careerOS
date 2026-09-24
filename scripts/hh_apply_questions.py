#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Отклик на вакансию с вопросами работодателя (Боржоми)."""
import sys, time, re
from playwright.sync_api import sync_playwright

VACANCY = sys.argv[1]
RESUME = sys.argv[2]
COVER_FILE = sys.argv[3]
ANSWER = sys.argv[4]
COVER = open(COVER_FILE, encoding="utf-8").read().strip()
VID = VACANCY.rstrip("/").split("/")[-1]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx = b.new_context(storage_state="/root/.hermes/hh_storage_state.json",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        locale="ru-RU", viewport={"width":1440,"height":1100})
    pg = ctx.new_page()
    try:
        pg.goto(VACANCY, wait_until="commit", timeout=45000)
    except Exception: pass
    time.sleep(7)
    pg.mouse.wheel(0, 500); time.sleep(1.4)

    body0 = pg.inner_text("body")
    if "Вы откликнулись" in body0 or pg.locator("[data-qa='vacancy-response-link-top-again']").count() > 0:
        print("⚠️ Уже есть отклик — пропускаю"); b.close(); sys.exit(2)

    pg.locator("[data-qa='vacancy-response-link-top']").first.click()
    time.sleep(4)
    dlg = pg.locator("[role='dialog']").first

    # Выбор резюме
    try:
        dlg.locator("[data-qa='resume-title']").first.click(); time.sleep(2)
        pg.get_by_text(RESUME, exact=True).last.click(); time.sleep(2.5)
        print("Резюме:", dlg.locator("[data-qa='resume-title']").first.inner_text())
    except Exception as e:
        print("выбор резюме warn:", str(e)[:60])

    # Ответ на вопрос работодателя
    ta_q = pg.locator("textarea[name*='task_']").first
    if ta_q.count():
        ta_q.click(); ta_q.fill(ANSWER); time.sleep(1)
        print("Ответ на вопрос:", ANSWER)

    # Сопроводительное (если есть кнопка/поле)
    if pg.locator("[data-qa='vacancy-response-popup-form-letter-input']").count() == 0:
        add = dlg.locator("[data-qa='add-cover-letter']")
        if add.count():
            add.first.click(); time.sleep(1.5)
    ta_c = pg.locator("[data-qa='vacancy-response-popup-form-letter-input']")
    if ta_c.count():
        ta_c.first.click(); ta_c.first.fill(COVER); time.sleep(1)
        print("Сопроводительное:", len(COVER), "знаков")

    submit = dlg.locator("[data-qa='vacancy-response-submit-popup']").first
    if not submit.count():
        submit = pg.locator("button:has-text('Откликнуться')").last
    print("Кнопка:", "disabled" if submit.is_disabled() else "АКТИВНА")
    if submit.is_disabled():
        pg.screenshot(path=f"/tmp/apply_{VID}_blocked.png"); b.close(); sys.exit(3)

    time.sleep(2.5)
    submit.click(); time.sleep(5)
    body = pg.inner_text("body")
    ok = any(k.lower() in body.lower() for k in ["Отклик отправлен","Вы откликнулись","Резюме отправлено"])
    pg.screenshot(path=f"/tmp/apply_{VID}_done.png")
    print("РЕЗУЛЬТАТ:", "✅ отклик отправлен" if ok else "⚠️ нет подтверждения")
    b.close()
    sys.exit(0 if ok else 4)
