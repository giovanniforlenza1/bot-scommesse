import requests
import json
import os
import uuid
import math
import html
import base64
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")
CHAT_ID = os.environ.get("CHAT_ID")

campionati = [
    'soccer_italy_serie_a', 'soccer_epl', 'soccer_spain_la_liga',
    'soccer_germany_bundesliga', 'soccer_france_ligue_one'
]

MAPPA_CAMPIONATI_ESPN = {
    'soccer_italy_serie_a': 'ita.1', 'soccer_epl': 'eng.1',
    'soccer_spain_la_liga': 'esp.1', 'soccer_germany_bundesliga': 'ger.1',
    'soccer_france_ligue_one': 'fra.1'
}

SEVERITA_ARBITRALE_LEGA = {
    'soccer_spain_la_liga': 0.95,
    'soccer_italy_serie_a': 0.80,
    'soccer_france_ligue_one': 0.45,
    'soccer_germany_bundesliga': 0.35,
    'soccer_epl': 0.30
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

def cripta_dati_sensibili(lista_partite):
    raw_bytes = json.dumps(lista_partite, ensure_ascii=False).encode('utf-8')
    key_hash = hashlib.sha256(TELEGRAM_TOKEN.encode('utf-8')).digest()
    xored = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(raw_bytes)])
    return base64.b64encode(xored).decode('ascii')

def crea_partite_offuscate_per_sito(lista_partite):
    return [{
        'id_partita': 'protetto',
        'data': p.get('data', ''),
        'squadra_casa': '🔒 Singola Esotica',
        'squadra_trasferta': 'In Corso',
        'pronostico': 'Poisson Riservato',
        'quota': p.get('quota', 1.0),
        'stato': 'in attesa',
        'risultato_reale': ''
    } for p in lista_partite]

def traduci_squadra(nome):
    nome_pulito = str(nome).strip()
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
    storico_squadre = {}
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    inizio_oggi = oggi.replace(hour=0, minute=0, second=0, microsecond=0)
    limite_temporale = inizio_oggi + timedelta(days=5)
    if data_ita < inizio_oggi or data_ita > limite_temporale: continue
    date_studio = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in [1, 2, 3, 4, 6, 7, 8, 10, 13, 14]]

    for _, lega_espn in MAPPA_CAMPIONATI_ESPN.items():
        for d_str in date_studio:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega_espn}/scoreboard?dates={d_str}"
            try:
                res = requests.get(url, timeout=6)
                if res.status_code != 200: continue
                for ev in res.json().get('events', []):
                    comp = ev.get('competitions', [{}])[0]
                    if not comp.get('status', {}).get('type', {}).get('completed', False): continue
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
            except: continue
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

def calcola_cassa_beta(db):
    cassa = 200.0
    for s in db.get('schedine', []):
        if s.get('modello') == 'beta' and s.get('stato_schedina') in ['vinta', 'persa']:
            imp = float(s.get('importo', 10.0))
            rit = float(s.get('ritorno_potenziale', 0.0))
            cassa += (rit - imp) if s['stato_schedina'] == 'vinta' else -imp
    return max(140.0, cassa)

def esegui_beta():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    limite_temporale = oggi + timedelta(days=3)
    
    db_principale = carica_database_principale()
    for s in db_principale['schedine']:
        if s.get('modello') == 'beta' and s.get('data_creazione') == oggi.strftime("%d/%m/%Y"):
            print("Beta già generata oggi.")
            return

    storico_espn = costruisci_storico_reale_espn()
    miglior_operazione, miglior_score = None, 0.0

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

            media_corner_casa = ottieni_media_storica(storico_espn, casa_ita, 'corners', 5.5)
            media_corner_trasf = ottieni_media_storica(storico_espn, trasf_ita, 'corners', 4.6)
            media_cards_casa = ottieni_media_storica(storico_espn, casa_ita, 'cards', 2.2)
            media_cards_trasf = ottieni_media_storica(storico_espn, trasf_ita, 'cards', 2.4)

            if 1.32 <= q1_med <= 1.95 and q2_med >= 3.60:
                lambda_quote = 10.6 + ((1.95 - q1_med) * 2.2)
                lambda_storico = media_corner_casa + media_corner_trasf
                lambda_corner = (lambda_storico * 0.65) + (lambda_quote * 0.35)
                
                prob_over_8_5 = prob_poisson_over(lambda_corner, 8.5)
                quota_target = 1.60
                edge = (prob_over_8_5 * quota_target) - 1.0
                if prob_over_8_5 >= 0.64 and edge > miglior_score:
                    miglior_score = edge
                    miglior_operazione = {
                        'id_partita': p['id'], 'data': data_ita.strftime("%d/%m %H:%M"),
                        'squadra_casa': casa_ita, 'squadra_trasferta': trasf_ita,
                        'pronostico': "Over 8.5 Calci d'Angolo", 'quota': quota_target,
                        'prob': prob_over_8_5, 'edge': edge
                    }

            elif 2.00 <= q1_med <= 3.40 and 2.00 <= q2_med <= 3.40:
                bonus_arbitro = SEVERITA_ARBITRALE_LEGA.get(camp, 0.35)
                lambda_quote = 4.5 + bonus_arbitro
                lambda_storico = media_cards_casa + media_cards_trasf
                lambda_cards = (lambda_storico * 0.65) + (lambda_quote * 0.35)
                
                prob_over_3_5 = prob_poisson_over(lambda_cards, 3.5)
                quota_target = 1.55
                edge = (prob_over_3_5 * quota_target) - 1.0
                if prob_over_3_5 >= 0.65 and edge > miglior_score:
                    miglior_score = edge
                    miglior_operazione = {
                        'id_partita': p['id'], 'data': data_ita.strftime("%d/%m %H:%M"),
                        'squadra_casa': casa_ita, 'squadra_trasferta': trasf_ita,
                        'pronostico': "Over 3.5 Cartellini Totali", 'quota': quota_target,
                        'prob': prob_over_3_5, 'edge': edge
                    }

    if not miglior_operazione: return

    cassa_attuale = calcola_cassa_beta(db_principale)
    b = miglior_operazione['quota'] - 1.0
    p_win = miglior_operazione['prob']
    kelly_fraction = ((b * p_win) - (1.0 - p_win)) / b
    stake_kelly = round(max(12.0, min(22.0, cassa_attuale * (kelly_fraction * 0.35))), 1)

    partita_reale = [{
        'id_partita': miglior_operazione['id_partita'],
        'data': miglior_operazione['data'],
        'squadra_casa': miglior_operazione['squadra_casa'],
        'squadra_trasferta': miglior_operazione['squadra_trasferta'],
        'pronostico': miglior_operazione['pronostico'],
        'quota': miglior_operazione['quota'],
        'stato': 'in attesa',
        'risultato_reale': ''
    }]

    c_casa = html.escape(miglior_operazione['squadra_casa'])
    c_trasf = html.escape(miglior_operazione['squadra_trasferta'])
    c_pron = html.escape(miglior_operazione['pronostico'])

    msg = "<b>⚡ MODELLO BETA | INFERENZA POISSON</b>\n\n"
    msg += f"⚽ <b>{miglior_operazione['data']} | {c_casa} - {c_trasf}</b>\n"
    msg += f"🎯 <b>Singola ad Alta Confidenza</b>: {c_pron}\n"
    msg += f"📊 <b>Quota Consigliata</b>: @{miglior_operazione['quota']}\n"
    msg += f"📈 <b>Probabilità Stimata</b>: {round(p_win * 100, 1)}%\n"
    msg += f"💰 <b>Stake Kelly</b>: {stake_kelly}€\n\n"
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
            'payload_criptato': cripta_dati_sensibili(partita_reale),
            'partite': crea_partite_offuscate_per_sito(partita_reale)
        })
        salva_database_principale(db_principale)

if __name__ == "__main__":
    esegui_beta()
