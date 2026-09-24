#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Монитор TG-канала HR-Tech.Карьера — выводит СТАБИЛЬНЫЙ список постов.
Изменение вывода = появились новые посты (или вакансия закрылась)."""
import sys, os
sys.path.insert(0, "/root/.hermes/scripts")
import importlib.util

spec = importlib.util.spec_from_file_location("hrtech_collector", "/root/.hermes/scripts/hrtech_collector.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

raw = mod.fetch_channel()
posts = mod.parse_posts(raw)
posts.sort(key=lambda x: x["num"])

print("# HRTech_Jobs monitor (stable output)")
for p in posts:
    role, comp = mod.parse_vacancy(p["text"])
    score, _ = mod.relevance(p["text"])
    status = "closed" if p["closed"] else "open"
    print(f"{p['num']}|{role}|{comp}|{status}|{score}")
