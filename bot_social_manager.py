import os
import sys
import json
import time
import random
import base64
import hashlib
import urllib.parse
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
IMAGE_FILE = "social_post_ready.png"

STILE_BOT = {
    "alpha": {"colore": "#F87060", "etichetta": "MODELLO ALPHA • CALCIO"},
    "beta":  {"colore": "#B3A394", "etichetta": "MODELLO BETA • POISSON"},
    "sigma": {"colore": "#2D6A4F", "etichetta": "MODELLO SIGMA • TENNIS"},
    "omega": {"colore": "#102542", "etichetta": "MODELLO OMEGA • QUANT"}
}

# Descrizione precisa delle maglie ufficiali per far generare all'AI scatti perfetti (solo busto/maglia, senza volti)
KIT_COLORI_SQUADRE = {
    "Inter": "iconic black and royal blue vertical striped soccer jersey",
    "Milan": "iconic red and black vertical striped soccer jersey",
    "Juventus": "iconic black and white vertical striped soccer jersey",
    "Napoli": "sky blue light-blue soccer jersey",
    "Roma": "deep crimson dark-red and golden yellow soccer jersey",
    "Lazio": "sky blue and white soccer jersey",
    "Atalanta": "black and blue vertical striped soccer jersey",
    "Fiorentina": "deep purple violet soccer jersey",
    "Bologna": "red and dark blue vertical striped soccer jersey",
    "Torino": "dark maroon burgundy granata soccer jersey",
    "Udinese": "black and white striped soccer jersey",
    "Genoa": "half red and half dark-blue soccer jersey",
    "Como": "royal blue lake-blue soccer jersey",
    "Parma": "white with black cross or yellow and blue striped soccer jersey",
    "Verona": "dark blue and bright yellow soccer jersey",
    "Empoli": "azure blue soccer jersey",
    "Lecce": "yellow and red vertical striped soccer jersey",
    "Cagliari": "half red and half navy-blue soccer jersey",
    "Venezia": "black soccer jersey with orange and green trim",
    "Monza": "bright red soccer jersey with white vertical band",
    "Real Madrid": "pure white royal soccer jersey",
    "Barcellona": "blue and garnet red striped soccer jersey",
    "Arsenal": "red body with white sleeves soccer jersey",
    "Manchester City": "sky blue soccer jersey",
    "Liverpool": "all red crimson soccer jersey",
    "Bayern Monaco": "bright red and white soccer jersey",
    "PSG": "navy blue soccer jersey with central red stripe"
}


def cerca_logo_espn(nome_squadra):
    headers = {"User-Agent": "Mozilla/5.0"}
    for lega in ("ita.1", "eng.1", "esp.1", "ger.1", "fra.1", "ned.1", "por.1", "uefa.champions"):
        try:
            r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/teams", headers=headers, timeout=5)
            if r.status_code == 200:
                sports = r.json().get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
                for item in sports:
                    tm = item.get("team", {})
                    d_name = str(tm.get("displayName", "")).lower()
                    s_name = str(tm.get("shortDisplayName", "")).lower()
                    if nome_squadra.lower() in d_name or nome_squadra.lower() in s_name:
                        logos = tm.get("logos", [])
                        if logos:
                            return logos[0].get("href")
        except Exception:
            continue
    return None


def genera_url_immagine_ai_maglia(sq_casa, sq_trasf, prompt_extra_ai=""):
    """
    Genera gratuitamente con Flux AI (Pollinations) uno scatto fotografico editoriale HD
    INQUADRATO DAL COLLO IN GIÙ (solo maglia/busto/pallone in azione, ZERO volti, ZERO testi finti)
    con i veri colori sociali delle due squadre del match!
    """
    kit_casa = KIT_COLORI_SQUADRE.get(sq_casa, f"{sq_casa} official football jersey colors")
    kit_trasf = KIT_COLORI_SQUADRE.get(sq_trasf, f"{sq_trasf} official football jersey colors")

    base_prompt = (
        f"Editorial sports photography, tight cropped shot from neck down to waist only, NO FACES visible, NO HEADS, "
        f"two soccer players clashing for the ball under dramatic night stadium floodlights, rain droplets, "
        f"one player wearing {kit_casa} and opponent wearing {kit_trasf}, "
        f"ultra realistic fabric texture, shallow depth of field, Nike football commercial aesthetic, 8k, no text, no numbers, no logos"
    )
    if prompt_extra_ai:
        base_prompt = f"{base_prompt}, {prompt_extra_ai}"

    seed = random.randint(1000, 999999)
    encoded = urllib.parse.quote(base_prompt)
    url_ai = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=760&seed={seed}&nologo=true&model=flux"

    # Verifica rapida che l'immagine AI risponda correttamente
    try:
        r = requests.get(url_ai, timeout=22)
        if r.status_code == 200 and len(r.content) > 15000:
            local_ai_img = "temp_ai_hero.jpg"
            with open(local_ai_img, "wb") as f:
                f.write(r.content)
            return f"file://{os.path.abspath(local_ai_img)}"
    except Exception as e:
        print(f"[AI IMAGE WARN] {e}")

    return None


def decripta_payload_se_presente(schedina):
    partite = schedina.get("partite", [])
    if partite and "🔒" not in str(partite[0].get("squadra_casa", "")) and "Operazione" not in str(partite[0].get("squadra_casa", "")) and "Singola" not in str(partite[0].get("squadra_casa", "")):
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


def genera_contenuto_creativo_con_groq(tipo_post, dati_contesto, usati_recenti):
    """
    Usa Groq AI (Llama 3.3 70B gratis) per creare testi specifici, intelligenti e mai banali
    cuciti sulle due squadre reali, più le 3 metriche tecniche e la regia fotografica.
    """
    if GROQ_API_KEY:
        prompt_sistema = (
            "Sei il Direttore Creativo 25enne di SBR Lab (@sbr.lab), il progetto italiano più seguito di Data Science e Analisi Tattica sul Calcio. "
            "Il tuo stile è magnetico, sveglio, tagliente e competente (pensa a Cronache di Spogliatoio + The Athletic). "
            "REGOLE TASSATIVE:\n"
            "1. Niente frasi fatte da robot: parla delle VERE caratteristiche tattiche delle squadre citate nei dati (ritmo, fasce, difesa alta, contropiede, pressione).\n"
            "2. VIETATO usare parole da scommettitori a rischio ban: scommessa, puntata, bookmaker, cassa, soldi, vincita.\n"
            "3. Rispondi ESCLUSIVAMENTE con un JSON valido contenente queste chiavi:\n"
            "- 'titolo_grafica': MASSIMO 3 PAROLE in MAIUSCOLO col punto finale, potentissime e specifiche sul match o sul tema (es. 'SAN SIRO ELETTRICO.', 'FASCE SOTTO ASSEDIO.', 'NUMERI CONTRO TIFO.');\n"
            "- 'testo_grafica': 15-20 parole incisive che spiegano l'anomalia tattica o statistica trovata dal nostro algoritmo sulla partita (niente HTML);\n"
            "- 'chip_1': metrica breve max 18 caratteri (es. 'RITMO: ALTISSIMO' o 'POISSON: +9.2%');\n"
            "- 'chip_2': seconda metrica breve max 18 caratteri (es. 'FASCE: DOMINANTI' o 'CONFIDENZA: ALTA');\n"
            "- 'chip_3': terza metrica breve max 18 caratteri (es. 'FILTRO: SUPERATO' o 'DATI: 30 GIORNI');\n"
            "- 'image_prompt': breve descrizione in inglese (max 15 parole) dell'atmosfera sul campo (es. 'intense derby atmosphere, wet grass, dramatic stadium lights');\n"
            "- 'caption_instagram': post scorrevole (70-95 parole) scritto come un ragazzo di 25 anni che capisce di calcio e smonta i luoghi comuni da bar usando i numeri del nostro algoritmo. Chiudi invitando con naturalezza a vedere le analisi gratuite sul canale Telegram dal link in bio + 5 hashtag."
        )
        prompt_utente = (
            f"Rubrica: {tipo_post}\n"
            f"Dati del match/report: {json.dumps(dati_contesto, ensure_ascii=False)}\n"
            f"Titoli già usati di recente (NON usarli): {usati_recenti}"
        )

        for modello_free in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": modello_free,
                        "messages": [
                            {"role": "system", "content": prompt_sistema},
                            {"role": "user", "content": prompt_utente}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.88
                    },
                    timeout=20
                )
                if r.status_code == 200:
                    contenuto = r.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(contenuto)
                    if "titolo_grafica" in parsed and "caption_instagram" in parsed:
                        print(f"[GROQ AI] Contenuto creativo generato con {modello_free}!")
                        return parsed
            except Exception as e:
                print(f"[GROQ WARN] {modello_free}: {e}")

    # Fallback se la chiave GROQ_API_KEY non è ancora stata inserita nei Secrets
    match = dati_contesto.get("match", "Big Match Serie A")
    focus = dati_contesto.get("focus", "Analisi Tattica")
    return {
        "titolo_grafica": "RITMO FUORI SCALA.",
        "testo_grafica": f"Incrociando i flussi offensivi degli ultimi 30 giorni, {match} mostra uno squilibrio netto sul ritmo gara.",
        "chip_1": "STORICO: 30GG",
        "chip_2": "INDICE: ALTO VALORE",
        "chip_3": "STATO: VERIFICATO",
        "image_prompt": "dramatic stadium floodlights, wet pitch action",
        "caption_instagram": (
            f"⚽ Al bar si parla solo di chi segnerà, in laboratorio guardiamo cosa succede nei 90 minuti.\n\n"
            f"Su {match} i nostri modelli hanno isolato un segnale chiarissimo su {focus}. Zero tifo, solo numeri reali.\n\n"
            f"📲 Trovi tutte le letture gratuite di Alpha, Beta e Tennis nel canale Telegram (Link in Bio).\n\n"
            f"#SBRLab #SerieA #Calcio #AnalisiTattica #StatisticheCalcio"
        )
    }


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
        page.goto(f"file://{os.path.abspath(temp_html)}", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(1200)
        page.screenshot(path=output_png, full_page=False)
        browser.close()

    for tmp in (temp_html, "temp_ai_hero.jpg"):
        if os.path.exists(tmp):
            os.remove(tmp)


def scegli_match_calcio_serie_a_prioritario(schedine, match_gia_usati):
    pool_serie_a = []
    pool_altro_calcio = []

    for s in reversed(schedine):
        mod = s.get("modello", "").lower()
        if mod in ("alpha", "beta"):
            partite_vere = decripta_payload_se_presente(s)
            for p in partite_vere:
                casa = str(p.get("squadra_casa", "")).strip()
                trasf = str(p.get("squadra_trasferta", "")).strip()
                pron = str(p.get("pronostico", "Analisi Tattica")).strip()
                lega = str(p.get("lega", "")).lower()
                if casa and trasf and "🔒" not in casa and "Operazione" not in casa and "Singola" not in casa:
                    chiave_m = f"{casa} - {trasf}"
                    item = (mod, casa, trasf, pron, chiave_m)
                    if "serie_a" in lega or casa in KIT_COLORI_SQUADRE or trasf in KIT_COLORI_SQUADRE:
                        if not any(x[4] == chiave_m for x in pool_serie_a):
                            pool_serie_a.append(item)
                    else:
                        if not any(x[4] == chiave_m for x in pool_altro_calcio):
                            pool_altro_calcio.append(item)

    freschi_sa = [m for m in pool_serie_a if m[4] not in match_gia_usati]
    if freschi_sa:
        scelto = freschi_sa[0]
        return scelto[0], scelto[1], scelto[2], scelto[3]

    freschi_altri = [m for m in pool_altro_calcio if m[4] not in match_gia_usati]
    if freschi_altri:
        scelto = freschi_altri[0]
        return scelto[0], scelto[1], scelto[2], scelto[3]

    if pool_serie_a:
        scelto = random.choice(pool_serie_a)
        return scelto[0], scelto[1], scelto[2], scelto[3]

    return "beta", "Milan", "Inter", "Over 8.5 Calci d'Angolo"


def invia_anteprima_su_telegram(image_path, caption_ig, tipo_format):
    if not TELEGRAM_TOKEN or not ADMIN_CHAT_ID:
        print("ERRORE: TELEGRAM_TOKEN o ADMIN_CHAT_ID mancanti nei Secrets!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    tastiera = {
        "inline_keyboard": [[
            {"text": "✅ Approva e Pubblica su IG", "callback_data": "APPROVA_IG"},
            {"text": "❌ Scarta Bozza", "callback_data": "SCARTA_IG"}
        ]]
    }
    testo_admin = f"🎨 *ANTEPRIMA POST AI ({tipo_format})*\n\n📝 *Copy scritto da AI:*\n\n{caption_ig}"
    with open(image_path, "rb") as img:
        r = requests.post(
            url,
            data={
                "chat_id": ADMIN_CHAT_ID,
                "caption": testo_admin[:1020],
                "reply_markup": json.dumps(tastiera)
            },
            files={"photo": img},
            timeout=30
        )
    r.raise_for_status()


def carica_stato_precedente():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ultimi_titoli_usati": [], "ultimi_match_usati": [], "indice_rotazione": 0}


def fase_1_genera_proposta(forza_tipo=None):
    db = {"schedine": []}
    if os.path.exists("database.json"):
        with open("database.json", "r", encoding="utf-8") as f:
            db = json.load(f)

    stato_prec = carica_stato_precedente()
    usati_titoli = stato_prec.get("ultimi_titoli_usati", [])[-10:]
    usati_match = stato_prec.get("ultimi_match_usati", [])[-8:]
    idx_rot = int(stato_prec.get("indice_rotazione", 0))

    sequenza_formati = ["PRE_MATCH", "RISULTATI", "PRE_MATCH", "OMEGA"]
    tipo_post = forza_tipo if forza_tipo in ("PRE_MATCH", "RISULTATI", "OMEGA") else sequenza_formati[idx_rot % len(sequenza_formati)]

    schedine = db.get("schedine", [])
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi_str = datetime.now(fuso_italia).strftime("%d/%m/%Y")

    if tipo_post == "RISULTATI" and schedine:
        concluse = [s for s in schedine if s.get("stato_schedina") in ("vinta", "persa") and s.get("modello") in ("alpha", "beta", "sigma")]
        vinte = [s for s in concluse if s.get("stato_schedina") == "vinta"]
        winrate = f"{round((len(vinte)/len(concluse))*100)}%" if concluse else "--%"
        ultime_3 = concluse[-3:]
        righe_html = ""
        for s in ultime_3:
            partite_vere = decripta_payload_se_presente(s) or s.get("partite", [])
            if not partite_vere:
                continue
            p0 = partite_vere[0]
            mod_label = s.get("modello", "SBR").upper()
            is_win = s["stato_schedina"] == "vinta"
            badge = "<span class='esito-vinto'>✓ PRESA</span>" if is_win else "<span class='esito-perso'>✕ STOP</span>"
            righe_html += (
                f"<div class='row'>"
                f"<div><span class='mod-pill'>{mod_label}</span>{p0['squadra_casa']} - {p0['squadra_trasferta']}</div>"
                f"{badge}</div>"
            )
        copy_ai = genera_contenuto_creativo_con_groq("RISULTATI", {"winrate": winrate, "operazioni_chiuse": len(concluse)}, usati_titoli)
        renderizza_html_in_png("templates_social/template_risultati.html", {
            "PERIODO": f"REPORT AL {oggi_str}",
            "TITOLO_RISULTATI": copy_ai["titolo_grafica"],
            "TOTALE_CHIUSE": len(concluse),
            "WINRATE": winrate,
            "RIGHE_OPERAZIONI": righe_html or "<div class='row'><span>Storico in aggiornamento</span></div>"
        }, IMAGE_FILE)

    elif tipo_post == "OMEGA":
        copy_ai = genera_contenuto_creativo_con_groq("OMEGA", {"motore": "10.000 simulazioni Monte Carlo", "funzione": "Rimozione aggio e calcolo probabilità reale", "stato": "Calibrazione privata"}, usati_titoli)
        renderizza_html_in_png("templates_social/template_omega.html", {
            "TITOLO_OMEGA": copy_ai["titolo_grafica"],
            "TESTO_OMEGA": copy_ai["testo_grafica"]
        }, IMAGE_FILE)

    else:
        mod_key, sq_casa, sq_trasf, mercato = scegli_match_calcio_serie_a_prioritario(schedine, usati_match)
        stile = STILE_BOT.get(mod_key, STILE_BOT["beta"])
        match_nome = f"{sq_casa} - {sq_trasf}"

        # 1. L'AI scrive titolo catchy, analisi tattica, 3 metriche e regia fotografica
        copy_ai = genera_contenuto_creativo_con_groq("PRE_MATCH", {
            "modello": mod_key.upper(),
            "match": match_nome,
            "squadra_casa": sq_casa,
            "squadra_trasferta": sq_trasf,
            "focus_algoritmo": mercato
        }, usati_titoli)

        # 2. L'AI genera l'immagine HD su misura con le maglie ufficiali delle due squadre (dal collo in giù, zero volti!)
        logo_casa = cerca_logo_espn(sq_casa)
        logo_trasf = cerca_logo_espn(sq_trasf)
        img_ai_path = genera_url_immagine_ai_maglia(sq_casa, sq_trasf, copy_ai.get("image_prompt", ""))

        if img_ai_path:
            hero_html = f"<img class='bg' src='{img_ai_path}' alt='Match Action'>"
        else:
            l1 = f"<img src='{logo_casa}' alt=''>" if logo_casa else ""
            l2 = f"<img src='{logo_trasf}' alt=''>" if logo_trasf else ""
            hero_html = f"<div class='club-split-hero'>{l1}{l2}</div>"

        logo_c_html = f"<img class='team-logo' src='{logo_casa}' alt=''>" if logo_casa else ""
        logo_t_html = f"<img class='team-logo' src='{logo_trasf}' alt=''>" if logo_trasf else ""

        renderizza_html_in_png("templates_social/template_analisi.html", {
            "HERO_VISUAL_HTML": hero_html,
            "COLORE_BOT": stile["colore"],
            "ETICHETTA_BOT": stile["etichetta"],
            "DATA_OGGI": oggi_str,
            "LOGO_CASA_HTML": logo_c_html,
            "LOGO_TRASFERTA_HTML": logo_t_html,
            "SQUADRA_CASA": sq_casa,
            "SQUADRA_TRASFERTA": sq_trasf,
            "CHIP_1": copy_ai.get("chip_1", "STORICO: 30GG"),
            "CHIP_2": copy_ai.get("chip_2", f"BOT: {mod_key.upper()}"),
            "CHIP_3": copy_ai.get("chip_3", "EDGE: POSITIVO"),
            "TITOLO_CALDO": copy_ai["titolo_grafica"],
            "TESTO_STORYTELLING": copy_ai["testo_grafica"],
            "MERCATO_CHIAVE": mercato
        }, IMAGE_FILE)
        usati_match.append(match_nome)

    usati_titoli.append(copy_ai["titolo_grafica"])

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "status": "WAITING_APPROVAL",
            "caption": copy_ai["caption_instagram"],
            "created_at": oggi_str,
            "ultimi_titoli_usati": usati_titoli[-10:],
            "ultimi_match_usati": usati_match[-8:],
            "indice_rotazione": idx_rot + 1
        }, f, ensure_ascii=False, indent=2)

    invia_anteprima_su_telegram(IMAGE_FILE, copy_ai["caption_instagram"], tipo_post)
    print(f"Post AI {tipo_post} generato e inviato su Telegram!")


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
        return
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        stato = json.load(f)
    if stato.get("status") != "WAITING_APPROVAL":
        return

    updates = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", timeout=15).json()
    azione_scelta = None
    ultimo_update_id = None

    for u in updates.get("result", []):
        ultimo_update_id = u.get("update_id")
        cb = u.get("callback_query", {})
        if str(cb.get("from", {}).get("id")) == str(ADMIN_CHAT_ID):
            if cb.get("data") in ("APPROVA_IG", "SCARTA_IG"):
                azione_scelta = cb.get("data")

    if azione_scelta == "APPROVA_IG":
        image_url = f"{GITHUB_RAW_BASE}/{IMAGE_FILE}?v={int(time.time())}"
        pubblica_su_instagram(image_url, stato["caption"])
        stato["status"] = "PUBLISHED"
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(stato, f, ensure_ascii=False, indent=2)
        if ultimo_update_id:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_update_id + 1}", timeout=10)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": ADMIN_CHAT_ID, "text": "✅ Post pubblicato in automatico su Instagram!"})

    elif azione_scelta == "SCARTA_IG":
        stato["status"] = "DISCARDED"
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(stato, f, ensure_ascii=False, indent=2)
        if ultimo_update_id:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_update_id + 1}", timeout=10)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": ADMIN_CHAT_ID, "text": "🗑️ Bozza scartata. Rilancia il workflow per generare un nuovo scatto AI!"})


if __name__ == "__main__":
    modalita = sys.argv[1] if len(sys.argv) > 1 else "genera"
    forza = sys.argv[2].upper() if len(sys.argv) > 2 else None
    if modalita == "genera":
        fase_1_genera_proposta(forza_tipo=forza)
    elif modalita == "pubblica":
        fase_2_controlla_ok_e_pubblica()
