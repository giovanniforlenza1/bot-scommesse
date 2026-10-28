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

FOTO_FALLBACK_CALCIO = [
    "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518091043644-c1d4457512c6?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1560272564-c83b66b1ad12?q=85&w=1200&auto=format&fit=crop"
]

FOTO_FALLBACK_TENNIS = [
    "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1554068865-24cecd4e34b8?q=85&w=1200&auto=format&fit=crop"
]

MAPPA_RICERCA_CLUB = {
    "Inter": "Inter Milan", "Milan": "AC Milan", "Juventus": "Juventus", "Napoli": "Napoli",
    "Roma": "AS Roma", "Lazio": "Lazio", "Atalanta": "Atalanta", "Fiorentina": "Fiorentina",
    "Bologna": "Bologna", "Torino": "Torino", "Verona": "Hellas Verona", "Como": "Como",
    "Parma": "Parma", "Udinese": "Udinese", "Genoa": "Genoa", "Lecce": "Lecce", "Empoli": "Empoli",
    "Venezia": "Venezia", "Cagliari": "Cagliari", "Monza": "Monza", "PSG": "Paris SG",
    "Bayern Monaco": "Bayern Munich", "Dortmund": "Borussia Dortmund", "Lipsia": "RB Leipzig",
    "Francoforte": "Eintracht Frankfurt", "Sporting Lisbona": "Sporting CP",
    "Betis Siviglia": "Real Betis", "Athletic Bilbao": "Athletic Bilbao",
    "Manchester United": "Manchester United", "Manchester City": "Manchester City",
    "Tottenham": "Tottenham", "Newcastle": "Newcastle", "Arsenal": "Arsenal",
    "Chelsea": "Chelsea", "Liverpool": "Liverpool", "Real Madrid": "Real Madrid",
    "Barcellona": "Barcelona", "Atletico Madrid": "Atletico Madrid"
}


def cerca_media_squadra_o_giocatore(nome_squadra, is_tennis=False, foto_gia_usate=None):
    """Cerca foto HD dei giocatori in azione e logo del club, evitando di ripetere sempre la stessa foto."""
    if foto_gia_usate is None:
        foto_gia_usate = []
    headers = {"User-Agent": "SBRLabSocialBot/2.0"}
    query_nome = MAPPA_RICERCA_CLUB.get(nome_squadra, nome_squadra)
    pool_foto_trovate = []
    logo_url = None

    try:
        if is_tennis:
            r = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchplayers.php?p={query_nome}", headers=headers, timeout=8)
            if r.status_code == 200 and r.json().get("player"):
                for pl in r.json()["player"]:
                    if "tennis" in str(pl.get("strSport", "")).lower():
                        for c in ("strFanart1", "strFanart2", "strFanart3", "strFanart4", "strThumb"):
                            if pl.get(c):
                                pool_foto_trovate.append(pl[c])
                        break
        else:
            r = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={query_nome}", headers=headers, timeout=8)
            if r.status_code == 200 and r.json().get("teams"):
                for tm in r.json()["teams"]:
                    if "soccer" in str(tm.get("strSport", "")).lower():
                        logo_url = tm.get("strBadge") or tm.get("strLogo")
                        id_team = tm.get("idTeam")

                        # 1. Foto in azione dei giocatori della rosa
                        if id_team:
                            rp = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/lookup_all_players.php?id={id_team}", headers=headers, timeout=8)
                            if rp.status_code == 200 and rp.json().get("player"):
                                for pl in rp.json()["player"]:
                                    for campo in ("strFanart1", "strFanart2", "strFanart3"):
                                        if pl.get(campo):
                                            pool_foto_trovate.append(pl[campo])

                        # 2. Fanart HD del club
                        for campo_tm in ("strFanart1", "strFanart2", "strFanart3", "strFanart4"):
                            if tm.get(campo_tm):
                                pool_foto_trovate.append(tm[campo_tm])
                        break

        # 3. Wikimedia Commons HD se il pool è vuoto
        if not pool_foto_trovate:
            q_wiki = f"{query_nome} {'tennis player' if is_tennis else 'football player match'}"
            w_url = (
                "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={requests.utils.quote(q_wiki)}&gsrnamespace=6&gsrlimit=8"
                "&prop=imageinfo&iiprop=url|dimensions&format=json"
            )
            rw = requests.get(w_url, headers=headers, timeout=8)
            if rw.status_code == 200:
                pages = rw.json().get("query", {}).get("pages", {})
                for pg in pages.values():
                    ii = (pg.get("imageinfo") or [{}])[0]
                    u = ii.get("url", "")
                    w = ii.get("width", 0)
                    h = ii.get("height", 0)
                    if w >= 900 and w >= h and any(u.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
                        pool_foto_trovate.append(u)
    except Exception as e:
        print(f"[MEDIA WARN] {nome_squadra}: {e}")

    # Filtra foto non ancora usate di recente
    fresche = [f for f in pool_foto_trovate if f not in foto_gia_usate]
    if fresche:
        return random.choice(fresche), logo_url, True
    if pool_foto_trovate:
        return random.choice(pool_foto_trovate), logo_url, True

    fallback_list = FOTO_FALLBACK_TENNIS if is_tennis else FOTO_FALLBACK_CALCIO
    fresche_fb = [f for f in fallback_list if f not in foto_gia_usate]
    return random.choice(fresche_fb if fresche_fb else fallback_list), logo_url, False


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


def scegli_senza_ripetere(lista_opzioni, usati_recenti):
    disponibili = [x for x in lista_opzioni if x not in usati_recenti]
    return random.choice(disponibili if disponibili else lista_opzioni)


def genera_copy_catchy(tipo_post, dati_contesto, usati_recenti):
    """Titoli corti, punchy ed enormi per la grafica + caption narrativa calda per Instagram."""
    modello = dati_contesto.get("modello", "BETA").upper()
    match = dati_contesto.get("match", "il big match")
    focus = dati_contesto.get("focus", "Analisi Tattica")

    hashtag_pool = [
        "#SBRLab #Calcio #SerieA #ChampionsLeague #AnalisiTattica #StatisticheCalcio",
        "#SBRLab #SportAnalytics #NumeriDelCalcio #TatticaCalcistica #FootballData",
        "#SBRLab #CalcioEuropeo #ModelliMatematici #MatchAnalysis #DataScience",
        "#SBRLab #InsiderSportivo #StatisticaSportiva #StudioDelMatch #CalcioVero"
    ]

    cta_pool = [
        "📲 L'analisi completa è già nel canale Telegram GRATUITO (Link in Bio).",
        "🔓 Entra GRATIS nel club su Telegram dal Link in Bio prima del fischio d'inizio.",
        "👉 Passa dal Link in Bio: Alpha, Beta e Tennis sono gratuiti sul nostro Telegram.",
        "📲 Unisciti gratis su Telegram (Link in Bio) e ricevi tutte le letture ogni mattina."
    ]

    if tipo_post == "PRE_MATCH":
        if modello == "ALPHA":
            # Titoli da 2-4 parole per impatto visivo gigante (74px)
            titoli = [
                "FAVORITA BLINDATA.", "RITMO DA ASSEDIO.",
                "NUMERI A SENSO UNICO.", "SCUDO SULLA GARA.",
                "DIVARIO NETTO.", "ZERO SPAZIO AL CASO.",
                "FATTORE CAMPO DECISIVO.", "DOMINIO TERRITORIALE.",
                "SOLO DATI REALI.", "LA SCELTA CHIRURGICA."
            ]
            sottotitoli = [
                f"Forma, tiri e tenuta difensiva: in {match} i parametri pendono da una sola parte.",
                f"Il Modello Alpha incrocia i flussi offensivi di {match} e attiva la copertura.",
                f"Quando il divario tecnico si unisce ai numeri, {match} diventa il bersaglio perfetto.",
                f"Niente tifo, solo freddezza: ecco cosa dicono gli algoritmi sui 90 minuti di {match}.",
                f"Continuità e peso offensivo: perché {match} guida la selezione Alpha di oggi."
            ]
            aperture_caption = [
                f"⚽ Il tifoso guarda il nome sulla maglia, i nostri modelli guardano cosa succede davvero nei 90 minuti.\n\nOggi il radar del Modello ALPHA punta dritto su {match} (segnale: {focus}).",
                f"🚀 C'è chi si affida all'istinto dell'ultimo minuto e chi studia le anomalie di rendimento.\n\nSu {match} il motore ALPHA ha isolato uno scenario ad altissima tenuta tattica: {focus}.",
                f"🏟️ Quando i ritmi offensivi e la solidità difensiva divergono così tanto, i numeri parlano prima del campo.\n\nFocus ALPHA del giorno su {match} 👉 {focus}."
            ]
        elif modello == "BETA":
            titoli = [
                "FASCE IN FIAMME.", "AREA SOTTO ASSEDIO.",
                "PARTITA AD ALTA TENSIONE.", "PIOGGIA DI DUELLI.",
                "NERVI A FIOR DI PELLE.", "SPINTA FINO AL 90°.",
                "RITMO FUORI SCALA.", "ANOMALIA POISSON.",
                "PRESSIONE COSTANTE.", "SCINTILLE IN CAMPO."
            ]
            sottotitoli = [
                f"Lo storico reale degli ultimi match accende {match}: volume di gioco altissimo.",
                f"Non guardiamo chi vince, ma come attacca: {match} promette scintille sulle corsie.",
                f"La curva di Poisson intercetta un valore netto su {match} incrociando le medie ESPN.",
                f"Baricentro alto e duelli continui: i numeri di {match} puntano dritti sul ritmo gara.",
                f"Cross, ribattute e contrasti: perché {match} è la singola perfetta per il Modello Beta."
            ]
            aperture_caption = [
                f"🔥 Alcune partite si leggono molto prima del risultato finale: basta osservare l'ampiezza sulle fasce e l'intensità dei contrasti.\n\nPer {match} il Modello BETA segnala un valore netto su: {focus}.",
                f"⚡ Mentre tutti cercano d'indovinare il marcatore, la distribuzione di Poisson analizza il volume reale di gioco.\n\nI dati storici di {match} accendono il semaforo verde del Modello BETA ({focus}).",
                f"📐 Storico ESPN verificato e calcolo delle probabilità pure: ecco perché oggi gli occhi del laboratorio sono tutti su {match}."
            ]
        else:  # SIGMA TENNIS
            titoli = [
                "DOMINIO DA FONDO.", "SUPERFICIE DECISIVA.",
                "ZERO PAREGGI.", "SERVIZIO INGIOCABILE.",
                "RITMO INSOPPORTABILE.", "VANTAGGIO NETTO."
            ]
            sottotitoli = [
                f"In {match} la resa sulla superficie e i turni di battuta scavano un solco profondo.",
                f"Uno contro uno, zero alibi: il laboratorio Sigma isola un vantaggio chiaro su {match}."
            ]
            aperture_caption = [
                f"🎾 Uno contro uno, dove i numeri al servizio e in risposta decidono ogni singolo set.\n\nAnalisi Sigma su {match}: {focus}."
            ]

        titolo_scelto = scegli_senza_ripetere(titoli, usati_recenti)
        sotto_scelto = random.choice(sottotitoli)
        caption = f"{random.choice(aperture_caption)}\n\n{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        return {"titolo_grafica": titolo_scelto, "testo_grafica": sotto_scelto, "caption_instagram": caption}

    elif tipo_post == "RISULTATI":
        winrate = dati_contesto.get("winrate", "--%")
        chiuse = dati_contesto.get("chiuse", 0)
        titoli_res = ["Il verdetto del campo.", "I numeri restano sempre.", "Trasparenza totale.", "Parla solo lo storico."]
        titolo_scelto = scegli_senza_ripetere(titoli_res, usati_recenti)
        caption = (
            f"📊 Niente promesse da bar: in SBR Lab ogni singola operazione viene registrata e certificata a database.\n\n"
            f"Con {chiuse} analisi concluse e un Win Rate del {winrate}, continuiamo a lavorare alla luce del sole.\n\n"
            f"{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        )
        return {"titolo_grafica": titolo_scelto, "testo_grafica": "", "caption_instagram": caption}

    else:
        titoli_omega = ["Giocare il match 10.000 volte.", "Cosa vede davvero Omega?", "La calma di Monte Carlo."]
        testi_omega = [
            "Prima del fischio d'inizio, il motore Omega simula l'incontro diecimila volte pesando attacco, difesa e fatica per isolare la probabilità pura.",
            "Omega nasce con un freno automatico: se il vantaggio matematico reale scende sotto soglia, il sistema blocca tutto. Fase privata in corso."
        ]
        titolo_scelto = scegli_senza_ripetere(titoli_omega, usati_recenti)
        caption = (
            f"🧪 Cosa succederebbe se potessi far giocare la stessa partita di calcio 10.000 volte prima del fischio d'inizio?\n\n"
            f"È ciò che fa il Modello OMEGA dietro le quinte. Nel frattempo, i segnali di Alpha, Beta e Tennis sono già liberi sul nostro canale.\n\n"
            f"{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        )
        return {"titolo_grafica": titolo_scelto, "testo_grafica": random.choice(testi_omega), "caption_instagram": caption}


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

    if os.path.exists(temp_html):
        os.remove(temp_html)


def scegli_match_calcio_protagonista(schedine, match_gia_usati):
    """
    90% CALCIO (Alpha e Beta), 10% Tennis.
    Non ripete MAI lo stesso match se lanci il bot più volte di fila!
    """
    pool_calcio = []

    # Raccoglie tutte le ultime partite di CALCIO (sia singole Beta che i singoli match delle multiple Alpha)
    for s in reversed(schedine):
        mod = s.get("modello", "").lower()
        if mod in ("alpha", "beta"):
            partite_vere = decripta_payload_se_presente(s)
            for p in partite_vere:
                casa = str(p.get("squadra_casa", "")).strip()
                trasf = str(p.get("squadra_trasferta", "")).strip()
                pron = str(p.get("pronostico", "Analisi Tattica")).strip()
                if casa and trasf and "🔒" not in casa and "Operazione" not in casa and "Singola" not in casa:
                    chiave_m = f"{casa} - {trasf}"
                    if not any(x[1] == casa and x[2] == trasf for x in pool_calcio):
                        pool_calcio.append((mod, casa, trasf, pron, chiave_m))
        if len(pool_calcio) >= 12:
            break

    # Filtra i match di calcio che NON hai ancora generato negli ultimi invii
    calcio_fresco = [m for m in pool_calcio if m[4] not in match_gia_usati]

    # Il Calcio è sempre la priorità assoluta
    if calcio_fresco:
        scelto = calcio_fresco[0]
        return scelto[0], scelto[1], scelto[2], scelto[3]

    if pool_calcio:
        scelto = random.choice(pool_calcio)
        return scelto[0], scelto[1], scelto[2], scelto[3]

    return "beta", "Inter", "Juventus", "Over 8.5 Calci d'Angolo"


def invia_anteprima_su_telegram(image_path, caption_ig):
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
    testo_admin = f"🎨 *ANTEPRIMA POST INSTAGRAM PRONTA*\n\n📝 *Caption proposta:*\n\n{caption_ig}"
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
    return {"ultimi_titoli_usati": [], "ultimi_match_usati": [], "ultime_foto_usate": []}


def fase_1_genera_proposta():
    db = {"schedine": []}
    if os.path.exists("database.json"):
        with open("database.json", "r", encoding="utf-8") as f:
            db = json.load(f)

    stato_prec = carica_stato_precedente()
    usati_titoli = stato_prec.get("ultimi_titoli_usati", [])[-10:]
    usati_match = stato_prec.get("ultimi_match_usati", [])[-8:]
    usate_foto = stato_prec.get("ultime_foto_usate", [])[-10:]

    schedine = db.get("schedine", [])
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi_str = datetime.now(fuso_italia).strftime("%d/%m/%Y")

    # Genera il post Pre-Match sul CALCIO con Foto Grande + Titoli Enormi
    mod_key, sq_casa, sq_trasf, mercato = scegli_match_calcio_protagonista(schedine, usati_match)
    is_tennis = (mod_key == "sigma")
    stile = STILE_BOT.get(mod_key, STILE_BOT["beta"])

    foto_casa, logo_casa, trovata_vera_c = cerca_media_squadra_o_giocatore(sq_casa, is_tennis=is_tennis, foto_gia_usate=usate_foto)
    foto_trasf, logo_trasf, trovata_vera_t = cerca_media_squadra_o_giocatore(sq_trasf, is_tennis=is_tennis, foto_gia_usate=usate_foto)

    # Usa la foto reale dei giocatori della squadra che ha la miglior immagine disponibile
    if trovata_vera_c and trovata_vera_t:
        foto_scelta = random.choice([foto_casa, foto_trasf])
    elif trovata_vera_t and not trovata_vera_c:
        foto_scelta = foto_trasf
    else:
        foto_scelta = foto_casa

    logo_c_html = f"<img class='team-logo' src='{logo_casa}' alt=''>" if logo_casa else ""
    logo_t_html = f"<img class='team-logo' src='{logo_trasf}' alt=''>" if logo_trasf else ""
    match_nome = f"{sq_casa} - {sq_trasf}"

    copy_scelto = genera_copy_catchy("PRE_MATCH", {"modello": mod_key.upper(), "match": match_nome, "focus": mercato}, usati_titoli)
    renderizza_html_in_png("templates_social/template_analisi.html", {
        "FOTO_HD_URL": foto_scelta,
        "COLORE_BOT": stile["colore"],
        "ETICHETTA_BOT": stile["etichetta"],
        "DATA_OGGI": oggi_str,
        "LOGO_CASA_HTML": logo_c_html,
        "LOGO_TRASFERTA_HTML": logo_t_html,
        "SQUADRA_CASA": sq_casa,
        "SQUADRA_TRASFERTA": sq_trasf,
        "TITOLO_CALDO": copy_scelto["titolo_grafica"],
        "TESTO_STORYTELLING": copy_scelto["testo_grafica"],
        "MERCATO_CHIAVE": mercato
    }, IMAGE_FILE)

    usati_titoli.append(copy_scelto["titolo_grafica"])
    usati_match.append(match_nome)
    usate_foto.append(foto_scelta)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "status": "WAITING_APPROVAL",
            "caption": copy_scelto["caption_instagram"],
            "created_at": oggi_str,
            "ultimi_titoli_usati": usati_titoli[-10:],
            "ultimi_match_usati": usati_match[-8:],
            "ultime_foto_usate": usate_foto[-10:]
        }, f, ensure_ascii=False, indent=2)

    invia_anteprima_su_telegram(IMAGE_FILE, copy_scelto["caption_instagram"])
    print(f"Post Calcio generato su {match_nome} ({mod_key.upper()}) e inviato su Telegram!")


def pubblica_su_instagram(image_public_url, caption):
    if not IG_USER_ID or not IG_ACCESS_TOKEN:
        raise ValueError("IG_USER_ID o IG_ACCESS_TOKEN non ancora inseriti nei Secrets di GitHub.")

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
                      json={"chat_id": ADMIN_CHAT_ID, "text": "🗑️ Bozza scartata. Rilancia il workflow per ricevere subito un'altra partita!"})


if __name__ == "__main__":
    modalita = sys.argv[1] if len(sys.argv) > 1 else "genera"
    if modalita == "genera":
        fase_1_genera_proposta()
    elif modalita == "pubblica":
        fase_2_controlla_ok_e_pubblica()
