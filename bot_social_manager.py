import os
import sys
import json
import time
import random
import base64
import hashlib
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
IG_USER_ID = os.environ.get("IG_USER_ID")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")
GITHUB_RAW_BASE = os.environ.get("GITHUB_RAW_BASE")

STATE_FILE = "pending_social_post.json"
IMAGE_FILE = "social_post_ready.jpg"

# Rotazione settimanale automatica (0=Lun .. 6=Dom)
CALENDARIO_RUBRICHE = [
    "VERDETTO_CAMPO",    # Lunedì
    "DATA_MATCHUP",      # Martedì
    "MITO_REALTA",       # Mercoledì
    "NUMERO_GIORNO",     # Giovedì
    "DIARIO_OMEGA",      # Venerdì
    "DATA_MATCHUP",      # Sabato
    "PARTITA_TRAPPOLA"   # Domenica
]

CSS_BASE = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    width: 1080px; height: 1350px;
    background-color: #FFFFFF; color: #102542;
    font-family: 'Inter', sans-serif;
    display: flex; flex-direction: column; justify-content: space-between;
}
.mono { font-family: 'JetBrains Mono', monospace; }
.footer {
    display: flex; justify-content: space-between; align-items: center;
    padding: 28px 65px; border-top: 3px solid #CDD7D6; background-color: #FFFFFF;
}
.cta { font-size: 24px; font-weight: 800; color: #576574; }
.brand { font-size: 34px; font-weight: 900; color: #102542; letter-spacing: -1px; }
.brand span { color: #F87060; }
"""

HEAD_HTML = """<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&family=JetBrains+Mono:wght@600;700;800&display=swap" rel="stylesheet">
<style>""" + CSS_BASE


def cerca_logo_espn(nome_squadra):
    headers = {"User-Agent": "Mozilla/5.0"}
    for lega in ("ita.1", "eng.1", "esp.1", "ger.1", "fra.1", "uefa.champions"):
        try:
            r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/teams", headers=headers, timeout=5)
            if r.status_code == 200:
                teams = r.json().get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
                for item in teams:
                    tm = item.get("team", {})
                    if nome_squadra.lower() in str(tm.get("displayName", "")).lower() or nome_squadra.lower() in str(tm.get("shortDisplayName", "")).lower():
                        logos = tm.get("logos", [])
                        if logos:
                            return logos[0].get("href")
        except Exception:
            continue
    return None


def decripta_payload_se_presente(schedina):
    partite = schedina.get("partite", [])
    if partite and "🔒" not in str(partite[0].get("squadra_casa", "")) and "Operazione" not in str(partite[0].get("squadra_casa", "")):
        return partite
    payload_b64 = schedina.get("payload_criptato")
    if not payload_b64:
        return []
    for tok in [TELEGRAM_TOKEN, "chiave_default_sicurezza", ""]:
        try:
            xored = base64.b64decode(payload_b64.encode("ascii"))
            key_hash = hashlib.sha256(tok.encode("utf-8")).digest()
            raw_bytes = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(xored)])
            dec = json.loads(raw_bytes.decode("utf-8"))
            if isinstance(dec, list) and dec:
                return dec
        except Exception:
            continue
    return []


def scegli_match_calcio(schedine, match_usati):
    pool = []
    for s in reversed(schedine):
        mod = s.get("modello", "").lower()
        if mod in ("alpha", "beta"):
            for p in decripta_payload_se_presente(s):
                casa = str(p.get("squadra_casa", "")).strip()
                trasf = str(p.get("squadra_trasferta", "")).strip()
                pron = str(p.get("pronostico", "Analisi Tattica")).strip()
                if casa and trasf and "🔒" not in casa and "Singola" not in casa:
                    chiave = f"{casa} - {trasf}"
                    if not any(x[4] == chiave for x in pool):
                        pool.append((mod, casa, trasf, pron, chiave))
        if len(pool) >= 12:
            break
    freschi = [m for m in pool if m[4] not in match_usati]
    if freschi:
        return freschi[0]
    if pool:
        return random.choice(pool)
    return ("beta", "Inter", "Milan", "Over 8.5 Calci d'Angolo", "Inter - Milan")


def chiama_groq_json(prompt_sistema, prompt_utente, fallback_dict):
    if GROQ_API_KEY:
        for modello in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"},
                    json={
                        "model": modello,
                        "messages": [
                            {"role": "system", "content": prompt_sistema},
                            {"role": "user", "content": prompt_utente}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.85
                    },
                    timeout=20
                )
                if r.status_code == 200:
                    parsed = json.loads(r.json()["choices"][0]["message"]["content"])
                    print(f"[GROQ OK] Generato con {modello}")
                    return parsed
            except Exception as e:
                print(f"[GROQ WARN] {modello}: {e}")
    return fallback_dict


# --- 6 GENERATORI HTML MINIMALI IN TINTA PIATTA ---

def html_data_matchup(casa, trasf, logo_c, logo_t, modello, mercato, dati, oggi_str):
    colore = "#F87060" if modello == "alpha" else "#B3A394"
    lc = f"<img src='{logo_c}' style='width:120px;height:120px;object-fit:contain;'>" if logo_c else f"<div class='mono' style='font-size:42px;font-weight:900;color:#102542;'>{casa[:3].upper()}</div>"
    lt = f"<img src='{logo_t}' style='width:120px;height:120px;object-fit:contain;'>" if logo_t else f"<div class='mono' style='font-size:42px;font-weight:900;color:#102542;'>{trasf[:3].upper()}</div>"
    barre = dati.get("barre", [
        {"label": "Pressione Offensiva", "v1": 74, "v2": 52},
        {"label": "Volume Fasce / Cross", "v1": 81, "v2": 48},
        {"label": "Indice Poisson SBR", "v1": 78, "v2": 41}
    ])
    barre_html = ""
    for b in barre[:3]:
        v1 = max(15, min(95, int(b.get("v1", 65))))
        v2 = max(15, min(95, int(b.get("v2", 45))))
        barre_html += f"""
        <div style="margin-bottom:26px;">
            <div style="display:flex;justify-content:space-between;font-size:22px;font-weight:800;text-transform:uppercase;margin-bottom:10px;color:#102542;">
                <span class="mono">{v1}%</span><span>{b.get('label','Metrica')}</span><span class="mono">{v2}%</span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;height:22px;">
                <div style="background:#CDD7D6;border-radius:6px;overflow:hidden;display:flex;justify-content:flex-end;">
                    <div style="width:{v1}%;background:#102542;height:100%;"></div>
                </div>
                <div style="background:#CDD7D6;border-radius:6px;overflow:hidden;">
                    <div style="width:{v2}%;background:{colore};height:100%;"></div>
                </div>
            </div>
        </div>"""
    return HEAD_HTML + f"""
    .top-bar {{ background:#102542; color:#FFFFFF; padding:34px 65px; display:flex; justify-content:space-between; align-items:center; border-bottom:10px solid {colore}; }}
    .wrap {{ flex:1; padding:50px 65px; display:flex; flex-direction:column; justify-content:space-between; }}
    </style></head><body>
    <div class="top-bar">
        <span class="mono" style="background:{colore};color:#FFFFFF;padding:10px 22px;border-radius:6px;font-size:22px;font-weight:800;">DATA MATCHUP • {modello.upper()}</span>
        <span class="mono" style="font-size:24px;color:#B3A394;font-weight:700;">{oggi_str}</span>
    </div>
    <div class="wrap">
        <div style="display:flex;align-items:center;justify-content:space-between;background:#F4F6F6;border:4px solid #102542;border-radius:16px;padding:36px 50px;">
            <div style="display:flex;flex-direction:column;align-items:center;gap:14px;width:38%;">{lc}<div style="font-size:34px;font-weight:900;text-transform:uppercase;text-align:center;">{casa}</div></div>
            <div class="mono" style="background:{colore};color:#FFFFFF;font-size:28px;font-weight:900;padding:14px 24px;border-radius:10px;">VS</div>
            <div style="display:flex;flex-direction:column;align-items:center;gap:14px;width:38%;">{lt}<div style="font-size:34px;font-weight:900;text-transform:uppercase;text-align:center;">{trasf}</div></div>
        </div>
        <div style="margin:24px 0;">
            <div style="font-size:62px;font-weight:900;line-height:1.02;letter-spacing:-2px;text-transform:uppercase;margin-bottom:14px;">{dati.get('titolo','SQUILIBRIO NETTO.')}</div>
            <div style="font-size:30px;font-weight:600;color:#576574;line-height:1.35;">{dati.get('sottotitolo','')}</div>
        </div>
        <div>{barre_html}</div>
        <div style="background:#102542;color:#FFFFFF;padding:24px 34px;border-radius:12px;border-left:16px solid {colore};display:flex;justify-content:space-between;align-items:center;">
            <span class="mono" style="font-size:22px;color:#B3A394;font-weight:800;">SEGNALE ALGORITMO</span>
            <span style="font-size:34px;font-weight:900;text-transform:uppercase;">{mercato}</span>
        </div>
    </div>
    <div class="footer"><span class="cta">Analisi gratis su Telegram • Link in Bio</span><span class="brand">SBR <span>LAB</span></span></div>
    </body></html>"""


def html_numero_giorno(dati, oggi_str):
    return HEAD_HTML + f"""
    body {{ background-color:#102542; color:#FFFFFF; }}
    .footer {{ background-color:#102542; border-top:2px solid #2A3F5F; }}
    .cta {{ color:#CDD7D6; }} .brand {{ color:#FFFFFF; }}
    </style></head><body>
    <div style="padding:55px 65px 0 65px;display:flex;justify-content:space-between;align-items:center;">
        <span class="mono" style="background:#F87060;color:#FFFFFF;padding:12px 24px;border-radius:6px;font-size:22px;font-weight:800;">IL NUMERO DEL GIORNO</span>
        <span class="mono" style="color:#B3A394;font-size:24px;font-weight:700;">{oggi_str}</span>
    </div>
    <div style="flex:1;padding:40px 65px;display:flex;flex-direction:column;justify-content:center;">
        <div class="mono" style="font-size:230px;font-weight:800;line-height:0.95;color:#F87060;letter-spacing:-10px;margin-bottom:36px;">{dati.get('numero','82%')}</div>
        <div style="font-size:66px;font-weight:900;line-height:1.05;letter-spacing:-2px;text-transform:uppercase;margin-bottom:28px;">{dati.get('titolo','LA MATEMATICA NON FA IL TIFO.')}</div>
        <div style="font-size:34px;line-height:1.42;color:#CDD7D6;font-weight:500;border-left:10px solid #B3A394;padding-left:28px;">{dati.get('spiegazione','')}</div>
    </div>
    <div class="footer"><span class="cta">Salva il post • Dati gratis su Telegram (Link in Bio)</span><span class="brand">SBR <span>LAB</span></span></div>
    </body></html>"""


def html_mito_realta(dati, oggi_str):
    return HEAD_HTML + f"""
    </style></head><body>
    <div style="background:#102542;color:#FFFFFF;padding:34px 65px;display:flex;justify-content:space-between;align-items:center;border-bottom:10px solid #B3A394;">
        <span class="mono" style="background:#F87060;color:#FFFFFF;padding:10px 22px;border-radius:6px;font-size:22px;font-weight:800;">MITO VS REALTÀ</span>
        <span class="mono" style="color:#B3A394;font-size:24px;">EDUCAZIONE QUANT</span>
    </div>
    <div style="flex:1;padding:55px 65px;display:flex;flex-direction:column;justify-content:space-between;">
        <div style="font-size:64px;font-weight:900;line-height:1.03;letter-spacing:-2px;text-transform:uppercase;">{dati.get('titolo','SMONTIAMO UN LUOGO COMUNE.')}</div>
        <div style="display:flex;flex-direction:column;gap:28px;margin:auto 0;">
            <div style="background:#F4F6F6;border:4px solid #CDD7D6;border-left:18px solid #F87060;border-radius:14px;padding:36px 40px;">
                <div class="mono" style="font-size:22px;font-weight:800;color:#F87060;margin-bottom:12px;">✕ COSA SI DICE AL BAR (MITO)</div>
                <div style="font-size:36px;font-weight:800;color:#102542;line-height:1.3;">"{dati.get('mito','')}"</div>
            </div>
            <div style="background:#102542;color:#FFFFFF;border-left:18px solid #10B981;border-radius:14px;padding:38px 40px;">
                <div class="mono" style="font-size:22px;font-weight:800;color:#10B981;margin-bottom:12px;">✓ COSA DICONO I DATI (REALTÀ SBR)</div>
                <div style="font-size:34px;font-weight:600;color:#FFFFFF;line-height:1.38;">{dati.get('realta','')}</div>
            </div>
        </div>
    </div>
    <div class="footer"><span class="cta">Condividilo con chi gioca di pancia • Link in Bio</span><span class="brand">SBR <span>LAB</span></span></div>
    </body></html>"""


def html_verdetto_campo(winrate, chiuse, righe_html, titolo, oggi_str):
    return HEAD_HTML + f"""
    .row {{ background:#FFFFFF; border:3px solid #102542; border-radius:12px; padding:24px 30px; display:flex; justify-content:space-between; align-items:center; font-size:30px; font-weight:800; }}
    .mod-pill {{ font-family:'JetBrains Mono',monospace; font-size:20px; background:#102542; color:#FFFFFF; padding:8px 16px; border-radius:6px; margin-right:16px; }}
    .win {{ background:#ECFDF5; color:#10B981; border:3px solid #10B981; padding:8px 20px; border-radius:8px; font-size:22px; font-weight:900; }}
    .loss {{ background:#FEF2F2; color:#EF4444; border:3px solid #EF4444; padding:8px 20px; border-radius:8px; font-size:22px; font-weight:900; }}
    </style></head><body>
    <div style="background:#102542;color:#FFFFFF;padding:34px 65px;display:flex;justify-content:space-between;align-items:center;border-bottom:10px solid #F87060;">
        <span class="mono" style="background:#10B981;color:#FFFFFF;padding:10px 22px;border-radius:6px;font-size:22px;font-weight:800;">✓ VERDETTO DEL CAMPO</span>
        <span class="mono" style="color:#B3A394;font-size:24px;">REPORT AL {oggi_str}</span>
    </div>
    <div style="flex:1;padding:50px 65px;display:flex;flex-direction:column;justify-content:space-between;">
        <div style="font-size:74px;font-weight:900;line-height:0.98;letter-spacing:-3px;text-transform:uppercase;">{titolo}</div>
        <div style="display:grid;grid-template-columns:1.25fr 0.75fr;border:4px solid #102542;border-radius:16px;overflow:hidden;">
            <div style="background:#102542;color:#FFFFFF;padding:38px 42px;">
                <div class="mono" style="font-size:22px;color:#B3A394;margin-bottom:8px;">WIN RATE CERTIFICATO</div>
                <div class="mono" style="font-size:112px;font-weight:800;line-height:1;color:#10B981;">{winrate}</div>
            </div>
            <div style="background:#F4F6F6;padding:38px 36px;border-left:4px solid #102542;">
                <div class="mono" style="font-size:22px;color:#576574;margin-bottom:8px;">CHIUSE</div>
                <div class="mono" style="font-size:84px;font-weight:800;line-height:1;color:#102542;">{chiuse}</div>
            </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:16px;">{righe_html}</div>
    </div>
    <div class="footer"><span class="cta">Storico pubblico integrale • Link in Bio</span><span class="brand">SBR <span>LAB</span></span></div>
    </body></html>"""


def html_partita_trappola(dati, oggi_str):
    return HEAD_HTML + f"""
    body {{ background-color:#F4F6F6; }}
    </style></head><body>
    <div style="background:#F87060;color:#FFFFFF;padding:34px 65px;display:flex;justify-content:space-between;align-items:center;">
        <span class="mono" style="background:#102542;color:#FFFFFF;padding:10px 22px;border-radius:6px;font-size:22px;font-weight:800;">🛡️ FILTRO ANTI-TRAPPOLA</span>
        <span class="mono" style="font-size:24px;font-weight:800;">{oggi_str}</span>
    </div>
    <div style="flex:1;padding:55px 65px;display:flex;flex-direction:column;justify-content:space-between;">
        <div style="background:#FFFFFF;border:5px solid #102542;border-radius:18px;padding:50px;flex:1;display:flex;flex-direction:column;justify-content:space-between;">
            <div style="display:inline-block;align-self:flex-start;border:5px solid #F87060;color:#F87060;padding:12px 26px;border-radius:8px;font-size:26px;font-weight:900;letter-spacing:2px;" class="mono">OPERAZIONE BLOCCATA</div>
            <div>
                <div style="font-size:66px;font-weight:900;line-height:1.02;letter-spacing:-2px;text-transform:uppercase;margin-bottom:24px;">{dati.get('titolo','NON SI FORZA MAI.')}</div>
                <div style="font-size:34px;line-height:1.42;color:#576574;font-weight:600;">{dati.get('spiegazione','')}</div>
            </div>
            <div style="background:#102542;color:#FFFFFF;padding:26px 32px;border-radius:12px;display:flex;justify-content:space-between;align-items:center;">
                <span class="mono" style="color:#B3A394;font-size:22px;font-weight:800;">REGOLA SBR LAB</span>
                <span style="font-size:28px;font-weight:900;">EDGE &lt; 0% = STOP</span>
            </div>
        </div>
    </div>
    <div class="footer"><span class="cta">Disciplina prima del profitto • Link in Bio</span><span class="brand">SBR <span>LAB</span></span></div>
    </body></html>"""


def html_diario_omega(dati, oggi_str):
    return HEAD_HTML + f"""
    body {{ background:#F4F6F6; padding:50px; }}
    </style></head><body>
    <div style="flex:1;background:#FFFFFF;border:5px solid #102542;border-radius:18px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden;">
        <div style="border-bottom:4px solid #102542;padding:32px 48px;display:flex;justify-content:space-between;align-items:center;">
            <span class="mono" style="background:#B3A394;color:#102542;padding:10px 20px;border-radius:6px;font-size:22px;font-weight:800;">SYS // DIARIO OMEGA</span>
            <span class="mono" style="background:#F87060;color:#FFFFFF;padding:10px 20px;border-radius:6px;font-size:20px;font-weight:800;">🔒 FASE PRIVATA</span>
        </div>
        <div style="padding:50px;flex:1;display:flex;flex-direction:column;justify-content:space-between;">
            <div>
                <div class="mono" style="color:#F87060;font-size:22px;font-weight:800;margin-bottom:14px;">LABORATORIO QUANTITATIVO • {oggi_str}</div>
                <div style="font-size:70px;font-weight:900;line-height:1.02;letter-spacing:-2.5px;text-transform:uppercase;margin-bottom:26px;">{dati.get('titolo','10.000 PARTITE IN UNA.')}</div>
                <div style="font-size:33px;line-height:1.42;color:#576574;font-weight:600;">{dati.get('spiegazione','')}</div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;">
                <div style="background:#102542;color:#FFFFFF;padding:24px;border-radius:12px;border-bottom:10px solid #F87060;"><div class="mono" style="color:#B3A394;font-size:20px;margin-bottom:8px;">01 // RUN</div><div style="font-size:26px;font-weight:900;">10.000 MONTE CARLO</div></div>
                <div style="background:#102542;color:#FFFFFF;padding:24px;border-radius:12px;border-bottom:10px solid #F87060;"><div class="mono" style="color:#B3A394;font-size:20px;margin-bottom:8px;">02 // QUOTA</div><div style="font-size:26px;font-weight:900;">DE-VIGGING PURO</div></div>
                <div style="background:#102542;color:#FFFFFF;padding:24px;border-radius:12px;border-bottom:10px solid #F87060;"><div class="mono" style="color:#B3A394;font-size:20px;margin-bottom:8px;">03 // RISCHIO</div><div style="font-size:26px;font-weight:900;">KELLY FRAZIONATO</div></div>
            </div>
        </div>
        <div style="background:#102542;color:#FFFFFF;padding:26px 48px;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:22px;color:#CDD7D6;font-weight:700;">Alpha & Beta già gratis su Telegram (Link in Bio)</span>
            <span class="brand" style="color:#FFFFFF;">SBR <span>LAB</span></span>
        </div>
    </div>
    </body></html>"""


def renderizza_html_in_jpg(html_str, output_jpg):
    temp_html = "temp_render.html"
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_str)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        page.goto(f"file://{os.path.abspath(temp_html)}", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(1000)
        # Formato JPEG obbligatorio per le API di Instagram!
        page.screenshot(path=output_jpg, type="jpeg", quality=92, full_page=False)
        browser.close()
    if os.path.exists(temp_html):
        os.remove(temp_html)


def carica_stato():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ultimi_titoli": [], "ultimi_match": [], "indice_rotazione": 0}


def invia_anteprima_telegram(image_path, caption_ig, rubrica):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    tastiera = {
        "inline_keyboard": [[
            {"text": "✅ Approva e Pubblica su IG", "callback_data": "APPROVA_IG"},
            {"text": "❌ Scarta Bozza", "callback_data": "SCARTA_IG"}
        ]]
    }
    testo = f"🎨 *ANTEPRIMA ({rubrica})*\n\n📝 *Caption:*\n\n{caption_ig}"
    with open(image_path, "rb") as img:
        r = requests.post(
            url,
            data={"chat_id": ADMIN_CHAT_ID, "caption": testo[:1020], "reply_markup": json.dumps(tastiera)},
            files={"photo": img},
            timeout=30
        )
    r.raise_for_status()


def fase_1_genera_proposta(forza_rubrica=None):
    db = {"schedine": []}
    if os.path.exists("database.json"):
        with open("database.json", "r", encoding="utf-8") as f:
            db = json.load(f)

    stato = carica_stato()
    usati_titoli = stato.get("ultimi_titoli", [])[-10:]
    usati_match = stato.get("ultimi_match", [])[-8:]
    idx_rot = int(stato.get("indice_rotazione", 0))

    fuso_italia = ZoneInfo("Europe/Rome")
    adesso = datetime.now(fuso_italia)
    oggi_str = adesso.strftime("%d/%m/%Y")

    rubriche_valide = ["DATA_MATCHUP", "NUMERO_GIORNO", "MITO_REALTA", "VERDETTO_CAMPO", "PARTITA_TRAPPOLA", "DIARIO_OMEGA"]
    if forza_rubrica in rubriche_valide:
        rubrica = forza_rubrica
    else:
        rubrica = rubriche_valide[idx_rot % len(rubriche_valide)]

    schedine = db.get("schedine", [])
    regole_tono = (
        "Sei il fondatore 25enne di SBR Lab (@sbr.lab), studio italiano di data science sul calcio. "
        "Scrivi in modo diretto, sveglio, naturale e competente (mai da robot, mai da scommettitore da bar). "
        "VIETATO usare parole a rischio ban: scommessa, puntata, bookmaker, cassa sicura, vincita facile. "
        "Chiudi sempre la caption invitando con naturalezza sul canale Telegram gratuito nel link in bio + 5 hashtag."
    )

    if rubrica == "DATA_MATCHUP":
        mod, casa, trasf, mercato, chiave_m = scegli_match_calcio(schedine, usati_match)
        logo_c, logo_t = cerca_logo_espn(casa), cerca_logo_espn(trasf)
        prompt = (
            regole_tono + " Rispondi SOLO in JSON con: "
            "'titolo' (max 3 parole MAIUSCOLO col punto), 'sottotitolo' (max 16 parole), "
            "'barre' (lista di 3 oggetti {'label': str, 'v1': int 30-90, 'v2': int 30-90}), "
            "'caption' (max 85 parole)."
        )
        fb = {
            "titolo": "RITMO A SENSO UNICO.",
            "sottotitolo": f"I numeri degli ultimi 30 giorni accendono {casa} - {trasf} su {mercato}.",
            "barre": [{"label": "Pressione Offensiva", "v1": 76, "v2": 51}, {"label": "Volume Fasce", "v1": 82, "v2": 49}, {"label": "Indice SBR", "v1": 79, "v2": 44}],
            "caption": f"⚽ Su {casa} - {trasf} i dati parlano prima del campo: il Modello {mod.upper()} isola un'anomalia netta su {mercato}.\n\n📲 Analisi completa gratis su Telegram (Link in Bio).\n\n#SBRLab #SerieA #Calcio #AnalisiTattica #FootballData"
        }
        dati = chiama_groq_json(prompt, f"Match: {casa} vs {trasf}, Modello: {mod}, Focus: {mercato}, Evita titoli: {usati_titoli}", fb)
        html = html_data_matchup(casa, trasf, logo_c, logo_t, mod, mercato, dati, oggi_str)
        usati_match.append(chiave_m)

    elif rubrica == "NUMERO_GIORNO":
        prompt = (
            regole_tono + " Scegli un dato statistico reale e sorprendente sul calcio europeo o sui modelli predittivi. "
            "Rispondi SOLO in JSON con: 'numero' (max 5 caratteri es. '10.000' o '78%'), 'titolo' (max 4 parole MAIUSCOLO), "
            "'spiegazione' (max 22 parole), 'caption' (max 85 parole)."
        )
        fb = {
            "numero": "78%",
            "titolo": "LA TRAPPOLA DELLE FAVORITE.",
            "spiegazione": "Oltre tre tifosi su quattro sovrastimano il peso del nome della squadra ignorando stanchezza e calendario.",
            "caption": "📊 Il nome sulla maglia non fa gol da solo. I nostri modelli pesano forma, calendario e ritmo reale.\n\n📲 Tutte le analisi gratuite sul canale Telegram (Link in Bio).\n\n#SBRLab #Calcio #StatisticheCalcio #DataScience #SerieA"
        }
        dati = chiama_groq_json(prompt, f"Evita titoli: {usati_titoli}", fb)
        html = html_numero_giorno(dati, oggi_str)

    elif rubrica == "MITO_REALTA":
        prompt = (
            regole_tono + " Smonta un luogo comune calcistico o statistico (es. 'quota bassa = sicura', 'in casa non si perde'). "
            "Rispondi SOLO in JSON con: 'titolo' (max 4 parole MAIUSCOLO), 'mito' (max 14 parole), "
            "'realta' (max 24 parole), 'caption' (max 85 parole)."
        )
        fb = {
            "titolo": "IL MITO DEL FATTORE CAMPO.",
            "mito": "Se una big gioca in casa contro una piccola, è una passeggiata scontata.",
            "realta": "Senza controllare il ritmo difensivo e gli impegni europei infrasettimanali, le sorprese saltano fuori molto più spesso di quanto pensi.",
            "caption": "🆚 Al bar sembra tutto facile, ma i numeri raccontano un'altra storia. Ecco perché in SBR Lab filtriamo ogni gara con i dati.\n\n📲 Entra gratis su Telegram dal Link in Bio.\n\n#SBRLab #Calcio #AnalisiTattica #NumeriDelCalcio #SerieA"
        }
        dati = chiama_groq_json(prompt, f"Evita titoli: {usati_titoli}", fb)
        html = html_mito_realta(dati, oggi_str)

    elif rubrica == "VERDETTO_CAMPO":
        concluse = [s for s in schedine if s.get("stato_schedina") in ("vinta", "persa") and s.get("modello") in ("alpha", "beta", "sigma")]
        vinte = [s for s in concluse if s.get("stato_schedina") == "vinta"]
        winrate = f"{round((len(vinte)/len(concluse))*100)}%" if concluse else "--%"
        righe_html = ""
        for s in concluse[-3:]:
            partite = decripta_payload_se_presente(s) or s.get("partite", [])
            if not partite:
                continue
            p0 = partite[0]
            badge = "<span class='win'>✓ PRESA</span>" if s["stato_schedina"] == "vinta" else "<span class='loss'>✕ STOP</span>"
            righe_html += f"<div class='row'><div><span class='mod-pill'>{s.get('modello','SBR').upper()}</span>{p0['squadra_casa']} - {p0['squadra_trasferta']}</div>{badge}</div>"
        prompt = regole_tono + " Rispondi SOLO in JSON con: 'titolo' (max 3 parole MAIUSCOLO), 'caption' (max 85 parole)."
        fb = {
            "titolo": "IL CAMPO PARLA.",
            "caption": f"📊 Zero promesse: ogni operazione resta tracciata a database ({len(concluse)} chiuse, {winrate} di precisione).\n\n📲 Segui i modelli gratis su Telegram (Link in Bio).\n\n#SBRLab #Trasparenza #Calcio #StatisticheCalcio #SerieA"
        }
        dati = chiama_groq_json(prompt, f"Winrate: {winrate}, Chiuse: {len(concluse)}, Evita titoli: {usati_titoli}", fb)
        html = html_verdetto_campo(winrate, len(concluse), righe_html or "<div class='row'><span>Storico in aggiornamento</span></div>", dati["titolo"], oggi_str)

    elif rubrica == "PARTITA_TRAPPOLA":
        prompt = (
            regole_tono + " Spiega perché un algoritmo serio a volte decide di NON operare su un big match (quote compresse, assenze, edge negativo). "
            "Rispondi SOLO in JSON con: 'titolo' (max 4 parole MAIUSCOLO), 'spiegazione' (max 24 parole), 'caption' (max 85 parole)."
        )
        fb = {
            "titolo": "LA FORZA DI STARE FERMI.",
            "spiegazione": "Quando il mercato prezza male il rischio e il vantaggio matematico scende sotto zero, i nostri filtri bloccano tutto.",
            "caption": "🛡️ Saper stare fermi vale quanto una lettura perfetta. In SBR Lab si entra solo quando i numeri danno un vantaggio reale.\n\n📲 Scopri il metodo gratis su Telegram (Link in Bio).\n\n#SBRLab #Disciplina #Calcio #AnalisiTattica #DataScience"
        }
        dati = chiama_groq_json(prompt, f"Evita titoli: {usati_titoli}", fb)
        html = html_partita_trappola(dati, oggi_str)

    else:  # DIARIO_OMEGA
        prompt = (
            regole_tono + " Racconta un retroscena affascinante del Modello Omega (10.000 simulazioni Monte Carlo, calibrazione privata). "
            "Rispondi SOLO in JSON con: 'titolo' (max 4 parole MAIUSCOLO), 'spiegazione' (max 24 parole), 'caption' (max 85 parole)."
        )
        fb = {
            "titolo": "10.000 PARTITE IN UNA.",
            "spiegazione": "Prima del fischio d'inizio Omega simula il match diecimila volte pesando attacco, difesa e fatica per isolare la probabilità pura.",
            "caption": "🧪 Dietro le quinte stiamo calibrando OMEGA su 10.000 simulazioni Monte Carlo. Intanto Alpha e Beta sono già liberi ogni mattina.\n\n📲 Entra gratis su Telegram dal Link in Bio.\n\n#SBRLab #ModelloOmega #MonteCarlo #Calcio #DataScience"
        }
        dati = chiama_groq_json(prompt, f"Evita titoli: {usati_titoli}", fb)
        html = html_diario_omega(dati, oggi_str)

    renderizza_html_in_jpg(html, IMAGE_FILE)
    usati_titoli.append(dati.get("titolo", rubrica))

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "status": "WAITING_APPROVAL",
            "rubrica": rubrica,
            "caption": dati["caption"],
            "created_at": oggi_str,
            "ultimi_titoli": usati_titoli[-10:],
            "ultimi_match": usati_match[-8:],
            "indice_rotazione": idx_rot + 1
        }, f, ensure_ascii=False, indent=2)

    invia_anteprima_telegram(IMAGE_FILE, dati["caption"], rubrica)
    print(f"Post {rubrica} (.jpg) generato e inviato su Telegram!")


def pubblica_su_instagram(image_public_url, caption):
    if not IG_USER_ID or not IG_ACCESS_TOKEN:
        raise ValueError("IG_USER_ID o IG_ACCESS_TOKEN mancanti nei Secrets di GitHub.")

    r1 = requests.post(f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media", data={
        "image_url": image_public_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    }, timeout=30)
    if r1.status_code != 200:
        raise RuntimeError(f"Errore Meta Container ({r1.status_code}): {r1.text}")
    creation_id = r1.json()["id"]

    time.sleep(8)

    r2 = requests.post(f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish", data={
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    }, timeout=30)
    if r2.status_code != 200:
        raise RuntimeError(f"Errore Meta Publish ({r2.status_code}): {r2.text}")
    return r2.json()


def fase_2_controlla_ok_e_pubblica():
    if not os.path.exists(STATE_FILE):
        print("STOP: File pending_social_post.json non trovato.")
        return
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        stato = json.load(f)
    print(f"Stato attuale in JSON: {stato.get('status')}")
    if stato.get("status") != "WAITING_APPROVAL":
        print("STOP: Nessuna bozza in attesa di approvazione.")
        return

    res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", timeout=15).json()
    updates = res.get("result", [])
    print(f"Aggiornamenti letti da Telegram: {len(updates)} | ADMIN_CHAT_ID atteso: {ADMIN_CHAT_ID}")

    azione_scelta = None
    ultimo_update_id = None
    callback_id = None

    for u in updates:
        ultimo_update_id = u.get("update_id")
        cb = u.get("callback_query", {})
        if cb:
            from_id = str(cb.get("from", {}).get("id"))
            data_cb = cb.get("data")
            print(f"Trovato clic bottone: data={data_cb} da user_id={from_id}")
            if from_id == str(ADMIN_CHAT_ID) and data_cb in ("APPROVA_IG", "SCARTA_IG"):
                azione_scelta = data_cb
                callback_id = cb.get("id")

    if not azione_scelta:
        print("STOP: Nessun clic APPROVA_IG/SCARTA_IG valido trovato per questo ADMIN_CHAT_ID.")
        return

    if callback_id:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                      json={"callback_query_id": callback_id, "text": "Comando ricevuto!"}, timeout=10)

    if azione_scelta == "APPROVA_IG":
        image_url = f"{GITHUB_RAW_BASE}/{IMAGE_FILE}?v={int(time.time())}"
        print(f"Pubblicazione su IG in corso con URL: {image_url}")
        try:
            pubblica_su_instagram(image_url, stato["caption"])
            stato["status"] = "PUBLISHED"
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(stato, f, ensure_ascii=False, indent=2)
            if ultimo_update_id:
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_update_id + 1}", timeout=10)
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                          json={"chat_id": ADMIN_CHAT_ID, "text": "🚀 Post pubblicato in automatico su Instagram!"})
            print("SUCCESSO: Pubblicato su Instagram!")
        except Exception as e:
            print(f"ERRORE META: {e}")
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                          json={"chat_id": ADMIN_CHAT_ID, "text": f"⚠️ Errore pubblicazione Instagram:\n{e}"})
            raise

    elif azione_scelta == "SCARTA_IG":
        stato["status"] = "DISCARDED"
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(stato, f, ensure_ascii=False, indent=2)
        if ultimo_update_id:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_update_id + 1}", timeout=10)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": ADMIN_CHAT_ID, "text": "🗑️ Bozza scartata. Rilancia il workflow per la prossima rubrica!"})


if __name__ == "__main__":
    modalita = sys.argv[1] if len(sys.argv) > 1 else "genera"
    forza = sys.argv[2].upper() if len(sys.argv) > 2 else None
    if modalita == "genera":
        fase_1_genera_proposta(forza_rubrica=forza)
    elif modalita == "pubblica":
        fase_2_controlla_ok_e_pubblica()
