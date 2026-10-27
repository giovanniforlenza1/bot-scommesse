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

# PALETTE PIATTA UFFICIALE SBR PER SINGOLO BOT
STILE_BOT = {
    "alpha": {"colore": "#F87060", "etichetta": "MODELLO ALPHA • MULTIPLA PROTETTA"},
    "beta":  {"colore": "#B3A394", "etichetta": "MODELLO BETA • POISSON"},
    "sigma": {"colore": "#2D6A4F", "etichetta": "MODELLO SIGMA • TENNIS LAB"},
    "omega": {"colore": "#102542", "etichetta": "MODELLO OMEGA • QUANTITATIVO"}
}


def decripta_payload_se_presente(schedina):
    """Se le partite di Alpha sono offuscate sul sito (🔒 Operazione), legge i nomi veri dal payload criptato."""
    partite = schedina.get("partite", [])
    if partite and "🔒" not in str(partite[0].get("squadra_casa", "")) and "Operazione" not in str(partite[0].get("squadra_casa", "")):
        return partite

    payload_b64 = schedina.get("payload_criptato")
    if not payload_b64 or not TELEGRAM_TOKEN:
        return []

    try:
        xored = base64.b64decode(payload_b64.encode("ascii"))
        key_hash = hashlib.sha256(TELEGRAM_TOKEN.encode("utf-8")).digest()
        raw_bytes = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(xored)])
        return json.loads(raw_bytes.decode("utf-8"))
    except Exception:
        return []


def scegli_senza_ripetere(lista_opzioni, usati_recenti):
    disponibili = [x for x in lista_opzioni if x not in usati_recenti]
    if not disponibili:
        disponibili = lista_opzioni
    scelta = random.choice(disponibili)
    return scelta


def genera_copy_dinamico_ricco(tipo_post, dati_contesto, usati_recenti):
    """Motore combinatorio ad alta varietà: centinaia di combinazioni calde, editoriali e anti-ban."""
    modello = dati_contesto.get("modello", "BETA").upper()
    match = dati_contesto.get("match", "il big match in programma")
    focus = dati_contesto.get("focus", "lettura tattica")

    hashtag_pool = [
        "#SBRLab #AnalisiSportiva #DataScience #CalcioTattico #StatisticheCalcio",
        "#SBRLab #SportAnalytics #NumeriDelCalcio #TatticaCalcistica #MatchAnalysis",
        "#SBRLab #CalcioNumeri #ModelliMatematici #AnalisiTattica #SportData",
        "#SBRLab #FootballAnalytics #AlgoritmiSportivi #LetturaDelMatch #DatiSportivi",
        "#SBRLab #InsiderSportivo #StatisticaApplicata #StudioDelMatch #SportScience",
        "#SBRLab #DietroINumeri #Calcio Europeo #AnalisiPreMatch #MetodoScientifico"
    ]

    cta_pool = [
        "📲 Trovi la lettura integrale nel nostro canale Telegram gratuito (Link in Bio).",
        "🔓 L'analisi completa di Alpha, Beta e Tennis è già dentro il canale Telegram gratis: Link in Bio.",
        "👉 Entra gratis nel club su Telegram dal Link in Bio per leggere tutti i report del giorno.",
        "📲 Unisciti gratuitamente al canale Telegram (Link in Bio) prima del fischio d'inizio.",
        "🔓 Tutti i segnali giornalieri di Alpha, Beta e Sigma escono gratis su Telegram. Link in Bio.",
        "👉 Passa dal Link in Bio ed entra nel canale gratuito per seguire le analisi in tempo reale."
    ]

    # --- RUBRICA 1: PRE-MATCH (ALPHA / BETA / SIGMA) ---
    if tipo_post == "PRE_MATCH":
        if modello == "ALPHA":
            titoli = [
                "Scudo tattico sulla multipla.",
                "Dove il pareggio non fa male.",
                "Costruire valore senza azzardo.",
                "Equilibrio rotto dai numeri.",
                "La geometria della continuità.",
                "Tre indizi fanno una prova.",
                "Proteggere il ritmo gara.",
                "Quando la favorita ha il vento.",
                " Margini stretti, copertura ampia.",
                "Oltre la semplice sensazione.",
                "Il peso specifico del fattore campo.",
                "Incrocio ad alta affidabilità."
            ]
            testi_grafica = [
                f"In {match} il ritmo offensivo spinge in una direzione chiara: il Modello Alpha attiva lo scudo statistico per assorbire gli imprevisti.",
                f"Il tifoso guarda solo il nome sulla maglia, i dati leggono la tenuta nei 90 minuti. Su {match} la struttura regge l'urto.",
                f"Niente salti nel buio su {match}: l'algoritmo incrocia forma recente e tenuta difensiva isolando uno scenario ad alta stabilità.",
                f"Quando due filosofie di gioco si scontrano come in {match}, i numeri svelano subito chi avrà il controllo territoriale.",
                f"Su {match} il divario di produzione offensiva è netto. Alpha seleziona la traiettoria più protetta evitando le trappole emotive.",
                f"Meno istinto da spogliatoio e più freddezza analitica: {match} entra nel radar di Alpha per solidità tattica e continuità.",
                f"Le partite sporche si leggono prima del calcio d'inizio. In {match} i parametri di copertura indicano una rotta precisa.",
                f"Non cerchiamo l'impresa impossibile, ma la costanza: {match} supera tutti i filtri di sicurezza del motore Alpha."
            ]
            aperture_caption = [
                f"⚽ C'è una bella differenza tra sperare in un risultato e preparare ogni scenario prima del fischio d'inizio.\n\nOggi i riflettori del Modello ALPHA si accendono su {match}.",
                f"🔍 Quante volte una partita dominata cambia volto per un episodio isolato all'85°?\n\nÈ proprio per questo che su {match} il nostro Modello ALPHA lavora di copertura strutturale.",
                f"🏟️ Il fascino del campo incontra la disciplina dei numeri.\n\nAnalizzando i flussi e i ritmi di {match}, l'algoritmo ALPHA ha isolato una direzione precisa: {focus}.",
                f"📊 Mentre fuori si discute di formazioni e pronostici di pancia, in laboratorio abbiamo passato ai raggi X {match}.\n\nIl verdetto del Modello ALPHA punta dritto sulla stabilità: {focus}.",
                f"⚡ Non tutte le favorite sono uguali, e i dati lo sanno bene.\n\nNel palinsesto di oggi {match} spicca per coerenza tattica e solidità nei novanta minuti secondo i filtri ALPHA."
            ]

        elif modello == "BETA":
            titoli = [
                "Stasera le fasce bruciano.",
                "Partita ad altissima tensione.",
                "Quando l'area diventa un assedio.",
                "Scintille attese in mezzo al campo.",
                "Il peso dei duelli individuali.",
                "Pressione costante fino al 90°.",
                "Quello che il tabellino non dice.",
                "Nervi tesi e spazi stretti.",
                "L'onda lunga sulle corsie esterne.",
                "Fischietto caldo, ritmo spezzato.",
                "Assedio tattico negli ultimi metri.",
                "La matematica dei calci piazzati."
            ]
            testi_grafica = [
                f"Lo storico reale degli ultimi 30 giorni parla chiaro: in {match} il volume di spinta e duelli accende la curva di Poisson.",
                f"Chi guarda solo il risultato finale perde metà dello spettacolo. In {match} il vero squilibrio nasce su ritmi, corner e contrasti.",
                f"Due squadre che non sanno speculare: incrociando le medie reali di {match}, il Modello Beta intercetta una pressione fuori scala.",
                f"Equilibrio sottile e posta in palio pesante. In {match} l'intensità agonistica promette un copione molto preciso nei dettagli.",
                f"Cross dal fondo, ribattute e difesa bassa: la conformazione tattica di {match} disegna il terreno perfetto per il Modello Beta.",
                f"Zero dati inventati, solo storico reale verificato: su {match} la distribuzione di Poisson segnala un'anomalia netta su {focus}.",
                f"Quando i duelli a centrocampo salgono di giri, i numeri anticipano la cronaca. Occhi puntati su {match} e sul parametro {focus}.",
                f"Ampiezza sulle ali e baricentro alto: gli indicatori statistici di {match} raccontano una gara pronta a esplodere sulle palle inattive."
            ]
            aperture_caption = [
                f"🔥 Alcune partite si decidono sui gol, altre si leggono molto prima osservando le fasce laterali e il nervosismo nei contrasti.\n\nPer {match} il Modello BETA ha incrociato 30 giorni di statistiche reali.",
                f"📐 La bellezza della distribuzione di Poisson applicata al calcio vero.\n\nSu {match} non ci interessa chi alzerà le braccia al 90°, ma il volume di gioco che genereranno in campo: focus su {focus}.",
                f"⚡ Baricentro alto, esterni che puntano l'uomo e falli tattici per fermare le ripartenze.\n\nI numeri storici di {match} hanno fatto scattare il semaforo verde del Modello BETA su {focus}.",
                f"🎯 Dove il tifoso vede caos, la statistica vede schemi che si ripetono.\n\nL'incrocio dei dati ESPN su {match} mostra una tendenza marcatissima analizzata stamattina dal motore BETA.",
                f"🏟️ Ci sono sfide bloccate e sfide destinate a viaggiare a strappi continui.\n\n{match} rientra pienamente nei parametri ad alta confidenza del nostro Modello BETA ({focus})."
            ]

        else:  # SIGMA TENNIS
            titoli = [
                "Nel tennis non esiste pareggio.",
                "Questione di superficie e ritmo.",
                "Servizio, risposta e nervi saldi.",
                "Geometrie pure da fondo campo.",
                "Chi comanda davvero lo scambio?",
                "L'inerzia invisibile del set.",
                "Velocità di palla e percentuali.",
                "Testa a testa ai raggi X.",
                "Il peso delle palle break.",
                "Uno contro uno, zero alibi."
            ]
            testi_grafica = [
                f"Nessun compagno dietro cui nascondersi: in {match} la resa sulla superficie e la tenuta al servizio tracciano un solco netto.",
                f"Il Laboratorio Sigma ha scandagliato il circuito: su {match} i ritmi di scambio premiano una direzione statistica limpida.",
                f"Tra prime in campo e punti vinti in risposta, {match} mette di fronte due curve di rendimento che oggi viaggiano a velocità opposte.",
                f"Sulla singola partita la classifica conta fino a un certo punto: in {match} l'adattamento al campo sposta gli equilibri reali.",
                f"Quando il braccio trema nei game decisivi, emergono le medie storiche. Il Modello Sigma accende il faro su {match}.",
                f"Angoli stretti, profondità di palla e gestione della fatica: {match} supera i filtri quantitativi del nostro laboratorio Tennis."
            ]
            aperture_caption = [
                f"🎾 Uno sport meravigliosamente spietato: niente melina, niente pareggio, solo due giocatori e la verità dei numeri punto dopo punto.\n\nOggi il Modello SIGMA entra in campo su {match}.",
                f"🔬 Superficie, velocità delle condizioni e rendimento nei turni di battuta.\n\nIl nostro laboratorio Tennis ha passato al setaccio il tabellone isolando {match} (focus: {focus}).",
                f"🎾 Spesso il nome più famoso attira l'attenzione, ma sono le percentuali di conversione nei momenti chiave a decidere chi passa il turno.\n\nEcco perché oggi seguiamo da vicino {match}."
            ]

        titolo_scelto = scegli_senza_ripetere(titoli, usati_recenti).strip()
        testo_scelto = random.choice(testi_grafica)
        caption = f"{random.choice(aperture_caption)}\n\n{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        return {"titolo_grafica": titolo_scelto, "testo_grafica": testo_scelto, "caption_instagram": caption}

    # --- RUBRICA 2: VERDETTO DEL CAMPO (RISULTATI E TRASPARENZA) ---
    elif tipo_post == "RISULTATI":
        winrate = dati_contesto.get("winrate", "--%")
        chiuse = dati_contesto.get("chiuse", 0)
        titoli_res = [
            "Il verdetto del campo.",
            "I numeri restano sempre.",
            "Trasparenza prima di tutto.",
            "Zero scuse, parla lo storico.",
            "La disciplina paga nel tempo.",
            "Dentro il nostro registro.",
            "Contano solo i fatti chiusi.",
            "Metodo batte improvvisazione."
        ]
        aperture_res = [
            f"📊 Sul web sono tutti fenomeni il lunedì mattina cancellando quello che va storto. Noi preferiamo fare l'esatto opposto: registrare ogni singola operazione a database.\n\nCon {chiuse} analisi archiviate e un Win Rate globale del {winrate}, il percorso di SBR Lab continua alla luce del sole.",
            f"✓ Prese e stop, tutto certificato nero su bianco.\n\nLa vera differenza tra chi vive lo sport con metodo e chi insegue l'emozione del momento sta tutta nella gestione sul lungo periodo ({chiuse} operazioni concluse, {winrate} di precisione).",
            f"📈 Non promettiamo miracoli: costruiamo modelli statistici e lasciamo che sia il campo a giudicarli settimana dopo settimana.\n\nEcco l'ultimo estratto reale dal nostro database pubblico ({winrate} Win Rate su {chiuse} chiusure).",
            f"🔍 La fiducia non si chiede, si dimostra coi dati aperti a tutti.\n\nOgni operazione generata dai nostri algoritmi viene verificata in automatico a fine gara: oggi contiamo {chiuse} analisi chiuse con il {winrate} di esiti positivi.",
            f"⚖️ Nello sport esiste la traversa al 94°, ed esiste la varianza. Ma quando analizzi centinaia di dati con rigore, la curva alla lunga racconta la verità.\n\nBilancio aggiornato: {chiuse} operazioni certificate, Win Rate al {winrate}."
        ]
        titolo_scelto = scegli_senza_ripetere(titoli_res, usati_recenti)
        caption = f"{random.choice(aperture_res)}\n\n{random.choice(cta_pool)}\n\n{random.choice(hashtag_pool)}"
        return {"titolo_grafica": titolo_scelto, "testo_grafica": "", "caption_instagram": caption}

    # --- RUBRICA 3: DIARIO DAL LABORATORIO (HYPE OMEGA) ---
    else:
        titoli_omega = [
            "Giocare il match 10.000 volte.",
            "Cosa vede davvero Omega?",
            "Smascherare il rumore di fondo.",
            "Quando NON entrare vale oro.",
            "Dietro la porta del laboratorio.",
            "Simulare ogni singolo rimbalzo.",
            "La calma fredda di Monte Carlo.",
            "Perché Omega è ancora chiuso.",
            "Cercare l'errore di valutazione.",
            "La scienza delle probabilità pure."
        ]
        testi_omega = [
            "Prima ancora del fischio d'inizio, il motore Omega simula l'incontro diecimila volte pesando attacco, difesa, fatica e calendario per isolare la probabilità pura.",
            "La maggior parte degli errori nasce dalla fretta. Omega è progettato con un freno automatico: se il vantaggio matematico reale scende sotto soglia, il sistema blocca tutto.",
            "Stiamo affinando la purificazione dei mercati e il tracciamento del valore di chiusura. Apriremo le porte di Omega solo quando ogni ingranaggio sarà chirurgico.",
            "Un gol casuale può ingannare l'occhio umano per settimane, ma non sfugge a diecimila simulazioni incrociate sui tiri nello specchio e sulla qualità della manovra.",
            "Mentre Alpha, Beta e Sigma lavorano in chiaro ogni giorno, in background Omega macina dati storici europei per costruire il nostro nucleo quantitativo di punta.",
            "Non basta capire chi è più forte: serve misurare al centesimo quanto vale davvero quella forza in campo. È questa la missione quotidiana del progetto Omega.",
            "Calibrazione dei pesi tattici casa/trasferta e gestione dinamica dell'esposizione: il diario di sviluppo di Omega procede spedito dietro le quinte di SBR Lab."
        ]
        aperture_omega = [
            "🧪 Cosa succederebbe se potessi far rigiocare la stessa identica partita 10.000 volte prima che le squadre scendano in campo?\n\nÈ esattamente ciò che sta facendo in questo momento il Modello OMEGA in fase di test privato.",
            "🔒 Molti ci chiedono perché il Modello OMEGA non sia ancora aperto al pubblico.\n\nLa risposta è semplice: la perfezione richiede pazienza. Stiamo calibrando il motore Monte Carlo affinché intervenga solo davanti a un vantaggio statistico netto.",
            "🧠 Nel calcio un episodio cambia una serata, ma su diecimila simulazioni emerge sempre la vera forza delle squadre.\n\nDietro le quinte di SBR Lab lo sviluppo di OMEGA continua senza sosta. Nel frattempo, Alpha, Beta e Tennis sono già liberi per tutti.",
            "⚙️ Purificazione delle probabilità reali, studio profondo di tiri e tenuta difensiva, blocco automatico delle partite trappola.\n\nVi portiamo per un attimo dentro la sala macchine del progetto OMEGA, il futuro fiore all'occhiello dell'ecosistema SBR.",
            "📡 Mentre seguiamo gratuitamente i campionati con Alpha, Beta e il laboratorio Tennis, in background gira silenziosamente OMEGA.\n\nAncora qualche settimana di calibrazione fine prima di svelare il nostro modello quantitativo più avanzato."
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
        page.goto(f"file://{os.path.abspath(temp_html)}", wait_until="networkidle")
        page.screenshot(path=output_png, full_page=False)
        browser.close()

    if os.path.exists(temp_html):
        os.remove(temp_html)


def trova_ultimo_match_valido(schedine):
    """Alterna intelligentemente tra Tennis (Mercoledì), Alpha e Beta leggendo anche i match decriptati."""
    fuso_italia = ZoneInfo("Europe/Rome")
    giorno_sett = datetime.now(fuso_italia).weekday()

    # Il Mercoledì (o se scelto casualmente quando disponibile) dà spazio anche al Tennis gratuito
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
                    return "sigma", f"{g1} - {g2}", p.get("pronostico", "Vantaggio Superficie")
        except Exception:
            pass

    candidati_recenti = []
    for s in reversed(schedine):
        mod = s.get("modello", "").lower()
        if mod in ("alpha", "beta"):
            partite_vere = decripta_payload_se_presente(s)
            if partite_vere:
                p0 = partite_vere[0]
                casa = p0.get("squadra_casa", "")
                trasf = p0.get("squadra_trasferta", "")
                if casa and trasf and "🔒" not in casa:
                    candidati_recenti.append((mod, f"{casa} - {trasf}", p0.get("pronostico", "Analisi Tattica")))
        if len(candidati_recenti) >= 4:
            break

    if candidati_recenti:
        return candidati_recenti[0]

    return "beta", "Big Match Europeo", "Pressione Offensiva & Corner"


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
    giorno = datetime.now(fuso_italia).weekday()  # 0=Lun, 4=Ven

    # Lunedì: Verdetto del Campo | Venerdì: Hype Omega | Altri giorni: Pre-Match Alpha/Beta/Tennis
    if giorno == 0 and schedine:
        concluse = [s for s in schedine if s.get("stato_schedina") in ("vinta", "persa") and s.get("modello") in ("alpha", "beta")]
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
        mod_key, match_nome, mercato = trova_ultimo_match_valido(schedine)
        stile = STILE_BOT.get(mod_key, STILE_BOT["beta"])
        copy_scelto = genera_copy_dinamico_ricco("PRE_MATCH", {"modello": mod_key.upper(), "match": match_nome, "focus": mercato}, usati_recenti)
        renderizza_html_in_png("templates_social/template_analisi.html", {
            "COLORE_BOT": stile["colore"],
            "ETICHETTA_BOT": stile["etichetta"],
            "DATA_OGGI": oggi_str,
            "TITOLO_CALDO": copy_scelto["titolo_grafica"],
            "MATCH": match_nome,
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
    print("Grafica generata con successo e inviata in anteprima su Telegram!")


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
                      json={"chat_id": ADMIN_CHAT_ID, "text": "🗑️ Bozza scartata. Puoi rilanciare il workflow se ne vuoi una nuova."})


if __name__ == "__main__":
    modalita = sys.argv[1] if len(sys.argv) > 1 else "genera"
    if modalita == "genera":
        fase_1_genera_proposta()
    elif modalita == "pubblica":
        fase_2_controlla_ok_e_pubblica()
