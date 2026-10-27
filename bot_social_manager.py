import os
import sys
import json
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
IG_USER_ID = os.environ.get("IG_USER_ID")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")
GITHUB_RAW_BASE = os.environ.get("GITHUB_RAW_BASE")

STATE_FILE = "pending_social_post.json"
IMAGE_FILE = "social_post_ready.png"

# PALETTE PIATTA UFFICIALE SBR PER SINGOLO BOT
STILE_BOT = {
    "alpha": {"colore": "#F87060", "etichetta": "MODELLO ALPHA • ALTO RENDIMENTO"},
    "beta":  {"colore": "#B3A394", "etichetta": "MODELLO BETA • POISSON"},
    "sigma": {"colore": "#2D6A4F", "etichetta": "MODELLO SIGMA • TENNIS LAB"},
    "omega": {"colore": "#102542", "etichetta": "MODELLO OMEGA • QUANTITATIVO"}
}


def genera_copy_caldo_con_ai(tipo_post, dati_contesto):
    prompt = f"""
    Sei l'editor sportivo di SBR Lab (@sbr.lab), studio italiano di analisi dati applicata a calcio e tennis.
    Stile: caldo, appassionato di campo e tattica, autorevole, pulito.
    REGOLE TASSATIVE:
    1. NON inserire MAI tag HTML o span colorati nel testo: restituisci solo testo puro.
    2. Evita termini da scommesse (vietati: puntata, scommessa, bookmaker, cassa facile, vincita sicura).
    
    Rubrica di oggi: {tipo_post}
    Dati reali dal database: {json.dumps(dati_contesto, ensure_ascii=False)}
    
    Rispondi SOLO con un JSON valido con queste 3 chiavi:
    - "titolo_grafica": massimo 7 parole incisive e sportive (niente HTML)
    - "testo_grafica": massimo 24 parole di racconto tattico/statistico chiaro e coinvolgente (niente HTML)
    - "caption_instagram": testo scorrevole (max 110 parole) che unisce emozione sportiva e lettura numerica, chiudendo con l'invito al canale Telegram gratuito (Alpha, Beta e Tennis) dal link in bio + 5 hashtag SEO.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])


def renderizza_html_in_png(template_path, sostituzioni, output_png):
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    for chiave, valore in sostituzioni.items():
        html = html.replace(f"{{{{{chiave}}}}}", str(valore))

    temp_html = "temp_render.html"
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        page.goto(f"file://{os.path.abspath(temp_html)}", wait_until="networkidle")
        page.screenshot(path=output_png, full_page=False)
        browser.close()

    if os.path.exists(temp_html):
        os.remove(temp_html)


def trova_ultimo_match_in_chiaro(schedine):
    """Cerca l'ultima giocata di Alpha, Beta o Tennis con nomi squadre visibili (ignora i match criptati VIP)."""
    if os.path.exists("tennis_test.json") and datetime.now().weekday() == 2:  # Mercoledì focus Tennis
        try:
            with open("tennis_test.json", "r", encoding="utf-8") as ft:
                t_db = json.load(ft)
            lista_t = t_db.get("schedine", []) if isinstance(t_db, dict) else t_db
            if lista_t:
                ult = lista_t[-1]
                p = ult.get("partite", [ult])[0]
                match_str = f"{p.get('squadra_casa', p.get('giocatore_1', 'ATP'))} - {p.get('squadra_trasferta', p.get('giocatore_2', 'Tour'))}"
                return "sigma", match_str, p.get("pronostico", "Analisi Superficie")
        except Exception:
            pass

    for s in reversed(schedine):
        mod = s.get("modello", "beta").lower()
        if mod in ("alpha", "beta") and s.get("partite"):
            p = s["partite"][0]
            casa = p.get("squadra_casa", "")
            if "🔒" not in casa and "Operazione" not in casa:
                return mod, f"{casa} - {p.get('squadra_trasferta', '')}", p.get("pronostico", "Lettura Statistica")

    return "beta", "Serie A • Analisi Tattica", "Pressione Offensiva & Corner"


def invia_anteprima_su_telegram(image_path, caption_ig):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    tastiera = {
        "inline_keyboard": [[
            {"text": "✅ Approva e Pubblica su IG", "callback_data": "APPROVA_IG"},
            {"text": "❌ Scarta Bozza", "callback_data": "SCARTA_IG"}
        ]]
    }
    testo_admin = f"🎨 *ANTEPRIMA POST INSTAGRAM*\n\n📝 *Caption:*\n{caption_ig}"
    with open(image_path, "rb") as img:
        r = requests.post(
            url,
            data={
                "chat_id": ADMIN_CHAT_ID,
                "caption": testo_admin[:1020],
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(tastiera)
            },
            files={"photo": img},
            timeout=30
        )
    r.raise_for_status()


def fase_1_genera_proposta():
    db = {"schedine": []}
    if os.path.exists("database.json"):
        with open("database.json", "r", encoding="utf-8") as f:
            db = json.load(f)

    schedine = db.get("schedine", [])
    oggi_str = datetime.now().strftime("%d/%m/%Y")
    giorno = datetime.now().weekday()  # 0=Lun, 2=Mer, 4=Ven, 5=Sab

    if giorno == 0 and schedine:
        concluse = [s for s in schedine if s.get("stato_schedina") in ("vinta", "persa") and s.get("modello") in ("alpha", "beta")]
        vinte = [s for s in concluse if s.get("stato_schedina") == "vinta"]
        winrate = f"{round((len(vinte)/len(concluse))*100)}%" if concluse else "--%"
        ultime_3 = concluse[-3:]
        righe_html = ""
        for s in ultime_3:
            if not s.get("partite"):
                continue
            p0 = s["partite"][0]
            mod_label = s.get("modello", "SBR").upper()
            is_win = s["stato_schedina"] == "vinta"
            badge = "<span class='esito-vinto'>✓ Presa</span>" if is_win else "<span class='esito-perso'>✕ Saltata</span>"
            righe_html += (
                f"<div class='row'>"
                f"<div><span class='mod-pill'>{mod_label}</span>{p0['squadra_casa']} - {p0['squadra_trasferta']}</div>"
                f"{badge}</div>"
            )
        copy_ai = genera_copy_caldo_con_ai("Verdetto del Campo (Report trasparenza risultati)", {"winrate": winrate, "chiuse": len(concluse)})
        renderizza_html_in_png("templates_social/template_risultati.html", {
            "PERIODO": f"AGGIORNATO AL {oggi_str}",
            "TOTALE_CHIUSE": len(concluse),
            "WINRATE": winrate,
            "RIGHE_OPERAZIONI": righe_html or "<div class='row'><span>Storico in aggiornamento</span></div>"
        }, IMAGE_FILE)

    elif giorno == 4:
        copy_ai = genera_copy_caldo_con_ai("Diario Laboratorio Omega (10.000 simulazioni Monte Carlo attualmente in calibrazione privata)", {})
        renderizza_html_in_png("templates_social/template_omega.html", {
            "TITOLO_OMEGA": copy_ai["titolo_grafica"],
            "TESTO_OMEGA": copy_ai["testo_grafica"]
        }, IMAGE_FILE)

    else:
        mod_key, match_nome, mercato = trova_ultimo_match_in_chiaro(schedine)
        stile = STILE_BOT.get(mod_key, STILE_BOT["beta"])
        copy_ai = genera_copy_caldo_con_ai("Analisi Pre-Match", {"modello": mod_key.upper(), "match": match_nome, "focus": mercato})
        renderizza_html_in_png("templates_social/template_analisi.html", {
            "COLORE_BOT": stile["colore"],
            "ETICHETTA_BOT": stile["etichetta"],
            "DATA_OGGI": oggi_str,
            "TITOLO_CALDO": copy_ai["titolo_grafica"],
            "MATCH": match_nome,
            "TESTO_STORYTELLING": copy_ai["testo_grafica"],
            "MERCATO_CHIAVE": mercato
        }, IMAGE_FILE)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": "WAITING_APPROVAL", "caption": copy_ai["caption_instagram"], "created_at": oggi_str}, f, ensure_ascii=False, indent=2)

    invia_anteprima_su_telegram(IMAGE_FILE, copy_ai["caption_instagram"])


def pubblica_su_instagram(image_public_url, caption):
    r1 = requests.post(f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media", data={
        "image_url": image_public_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    }, timeout=30)
    r1.raise_for_status()
    creation_id = r1.json()["id"]

    time.sleep(8)

    r2 = requests.post(f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish", data={
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    }, timeout=30)
    r2.raise_for_status()
    return r2.json()


def fase_2_controlla_ok_e_pubblica():
    if not os.path.exists(STATE_FILE):
        return
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        stato = json.load(f)
    if stato.get("status") != "WAITING_APPROVAL":
        return

    updates = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", timeout=15).json()
    azione_scelta = None
    for u in updates.get("result", []):
        cb = u.get("callback_query", {})
        if str(cb.get("from", {}).get("id")) == str(ADMIN_CHAT_ID):
            if cb.get("data") in ("APPROVA_IG", "SCARTA_IG"):
                azione_scelta = cb.get("data")

    if azione_scelta == "APPROVA_IG":
        image_url = f"{GITHUB_RAW_BASE}/{IMAGE_FILE}?v={int(time.time())}"
        pubblica_su_instagram(image_url, stato["caption"])
        stato["status"] = "PUBLISHED"
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(stato, f, indent=2)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": ADMIN_CHAT_ID, "text": "✅ Post pubblicato in automatico su Instagram!"})

    elif azione_scelta == "SCARTA_IG":
        stato["status"] = "DISCARDED"
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(stato, f, indent=2)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": ADMIN_CHAT_ID, "text": "🗑️ Bozza scartata."})


if __name__ == "__main__":
    modalita = sys.argv[1] if len(sys.argv) > 1 else "genera"
    if modalita == "genera":
        fase_1_genera_proposta()
    elif modalita == "pubblica":
        fase_2_controlla_ok_e_pubblica()
