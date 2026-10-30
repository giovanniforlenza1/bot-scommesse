import requests
import json
import os
import uuid
import math
import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")
CHAT_ID = os.environ.get("CHAT_ID") or os.environ.get("OMEGA_CHAT_ID")

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

# Baseline reali per campionato: (Media Angoli Totali Lega, Media Cartellini Totali Lega)
BASELINE_LEGA = {
    'soccer_italy_serie_a': (9.6, 4.6),
    'soccer_spain_la_liga': (9.4, 5.1),
    'soccer_portugal_primeira_liga': (9.9, 5.0),
    'soccer_epl': (10.5, 3.8),
    'soccer_germany_bundesliga': (9.7, 3.8),
    'soccer_france_ligue_one': (9.2, 4.0),
    'soccer_netherlands_eredivisie': (10.2, 3.3),
    'soccer_uefa_champs_league': (9.3, 3.9),
    'soccer_uefa_europa_league': (9.6, 4.4),
    'soccer_uefa_europa_conference_league': (9.5, 4.3)
}

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "Internazionale": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus",
    "Hellas Verona": "Verona", "Bologna FC": "Bologna", "ACF Fiorentina": "Fiorentina", "Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Parma Calcio 1913": "Parma", "Venezia FC": "Venezia",
    "Como 1907": "Como", "US Lecce": "Lecce", "Cagliari Calcio": "Cagliari", "AC Monza": "Monza",
    "Atalanta BC": "Atalanta", "Manchester Utd": "Manchester United", "Manchester United FC": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham", "Tottenham Hotspur": "Tottenham",
    "Newcastle Utd": "Newcastle", "Newcastle United": "Newcastle", "Paris Saint Germain": "PSG",
    "Paris Saint-Germain": "PSG", "Bayern Munich": "Bayern Monaco", "Bayer Leverkusen": "Bayer Leverkusen",
    "Borussia Dortmund": "Dortmund", "RB Leipzig": "Lipsia", "Eintracht Frankfurt": "Francoforte",
    "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad", "Atletico Madrid": "Atletico Madrid",
    "Athletic Club": "Athletic Bilbao", "Sporting CP": "Sporting Lisbona",
    "PSV Eindhoven": "PSV", "Feyenoord Rotterdam": "Feyenoord",
    "Wolverhampton Wanderers": "Wolverhampton", "Wolves": "Wolverhampton",
    "Brighton and Hove Albion": "Brighton", "West Ham United": "West Ham"
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

def costruisci_storico_14_giorni_espn():
    """Scansiona giorno per giorno gli ultimi 14 giorni registrando angoli fatti+subiti e cartellini totali"""
    storico = {}
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    date_studio = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(1, 15)]

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

                    dati_match = []
                    for t in teams:
                        nome_norm = normalizza_nome(t.get('team', {}).get('displayName', ''))
                        corners, cards = None, 0
                        ha_cards = False
                        for s in t.get('statistics', []):
                            nome_s = str(s.get('name', '')).lower()
                            val_str = str(s.get('displayValue', '0')).strip()
                            val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
                            if nome_s in ['woncorners', 'cornerkicks', 'corners']:
                                corners = val
                            elif nome_s in ['yellowcards', 'redcards']:
                                cards += val
                                ha_cards = True
                        dati_match.append({'nome': nome_norm, 'corners': corners, 'cards': cards if ha_cards else None})

                    t0, t1 = dati_match[0], dati_match[1]
                    if t0['corners'] is not None and t1['corners'] is not None:
                        tot_c = t0['corners'] + t1['corners']
                        storico.setdefault(t0['nome'], {'tot_corners': [], 'fatti_corners': [], 'tot_cards': []})
                        storico.setdefault(t1['nome'], {'tot_corners': [], 'fatti_corners': [], 'tot_cards': []})
                        storico[t0['nome']]['tot_corners'].append(tot_c)
                        storico[t0['nome']]['fatti_corners'].append(t0['corners'])
                        storico[t1['nome']]['tot_corners'].append(tot_c)
                        storico[t1['nome']]['fatti_corners'].append(t1['corners'])

                    if t0['cards'] is not None and t1['cards'] is not None:
                        tot_k = t0['cards'] + t1['cards']
                        storico.setdefault(t0['nome'], {'tot_corners': [], 'fatti_corners': [], 'tot_cards': []})
                        storico.setdefault(t1['nome'], {'tot_corners': [], 'fatti_corners': [], 'tot_cards': []})
                        storico[t0['nome']]['tot_cards'].append(tot_k)
                        storico[t1['nome']]['tot_cards'].append(tot_k)
            except:
                continue
    print(f"[BETA 2.0] Squadre analizzate nello storico ESPN (14gg): {len(storico)}")
    return storico

def cerca_stat_squadra(storico, squadra_ita):
    n_cerca = normalizza_nome(squadra_ita)
    if n_cerca in storico:
        return storico[n_cerca]
    for k, dati in storico.items():
        if len(n_cerca) >= 3 and (n_cerca in k or k in n_cerca):
            return dati
    return None

def prob_poisson_over(lmbda, linea):
    soglia = int(math.floor(linea))
    prob_under = sum((math.exp(-lmbda) * (lmbda**k)) / math.factorial(k) for k in range(soglia + 1))
    return 1.0 - prob_under

def prob_poisson_under(lmbda, linea):
    soglia = int(math.floor(linea))
    return sum((math.exp(-lmbda) * (lmbda**k)) / math.factorial(k) for k in range(soglia + 1))

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

def esegui_beta():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    data_oggi_str = oggi.strftime("%d/%m/%Y")
    
    inizio_finestra = oggi + timedelta(minutes=30)
    limite_temporale = oggi + timedelta(days=3)
    
    db_principale = carica_database_principale()

    if any(s.get('modello') == 'beta' and s.get('data_creazione') == data_oggi_str for s in db_principale.get('schedine', [])):
        print(f"[BETA] Giocata del {data_oggi_str} già presente nel database. Salto.")
        return

    id_gia_giocati, match_gia_giocati = ottieni_partite_gia_giocate(db_principale, 'beta')
    storico_espn = costruisci_storico_14_giorni_espn()
    candidati_beta = []

    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        partite = esegui_richiesta_api(url_template)
        if not partite:
            continue

        base_c_lega, base_k_lega = BASELINE_LEGA.get(camp, (9.6, 4.2))

        for p in partite:
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < inizio_finestra or data_ita > limite_temporale:
                continue

            casa_orig, trasf_orig = p['home_team'], p['away_team']
            casa_ita, trasf_ita = traduci_squadra(casa_orig), traduci_squadra(trasf_orig)
            match_intero = f"{casa_ita} - {trasf_ita}".lower()

            if str(p['id']) in id_gia_giocati or match_intero in match_gia_giocati:
                continue

            q1_list, q2_list = [], []
            for book in p.get('bookmakers', []):
                if 'exchange' in book.get('title', '').lower():
                    continue
                for m in book.get('markets', []):
                    if m['key'] == 'h2h':
                        for out in m['outcomes']:
                            if out['name'] == casa_orig: q1_list.append(out['price'])
                            elif out['name'] == trasf_orig: q2_list.append(out['price'])

            if not q1_list or not q2_list:
                continue

            q1_med = sum(q1_list) / len(q1_list)
            q2_med = sum(q2_list) / len(q2_list)
            fav_q = min(q1_med, q2_med)
            diff_quote = abs(q1_med - q2_med)
            giorni_attesa = max(0, (data_ita.date() - oggi.date()).days)

            st_casa = cerca_stat_squadra(storico_espn, casa_ita)
            st_trasf = cerca_stat_squadra(storico_espn, trasf_ita)

            # --- 1. MODELLO ANGOLI BIDIREZIONALE (OVER & UNDER) ---
            ha_c_casa = bool(st_casa and st_casa['tot_corners'])
            ha_c_trasf = bool(st_trasf and st_trasf['tot_corners'])
            c_casa = (sum(st_casa['tot_corners']) / len(st_casa['tot_corners'])) if ha_c_casa else base_c_lega
            c_trasf = (sum(st_trasf['tot_corners']) / len(st_trasf['tot_corners'])) if ha_c_trasf else base_c_lega
            
            peso_storico_c = 0.75 if (ha_c_casa and ha_c_trasf) else (0.45 if (ha_c_casa or ha_c_trasf) else 0.15)
            lambda_c = (peso_storico_c * ((c_casa + c_trasf) / 2.0)) + ((1.0 - peso_storico_c) * base_c_lega)

            # Dinamica tattica dal mercato quote
            if fav_q <= 1.45 and diff_quote >= 2.6:
                lambda_c += 0.85  # Assedio costante della super-favorita
            elif diff_quote <= 0.65 and 'uefa' in camp:
                lambda_c -= 0.70  # Gara bloccata a centrocampo

            bonus_affidabilita_c = 0.03 if (ha_c_casa and ha_c_trasf) else 0.0

            opzioni_match = []

            # Opzione A: Over 8.5 Calci d'Angolo (@1.58)
            p_o85 = prob_poisson_over(lambda_c, 8.5)
            opzioni_match.append(("Over 8.5 Calci d'Angolo", 1.58, p_o85, (p_o85 * 1.58) - 1.0 + bonus_affidabilita_c))

            # Opzione B: Over 9.5 Calci d'Angolo (@1.80) se volume altissimo
            if lambda_c >= 10.6:
                p_o95 = prob_poisson_over(lambda_c, 9.5)
                opzioni_match.append(("Over 9.5 Calci d'Angolo", 1.80, p_o95, (p_o95 * 1.80) - 1.0 + bonus_affidabilita_c))

            # Opzione C: Under 10.5 Calci d'Angolo (@1.57) per gare a basso volume di corner
            if lambda_c <= 9.3:
                p_u105 = prob_poisson_under(lambda_c, 10.5)
                opzioni_match.append(("Under 10.5 Calci d'Angolo", 1.57, p_u105, (p_u105 * 1.57) - 1.0 + bonus_affidabilita_c))

            # Opzione D: Under 9.5 Calci d'Angolo (@1.75) per gare ultra-bloccate
            if lambda_c <= 8.5:
                p_u95 = prob_poisson_under(lambda_c, 9.5)
                opzioni_match.append(("Under 9.5 Calci d'Angolo", 1.75, p_u95, (p_u95 * 1.75) - 1.0 + bonus_affidabilita_c))

            # --- 2. MODELLO CARTELLINI BIDIREZIONALE (OVER & UNDER) ---
            ha_k_casa = bool(st_casa and st_casa['tot_cards'])
            ha_k_trasf = bool(st_trasf and st_trasf['tot_cards'])
            k_casa = (sum(st_casa['tot_cards']) / len(st_casa['tot_cards'])) if ha_k_casa else base_k_lega
            k_trasf = (sum(st_trasf['tot_cards']) / len(st_trasf['tot_cards'])) if ha_k_trasf else base_k_lega

            peso_storico_k = 0.70 if (ha_k_casa and ha_k_trasf) else (0.40 if (ha_k_casa or ha_k_trasf) else 0.15)
            lambda_k = (peso_storico_k * ((k_casa + k_trasf) / 2.0)) + ((1.0 - peso_storico_k) * base_k_lega)

            if diff_quote <= 0.80:
                lambda_k += 0.55  # Scontro diretto in bilico = alta tensione agonistica
            elif fav_q <= 1.32:
                lambda_k -= 0.65  # Partita a senso unico = pochissimi falli

            bonus_affidabilita_k = 0.03 if (ha_k_casa and ha_k_trasf) else 0.0

            # Opzione E: Over 3.5 Cartellini Totali (@1.60) solo in campionati severi o match infuocati
            if lambda_k >= 4.3:
                p_o35k = prob_poisson_over(lambda_k, 3.5)
                opzioni_match.append(("Over 3.5 Cartellini Totali", 1.60, p_o35k, (p_o35k * 1.60) - 1.0 + bonus_affidabilita_k))

            # Opzione F: Under 4.5 Cartellini Totali (@1.57) ottimo in Premier, Bundesliga, Olanda o match sbilanciati
            if lambda_k <= 3.9:
                p_u45k = prob_poisson_under(lambda_k, 4.5)
                opzioni_match.append(("Under 4.5 Cartellini Totali", 1.57, p_u45k, (p_u45k * 1.57) - 1.0 + bonus_affidabilita_k))

            # Prende solo la migliore giocata per questa singola partita (evita bias fisso!)
            opzioni_match.sort(key=lambda x: -x[3])
            best_pick, best_q, best_prob, best_edge = opzioni_match[0]

            if best_prob >= 0.60:
                candidati_beta.append({
                    'id_partita': p['id'],
                    'data': data_ita.strftime("%d/%m %H:%M"),
                    'giorni_attesa': giorni_attesa,
                    'lega': camp,
                    'squadra_casa': casa_ita,
                    'squadra_trasferta': trasf_ita,
                    'pronostico': best_pick,
                    'quota': best_q,
                    'prob': best_prob,
                    'edge': best_edge
                })

    if not candidati_beta:
        print("[BETA 2.0] Nessuna partita disponibile nei prossimi 3 giorni.")
        return

    # Privilegia le partite più vicine nel tempo (oggi/domani) con il massimo vantaggio statistico (Edge)
    candidati_beta.sort(key=lambda x: (1 if x['giorni_attesa'] > 1 else 0, -x['edge']))
    miglior_operazione = candidati_beta[0]
    p_win = min(0.82, max(0.62, miglior_operazione['prob']))
    q_scelta = miglior_operazione['quota']

    # Stake Kelly protetto e calibrato (tra 8.5€ e 12.0€, mai più 15€ fissi che bruciano cassa)
    b = q_scelta - 1.0
    kelly_puro = max(0.05, ((b * p_win) - (1.0 - p_win)) / b)
    stake_kelly = round(max(8.5, min(12.0, 200.0 * kelly_puro * 0.40)), 1)

    partita_reale = [{
        'id_partita': miglior_operazione['id_partita'],
        'data': miglior_operazione['data'],
        'squadra_casa': miglior_operazione['squadra_casa'],
        'squadra_trasferta': miglior_operazione['squadra_trasferta'],
        'pronostico': miglior_operazione['pronostico'],
        'quota': q_scelta,
        'lega': miglior_operazione['lega'],
        'stato': 'in attesa',
        'risultato_reale': ''
    }]

    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'modello': 'beta',
        'data_creazione': data_oggi_str,
        'importo': stake_kelly,
        'quota_totale': q_scelta,
        'ritorno_potenziale': round(stake_kelly * q_scelta, 2),
        'stato_schedina': 'in attesa',
        'partite': partita_reale
    })
    salva_database_principale(db_principale)
    print(f"BETA 2.0 SALVATO: {miglior_operazione['squadra_casa']} - {miglior_operazione['squadra_trasferta']} -> {miglior_operazione['pronostico']} (@{q_scelta}) | Stake: {stake_kelly}€")

    c_casa = html.escape(miglior_operazione['squadra_casa'])
    c_trasf = html.escape(miglior_operazione['squadra_trasferta'])
    c_pron = html.escape(miglior_operazione['pronostico'])

    msg = "<b>⚡ MODELLO BETA 2.0 | POISSON BIDIREZIONALE</b>\n\n"
    msg += f"⚽ <b>{miglior_operazione['data']} | {c_casa} - {c_trasf}</b>\n"
    msg += f"🎯 <b>Singola ad Alta Confidenza</b>: {c_pron}\n"
    msg += f"📊 <b>Quota di Riferimento</b>: @{q_scelta}\n"
    msg += f"📈 <b>Probabilità Stimata</b>: {round(p_win * 100, 1)}%\n"
    msg += f"💰 <b>Stake Kelly Protetto</b>: {stake_kelly}€\n\n"
    msg += "<b>#ModelloBeta #Poisson #SmartBankroll</b>"

    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Errore Telegram Beta: {e}")

if __name__ == "__main__":
    esegui_beta()
