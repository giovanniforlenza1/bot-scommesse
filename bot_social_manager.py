import os
import sys
import json
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# Variabili d'ambiente da salvare nei Secrets di GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")       # Il TUO ID Telegram personale (non il canale pubblico!)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")     # Chiave gratuita Google AI Studio
IG_USER_ID = os.environ.get("IG_USER_ID")             # ID del tuo account Instagram Business
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")   # Token Meta Graph API
GITHUB_RAW_BASE = os.environ.get("GITHUB_RAW_BASE")   # Es: https://raw.githubusercontent.com/tuo-user/tuo-repo/main

STATE_FILE = "pending_social_post.json"
IMAGE_FILE = "social_post_ready.png"


def genera_copy_caldo_con_ai(tipo_post, dati_contesto):
    """Chiede a Gemini di creare testi narrativi, caldi e anti-ban (stile editoriale sportivo)."""
    prompt = f"""
    Sei il direttore creativo di SBR Lab (@sbr.lab), un progetto italiano di analisi sportiva e data science.
    Tono di voce: appassionato di sport, narrativo, elegante, MAI freddo/robotico e MAI da scommettitore (VIETATE parole come: scommessa, puntata, soldi facili, cassa sicura, bookmaker).
    
    Tipo di post di oggi: {tipo_post}
    Dati reali dal nostro database: {json.dumps(dati_contesto, ensure_ascii=False)}
    
    Rispondi ESCLUSIVAMENTE con un JSON valido con queste chiavi:
    - "titolo_grafica": massimo 7 parole d'impatto (puoi racchiudere 1-2 parole chiave in <span class='accent'>...</span>)
    - "testo_grafica": massimo 24 parole di storytelling tattico sulla partita o sul laboratorio
    - "caption_instagram": didascalia coinvolgente (massimo 120 parole) con invito finale a entrare nel canale Telegram gratuito dal link in bio + 5 hashtag SEO sportivi.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    testo_json = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(testo_json)


def renderizza_html_in_png(template_path, sostituzioni, output_png):
    """Compila il template HTML e scatta uno screenshot 1080x1350 nitido."""
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


def invia_anteprima_su_telegram(image_path, caption_ig):
    """Manda a TE sul telefono la grafica pronta con i pulsanti Approva / Scarta."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    tastiera = {
        "inline_keyboard": [[
            {"text": "✅ Approva e Pubblica su IG", "callback_data": "APPROVA_IG"},
            {"text": "❌ Scarta Bozza", "callback_data": "SCARTA_IG"}
        ]]
    }
    testo_admin = f"🎨 *ANTEPRIMA POST INSTAGRAM PRONTA*\n\n📝 *Caption proposta:*\n{caption_ig}"
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
    """Legge database.json, sceglie il format del giorno, crea la grafica e te la manda su Telegram."""
    with open("database.json", "r", encoding="utf-8") as f:
        db = json.load(f)

    schedine = db.get("schedine", [])
    oggi_str = datetime.now().strftime("%d/%m/%Y")
    giorno_settimana = datetime.now().weekday()  # 0=Lun, 4=Ven, ecc.

    # Lunedì: Verdetto del Campo | Venerdì: Hype Omega | Altri giorni: L'Occhio Clinico
    if giorno_settimana == 0 and schedine:
        concluse = [s for s in schedine if s.get("stato_schedina") in ("vinta", "persa")]
        vinte = [s for s in concluse if s.get("stato_schedina") == "vinta"]
        winrate = f"{round((len(vinte)/len(concluse))*100)}%" if concluse else "--%"
        ultime_3 = concluse[-3:]
        righe_html = "".join([
            f"<div class='list-item'><span>{s['partite'][0]['squadra_casa']} - {s['partite'][0]['squadra_trasferta']}</span>"
            f"<span style='color:{'#22c55e' if s['stato_schedina']=='vinta' else '#ef4444'};'>{s['stato_schedina'].upper()}</span></div>"
            for s in ultime_3 if s.get("partite")
        ])
        copy_ai = genera_copy_caldo_con_ai("Verdetto del Campo (Trasparenza risultati)", {"winrate": winrate, "totale_analizzate": len(concluse)})
        renderizza_html_in_png("templates_social/template_risultati.html", {
            "PERIODO": f"REPORT AL {oggi_str}",
            "YIELD": "CERTIFICATO",
            "WINRATE": winrate,
            "RIGHE_OPERAZIONI": righe_html
        }, IMAGE_FILE)

    elif giorno_settimana == 4:
        copy_ai = genera_copy_caldo_con_ai("Diario Laboratorio Modello Omega (10.000 simulazioni Monte Carlo in fase di calibrazione privata)", {})
        renderizza_html_in_png("templates_social/template_omega.html", {
            "TITOLO_OMEGA": copy_ai["titolo_grafica"],
            "TESTO_OMEGA": copy_ai["testo_grafica"]
        }, IMAGE_FILE)

    else:
        # Prende l'ultima operazione generata (Alpha o Beta) per raccontare il pre-match
        ultima = schedine[-1] if schedine else {"modello": "BETA", "partite": [{"squadra_casa": "Big Match", "squadra_trasferta": "Serie A", "pronostico": "Pressione Corner"}]}
        partita = ultima["partite"][0]
        match_nome = f"{partita['squadra_casa']} - {partita['squadra_trasferta']}"
        copy_ai = genera_copy_caldo_con_ai("Analisi Tattica Pre-Match", {"match": match_nome, "modello": ultima.get("modello", "beta"), "focus": partita.get("pronostico", "")})
        renderizza_html_in_png("templates_social/template_analisi.html", {
            "MODELLO": ultima.get("modello", "BETA").upper(),
            "DATA_OGGI": oggi_str,
            "TITOLO_CALDO": copy_ai["titolo_grafica"],
            "MATCH": match_nome,
            "TESTO_STORYTELLING": copy_ai["testo_grafica"],
            "MERCATO_CHIAVE": partita.get("pronostico", "Analisi Ritmo")
        }, IMAGE_FILE)

    # Salva stato in attesa del tuo OK
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "status": "WAITING_APPROVAL",
            "caption": copy_ai["caption_instagram"],
            "created_at": oggi_str
        }, f, ensure_ascii=False, indent=2)

    invia_anteprima_su_telegram(IMAGE_FILE, copy_ai["caption_instagram"])
    print("Bozza creata e inviata su Telegram per approvazione.")


def pubblica_su_instagram(image_public_url, caption):
    """Pubblica automaticamente su Instagram tramite le API ufficiali Meta."""
    # Step 1: Crea il contenitore media su Meta
    url_container = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    r1 = requests.post(url_container, data={
        "image_url": image_public_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    }, timeout=30)
    r1.raise_for_status()
    creation_id = r1.json()["id"]

    time.sleep(8)  # Attesa tecnica elaborazione immagine lato Instagram

    # Step 2: Pubblica definitivamente nel feed
    url_publish = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    r2 = requests.post(url_publish, data={
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    }, timeout=30)
    r2.raise_for_status()
    return r2.json()


def fase_2_controlla_ok_e_pubblica():
    """Controlla se hai premuto 'Approva' su Telegram e pubblica su Instagram."""
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
                      json={"chat_id": ADMIN_CHAT_ID, "text": "🚀 *Post pubblicato con successo su Instagram!*", "parse_mode": "Markdown"})

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
