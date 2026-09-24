#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, re, json, html as H, time

ids = [136872873,136878924,136903450,136375063,136029603,136908760,136883857,134944482,
       136932863,137045112,137073395,135525434,136583324,136624183,137101098,137106674,
       137152994,136780906,136978941,137221551,137221568,137128882,137096776,137005113,
       136656298,137119100,137142209,137220011,136610136,134843834,136402326,136998190]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
out = []

for vid in ids:
    url = f"https://hh.ru/vacancy/{vid}"
    try:
        r = subprocess.run(["curl","-s","-L",url,"-H",f"User-Agent: {UA}","--max-time","25"],
                           capture_output=True, text=True)
        html = r.stdout
        title = org = desc = loc = ""
        m = re.search(r'"@type":\s*"JobPosting".*?\}', html, re.DOTALL)
        if m:
            blk = m.group(0)
            for key, pat in [("title", r'"title":\s*"(.*?)"'),
                             ("loc", r'"addressLocality":\s*"(.*?)"')]:
                mm = re.search(pat, blk)
                if mm: 
                    if key=="title": title = H.unescape(mm.group(1))
                    else: loc = mm.group(1)
            mm = re.search(r'"name":\s*"(.*?)"', blk)
            if mm: org = H.unescape(mm.group(1))
            mm = re.search(r'"description":\s*"(.*?)"\s*,\s*"datePosted"', blk, re.DOTALL)
            if mm: desc = mm.group(1)
        # fallback: og:title
        if not title:
            mm = re.search(r'<meta property="og:title" content="(.*?)"', html)
            if mm: title = H.unescape(mm.group(1))
        # Компания из og:description / employer
        if not org:
            mm = re.search(r'"employer".*?"name":\s*"(.*?)"', html, re.DOTALL)
            if mm: org = H.unescape(mm.group(1))
        # Собираем текст описания (снимаем теги)
        desc_txt = re.sub(r'<[^>]+>', ' ', H.unescape(desc))
        desc_txt = re.sub(r'\s+', ' ', desc_txt)[:1200]
        out.append({"id": vid, "url": url, "title": title, "company": org,
                    "loc": loc, "desc": desc_txt})
        print(f"{vid} | {title[:55]:55} | {org[:35]:35} | {loc[:20]}")
    except Exception as e:
        print(f"{vid} | ОШИБКА: {e}")
        out.append({"id": vid, "url": url, "title": "", "company": "", "loc": "", "desc": ""})
    time.sleep(0.7)

json.dump(out, open("/root/.hermes/jobs_batch.json","w"), ensure_ascii=False, indent=2)
print(f"\nВсего: {len(out)}")
