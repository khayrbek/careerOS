#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Веб-дашборд поиска работы — читает CRM из Google Sheets, отдаёт HTML + JSON API."""
import json, subprocess, time, os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SHEET_ID = "1cNzjNK8gZMwag8TbJ1SmwNViaIlRDzDfS4EGNWf-kvY"
COMPANIES_SHEET_ID = "13I_d2FiGd3xZ3yx6Y9dV7pw6dleVkDhk1UCjRXgr3zc"
OUTREACH_SHEET_ID = "1GwnXoOGTYnTGHR1s29Wv0Y3xg7bZPp_MkKrZbMgTHb4"
BACKLOG_SHEET_ID = "1ktRp6EftgVRRwPBI8EmnLou3CuQxlxp3zG8yTnYisaM"
GAPI = "/root/.hermes/skills/productivity/google-workspace/scripts/google_api.py"
PY = "/usr/local/lib/hermes-agent/venv/bin/python3"
PORT = 8902
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_cache = {"t": 0, "rows": []}
_cc = {"t": 0, "rows": []}
CACHE_TTL = 45


def read_companies():
    now = time.time()
    if now - _cc["t"] < CACHE_TTL and _cc["rows"]:
        return _cc["rows"]
    try:
        r = subprocess.run([PY, GAPI, "sheets", "get", COMPANIES_SHEET_ID, "Компании!A1:F100"],
                           capture_output=True, text=True, timeout=30)
        rows = json.loads(r.stdout) if r.stdout.strip() else []
    except Exception:
        rows = _cc["rows"]
    _cc["t"] = now
    _cc["rows"] = rows
    return rows


def normalize_companies(rows):
    if not rows:
        return []
    out = []
    for row in rows[1:]:
        row = (row + [""] * (6 - len(row)))[:6]
        if not any(c.strip() for c in row):
            continue
        out.append({"prio": row[0], "name": row[1], "category": row[2],
                    "why": row[3], "search": row[4], "status": row[5]})
    return out


_oc = {"t": 0, "rows": []}
_bc = {"t": 0, "rows": []}


def read_outreach():
    now = time.time()
    if now - _oc["t"] < CACHE_TTL and _oc["rows"]:
        return _oc["rows"]
    try:
        r = subprocess.run([PY, GAPI, "sheets", "get", OUTREACH_SHEET_ID, "Аутрич!A1:I500"],
                           capture_output=True, text=True, timeout=30)
        rows = json.loads(r.stdout) if r.stdout.strip() else []
    except Exception:
        rows = _oc["rows"]
    _oc["t"] = now
    _oc["rows"] = rows
    return rows


def normalize_outreach(rows):
    if not rows:
        return []
    out = []
    for row in rows[1:]:
        row = (row + [""] * (9 - len(row)))[:9]
        if not any(c.strip() for c in row):
            continue
        out.append({"date": row[0], "company": row[1], "contact": row[2],
                    "position": row[3], "channel": row[4], "reason": row[5],
                    "message": row[6], "status": row[7], "reply": row[8]})
    return out


def read_backlog():
    now = time.time()
    if now - _bc["t"] < CACHE_TTL and _bc["rows"]:
        return _bc["rows"]
    try:
        r = subprocess.run([PY, GAPI, "sheets", "get", BACKLOG_SHEET_ID, "Бэклог!A1:F500"],
                           capture_output=True, text=True, timeout=30)
        rows = json.loads(r.stdout) if r.stdout.strip() else []
    except Exception:
        rows = []
    _bc["t"] = now
    _bc["rows"] = rows
    return rows


def normalize_backlog(rows):
    if not rows:
        return []
    out = []
    for row in rows[1:]:
        row = (row + [""] * (6 - len(row)))[:6]
        if not any(c.strip() for c in row):
            continue
        out.append({"task": row[0], "project": row[1], "priority": row[2],
                    "status": row[3], "deadline": row[4], "comment": row[5]})
    return out


def read_sheet():
    now = time.time()
    if now - _cache["t"] < CACHE_TTL and _cache["rows"]:
        return _cache["rows"]
    try:
        r = subprocess.run([PY, GAPI, "sheets", "get", SHEET_ID, "Вакансии!A1:N300"],
                           capture_output=True, text=True, timeout=30)
        rows = json.loads(r.stdout) if r.stdout.strip() else []
    except Exception as e:
        rows = _cache["rows"]
    _cache["t"] = now
    _cache["rows"] = rows
    return rows


def normalize(rows):
    if not rows:
        return []
    header = rows[0]
    items = []
    for i, row in enumerate(rows[1:], start=2):
        row = (row + [""] * (14 - len(row)))[:14]
        if not any(c.strip() for c in row):
            continue
        items.append({
            "row": i,
            "date": row[0], "company": row[1], "vacancy": row[2], "url": row[3],
            "source": row[4], "location": row[5], "salary": row[6], "relevance": row[7],
            "status": row[8] or "Новая", "resume": row[9], "cover": row[10],
            "applied": row[11], "next": row[12], "comment": row[13],
        })
    return items


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/data"):
            items = normalize(read_sheet())
            companies = normalize_companies(read_companies())
            outreach = normalize_outreach(read_outreach())
            backlog = normalize_backlog(read_backlog())
            self._send(200, json.dumps({"items": items, "companies": companies,
                                        "outreach": outreach, "backlog": backlog},
                                       ensure_ascii=False).encode("utf-8"), "application/json")
        elif self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(BASE_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "index.html not found", "text/plain; charset=utf-8")
        elif self.path in ("/about", "/about/", "/about.html", "/product", "/product/"):
            try:
                with open(os.path.join(BASE_DIR, "about.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "about.html not found", "text/plain; charset=utf-8")
        elif self.path in ("/outreach", "/outreach/", "/outreach.html"):
            try:
                with open(os.path.join(BASE_DIR, "outreach.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "outreach.html not found", "text/plain; charset=utf-8")
        elif self.path in ("/applications", "/applications/", "/applications.html", "/responses", "/responses/"):
            try:
                with open(os.path.join(BASE_DIR, "applications.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "applications.html not found", "text/plain; charset=utf-8")
        elif self.path in ("/backlog", "/backlog/", "/backlog.html", "/roadmap", "/roadmap/"):
            try:
                with open(os.path.join(BASE_DIR, "backlog.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "backlog.html not found", "text/plain; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")


if __name__ == "__main__":
    # фоновый прогрев кэша: первый запрос отвечает мгновенно
    def _warm():
        while True:
            try:
                read_sheet(); read_companies(); read_outreach(); read_backlog()
            except Exception as e:
                print("warm:", str(e)[:120])
            time.sleep(40)

    threading.Thread(target=_warm, daemon=True).start()
    print(f"Дашборд: http://0.0.0.0:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
