#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Рассылка личных сообщений в «Сетке» (setka.ru — соцсеть hh.ru).

Использование:
  setka_write.py "<поисковый запрос>" <файл_текста> [--limit N] [--dry-run]

Примеры:
  setka_write.py "Сбер HR" msg.txt --limit 5
  setka_write.py "РусГидро" msg.txt --dry-run     # только найти, не писать

Авторизация: cookies Сетки в /root/.hermes/setka_storage_state.json
(вход по телефону; экспорт через Cookie-Editor для домена setka.ru).
"""
import sys, time, os, json
from playwright.sync_api import sync_playwright

STATE = "/root/.hermes/setka_storage_state.json"
BASE = "https://setka.ru"

def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    query = sys.argv[1]
    msg = open(sys.argv[2], encoding="utf-8").read().strip()
    limit = int(arg("--limit", "10"))
    dry = "--dry-run" in sys.argv

    if not os.path.exists(STATE):
        print("НЕТ cookies Сетки:", STATE)
        print("Экспортируй cookies setka.ru через Cookie-Editor и пришли — сохраню.")
        sys.exit(2)

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = b.new_context(storage_state=STATE, viewport={"width":1440,"height":900})
        pg = ctx.new_page()

        # 1) Поиск людей
        pg.goto(f"{BASE}/search?query={query}", wait_until="commit", timeout=60000)
        time.sleep(9)
        print("URL поиска:", pg.url)
        print("Заголовок:", pg.title())
        pg.screenshot(path="/tmp/setka_search.png", full_page=True)

        # Собираем ссылки на профили (SPA — берём из DOM)
        links = pg.eval_on_selector_all(
            "a[href*='/profile'], a[href*='/user']",
            "els => [...new Set(els.map(e => e.getAttribute('href')))]"
        )
        links = [l for l in links if l][:limit]
        print("Найдено профилей:", len(links))
        for l in links:
            print("  ", l)

        if dry or not links:
            print("(--dry-run / нет профилей — не пишу)")
            b.close(); return

        # 2) Каждому — «Написать» + сообщение
        sent = 0
        for l in links:
            url = l if l.startswith("http") else BASE + l
            try:
                pg.goto(url, wait_until="commit", timeout=45000)
                time.sleep(5)
                # кнопка «Написать»
                btn = pg.get_by_text("Написать", exact=True).first
                if btn.count() == 0:
                    print("  нет кнопки «Написать»:", url); continue
                btn.click(); time.sleep(3)
                # поле ввода
                box = pg.locator("textarea, [contenteditable='true']").last
                box.click(); time.sleep(0.7)
                box.type(msg, delay=25); time.sleep(0.8)
                # отправка
                snd = pg.get_by_text("Отправить", exact=False).first
                if snd.count():
                    snd.click()
                else:
                    pg.keyboard.press("Enter")
                sent += 1
                print("  ✅ отправлено:", url)
                time.sleep(4)  # пауза (анти-бот)
            except Exception as e:
                print("  ⚠️ ошибка:", url, str(e)[:80])
        print("Итого отправлено:", sent)
        b.close()

if __name__ == "__main__":
    main()
