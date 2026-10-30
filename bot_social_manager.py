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

# Categorie Wikimedia Commons Ufficiali + Pagine Wikipedia Stadio/Tifosi per avere SEMPRE foto vere della squadra
CLUB_MEDIA_MAP = {
    "Inter": {
        "tsdb": ["Inter", "Internazionale"],
        "commons_cats": ["Category:FC Internazionale Milano", "Category:San Siro"],
        "wiki_pages": ["San Siro", "Derby della Madonnina", "FC Internazionale Milano"]
    },
    "Milan": {
        "tsdb": ["AC Milan", "Milan"],
        "commons_cats": ["Category:AC Milan", "Category:San Siro"],
        "wiki_pages": ["San Siro", "AC Milan", "Derby della Madonnina"]
    },
    "Juventus": {
        "tsdb": ["Juventus"],
        "commons_cats": ["Category:Juventus FC", "Category:Juventus Stadium"],
        "wiki_pages": ["Juventus Stadium", "Juventus FC"]
    },
    "Napoli": {
        "tsdb": ["Napoli", "SSC Napoli"],
        "commons_cats": ["Category:SSC Napoli", "Category:Stadio Diego Armando Maradona (Naples)"],
        "wiki_pages": ["Stadio Diego Armando Maradona", "SSC Napoli"]
    },
    "Roma": {
        "tsdb": ["AS Roma", "Roma"],
        "commons_cats": ["Category:AS Roma", "Category:Stadio Olimpico (Rome)"],
        "wiki_pages": ["Stadio Olimpico", "AS Roma", "Derby della Capitale"]
    },
    "Lazio": {
        "tsdb": ["Lazio", "SS Lazio"],
        "commons_cats": ["Category:SS Lazio", "Category:Stadio Olimpico (Rome)"],
        "wiki_pages": ["Stadio Olimpico", "SS Lazio"]
    },
    "Atalanta": {
        "tsdb": ["Atalanta"],
        "commons_cats": ["Category:Atalanta BC", "Category:Stadio Atleti Azzurri d'Italia"],
        "wiki_pages": ["Gewiss Stadium", "Atalanta BC"]
    },
    "Fiorentina": {
        "tsdb": ["Fiorentina"],
        "commons_cats": ["Category:ACF Fiorentina", "Category:Stadio Artemio Franchi (Florence)"],
        "wiki_pages": ["Stadio Artemio Franchi", "ACF Fiorentina"]
    },
    "Bologna": {
        "tsdb": ["Bologna"],
        "commons_cats": ["Category:Bologna FC 1909", "Category:Stadio Renato Dall'Ara"],
        "wiki_pages": ["Stadio Renato Dall'Ara", "Bologna FC 1909"]
    },
    "Torino": {
        "tsdb": ["Torino"],
        "commons_cats": ["Category:Torino FC", "Category:Stadio Olimpico Grande Torino"],
        "wiki_pages": ["Stadio Olimpico Grande Torino", "Torino FC"]
    },
    "Udinese": {
        "tsdb": ["Udinese"],
        "commons_cats": ["Category:Udinese Calcio", "Category:Stadio Friuli"],
        "wiki_pages": ["Stadio Friuli", "Udinese Calcio"]
    },
    "Genoa": {
        "tsdb": ["Genoa"],
        "commons_cats": ["Category:Genoa CFC", "Category:Stadio Luigi Ferraris"],
        "wiki_pages": ["Stadio Luigi Ferraris", "Genoa CFC"]
    },
    "Como": {
        "tsdb": ["Como"],
        "commons_cats": ["Category:Como 1907", "Category:Stadio Giuseppe Sinigaglia"],
        "wiki_pages": ["Stadio Giuseppe Sinigaglia", "Como 1907"]
    },
    "Parma": {
        "tsdb": ["Parma"],
        "commons_cats": ["Category:Parma Calcio 1913", "Category:Stadio Ennio Tardini"],
        "wiki_pages": ["Stadio Ennio Tardini", "Parma Calcio 1913"]
    },
    "Verona": {
        "tsdb": ["Hellas Verona", "Verona"],
        "commons_cats": ["Category:Hellas Verona FC", "Category:Stadio Marcantonio Bentegodi"],
        "wiki_pages": ["Stadio Marcantonio Bentegodi", "Hellas Verona FC"]
    },
    "Empoli": {
        "tsdb": ["Empoli"],
        "commons_cats": ["Category:Empoli FC", "Category:Stadio Carlo Castellani"],
        "wiki_pages": ["Stadio Carlo Castellani", "Empoli FC"]
    },
    "Lecce": {
        "tsdb": ["Lecce"],
        "commons_cats": ["Category:US Lecce", "Category:Stadio Via del Mare"],
        "wiki_pages": ["Stadio Via del Mare", "US Lecce"]
    },
    "Cagliari": {
        "tsdb": ["Cagliari"],
        "commons_cats": ["Category:Cagliari Calcio", "Category:Unipol Domus"],
        "wiki_pages": ["Unipol Domus", "Cagliari Calcio"]
    },
    "Venezia": {
        "tsdb": ["Venezia"],
        "commons_cats": ["Category:Venezia FC", "Category:Stadio Pier Luigi Penzo"],
        "wiki_pages": ["Stadio Pier Luigi Penzo", "Venezia FC"]
    },
    "Monza": {
        "tsdb": ["Monza"],
        "commons_cats": ["Category:AC Monza", "Category:Stadio Brianteo"],
        "wiki_pages": ["Stadio Brianteo", "AC Monza"]
    },
    "Real Madrid": {
        "tsdb": ["Real Madrid"],
        "commons_cats": ["Category:Real Madrid CF", "Category:Santiago Bernabéu Stadium"],
        "wiki_pages": ["Santiago Bernabéu", "Real Madrid CF"]
    },
    "Barcellona": {
        "tsdb": ["Barcelona"],
        "commons_cats": ["Category:FC Barcelona", "Category:Camp Nou"],
        "wiki_pages": ["Camp Nou", "FC Barcelona"]
    },
    "Arsenal": {
        "tsdb": ["Arsenal"],
        "commons_cats": ["Category:Arsenal F.C.", "Category:Emirates Stadium"],
        "wiki_pages": ["Emirates Stadium", "Arsenal F.C."]
    },
    "Manchester City": {
        "tsdb": ["Manchester City"],
        "commons_cats": ["Category:Manchester City F.C.", "Category:City of Manchester Stadium"],
        "wiki_pages": ["City of Manchester Stadium", "Manchester City F.C."]
    },
    "Manchester United": {
        "tsdb": ["Manchester United"],
        "commons_cats": ["Category:Manchester United F.C.", "Category:Old Trafford"],
        "wiki_pages": ["Old Trafford", "Manchester United F.C."]
    },
    "Liverpool": {
        "tsdb": ["Liverpool"],
        "commons_cats": ["Category:Liverpool F.C.", "Category:Anfield"],
        "wiki_pages": ["Anfield", "Liverpool F.C."]
    },
    "Chelsea": {
        "tsdb": ["Chelsea"],
        "commons_cats": ["Category:Chelsea F.C.", "Category:Stamford Bridge"],
        "wiki_pages": ["Stamford Bridge", "Chelsea F.C."]
    },
    "Bayern Monaco": {
        "tsdb": ["Bayern Munich"],
        "commons_cats": ["Category:FC Bayern München", "Category:Allianz Arena"],
        "wiki_pages": ["Allianz Arena", "FC Bayern Munich"]
    },
    "Dortmund": {
        "tsdb": ["Borussia Dortmund"],
        "commons_cats": ["Category:Borussia Dortmund", "Category:Signal Iduna Park"],
        "wiki_pages": ["Westfalenstadion", "Borussia Dortmund"]
    },
    "PSG": {
        "tsdb": ["Paris SG"],
        "commons_cats": ["Category:Paris Saint-Germain F.C.", "Category:Parc des Princes"],
        "wiki_pages": ["Parc des Princes", "Paris Saint-Germain F.C."]
    }
}


def immagine_valida_non_ritratto(url, width, height):
    if not url:
        return False
    low = url.lower()
    if any(b in low for b in (".svg", ".gif", "logo", "crest", "badge", "coat_of_arms", "map", "diagram", "signature", "icon")):
        return False
    # Richiede formato orizzontale (così sono sempre foto di campo/partita/maglie/stadio e mai fototessere di vecchi giocatori)
    if width and height and width < height:
        return False
    if width and width < 700:
        return False
    return any(low.endswith(ext) for ext in (".jpg", ".jpeg", ".png"))


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


def cerca_foto_reali_club(nome_squadra, foto_gia_usate=None):
    """
    Cerca ESCLUSIVAMENTE foto reali appartenenti alla squadra del post:
    1. TheSportsDB con tutte le varianti del nome club
    2. Categorie Ufficiali Wikimedia Commons della squadra (es. Category:AC Milan, Category:FC Internazionale Milano)
    3. Voci Wikipedia dello Stadio e del Club (it.wikipedia e en.wikipedia)
    4. Ricerca libera Wikimedia per nome squadra
    """
    if foto_gia_usate is None:
        foto_gia_usate = []

    headers = {"User-Agent": "SBRLabEditorialBot/5.0"}
    cfg = CLUB_MEDIA_MAP.get(nome_squadra, {
        "tsdb": [nome_squadra],
        "commons_cats": [f"Category:{nome_squadra}"],
        "wiki_pages": [nome_squadra]
    })

    pool_foto = []
    logo_url = cerca_logo_espn(nome_squadra)

    # 1. TheSportsDB (tutte le varianti del nome)
    for q_tsdb in cfg["tsdb"]:
        try:
            r = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={requests.utils.quote(q_tsdb)}", headers=headers, timeout=6)
            if r.status_code == 200 and r.json().get("teams"):
                for tm in r.json()["teams"]:
                    if "soccer" in str(tm.get("strSport", "")).lower():
                        if not logo_url:
                            logo_url = tm.get("strBadge") or tm.get("strLogo")
                        for campo in ("strFanart1", "strFanart2", "strFanart3", "strFanart4", "strStadiumThumb"):
                            if tm.get(campo):
                                pool_foto.append(tm[campo])
                        break
        except Exception:
            continue

    # 2. Categorie Ufficiali Wikimedia Commons del Club (es. Category:AC Milan)
    for cat in cfg["commons_cats"]:
        try:
            url_cat = (
                "https://commons.wikimedia.org/w/api.php?action=query&generator=categorymembers"
                f"&gcmtitle={requests.utils.quote(cat)}&gcmtype=file&gcmlimit=15"
                "&prop=imageinfo&iiprop=url|dimensions&iiurlwidth=1280&format=json"
            )
            rc = requests.get(url_cat, headers=headers, timeout=6)
            if rc.status_code == 200:
                pages = rc.json().get("query", {}).get("pages", {})
                for pg in pages.values():
                    ii = (pg.get("imageinfo") or [{}])[0]
                    u = ii.get("thumburl") or ii.get("url", "")
                    w = ii.get("width", 0)
                    h = ii.get("height", 0)
                    if immagine_valida_non_ritratto(u, w, h):
                        pool_foto.append(u)
        except Exception:
            continue

    # 3. Voci Wikipedia Ufficiali del Club e dello Stadio (es. San Siro, Stadio Olimpico, Derby)
    for pagina in cfg["wiki_pages"]:
        for lang in ("it", "en"):
            try:
                url_wp = (
                    f"https://{lang}.wikipedia.org/w/api.php?action=query"
                    f"&titles={requests.utils.quote(pagina)}"
                    "&prop=pageimages&pithumbsize=1280&format=json&redirects=1"
                )
                rw = requests.get(url_wp, headers=headers, timeout=5)
                if rw.status_code == 200:
                    pages = rw.json().get("query", {}).get("pages", {})
                    for pg in pages.values():
                        src = pg.get("thumbnail", {}).get("source", "")
                        w = pg.get("thumbnail", {}).get("width", 1200)
                        h = pg.get("thumbnail", {}).get("height", 800)
                        if immagine_valida_non_ritratto(src, w, h):
                            pool_foto.append(src)
            except Exception:
                continue

    # 4. Ricerca diretta su Wikimedia Commons col nome della squadra
    if not pool_foto:
        try:
            url_s = (
                "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={requests.utils.quote(nome_squadra + ' football')}&gsrnamespace=6&gsrlimit=12"
                "&prop=imageinfo&iiprop=url|dimensions&iiurlwidth=1280&format=json"
            )
            rs = requests.get(url_s, headers=headers, timeout=6)
            if rs.status_code == 200:
                pages = rs.json().get("query", {}).get("pages", {})
                for pg in pages.values():
                    ii = (pg.get("imageinfo") or [{}])[0]
                    u = ii.get("thumburl") or ii.get("url", "")
                    w = ii.get("width", 0)
                    h = ii.get("height", 0)
                    if immagine_valida_non_ritratto(u, w, h):
                        pool_foto.append(u)
        except Exception:
            pass

    fresche = [f for f in pool_foto if f not in foto_gia_usate]
    if fresche:
        return fresche[0], logo_url
    if pool_foto:
        return random.choice(pool_foto), logo_url

    return None, logo_url


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
    modello = dati_contesto.get("modello", "BETA").upper()
    match = dati_contesto.get("match", "il big match")
    focus = dati_contesto.get("focus", "Analisi Tattica")

    hashtag_pool = [
        "#SBRLab #SerieA #Calcio #AnalisiTattica #StatisticheCalcio",
        "#SBRLab #SportAnalytics #NumeriDelCalcio #TatticaCalcistica #SerieATim",
        "#SBRLab #CalcioItaliano #ModelliMatematici #MatchAnalysis #DataScience"
    ]

    cta_pool = [
        "📲 L'analisi completa è nel canale Telegram GRATUITO (Link in Bio).",
        "🔓 Entra GRATIS nel club su Telegram dal Link in Bio prima del fischio d'inizio.",
        "👉 Passa dal Link in Bio: Alpha, Beta e Tennis sono gratuiti sul nostro Telegram."
    ]

    if tipo_post == "PRE_MATCH":
        if modello == "ALPHA":
            titoli = [
                "FAVORITA BLINDATA.", "RITMO DA ASSEDIO.",
                "NUMERI A SENSO UNICO.", "SCUDO SULLA GARA.",
                "DIVARIO NETTO.", "ZERO SPAZIO AL CASO.",
                "FATTORE CAMPO DECISIVO.", "DOMINIO TERRITORIALE."
            ]
            sottotitoli = [
                f"Forma, tiri e tenuta difensiva: in {match} i parametri pendono da una sola parte.",
                f"Il Modello Alpha incrocia i flussi offensivi di {match} e attiva la copertura.",
                f"Niente tifo, solo freddezza: ecco cosa dicono gli algoritmi sui 90 minuti di {match}."
            ]
            aperture_caption = [
                f"⚽ Il tifoso guarda il nome sulla maglia, i nostri modelli guardano cosa succede davvero nei 90 minuti.\n\nOggi il radar del Modello ALPHA punta dritto su {match} (segnale: {focus}).",
                f"🚀 C'è chi si affida all'istinto dell'ultimo minuto e chi studia le anomalie di rendimento.\n\nSu {match} il motore ALPHA ha isolato uno scenario ad altissima tenuta tattica: {focus}."
            ]
        else:
            titoli = [
                "FASCE IN FIAMME.", "AREA SOTTO ASSEDIO.",
                "PARTITA AD ALTA TENSIONE.", "PIOGGIA DI DUELLI.",
                "NERVI A FIOR DI PELLE.", "SPINTA FINO AL 90°.",
                "RITMO FUORI SCALA.", "ANOMALIA POISSON."
            ]
            sottotitoli = [
                f"Lo storico reale degli ultimi match accende {match}: volume di gioco altissimo.",
                f"Non guardiamo chi vince, ma come attacca: {match} promette scintille sulle corsie.",
                f"La curva di Poisson intercetta un valore netto su {match} incrociando le medie ESPN."
            ]
            aperture_caption = [
                f"🔥 Alcune partite si leggono molto prima del risultato finale: basta osservare l'ampiezza sulle fasce e l'intensità dei contrasti.\n\nPer {match} il Modello BETA segnala un valore netto su: {focus}.",
                f"⚡ Mentre tutti cercano d'indovinare il marcatore, la distribuzione di Poisson analizza il volume reale di gioco.\n\nI dati storici di {match} accendono il semaforo verde del Modello BETA ({focus})."
            ]

        titolo_scelto = scegli_senza_ripetere(titoli, usati_recenti)
        return {
            "titolo_grafica": titolo_scelto,
            "testo_grafica": random.choice(sottotitoli),
            "caption_instagram": f"{random.choice(aperture_caption)}\n\n{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        }

    elif tipo_post == "RISULTATI":
        winrate = dati_contesto.get("winrate", "--%")
        chiuse = dati_contesto.get("chiuse", 0)
        titoli_res = [
            "IL CAMPO PARLA<span>.</span>",
            "NUMERI REALI<span>.</span>",
            "ZERO SCUSE<span>.</span>",
            "STORICO PURO<span>.</span>"
        ]
        titolo_scelto = scegli_senza_ripetere(titoli_res, usati_recenti)
        caption = (
            f"📊 Niente promesse da bar: in SBR Lab ogni singola operazione viene registrata e certificata a database.\n\n"
            f"Con {chiuse} analisi concluse e un Win Rate del {winrate}, continuiamo a lavorare alla luce del sole.\n\n"
            f"{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        )
        return {"titolo_grafica": titolo_scelto, "testo_grafica": "", "caption_instagram": caption}

    else:
        titoli_omega = [
            "10.000 PARTITE IN UNA.",
            "DENTRO IL MOTORE OMEGA.",
            "LA LEGGE DI MONTE CARLO.",
            "DOVE NASCE IL VALORE."
        ]
        testi_omega = [
            "Prima del fischio d'inizio, Omega simula l'incontro diecimila volte pesando attacco, difesa e fatica per isolare la probabilità reale.",
            "Omega nasce con un freno automatico: se il vantaggio matematico scende sotto soglia, il sistema blocca l'operazione.",
            "Mentre Alpha, Beta e Sigma lavorano gratis ogni giorno su Telegram, in laboratorio stiamo ultimando la calibrazione di Omega."
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
                    if "serie_a" in lega or casa in CLUB_MEDIA_MAP or trasf in CLUB_MEDIA_MAP:
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

    return "beta", "Inter", "Milan", "Over 8.5 Calci d'Angolo"


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
    testo_admin = f"🎨 *ANTEPRIMA POST ({tipo_format})*\n\n📝 *Caption proposta:*\n\n{caption_ig}"
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
    return {"ultimi_titoli_usati": [], "ultimi_match_usati": [], "ultime_foto_usate": [], "indice_rotazione": 0}


def fase_1_genera_proposta(forza_tipo=None):
    db = {"schedine": []}
    if os.path.exists("database.json"):
        with open("database.json", "r", encoding="utf-8") as f:
            db = json.load(f)

    stato_prec = carica_stato_precedente()
    usati_titoli = stato_prec.get("ultimi_titoli_usati", [])[-10:]
    usati_match = stato_prec.get("ultimi_match_usati", [])[-8:]
    usate_foto = stato_prec.get("ultime_foto_usate", [])[-10:]
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
        copy_scelto = genera_copy_catchy("RISULTATI", {"winrate": winrate, "chiuse": len(concluse)}, usati_titoli)
        renderizza_html_in_png("templates_social/template_risultati.html", {
            "PERIODO": f"REPORT AL {oggi_str}",
            "TITOLO_RISULTATI": copy_scelto["titolo_grafica"],
            "TOTALE_CHIUSE": len(concluse),
            "WINRATE": winrate,
            "RIGHE_OPERAZIONI": righe_html or "<div class='row'><span>Storico in aggiornamento</span></div>"
        }, IMAGE_FILE)

    elif tipo_post == "OMEGA":
        copy_scelto = genera_copy_catchy("OMEGA", {}, usati_titoli)
        renderizza_html_in_png("templates_social/template_omega.html", {
            "TITOLO_OMEGA": copy_scelto["titolo_grafica"],
            "TESTO_OMEGA": copy_scelto["testo_grafica"]
        }, IMAGE_FILE)

    else:
        mod_key, sq_casa, sq_trasf, mercato = scegli_match_calcio_serie_a_prioritario(schedine, usati_match)
        stile = STILE_BOT.get(mod_key, STILE_BOT["beta"])

        foto_casa, logo_casa = cerca_foto_reali_club(sq_casa, foto_gia_usate=usate_foto)
        foto_trasf, logo_trasf = cerca_foto_reali_club(sq_trasf, foto_gia_usate=usate_foto)

        foto_scelta = foto_casa or foto_trasf

        # Se trova la foto reale della squadra la usa; se è una squadra minore senza foto, mostra gli stemmi giganti delle 2 squadre!
        if foto_scelta:
            hero_html = f"<img class='bg' src='{foto_scelta}' alt='Match Action'>"
            usate_foto.append(foto_scelta)
        else:
            l1 = f"<img src='{logo_casa}' alt=''>" if logo_casa else ""
            l2 = f"<img src='{logo_trasf}' alt=''>" if logo_trasf else ""
            hero_html = f"<div class='club-split-hero'>{l1}{l2}</div>"

        logo_c_html = f"<img class='team-logo' src='{logo_casa}' alt=''>" if logo_casa else ""
        logo_t_html = f"<img class='team-logo' src='{logo_trasf}' alt=''>" if logo_trasf else ""
        match_nome = f"{sq_casa} - {sq_trasf}"

        copy_scelto = genera_copy_catchy("PRE_MATCH", {"modello": mod_key.upper(), "match": match_nome, "focus": mercato}, usati_titoli)
        renderizza_html_in_png("templates_social/template_analisi.html", {
            "HERO_VISUAL_HTML": hero_html,
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
        usati_match.append(match_nome)

    usati_titoli.append(copy_scelto["titolo_grafica"])

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "status": "WAITING_APPROVAL",
            "caption": copy_scelto["caption_instagram"],
            "created_at": oggi_str,
            "ultimi_titoli_usati": usati_titoli[-10:],
            "ultimi_match_usati": usati_match[-8:],
            "ultime_foto_usate": usate_foto[-10:],
            "indice_rotazione": idx_rot + 1
        }, f, ensure_ascii=False, indent=2)

    invia_anteprima_su_telegram(IMAGE_FILE, copy_scelto["caption_instagram"], tipo_post)
    print(f"Post {tipo_post} generato e inviato su Telegram!")


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
                      json={"chat_id": ADMIN_CHAT_ID, "text": "🗑️ Bozza scartata. Rilancia il workflow per passare al formato/match successivo!"})


if __name__ == "__main__":
    modalita = sys.argv[1] if len(sys.argv) > 1 else "genera"
    forza = sys.argv[2].upper() if len(sys.argv) > 2 else None
    if modalita == "genera":
        fase_1_genera_proposta(forza_tipo=forza)
    elif modalita == "pubblica":
        fase_2_controlla_ok_e_pubblica()
