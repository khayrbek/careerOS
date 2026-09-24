#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Монитор чатов hh.ru (chatik). Выводит СТАБИЛЬНЫЙ список диалогов.
Изменение = новое сообщение или новый чат."""
import time, sys, re
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = b.new_context(storage_state="/root/.hermes/hh_storage_state.json", viewport={"width":1440,"height":1400})
        pg = ctx.new_page()
        try:
            pg.goto("https://chatik.hh.ru/", wait_until="commit", timeout=45000)
        except Exception:
            pass
        time.sleep(9)
        txt = pg.inner_text("body")
        b.close()

    # отрезаем навигацию, оставляем список чатов
    i = txt.find("Только непрочитанные")
    chats = txt[i+len("Только непрочитанные"):] if i >= 0 else txt
    lines = [l.strip() for l in chats.split("\n") if l.strip()]
    # убираем счётчик непрочитанных "99+" и пустое
    out = [l for l in lines if not re.fullmatch(r"\d+\+?", l)]
    print("\n".join(out[:80]))

if __name__ == "__main__":
    main()
