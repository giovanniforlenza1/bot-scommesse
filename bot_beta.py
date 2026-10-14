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

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus",
    "Hellas Verona": "Verona", "Bologna FC": "Bologna", "Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Venezia FC": "Venezia", "Parma Calcio 1913": "Parma",
    "Como 1907": "Como", "Manchester Utd": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham",
    "Newcastle Utd": "Newcastle", "Paris Saint Germain": "PSG",
    "Bayern Munich": "Bayern Monaco", "Bayer Leverkusen": "Bayer Leverkusen"
}

def traduci_squadra(nome):
    nome_pulito = nome.strip()
    if nome_pulito in TRADUZIONI_SQUADRE: return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "")

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

def prob_poisson_over(lmbda, linea):
    # Calcola probabilità che escano più eventi della linea (es. Over 9.5 -> almeno 10)
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
                for m in book.get('markets', []):
                    if m['key'] == 'h2h':
                        for out in m['outcomes']:
                            if out['name'] == casa_orig: q1_list.append(out['price'])
                            elif out['name'] == trasf_orig: q2_list.append(out['price'])

            if not q1_list or not q2_list: continue
            q1_med = sum(q1_list) / len(q1_list)
            q2_med = sum(q2_list) / len(q2_list)

            # CASO 1: Pressione Offensiva Corner (Favorita in casa tra 1.40 e 1.85 contro difesa chiusa)
            if 1.40 <= q1_med <= 1.85 and q2_med >= 4.20:
                lambda_corner = 10.6 + ((1.85 - q1_med) * 2.2)
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

            # CASO 2: Alta Tensione Cartellini (Match in totale equilibrio / Scontro Diretto)
            elif 2.25 <= q1_med <= 2.95 and 2.25 <= q2_med <= 2.95:
                bonus_campionato = 0.8 if camp in ['soccer_italy_serie_a', 'soccer_spain_la_liga'] else 0.2
                lambda_cards = 4.6 + bonus_campionato
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

    # Calcolo Criterio di Kelly Frazionato (1/4 di Kelly su cassa 200€)
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

    msg = "**⚡ MODELLO BETA | INFERENZA POISSON**\n\n"
    msg += f"⚽ **{partita_db['data']} | {partita_db['squadra_casa']} - {partita_db['squadra_trasferta']}**\n"
    msg += f"🎯 **Singola Esotica**: {partita_db['pronostico']}\n"
    msg += f"📊 **Quota Minima Consigliata**: @{partita_db['quota']}\n"
    msg += f"📈 **Probabilità Poisson**: {round(p_win * 100, 1)}%\n"
    msg += f"💰 **Stake Kelly Suggerito**: {stake_kelly}€\n\n"
    msg += "**#ModelloBeta #Poisson #ValueBetting**"

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    salva_database_principale(db_principale)

if __name__ == "__main__":
    esegui_beta()
