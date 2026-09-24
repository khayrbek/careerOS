#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Переотправка отклика с выбором резюме (форма с вопросами, Боржоми)."""
import sys, time
from playwright.sync_api import sync_playwright

VACANCY, RESUME, COVER_FILE, ANSWER = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
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
    time.sleep(8)
    pg.mouse.wheel(0, 400); time.sleep(1.2)

    # Кнопка повторного отклика (или обычного, если отклика нет)
    again = pg.locator("[data-qa='vacancy-response-link-top-again']")
    normal = pg.locator("[data-qa='vacancy-response-link-top']")
    if again.count():
        again.first.click()
    elif normal.count():
        normal.first.click()
    else:
        print("нет кнопки отклика"); b.close(); sys.exit(5)
    time.sleep(4)

    # 1) Открыть выбор резюме и выбрать нужное
    card = pg.locator(".magritte-select-layout [role='button']").first
    if card.count():
        card.click(); time.sleep(2)
        try:
            pg.get_by_text(RESUME, exact=True).last.click(); time.sleep(2.5)
            print("Резюме выбрано:", RESUME)
        except Exception as e:
            print("выбор резюме warn:", str(e)[:70])
    else:
        print("карточка резюме не найдена")

    # 2) Ответ на вопрос работодателя
    ta_q = pg.locator("textarea[name*='task_']").first
    if ta_q.count():
        ta_q.click(); ta_q.fill(ANSWER); time.sleep(1); print("Ответ:", ANSWER)

    # 3) Сопроводительное
    toggle = pg.locator("[data-qa='vacancy-response-letter-toggle']")
    if toggle.count():
        toggle.first.click(); time.sleep(1.5)
    # ищем textarea сопроводительного (не task_)
    cover_ta = None
    for ta in pg.locator("textarea").all():
        nm = ta.get_attribute("name") or ""
        if "task_" not in nm:
            cover_ta = ta; break
    if cover_ta is not None:
        cover_ta.click(); cover_ta.fill(COVER); time.sleep(1)
        print("Сопроводительное:", len(COVER))

    submit = pg.locator("[data-qa='vacancy-response-submit-popup']").first
    print("Кнопка:", "disabled" if submit.is_disabled() else "активна")
    if submit.is_disabled():
        pg.screenshot(path=f"/tmp/apply_{VID}_blocked.png"); b.close(); sys.exit(3)
    submit.click(); time.sleep(5)
    body = pg.inner_text("body")
    ok = any(k.lower() in body.lower() for k in ["Отклик отправлен","Вы откликнулись","Резюме отправлено"])
    pg.screenshot(path=f"/tmp/apply_{VID}_done.png")
    print("РЕЗУЛЬТАТ:", "✅ отправлено" if ok else "⚠️ нет подтверждения")
    b.close()
