import requests
import json
import os
import uuid
import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")
CHAT_ID = os.environ.get("CHAT_ID")

campionati = [
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'soccer_uefa_europa_conference_league',
    'soccer_italy_serie_a', 'soccer_epl', 'soccer_spain_la_liga', 
    'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga'
]

MAPPA_CAMPIONATI_ESPN = {
    'soccer_uefa_champs_league': 'uefa.champions',
    'soccer_uefa_europa_league': 'uefa.europa',
    'soccer_uefa_europa_conference_league': 'uefa.europa.conf',
    'soccer_italy_serie_a': 'ita.1',
    'soccer_epl': 'eng.1',
    'soccer_spain_la_liga': 'esp.1',
    'soccer_germany_bundesliga': 'ger.1',
    'soccer_france_ligue_one': 'fra.1',
    'soccer_netherlands_eredivisie': 'ned.1',
    'soccer_portugal_primeira_liga': 'por.1'
}

# DNA statistico dei campionati: propensione ai gol (>1.0 = offensivo, <1.0 = tattico/bloccato)
PROFILO_GOL_LEGA = {
    'soccer_germany_bundesliga': 1.12,
    'soccer_netherlands_eredivisie': 1.14,
    'soccer_epl': 1.08,
    'soccer_italy_serie_a': 1.02,
    'soccer_uefa_europa_league': 1.03,
    'soccer_uefa_europa_conference_league': 1.02,
    'soccer_portugal_primeira_liga': 0.96,
    'soccer_france_ligue_one': 0.95,
    'soccer_spain_la_liga': 0.92,
    'soccer_uefa_champs_league': 0.88  # In Champions match molto più tattici e bloccati!
}

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "Internazionale": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus", "Hellas Verona": "Verona",
    "Bologna FC": "Bologna", "ACF Fiorentina": "Fiorentina", "Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Parma Calcio 1913": "Parma", "Como 1907": "Como",
    "Venezia FC": "Venezia", "US Lecce": "Lecce", "Cagliari Calcio": "Cagliari", "AC Monza": "Monza",
    "Atalanta BC": "Atalanta", "Manchester Utd": "Manchester United", "Nott'm Forest": "Nottingham Forest",
    "Spurs": "Tottenham", "Tottenham Hotspur": "Tottenham", "Newcastle Utd": "Newcastle",
    "Paris Saint Germain": "PSG", "Paris Saint-Germain": "PSG", "Bayern Munich": "Bayern Monaco",
    "Bayer Leverkusen": "Bayer Leverkusen", "Borussia Dortmund": "Dortmund", "RB Leipzig": "Lipsia",
    "Eintracht Frankfurt": "Francoforte", "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad",
    "Athletic Club": "Athletic Bilbao", "Wolverhampton Wanderers": "Wolverhampton",
    "Sporting CP": "Sporting Lisbona", "PSV Eindhoven": "PSV", "Feyenoord Rotterdam": "Feyenoord"
}

def ottieni_pool_chiavi():
    nomi_secrets = [
        "CHIAVE_D", "CHIAVE_E", "CHIAVE_A", "CHIAVE_B", "CHIAVE_C", 
        "ODDS_API_KEY", "API_KEY_ALPHA", "API_KEY_ARBITRO",
        "API_FOOTBALL_OMEGA_KEY", "API_FOOTBALL_KEY", "FOOTBALL_DATA_KEY"
    ]
    pool = []
    for nome in nomi_secrets:
        val = os.environ.get(nome, "")
        for k in val.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in pool:
                pool.append(k_clean)
    return pool

def esegui_richiesta_api(url_template):
    for chiave in ottieni_pool_chiavi():
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=12)
            if res.status_code == 200:
                return res.json()
        except:
            pass
    return None

def traduci_squadra(nome):
    nome_pulito = str(nome).strip()
    if nome_pulito in TRADUZIONI_SQUADRE:
        return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "")

def normalizza_nome(nome):
    n = traduci_squadra(nome).lower()
    for p in ["calcio", "fc", "ac", "sc", "cf", "1907", "1913", "bc", "us", "ss", "cfc", "as"]:
        n = n.replace(f" {p}", "").replace(f"{p} ", "")
    return n.strip()

def costruisci_storico_gol_espn():
    """Legge le ultime partite reali su ESPN per sapere se due squadre segnano tanto o fanno partite chiuse"""
    storico_gol = {}
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    date_studio = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(1, 12)]

    for _, lega_espn in MAPPA_CAMPIONATI_ESPN.items():
        for d_str in date_studio:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega_espn}/scoreboard?dates={d_str}"
            try:
                res = requests.get(url, timeout=4)
                if res.status_code != 200:
                    continue
                for ev in res.json().get('events', []):
                    comp = ev.get('competitions', [{}])[0]
                    if not comp.get('status', {}).get('type', {}).get('completed', False):
                        continue
                    teams = comp.get('competitors', [])
                    if len(teams) < 2:
                        continue
                    
                    nomi_t = []
                    tot_gol_match = 0
                    for t in teams:
                        n_norm = normalizza_nome(t.get('team', {}).get('displayName', ''))
                        sc_str = str(t.get('score', '0')).strip()
                        g_val = int(float(sc_str)) if sc_str.isdigit() else 0
                        tot_gol_match += g_val
                        nomi_t.append(n_norm)

                    for n_norm in nomi_t:
                        storico_gol.setdefault(n_norm, []).append(tot_gol_match)
            except:
                continue
    return storico_gol

def media_gol_squadra(storico_gol, squadra_ita, default_gol=2.65):
    n_cerca = normalizza_nome(squadra_ita)
    if n_cerca in storico_gol and storico_gol[n_cerca]:
        return sum(storico_gol[n_cerca]) / len(storico_gol[n_cerca])
    for k, lista_g in storico_gol.items():
        if len(n_cerca) >= 3 and (n_cerca in k or k in n_cerca) and lista_g:
            return sum(lista_g) / len(lista_g)
    return default_gol

def carica_id_omega_oggi():
    if os.path.exists('omega_oggi.json'):
        try:
            with open('omega_oggi.json', 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            pass
    return set()

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def ottieni_partite_gia_giocate(db, modello_target):
    id_giocati = set()
    match_giocati = set()
    for s in db.get('schedine', []):
        if s.get('modello') == modello_target:
            for p in s.get('partite', []):
                if p.get('id_partita'):
                    id_giocati.add(str(p.get('id_partita')))
                c = str(p.get('squadra_casa', '')).lower().strip()
                t = str(p.get('squadra_trasferta', '')).lower().strip()
                if c and t:
                    match_giocati.add(f"{c} - {t}")
    return id_giocati, match_giocati

def priorita_lega(lega):
    return 0 if ('italy_serie_a' in lega or 'uefa' in lega) else 1

def esegui_alpha():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    data_oggi_str = oggi.strftime("%d/%m/%Y")
    
    inizio_finestra = oggi + timedelta(minutes=30)
    limite_temporale = oggi + timedelta(days=3)
    
    db_principale = carica_database_principale()

    if any(s.get('modello') == 'alpha' and s.get('data_creazione') == data_oggi_str for s in db_principale.get('schedine', [])):
        print(f"[ALPHA] Giocata del {data_oggi_str} già presente nel database. Salto.")
        return

    id_esclusi_omega = carica_id_omega_oggi()
    id_gia_giocati, match_gia_giocati = ottieni_partite_gia_giocate(db_principale, 'alpha')
    storico_gol = costruisci_storico_gol_espn()
    candidati_alpha = []

    for camp in campionati:
        # Scarica sia 1X2 (h2h) sia Over/Under reali dei bookmaker (totals)
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h,totals"
        partite = esegui_richiesta_api(url_template)
        if not partite:
            continue

        coeff_lega = PROFILO_GOL_LEGA.get(camp, 1.0)

        for p in partite:
            if p['id'] in id_esclusi_omega:
                continue
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < inizio_finestra or data_ita > limite_temporale:
                continue

            casa_orig, trasf_orig = p['home_team'], p['away_team']
            casa_ita, trasf_ita = traduci_squadra(casa_orig), traduci_squadra(trasf_orig)
            match_intero = f"{casa_ita} - {trasf_ita}".lower()

            if str(p['id']) in id_gia_giocati or match_intero in match_gia_giocati:
                continue

            q1_list, qx_list, q2_list = [], [], []
            over25_list, under25_list = [], []

            for book in p.get('bookmakers', []):
                titolo_book = book.get('title', '').lower()
                key_book = book.get('key', '').lower()
                if 'exchange' in titolo_book or 'betfair' in key_book or 'matchbook' in key_book:
                    continue
                
                for m in book.get('markets', []):
                    if m['key'] == 'h2h':
                        for out in m['outcomes']:
                            if out['name'] == casa_orig: q1_list.append(out['price'])
                            elif out['name'] == trasf_orig: q2_list.append(out['price'])
                            elif out['name'].lower() == 'draw': qx_list.append(out['price'])
                    elif m['key'] == 'totals':
                        for out in m['outcomes']:
                            pt = float(out.get('point', 0))
                            if pt == 2.5:
                                if out['name'].lower() == 'over': over25_list.append(out['price'])
                                elif out['name'].lower() == 'under': under25_list.append(out['price'])

            if not q1_list or not qx_list or not q2_list:
                continue

            # Probabilità Reali De-Vigged dal consenso di tutti i bookmaker
            m1 = sum(q1_list) / len(q1_list)
            mx = sum(qx_list) / len(qx_list)
            m2 = sum(q2_list) / len(q2_list)
            inv_1x2 = (1.0 / m1) + (1.0 / mx) + (1.0 / m2)
            p1_reale = (1.0 / m1) / inv_1x2
            px_reale = (1.0 / mx) / inv_1x2
            p2_reale = (1.0 / m2) / inv_1x2

            max_q1 = min(2.05, max(q1_list))
            max_q2 = min(2.05, max(q2_list))

            # Media gol storica delle due squadre su ESPN corretta per il profilo del campionato
            gol_esp_casa = media_gol_squadra(storico_gol, casa_ita, 2.65)
            gol_esp_trasf = media_gol_squadra(storico_gol, trasf_ita, 2.65)
            gol_attesi_match = ((gol_esp_casa + gol_esp_trasf) / 2.0) * coeff_lega

            opzioni_valore = []

            # 1. VITTORIA SECCA (1 o 2) -> Quando la favorita ha una quota sovraprezzata rispetto alla probabilità reale
            if 1.35 <= max_q1 <= 1.88 and p1_reale >= 0.54:
                valore_1 = (p1_reale * max_q1) - 1.0
                score_1 = (p1_reale * 0.75) + (valore_1 * 1.40) + (0.04 if p1_reale >= 0.62 else 0.0)
                opzioni_valore.append((f"Vittoria {casa_ita}", round(max_q1, 2), score_1, "1X2"))

            if 1.35 <= max_q2 <= 1.88 and p2_reale >= 0.54:
                valore_2 = (p2_reale * max_q2) - 1.0
                score_2 = (p2_reale * 0.75) + (valore_2 * 1.40) + (0.04 if p2_reale >= 0.62 else 0.0)
                opzioni_valore.append((f"Vittoria {trasf_ita}", round(max_q2, 2), score_2, "1X2"))

            # 2. DOPPIA CHANCE (1X o X2) -> Ottima quando una squadra solida gioca un match combattuto (quota tra 1.30 e 1.62)
            p_1x = p1_reale + px_reale
            q_1x_max = round((1.0 / ((1.0 / max_q1) + (1.0 / max(qx_list)))) * 0.96, 2)
            if 1.30 <= q_1x_max <= 1.65 and p_1x >= 0.72:
                valore_1x = (p_1x * q_1x_max) - 1.0
                score_1x = (p_1x * 0.68) + (valore_1x * 1.35)
                opzioni_valore.append((f"Doppia Chance 1X ({casa_ita})", q_1x_max, score_1x, "DC"))

            p_x2 = p2_reale + px_reale
            q_x2_max = round((1.0 / ((1.0 / max_q2) + (1.0 / max(qx_list)))) * 0.96, 2)
            if 1.30 <= q_x2_max <= 1.65 and p_x2 >= 0.72:
                valore_x2 = (p_x2 * q_x2_max) - 1.0
                score_x2 = (p_x2 * 0.68) + (valore_x2 * 1.35)
                opzioni_valore.append((f"Doppia Chance X2 ({trasf_ita})", q_x2_max, score_x2, "DC"))

            # 3. MERCATI GOL REALI (UNDER 3.5 / UNDER 2.5 / OVER 1.5 / OVER 2.5)
            if over25_list and under25_list:
                mo25 = sum(over25_list) / len(over25_list)
                mu25 = sum(under25_list) / len(under25_list)
                inv_ou = (1.0 / mo25) + (1.0 / mu25)
                p_over25_mkt = (1.0 / mo25) / inv_ou
                p_under25_mkt = (1.0 / mu25) / inv_ou
            else:
                # Stima prudente se il bookmaker non espone la linea 2.5
                p_over25_mkt = 0.54 if (mx >= 3.60 and gol_attesi_match >= 2.85) else 0.46
                p_under25_mkt = 1.0 - p_over25_mkt

            # A) UNDER 3.5 GOL / UNDER 2.5 GOL -> Ideale in Champions League, Liga, Ligue 1 o match tattici!
            if gol_attesi_match <= 2.65 or p_under25_mkt >= 0.53 or camp == 'soccer_uefa_champs_league':
                # Derivazione matematica Under 3.5 da Under 2.5 + storico ESPN
                p_under35 = min(0.84, p_under25_mkt + 0.24 + (0.03 if gol_attesi_match <= 2.40 else 0.0))
                q_under35 = round(max(1.28, min(1.52, (1.0 / p_under35) * 0.98)), 2)
                if 1.28 <= q_under35 <= 1.52 and p_under35 >= 0.73:
                    valore_u35 = (p_under35 * q_under35) - 1.0
                    bonus_champions = 0.05 if camp == 'soccer_uefa_champs_league' else 0.02
                    score_u35 = (p_under35 * 0.67) + (valore_u35 * 1.25) + bonus_champions
                    opzioni_valore.append(("Under 3.5 Gol", q_under35, score_u35, "UNDER"))

                # Se la partita è blindatissima e la quota Under 2.5 reale è sovraprezzata
                if under25_list and gol_attesi_match <= 2.30 and p_under25_mkt >= 0.58:
                    max_u25 = min(1.85, round(max(under25_list), 2))
                    if 1.50 <= max_u25 <= 1.85:
                        valore_u25 = (p_under25_mkt * max_u25) - 1.0
                        score_u25 = (p_under25_mkt * 0.72) + (valore_u25 * 1.40)
                        opzioni_valore.append(("Under 2.5 Gol", max_u25, score_u25, "UNDER"))

            # B) OVER 1.5 GOL / OVER 2.5 GOL -> SOLO se il campionato e le squadre fanno davvero tanti gol!
            if gol_attesi_match >= 2.85 and p_over25_mkt >= 0.55 and camp != 'soccer_uefa_champs_league':
                p_over15 = min(0.83, p_over25_mkt + 0.22)
                q_over15 = round(max(1.28, min(1.48, (1.0 / p_over15) * 0.97)), 2)
                if 1.28 <= q_over15 <= 1.48 and p_over15 >= 0.75:
                    valore_o15 = (p_over15 * q_over15) - 1.0
                    score_o15 = (p_over15 * 0.64) + (valore_o15 * 1.20)
                    opzioni_valore.append(("Over 1.5 Gol", q_over15, score_o15, "OVER15"))

                if over25_list and gol_attesi_match >= 3.15 and p_over25_mkt >= 0.60:
                    max_o25 = min(1.80, round(max(over25_list), 2))
                    if 1.48 <= max_o25 <= 1.80:
                        valore_o25 = (p_over25_mkt * max_o25) - 1.0
                        score_o25 = (p_over25_mkt * 0.72) + (valore_o25 * 1.40)
                        opzioni_valore.append(("Over 2.5 Gol", max_o25, score_o25, "OVER25"))

            if not opzioni_valore:
                continue

            # Sceglie la giocata che si adatta meglio alle caratteristiche reali di QUESTA partita
            opzioni_valore.sort(key=lambda x: -x[2])
            miglior_pick, quota_scelta, miglior_score, famiglia_mercato = opzioni_valore[0]

            giorni_attesa = max(0, (data_ita.date() - oggi.date()).days)
            candidati_alpha.append({
                'id_partita': p['id'],
                'data': data_ita.strftime("%d/%m %H:%M"),
                'giorni_attesa': giorni_attesa,
                'squadra_casa': casa_ita,
                'squadra_trasferta': trasf_ita,
                'pronostico': miglior_pick,
                'quota': quota_scelta,
                'score': round(miglior_score, 4),
                'famiglia': famiglia_mercato,
                'lega': camp,
                'stato': 'in attesa',
                'risultato_reale': ''
            })

    if not candidati_alpha:
        print("[ALPHA] Nessuna partita idonea trovata.")
        return

    ordinati = sorted(candidati_alpha, key=lambda x: (1 if x['giorni_attesa'] > 1 else 0, priorita_lega(x['lega']), -x['score']))

    # COSTRUZIONE INTELLIGENTE DELLA SCHEDINA:
    # - Massimo 1 solo "Over 1.5 Gol" ammesso in schedina (Basta schedine tutte Over 1.5!)
    # - Punta a una quota totale > 1.70 (preferibilmente tra 2.00 e 2.50) con 2 o 3 partite
    selezionati = []
    quota_totale = 1.0
    conteggio_over15 = 0

    for c in ordinati:
        if len(selezionati) >= 3:
            break
        # Impedisce di inserire più di un Over 1.5 Gol nella stessa multipla!
        if c['famiglia'] == "OVER15" and conteggio_over15 >= 1:
            continue

        nuova_quota = quota_totale * c['quota']
        # Se abbiamo già 2 partite e superiamo quota 2.05, ci fermiamo (2 partite sono più sicure di 3!)
        if len(selezionati) >= 2 and quota_totale >= 2.05:
            break
        # Evita che la quota totale esploda oltre 2.65 aumentando il rischio
        if len(selezionati) >= 2 and nuova_quota > 2.65:
            continue

        selezionati.append(c)
        quota_totale = nuova_quota
        if c['famiglia'] == "OVER15":
            conteggio_over15 += 1

    # Se con 2 partite la quota è ancora sotto 1.75, cerca una terza partita compatibile per superare 1.85-2.00
    if quota_totale < 1.75 and len(selezionati) < 3:
        for c in ordinati:
            if c not in selezionati:
                if c['famiglia'] == "OVER15" and conteggio_over15 >= 1:
                    continue
                selezionati.append(c)
                quota_totale *= c['quota']
                if quota_totale >= 1.80 or len(selezionati) == 3:
                    break

    quota_totale = round(quota_totale, 2)
    partite_pulite = [{k: v for k, v in c.items() if k not in ['score', 'giorni_attesa', 'famiglia']} for c in selezionati]
    stake = 12.0

    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'modello': 'alpha',
        'data_creazione': data_oggi_str,
        'importo': stake,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(stake * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'telegram_inviato': True,
        'partite': partite_pulite
    })
    salva_database_principale(db_principale)
    print(f"ALPHA ADATTIVO SALVATO IN DATABASE.JSON: Quota Totale @{quota_totale} ({len(partite_pulite)} eventi)")

    msg = f"<b>🚀 MODELLO ALPHA | MULTIPLA ADATTIVA DI VALORE</b>\n\n📊 <b>Moltiplicatore Totale</b>: @{quota_totale}\n💰 <b>Stake</b>: {stake}€\n\n"
    for c in partite_pulite:
        msg += f"⚽ <b>{c['data']} | {html.escape(c['squadra_casa'])} - {html.escape(c['squadra_trasferta'])}</b>\n🛡️ <b>Scelta</b>: {html.escape(c['pronostico'])} (@{c['quota']})\n\n"
    msg += "<b>#ModelloAlpha #ValueBetting #SmartMultipla</b>"
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Errore Telegram Alpha: {e}")

if __name__ == "__main__":
    esegui_alpha()
