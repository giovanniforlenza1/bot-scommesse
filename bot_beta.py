import requests
import json
import os
import uuid
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

campionati = [
    'soccer_italy_serie_a', 'soccer_epl', 'soccer_spain_la_liga',
    'soccer_germany_bundesliga', 'soccer_france_ligue_one'
]

MAPPA_CAMPIONATI_ESPN = {
    'soccer_italy_serie_a': 'ita.1',
    'soccer_epl': 'eng.1',
    'soccer_spain_la_liga': 'esp.1',
    'soccer_germany_bundesliga': 'ger.1',
    'soccer_france_ligue_one': 'fra.1'
}

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "Internazionale": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus",
    "Hellas Verona": "Verona", "Bologna FC": "Bologna", "Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Venezia FC": "Venezia", "Parma Calcio 1913": "Parma",
    "Como 1907": "Como", "Manchester Utd": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham", "Tottenham Hotspur": "Tottenham",
    "Newcastle Utd": "Newcastle", "Paris Saint Germain": "PSG",
    "Bayern Munich": "Bayern Monaco", "Bayer Leverkusen": "Bayer Leverkusen",
    "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad",
    "Athletic Club": "Athletic Bilbao", "Wolverhampton Wanderers": "Wolverhampton"
}

def traduci_squadra(nome):
    nome_pulito = nome.strip()
    if nome_pulito in TRADUZIONI_SQUADRE: return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "")

def normalizza_nome(nome):
    n = traduci_squadra(nome).lower()
    for p in ["calcio", "fc", "ac", "sc", "cf", "united", "city", "1907", "1913"]:
        n = n.replace(p, "")
    return n.strip()

def esegui_richiesta_api(url_template):
    chiavi = [k.strip() for k in os.environ.get("ODDS_API_KEY", "").split(",") if k.strip()]
    if not chiavi: return None
    for chiave in chiavi:
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200: return res.json()
        except: pass
    return None

def costruisci_storico_reale_espn():
    """Scarica gli ultimi 14 giorni di partite da ESPN per calcolare le medie reali di Corner e Cartellini per squadra"""
    storico_squadre = {}
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    # Controlla campioni di giornate negli ultimi 14 giorni
    date_studio = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in [1, 2, 3, 4, 6, 7, 8, 10, 13, 14]]

    for _, lega_espn in MAPPA_CAMPIONATI_ESPN.items():
        for d_str in date_studio:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega_espn}/scoreboard?dates={d_str}"
            try:
                res = requests.get(url, timeout=6)
                if res.status_code != 200: continue
                for ev in res.json().get('events', []):
                    comp = ev.get('competitions', [{}])[0]
                    if not comp.get('status', {}).get('type', {}).get('completed', False):
                        continue
                    for t in comp.get('competitors', []):
                        nome_norm = normalizza_nome(t.get('team', {}).get('displayName', ''))
                        corners, cards = 0, 0
                        for s in t.get('statistics', []):
                            val_str = str(s.get('displayValue', '0')).strip()
                            val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
                            if s.get('name') == 'wonCorners': corners = val
                            elif s.get('name') in ['yellowCards', 'redCards']: cards += val
                        if corners > 0 or cards > 0:
                            info = storico_squadre.setdefault(nome_norm, {'corners': [], 'cards': []})
                            info['corners'].append(corners)
                            info['cards'].append(cards)
            except:
                continue
    return storico_squadre

def ottieni_media_storica(storico, squadra_ita, tipo, default_val):
    n_cerca = normalizza_nome(squadra_ita)
    for k, dati in storico.items():
        if (n_cerca in k or k in n_cerca) and dati[tipo]:
            return sum(dati[tipo]) / len(dati[tipo])
    return default_val

def prob_poisson_over(lmbda, linea):
    soglia = int(math.floor(linea))
    prob_under = sum((math.exp(-lmbda) * (lmbda**k)) / math.factorial(k) for k in range(soglia + 1))
    return 1.0 - prob_under

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def esegui_beta():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    limite_temporale = oggi + timedelta(days=3)
    
    db_principale = carica_database_principale()
    for s in db_principale['schedine']:
        if s.get('modello') == 'beta' and s.get('data_creazione') == oggi.strftime("%d/%m/%Y"):
            print("Beta già generata oggi.")
            return

    print("Beta: Analisi storico reale ESPN per Angoli e Cartellini in corso...")
    storico_espn = costruisci_storico_reale_espn()

    miglior_operazione = None
    miglior_edge = 0.0

    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu&markets=h2h"
        partite = esegui_richiesta_api(url_template)
        if not partite: continue

        for p in partite:
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < oggi or data_ita > limite_temporale: continue

            casa_orig, trasf_orig = p['home_team'], p['away_team']
            casa_ita, trasf_ita = traduci_squadra(casa_orig), traduci_squadra(trasf_orig)

            q1_list, q2_list = [], []
            for book in p.get('bookmakers', []):
                if 'exchange' in book.get('title', '').lower(): continue
                for m in book.get('markets', []):
                    if m['key'] == 'h2h':
                        for out in m['outcomes']:
                            if out['name'] == casa_orig: q1_list.append(out['price'])
                            elif out['name'] == trasf_orig: q2_list.append(out['price'])

            if not q1_list or not q2_list: continue
            q1_med = sum(q1_list) / len(q1_list)
            q2_med = sum(q2_list) / len(q2_list)

            # Estrae le medie storiche reali da ESPN (o usa baseline se squadra neopromossa)
            media_corner_casa = ottieni_media_storica(storico_espn, casa_ita, 'corners', 5.4)
            media_corner_trasf = ottieni_media_storica(storico_espn, trasf_ita, 'corners', 4.5)
            
            media_cards_casa = ottieni_media_storica(storico_espn, casa_ita, 'cards', 2.2)
            media_cards_trasf = ottieni_media_storica(storico_espn, trasf_ita, 'cards', 2.4)

            # CASO 1: Pressione Offensiva Corner (Quote + Storico Reale ESPN)
            if 1.38 <= q1_med <= 1.90 and q2_med >= 3.90:
                lambda_quote = 10.5 + ((1.90 - q1_med) * 2.1)
                lambda_storico = media_corner_casa + media_corner_trasf
                # Media pesata: 60% Storico Reale ESPN + 40% Pressione Tattica Quote
                lambda_corner = (lambda_storico * 0.60) + (lambda_quote * 0.40)
                
                prob_over_9_5 = prob_poisson_over(lambda_corner, 9.5)
                quota_target = 1.80
                edge = (prob_over_9_5 * quota_target) - 1.0
                if edge > miglior_edge and prob_over_9_5 >= 0.58:
                    miglior_edge = edge
                    miglior_operazione = {
                        'id_partita': p['id'],
                        'data': data_ita.strftime("%d/%m %H:%M"),
                        'squadra_casa': casa_ita,
                        'squadra_trasferta': trasf_ita,
                        'pronostico': "Over 9.5 Calci d'Angolo",
                        'quota': quota_target,
                        'prob': prob_over_9_5,
                        'edge': edge
                    }

            # CASO 2: Alta Tensione Cartellini (Equilibrio Quote + Storico Reale ESPN)
            elif 2.15 <= q1_med <= 3.10 and 2.15 <= q2_med <= 3.10:
                bonus_campionato = 0.7 if camp in ['soccer_italy_serie_a', 'soccer_spain_la_liga'] else 0.2
                lambda_quote = 4.6 + bonus_campionato
                lambda_storico = media_cards_casa + media_cards_trasf
                lambda_cards = (lambda_storico * 0.60) + (lambda_quote * 0.40)
                
                prob_over_4_5 = prob_poisson_over(lambda_cards, 4.5)
                quota_target = 1.75
                edge = (prob_over_4_5 * quota_target) - 1.0
                if edge > miglior_edge and prob_over_4_5 >= 0.60:
                    miglior_edge = edge
                    miglior_operazione = {
                        'id_partita': p['id'],
                        'data': data_ita.strftime("%d/%m %H:%M"),
                        'squadra_casa': casa_ita,
                        'squadra_trasferta': trasf_ita,
                        'pronostico': "Over 4.5 Cartellini Totali",
                        'quota': quota_target,
                        'prob': prob_over_4_5,
                        'edge': edge
                    }

    if not miglior_operazione: return

    b = miglior_operazione['quota'] - 1.0
    p_win = miglior_operazione['prob']
    q_lose = 1.0 - p_win
    kelly_fraction = ((b * p_win) - q_lose) / b
    stake_kelly = round(max(8.0, min(20.0, 200.0 * (kelly_fraction * 0.25))), 1)

    partita_db = {
        'id_partita': miglior_operazione['id_partita'],
        'data': miglior_operazione['data'],
        'squadra_casa': miglior_operazione['squadra_casa'],
        'squadra_trasferta': miglior_operazione['squadra_trasferta'],
        'pronostico': miglior_operazione['pronostico'],
        'quota': miglior_operazione['quota'],
        'stato': 'in attesa',
        'risultato_reale': ''
    }

    msg = "<b>⚡ MODELLO BETA | INFERENZA POISSON</b>\n\n"
    msg += f"⚽ <b>{partita_db['data']} | {partita_db['squadra_casa']} - {partita_db['squadra_trasferta']}</b>\n"
    msg += f"🎯 <b>Singola Esotica</b>: {partita_db['pronostico']}\n"
    msg += f"📊 <b>Quota Minima Consigliata</b>: @{partita_db['quota']}\n"
    msg += f"📈 <b>Probabilità Poisson</b>: {round(p_win * 100, 1)}%\n"
    msg += f"💰 <b>Stake Kelly Suggerito</b>: {stake_kelly}€\n\n"
    msg += "<b>#ModelloBeta #Poisson #ValueBetting</b>"

    res = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    if res.status_code == 200:
        db_principale['schedine'].append({
            'id': str(uuid.uuid4())[:8],
            'modello': 'beta',
            'data_creazione': oggi.strftime("%d/%m/%Y"),
            'importo': stake_kelly,
            'quota_totale': miglior_operazione['quota'],
            'ritorno_potenziale': round(stake_kelly * miglior_operazione['quota'], 2),
            'stato_schedina': 'in attesa',
            'partite': [partita_db]
        })
        salva_database_principale(db_principale)

if __name__ == "__main__":
    esegui_beta()
