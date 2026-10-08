"""Lê o iCal do calendário COMPETITIVO FLUXO W7M e grava agenda.json para o telão.

Usa a variável de ambiente GCAL_ICS_URL (endereço secreto iCal do Google Calendar).
Só entram eventos com horário (eventos de dia inteiro ficam de fora), de 1 dia atrás até 60 dias à frente.
Se a descrição ou o local do evento tiver um link http(s), ele vira o link da live.
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

import icalendar
import recurring_ical_events

URL = os.environ.get("GCAL_ICS_URL", "").strip()
if not URL:
    print("GCAL_ICS_URL não configurado; nada a fazer.")
    sys.exit(0)

BRT = timezone(timedelta(hours=-3))
now = datetime.now(BRT)
raw = urllib.request.urlopen(URL, timeout=60).read()
cal = icalendar.Calendar.from_ical(raw)

url_re = re.compile(r"https?://[^\s<>\"']+")
out = []
for ev in recurring_ical_events.of(cal).between(now - timedelta(days=1), now + timedelta(days=60)):
    start = ev.get("DTSTART").dt
    if not isinstance(start, datetime):
        continue  # dia inteiro
    if str(ev.get("STATUS", "")).upper() == "CANCELLED":
        continue
    end = ev.get("DTEND").dt if ev.get("DTEND") else start + timedelta(hours=3)
    if start.tzinfo is None:
        start = start.replace(tzinfo=BRT)
    if end.tzinfo is None:
        end = end.replace(tzinfo=BRT)
    text = f"{ev.get('DESCRIPTION', '')} {ev.get('LOCATION', '')}"
    m = url_re.search(text)
    out.append({
        "id": f"{ev.get('UID')}-{start.isoformat()}",
        "title": str(ev.get("SUMMARY", "")).strip(),
        "start": start.astimezone(BRT).isoformat(),
        "end": end.astimezone(BRT).isoformat(),
        "live": m.group(0).rstrip(".,)") if m else "",
    })

out.sort(key=lambda e: e["start"])
data = {"source": "COMPETITIVO FLUXO W7M", "updated": now.isoformat(timespec="seconds"), "events": out[:40]}

path = "agenda.json"
old = None
if os.path.exists(path):
    with open(path, encoding="utf-8") as f:
        try:
            old = json.load(f)
        except Exception:
            old = None
if old and old.get("events") == data["events"]:
    print("Agenda sem mudanças.")
    sys.exit(0)
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"agenda.json atualizado com {len(out[:40])} jogos.")
