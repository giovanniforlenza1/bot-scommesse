import requests
import json
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Le chiavi vengono pescate in totale sicurezza dai Secrets
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

campionati = [
    'soccer_italy_serie_a', 
    'soccer_uefa_nations_league',
    'soccer_uefa_champs_league',
    'soccer_uefa_europa_league'
]
siti_italiani = ['Bet365', 'Snai', 'Sisal', 'Eurobet', 'PlanetWin365', 'GoldBet', 'Lottomatica', 'Betfair', 'William Hill']

def carica_database():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database(db):
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def aggiorna_risultati(db):
    risultati_live = {}
    for camp in campionati:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/scores/?apiKey={ODDS_API_KEY}&daysFrom=3"
        res = requests.get(url)
        if res.status_code == 200:
            for match in res.json():
                if match.get('completed'):
                    risultati_live[match['id']] = match.get('scores')
    
    for schedina in db['schedine']:
        if schedina['stato_schedina'] == 'in attesa':
            tutte_vinte = True
            almeno_una_persa = False
            for p in schedina['partite']:
                if p['stato'] == 'in attesa' and p['id_partita'] in risultati_live:
                    scores = risultati_live[p['id_partita']]
                    if not scores: continue
                    score_casa = int(next((s['score'] for s in scores if s['name'] == p['squadra_casa']), 0))
                    score_trasferta = int(next((s['score'] for s in scores if s['name'] == p['squadra_trasferta']), 0))
                    
                    vinta = False
                    if p['pronostico'].startswith('vittoria'):
                        vinta = score_casa > score_trasferta
                    elif 'over 2.5' in p['pronostico']:
                        vinta = (score_casa + score_trasferta) > 2
                    elif 'gol' in p['pronostico']:
                        vinta = score_casa > 0 and score_trasferta > 0
                        
                    p['stato'] = 'vinta' if vinta else 'persa'
                    p['risultato_reale'] = f"{score_casa}-{score_trasferta}"
                
                if p['stato'] == 'persa': almeno_una_persa = True
                if p['stato'] == 'in attesa': tutte_vinte = False
                
            if almeno_una_persa:
                schedina['stato_schedina'] = 'persa'
            elif tutte_vinte:
                schedina['stato_schedina'] = 'vinta'

def crea_schedina(db):
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia).date()
    fine_turno = oggi + timedelta(days=3)
    
    giocate_selezionate = []
    
    for camp in campionati:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals"
        res = requests.get(url)
        if res.status_code != 200: continue
        
        for partita in res.json():
            data_ita = datetime.strptime(partita['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if oggi <= data_ita.date() <= fine_turno and partita.get('bookmakers'):
                for book in partita['bookmakers']:
                    if book['title'] in siti_italiani:
                        quota_max = 0
                        miglior_giocata = ""
                        for mercato in book['markets']:
                            if mercato['key'] == 'h2h':
                                q = next((o['price'] for o in mercato['outcomes'] if o['name'] == partita['home_team']), 0)
                                if 1.45 <= q <= 1.95 and q > quota_max:
                                    quota_max, miglior_giocata = q, f"vittoria {partita['home_team']}"
                            elif mercato['key'] == 'totals':
                                q = next((o['price'] for o in mercato['outcomes'] if o['name'] == 'Over' and o.get('point') == 2.5), 0)
                                if 1.45 <= q <= 1.95 and q > quota_max:
                                    quota_max, miglior_giocata = q, "over 2.5 gol"
                        
                        if miglior_giocata:
                            giocate_selezionate.append({
                                'id_partita': partita['id'],
                                'data': data_ita.strftime("%d/%m %H:%M"),
                                'squadra_casa': partita['home_team'],
                                'squadra_trasferta': partita['away_team'],
                                'pronostico': miglior_giocata,
                                'quota': quota_max,
                                'stato': 'in attesa',
                                'risultato_reale': ''
                            })
                        break

    if not giocate_selezionate: return
    
    giocate_selezionate.sort(key=lambda x: x['quota'], reverse=True)
    top_4 = giocate_selezionate[:4]
    
    quota_totale = 1.0
    for g in top_4: quota_totale *= g['quota']
    quota_totale = round(quota_totale, 2)
    importo = 10.0
    
    nuova_schedina = {
        'id': str(uuid.uuid4())[:8],
        'data_creazione': datetime.now(fuso_italia).strftime("%d/%m/%Y"),
        'importo': importo,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(importo * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'partite': top_4
    }
    
    db['schedine'].append(nuova_schedina)
    
    msg = f"🔥 **NUOVA SCHEDINA MATCH LAB**\nInvestimento: {importo}€ | Quota Totale: {quota_totale}\n\n"
    for p in top_4:
        msg += f"⚽ {p['data']} | {p['squadra_casa']} - {p['squadra_trasferta']}\n🎯 {p['pronostico']} (@{p['quota']})\n\n"
    msg += "**#PronosticiCalcio #Schedina #MatchLab #ValueBetting**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    db = carica_database()
    aggiorna_risultati(db)
    crea_schedina(db)
    salva_database(db)

if __name__ == "__main__":
    main()
