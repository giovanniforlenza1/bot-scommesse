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
    "alpha": {"colore": "#F87060", "etichetta": "MODELLO ALPHA • MULTIPLA PROTETTA"},
    "beta":  {"colore": "#B3A394", "etichetta": "MODELLO BETA • POISSON"},
    "sigma": {"colore": "#2D6A4F", "etichetta": "MODELLO SIGMA • TENNIS LAB"},
    "omega": {"colore": "#102542", "etichetta": "MODELLO OMEGA • QUANTITATIVO"}
}

# Foto sportive editoriali HD di backup (calcio/tennis) se una squadra minore non ha fanart
FOTO_FALLBACK_CALCIO = [
    "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518091043644-c1d4457512c6?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?q=85&w=1200&auto=format&fit=crop"
]

FOTO_FALLBACK_TENNIS = [
    "https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?q=85&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1554068865-24cecd4e34b8?q=85&w=1200&auto=format&fit=crop"
]

MAPPA_RICERCA_CLUB = {
    "Inter": "Inter Milan", "Milan": "AC Milan", "Juventus": "Juventus", "Napoli": "Napoli",
    "Roma": "AS Roma", "Lazio": "Lazio", "Atalanta": "Atalanta", "Fiorentina": "Fiorentina",
    "Bologna": "Bologna", "Torino": "Torino", "PSG": "Paris SG", "Bayern Monaco": "Bayern Munich",
    "Dortmund": "Borussia Dortmund", "Lipsia": "RB Leipzig", "Francoforte": "Eintracht Frankfurt",
    "Sporting Lisbona": "Sporting CP", "Betis Siviglia": "Real Betis", "Athletic Bilbao": "Athletic Bilbao"
}


def cerca_media_squadra_o_giocatore(nome_squadra, is_tennis=False):
    """Restituisce (foto_azione_hd, logo_png) cercando giocatori e club su TheSportsDB e Wikimedia."""
    headers = {"User-Agent": "SBRLabSocialBot/1.0"}
    query_nome = MAPPA_RICERCA_CLUB.get(nome_squadra, nome_squadra)
    foto_hd = None
    logo_url = None

    try:
        if is_tennis:
            # Cerca foto in azione del tennista su TheSportsDB
            r = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchplayers.php?p={query_nome}", headers=headers, timeout=8)
            if r.status_code == 200 and r.json().get("player"):
                for pl in r.json()["player"]:
                    if "tennis" in str(pl.get("strSport", "")).lower():
                        cand_foto = [pl.get("strFanart1"), pl.get("strFanart2"), pl.get("strFanart3"), pl.get("strThumb")]
                        valide = [x for x in cand_foto if x]
                        if valide:
                            foto_hd = random.choice(valide)
                            break
        else:
            # 1. Cerca squadra su TheSportsDB (logo ufficiale + fanart partita HD)
            r = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={query_nome}", headers=headers, timeout=8)
            if r.status_code == 200 and r.json().get("teams"):
                for tm in r.json()["teams"]:
                    if "soccer" in str(tm.get("strSport", "")).lower():
                        logo_url = tm.get("strBadge") or tm.get("strLogo")
                        id_team = tm.get("idTeam")

                        # Cerca prima le foto d'azione dei giocatori chiave della squadra!
                        foto_giocatori = []
                        if id_team:
                            rp = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/lookup_all_players.php?id={id_team}", headers=headers, timeout=8)
                            if rp.status_code == 200 and rp.json().get("player"):
                                for pl in rp.json()["player"]:
                                    for campo in ("strFanart1", "strFanart2", "strFanart3"):
                                        if pl.get(campo):
                                            foto_giocatori.append(pl[campo])

                        fanart_club = [tm.get("strFanart1"), tm.get("strFanart2"), tm.get("strFanart3"), tm.get("strFanart4")]
                        pool_foto = foto_giocatori + [x for x in fanart_club if x]
                        if pool_foto:
                            foto_hd = random.choice(pool_foto)
                        break

        # 2. Fallback Wikimedia Commons in alta risoluzione se TheSportsDB non aveva fanart
        if not foto_hd:
            q_wiki = f"{query_nome} {'tennis' if is_tennis else 'football match'}"
            w_url = (
                "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={requests.utils.quote(q_wiki)}&gsrnamespace=6&gsrlimit=6"
                "&prop=imageinfo&iiprop=url|dimensions&format=json"
            )
            rw = requests.get(w_url, headers=headers, timeout=8)
            if rw.status_code == 200:
                pages = rw.json().get("query", {}).get("pages", {})
                foto_wiki = []
                for pg in pages.values():
                    ii = (pg.get("imageinfo") or [{}])[0]
                    u = ii.get("url", "")
                    w = ii.get("width", 0)
                    h = ii.get("height", 0)
                    if w >= 900 and w > h and any(u.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
                        foto_wiki.append(u)
                if foto_wiki:
                    foto_hd = random.choice(foto_wiki)
    except Exception as e:
        print(f"[MEDIA WARN] Ricerca foto per {nome_squadra}: {e}")

    if not foto_hd:
        foto_hd = random.choice(FOTO_FALLBACK_TENNIS if is_tennis else FOTO_FALLBACK_CALCIO)

    return foto_hd, logo_url


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


def scegli_senza_ripetere(lista_opzioni, usati_recenti):
    disponibili = [x for x in lista_opzioni if x not in usati_recenti]
    return random.choice(disponibili if disponibili else lista_opzioni)


def genera_copy_dinamico_ricco(tipo_post, dati_contesto, usati_recenti):
    modello = dati_contesto.get("modello", "BETA").upper()
    match = dati_contesto.get("match", "il big match in programma")
    focus = dati_contesto.get("focus", "lettura tattica")

    hashtag_pool = [
        "#SBRLab #AnalisiSportiva #DataScience #CalcioTattico #StatisticheCalcio",
        "#SBRLab #SportAnalytics #NumeriDelCalcio #TatticaCalcistica #MatchAnalysis",
        "#SBRLab #CalcioNumeri #ModelliMatematici #AnalisiTattica #SportData",
        "#SBRLab #FootballAnalytics #AlgoritmiSportivi #LetturaDelMatch #DatiSportivi",
        "#SBRLab #InsiderSportivo #StatisticaApplicata #StudioDelMatch #SportScience"
    ]

    cta_pool = [
        "📲 Trovi la lettura integrale nel nostro canale Telegram gratuito (Link in Bio).",
        "🔓 L'analisi completa di Alpha, Beta e Tennis è già dentro il canale Telegram gratis: Link in Bio.",
        "👉 Entra gratis nel club su Telegram dal Link in Bio per leggere tutti i report del giorno.",
        "📲 Unisciti gratuitamente al canale Telegram (Link in Bio) prima del fischio d'inizio.",
        "🔓 Tutti i segnali giornalieri di Alpha, Beta e Sigma escono gratis su Telegram. Link in Bio."
    ]

    if tipo_post == "PRE_MATCH":
        if modello == "ALPHA":
            titoli = [
                "Scudo tattico sulla gara.", "Dove il pareggio non fa male.",
                "Costruire valore senza azzardo.", "Equilibrio rotto dai numeri.",
                "La geometria della continuità.", "Proteggere il ritmo partita.",
                "Quando la favorita ha il vento.", "Oltre la semplice sensazione.",
                "Il peso del fattore campo.", "Incrocio ad alta tenuta."
            ]
            testi_grafica = [
                f"In {match} il ritmo offensivo spinge in una direzione chiara: Alpha attiva lo scudo statistico per assorbire gli imprevisti.",
                f"Il tifoso guarda il nome sulla maglia, i dati leggono la tenuta nei 90 minuti. Su {match} la struttura regge l'urto.",
                f"Niente salti nel buio su {match}: forma recente e solidità difensiva isolano uno scenario ad alta affidabilità.",
                f"Su {match} il divario di produzione offensiva è netto. Alpha seleziona la rotta più protetta evitando trappole emotive.",
                f"Le partite sporche si leggono prima del calcio d'inizio: {match} supera tutti i filtri di sicurezza del motore Alpha."
            ]
            aperture_caption = [
                f"⚽ C'è una bella differenza tra sperare in un risultato e preparare ogni scenario prima del fischio d'inizio.\n\nOggi i riflettori del Modello ALPHA si accendono su {match}.",
                f"🔍 Quante volte una partita dominata cambia volto per un episodio all'85°?\n\nÈ proprio per questo che su {match} il nostro Modello ALPHA lavora di copertura strutturale ({focus}).",
                f"🏟️ Il fascino del campo incontra la disciplina dei numeri.\n\nAnalizzando i flussi e i ritmi di {match}, l'algoritmo ALPHA ha isolato una direzione precisa: {focus}."
            ]
        elif modello == "BETA":
            titoli = [
                "Stasera le fasce bruciano.", "Partita ad altissima tensione.",
                "Quando l'area diventa assedio.", "Scintille in mezzo al campo.",
                "Il peso dei duelli individuali.", "Pressione costante fino al 90°.",
                "Quello che il tabellino non dice.", "Nervi tesi e spazi stretti.",
                "L'onda lunga sulle corsie.", "La matematica dei piazzati."
            ]
            testi_grafica = [
                f"Lo storico reale degli ultimi giorni parla chiaro: in {match} il volume di spinta sulle fasce accende la curva di Poisson.",
                f"Chi guarda solo il tabellino perde metà dello spettacolo. In {match} il vero squilibrio nasce su ritmi, corner e contrasti.",
                f"Due squadre che non sanno speculare: incrociando le medie reali di {match}, il Modello Beta intercetta una pressione fuori scala.",
                f"Cross dal fondo, ribattute e difesa bassa: la conformazione tattica di {match} disegna il terreno perfetto per il motore Beta.",
                f"Quando i duelli a centrocampo salgono di giri, i numeri anticipano la cronaca. Occhi puntati su {match}."
            ]
            aperture_caption = [
                f"🔥 Alcune partite si decidono sui gol, altre si leggono molto prima osservando le fasce laterali e il nervosismo nei contrasti.\n\nPer {match} il Modello BETA ha incrociato lo storico reale delle due squadre.",
                f"📐 La bellezza della distribuzione di Poisson applicata al calcio vero.\n\nSu {match} non guardiamo chi alzerà le braccia al 90°, ma il volume di gioco che genereranno in campo: focus su {focus}.",
                f"⚡ Baricentro alto, esterni che puntano l'uomo e falli tattici per fermare le ripartenze.\n\nI dati di {match} hanno fatto scattare il semaforo verde del Modello BETA su {focus}."
            ]
        else:
            titoli = [
                "Nel tennis non esiste pareggio.", "Questione di superficie e ritmo.",
                "Servizio, risposta e nervi saldi.", "Geometrie da fondo campo.",
                "Chi comanda davvero lo scambio?", "Velocità di palla e percentuali.",
                "Il peso delle palle break.", "Uno contro uno, zero alibi."
            ]
            testi_grafica = [
                f"Nessun compagno dietro cui nascondersi: in {match} la resa sulla superficie e la tenuta al servizio tracciano un solco netto.",
                f"Il Laboratorio Sigma ha scandagliato il circuito: su {match} i ritmi di scambio premiano una direzione statistica limpida.",
                f"Tra prime in campo e punti in risposta, {match} mette di fronte due curve di rendimento che viaggiano a velocità opposte.",
                f"Angoli stretti, profondità di palla e gestione della pressione: {match} supera i filtri quantitativi del laboratorio Tennis."
            ]
            aperture_caption = [
                f"🎾 Niente melina, niente pareggio: solo due giocatori e la verità dei numeri punto dopo punto.\n\nOggi il Modello SIGMA entra in campo su {match} ({focus}).",
                f"🔬 Superficie, velocità delle condizioni e rendimento nei turni di battuta.\n\nIl nostro laboratorio Tennis ha passato al setaccio il tabellone isolando {match}."
            ]

        titolo_scelto = scegli_senza_ripetere(titoli, usati_recenti).strip()
        testo_scelto = random.choice(testi_grafica)
        caption = f"{random.choice(aperture_caption)}\n\n{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        return {"titolo_grafica": titolo_scelto, "testo_grafica": testo_scelto, "caption_instagram": caption}

    elif tipo_post == "RISULTATI":
        winrate = dati_contesto.get("winrate", "--%")
        chiuse = dati_contesto.get("chiuse", 0)
        titoli_res = [
            "Il verdetto del campo.", "I numeri restano sempre.",
            "Trasparenza prima di tutto.", "Zero scuse, parla lo storico.",
            "La disciplina paga nel tempo.", "Contano solo i fatti chiusi."
        ]
        aperture_res = [
            f"📊 Sul web sono tutti fenomeni il lunedì mattina cancellando quello che va storto. Noi registriamo ogni singola operazione a database.\n\nCon {chiuse} analisi archiviate e un Win Rate del {winrate}, il percorso di SBR Lab continua alla luce del sole.",
            f"✓ Prese e stop, tutto certificato nero su bianco.\n\nLa differenza tra metodo ed emozione del momento sta tutta sul lungo periodo ({chiuse} operazioni concluse, {winrate} di precisione)."
        ]
        titolo_scelto = scegli_senza_ripetere(titoli_res, usati_recenti)
        caption = f"{random.choice(aperture_res)}\n\n{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        return {"titolo_grafica": titolo_scelto, "testo_grafica": "", "caption_instagram": caption}

    else:
        titoli_omega = [
            "Giocare il match 10.000 volte.", "Cosa vede davvero Omega?",
            "Quando NON entrare vale oro.", "Dietro la porta del laboratorio.",
            "La calma fredda di Monte Carlo.", "Perché Omega è ancora chiuso."
        ]
        testi_omega = [
            "Prima del fischio d'inizio, il motore Omega simula l'incontro diecimila volte pesando attacco, difesa, fatica e calendario per isolare la probabilità pura.",
            "Omega nasce con un freno automatico: se il vantaggio matematico reale scende sotto soglia, il sistema blocca tutto. Apriremo solo a calibrazione ultimata.",
            "Mentre Alpha, Beta e Sigma lavorano gratis ogni giorno, in background Omega macina dati europei per costruire il nostro nucleo quantitativo di punta."
        ]
        aperture_omega = [
            "🧪 Cosa succederebbe se potessi far rigiocare la stessa partita 10.000 volte prima che le squadre scendano in campo?\n\nÈ esattamente ciò che sta facendo il Modello OMEGA in fase di test privato.",
            "🔒 Perché OMEGA non è ancora aperto al pubblico? Perché stiamo calibrando il motore Monte Carlo affinché intervenga solo davanti a un vantaggio statistico chirurgico."
        ]
        titolo_scelto = scegli_senza_ripetere(titoli_omega, usati_recenti)
        testo_scelto = random.choice(testi_omega)
        caption = f"{random.choice(aperture_omega)}\n\n{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        return {"titolo_grafica": titolo_scelto, "testo_grafica": testo_scelto, "caption_instagram": caption}


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


def trova_ultimo_match_valido(schedine):
    fuso_italia = ZoneInfo("Europe/Rome")
    giorno_sett = datetime.now(fuso_italia).weekday()

    if os.path.exists("tennis_test.json") and (giorno_sett == 2 or random.random() < 0.25):
        try:
            with open("tennis_test.json", "r", encoding="utf-8") as ft:
                t_db = json.load(ft)
            lista_t = t_db.get("schedine", []) if isinstance(t_db, dict) else t_db
            if lista_t:
                ult = lista_t[-1]
                p = ult.get("partite", [ult])[0]
                g1 = p.get("squadra_casa", p.get("giocatore_1", ""))
                g2 = p.get("squadra_trasferta", p.get("giocatore_2", ""))
                if g1 and g2 and "🔒" not in g1:
                    return "sigma", g1, g2, p.get("pronostico", "Vantaggio Superficie")
        except Exception:
            pass

    for s in reversed(schedine):
        mod = s.get("modello", "").lower()
        if mod in ("alpha", "beta", "sigma"):
            partite_vere = decripta_payload_se_presente(s)
            if partite_vere:
                p0 = partite_vere[0]
                casa = p0.get("squadra_casa", "")
                trasf = p0.get("squadra_trasferta", "")
                if casa and trasf and "🔒" not in casa:
                    return mod, casa, trasf, p0.get("pronostico", "Analisi Tattica")

    return "beta", "Inter", "Arsenal", "Over 8.5 Calci d'Angolo"


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
    return {"ultimi_titoli_usati": []}


def fase_1_genera_proposta():
    db = {"schedine": []}
    if os.path.exists("database.json"):
        with open("database.json", "r", encoding="utf-8") as f:
            db = json.load(f)

    stato_prec = carica_stato_precedente()
    usati_recenti = stato_prec.get("ultimi_titoli_usati", [])[-10:]

    schedine = db.get("schedine", [])
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi_str = datetime.now(fuso_italia).strftime("%d/%m/%Y")
    giorno = datetime.now(fuso_italia).weekday()

    # Lunedì: Tinta Piatta Risultati | Venerdì: Tinta Piatta Omega | Altri giorni: Foto HD Giocatori/Squadra!
    if giorno == 0 and schedine:
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
            badge = "<span class='esito-vinto'>✓ Presa</span>" if is_win else "<span class='esito-perso'>✕ Saltata</span>"
            righe_html += (
                f"<div class='row'>"
                f"<div><span class='mod-pill'>{mod_label}</span>{p0['squadra_casa']} - {p0['squadra_trasferta']}</div>"
                f"{badge}</div>"
            )
        copy_scelto = genera_copy_dinamico_ricco("RISULTATI", {"winrate": winrate, "chiuse": len(concluse)}, usati_recenti)
        renderizza_html_in_png("templates_social/template_risultati.html", {
            "PERIODO": f"AGGIORNATO AL {oggi_str}",
            "TOTALE_CHIUSE": len(concluse),
            "WINRATE": winrate,
            "RIGHE_OPERAZIONI": righe_html or "<div class='row'><span>Storico in aggiornamento</span></div>"
        }, IMAGE_FILE)

    elif giorno == 4:
        copy_scelto = genera_copy_dinamico_ricco("OMEGA", {}, usati_recenti)
        renderizza_html_in_png("templates_social/template_omega.html", {
            "TITOLO_OMEGA": copy_scelto["titolo_grafica"],
            "TESTO_OMEGA": copy_scelto["testo_grafica"]
        }, IMAGE_FILE)

    else:
        mod_key, sq_casa, sq_trasf, mercato = trova_ultimo_match_valido(schedine)
        is_tennis = (mod_key == "sigma")
        stile = STILE_BOT.get(mod_key, STILE_BOT["beta"])

        # Cerca automaticamente foto d'azione HD dei giocatori/club + loghi ufficiali
        foto_casa, logo_casa = cerca_media_squadra_o_giocatore(sq_casa, is_tennis=is_tennis)
        foto_trasf, logo_trasf = cerca_media_squadra_o_giocatore(sq_trasf, is_tennis=is_tennis)

        # Se la squadra di casa ha solo il fallback generico e quella ospite ha una foto vera, usa l'ospite!
        foto_scelta = foto_casa
        if foto_casa in (FOTO_FALLBACK_CALCIO + FOTO_FALLBACK_TENNIS) and foto_trasf not in (FOTO_FALLBACK_CALCIO + FOTO_FALLBACK_TENNIS):
            foto_scelta = foto_trasf

        logo_c_html = f"<img class='team-logo' src='{logo_casa}' alt=''>" if logo_casa else ""
        logo_t_html = f"<img class='team-logo' src='{logo_trasf}' alt=''>" if logo_trasf else ""
        match_nome = f"{sq_casa} - {sq_trasf}"

        copy_scelto = genera_copy_dinamico_ricco("PRE_MATCH", {"modello": mod_key.upper(), "match": match_nome, "focus": mercato}, usati_recenti)
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

    usati_recenti.append(copy_scelto["titolo_grafica"])
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "status": "WAITING_APPROVAL",
            "caption": copy_scelto["caption_instagram"],
            "created_at": oggi_str,
            "ultimi_titoli_usati": usati_recenti[-12:]
        }, f, ensure_ascii=False, indent=2)

    invia_anteprima_su_telegram(IMAGE_FILE, copy_scelto["caption_instagram"])
    print("Grafica con foto HD generata e inviata in anteprima su Telegram!")


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
                      json={"chat_id": ADMIN_CHAT_ID, "text": "🗑️ Bozza scartata. Rilancia il workflow per pescare una nuova foto e un nuovo testo!"})


if __name__ == "__main__":
    modalita = sys.argv[1] if len(sys.argv) > 1 else "genera"
    if modalita == "genera":
        fase_1_genera_proposta()
    elif modalita == "pubblica":
        fase_2_controlla_ok_e_pubblica()
