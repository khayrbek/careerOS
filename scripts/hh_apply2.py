#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Универсальный отклик на hh.ru: hh_apply2.py <vacancy_url> <resume_name> <cover_file>"""
import sys, time
from playwright.sync_api import sync_playwright

if len(sys.argv) < 4:
    print("usage: hh_apply2.py <vacancy_url> <resume_name> <cover_file>")
    sys.exit(1)

VACANCY, RESUME, COVER_FILE = sys.argv[1], sys.argv[2], sys.argv[3]
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
    except Exception as e:
        print("goto warn:", str(e)[:70])
    time.sleep(7)
    pg.mouse.wheel(0, 500); time.sleep(1.4)

    # Проверка: не откликались ли уже
    body0 = pg.inner_text("body")
    if ("Вы откликнулись" in body0) or (pg.locator("[data-qa='vacancy-response-link-top-again']").count() > 0):
        print("⚠️ Уже есть отклик на эту вакансию — пропускаю")
        b.close(); sys.exit(2)
    if pg.locator("[data-qa='vacancy-response-link-top']").count() == 0:
        print("⚠️ Кнопка «Откликнуться» не найдена (вакансия недоступна/архив?)")
        pg.screenshot(path=f"/tmp/apply_{VID}_nobtn.png")
        b.close(); sys.exit(5)

    btn = pg.locator("[data-qa='vacancy-response-link-top']").first
    try:
        btn.scroll_into_view_if_needed()
    except Exception:
        pass
    time.sleep(1.2)
    btn.click()
    # ждём появления формы (до 18 сек); при неудаче — повторный клик
    dlg = pg.locator("[role='dialog']").first
    for _ in range(18):
        if dlg.count() > 0 or pg.locator("[data-qa='vacancy-response-submit-popup']").count() > 0:
            break
        time.sleep(1)
    if dlg.count() == 0:
        try:
            btn.click(force=True)
            time.sleep(5)
        except Exception:
            pass
    if dlg.count() == 0 and pg.locator("[data-qa='vacancy-response-submit-popup']").count() == 0:
        print("⚠️ Форма отклика не открылась")
        pg.screenshot(path=f"/tmp/apply_{VID}_nodialog.png")
        b.close(); sys.exit(6)
    dlg = pg.locator("[role='dialog']").first

    # Выбор резюме (если селектор есть в этой форме)
    if dlg.locator("[data-qa='resume-title']").count():
        dlg.locator("[data-qa='resume-title']").first.click()
        time.sleep(2)
        try:
            pg.get_by_text(RESUME, exact=True).last.click()
            time.sleep(2.5)
            print("Резюме:", dlg.locator("[data-qa='resume-title']").first.inner_text())
        except Exception:
            print("Резюме: не удалось переключить (оставлено по умолчанию)")
    else:
        print("Резюме: селектор выбора отсутствует в этой форме")

    # Сопроводительное — если поля нет, нажать «Добавить сопроводительное»
    if pg.locator("[data-qa='vacancy-response-popup-form-letter-input']").count() == 0:
        add = dlg.locator("[data-qa='add-cover-letter']")
        if add.count() == 0:
            add = pg.locator("[data-qa='add-cover-letter']")
        if add.count():
            add.first.click()
            for _ in range(10):
                if pg.locator("[data-qa='vacancy-response-popup-form-letter-input']").count() > 0:
                    break
                time.sleep(0.8)
    ta = pg.locator("[data-qa='vacancy-response-popup-form-letter-input']").first
    ta.click(); time.sleep(0.6)
    ta.fill(COVER)
    time.sleep(1.5)
    print("Письмо:", len(COVER), "знаков")

    submit = dlg.locator("[data-qa='vacancy-response-submit-popup']").first
    if submit.is_disabled():
        print("⚠️ Кнопка заблокирована — отклик не отправлен")
        pg.screenshot(path=f"/tmp/apply_{VID}_blocked.png")
        b.close(); sys.exit(3)

    time.sleep(2.5)
    submit.click()
    time.sleep(5)
    body = pg.inner_text("body")
    pg.screenshot(path=f"/tmp/apply_{VID}_done.png")
    ok = any(k.lower() in body.lower() for k in ["Отклик отправлен","Вы откликнулись","Резюме отправлено"])
    print("РЕЗУЛЬТАТ:", "✅ отклик отправлен" if ok else "⚠️ нет явного подтверждения")
    print("Скриншот: /tmp/apply_%s_done.png" % VID)
    b.close()
    sys.exit(0 if ok else 4)
