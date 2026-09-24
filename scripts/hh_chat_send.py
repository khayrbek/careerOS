#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Отправка сообщения в чат hh.ru (chatik).
Использование: hh_chat_send.py <chat_id> <text_file>
"""
import sys, time
from playwright.sync_api import sync_playwright

CHAT_ID = sys.argv[1]
TEXT = open(sys.argv[2]).read().strip()
URL = f"https://chatik.hh.ru/chat/{CHAT_ID}?without_list=1&platform=xhh&theme=hh-day&dest=iframe"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx = b.new_context(storage_state="/root/.hermes/hh_storage_state.json", viewport={"width":1400,"height":900})
    pg = ctx.new_page()
    pg.goto(URL, wait_until="commit", timeout=60000)
    time.sleep(8)
    ta = pg.locator("textarea[placeholder='Сообщение']").first
    ta.scroll_into_view_if_needed()
    ta.click()
    time.sleep(0.6)
    ta.fill(TEXT)
    time.sleep(1.2)
    pg.keyboard.press("Enter")
    time.sleep(4)
    body = pg.inner_text("body")
    ok = TEXT[:40] in body
    print("РЕЗУЛЬТАТ:", "✅ сообщение отправлено" if ok else "⚠️ не подтверждено")
    pg.screenshot(path="/tmp/chat_sent.png")
    b.close()
