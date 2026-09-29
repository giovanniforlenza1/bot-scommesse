import requests
import json
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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

TRADUZIONI_NAZIONALI = {
    "Italy": "Italia", "France": "Francia", "Germany": "Germania", 
    "Spain": "Spagna", "England": "Inghilterra", "Netherlands": "Olanda", 
    "Belgium": "Belgio", "Portugal": "Portogallo", "Croatia": "Croazia", 
    "Switzerland": "Svizzera", "Poland": "Polonia", "Denmark": "Danimarca", 
    "Sweden": "Svezia", "Norway": "Norvegia", "Austria": "Austria", 
    "Scotland": "Scozia", "Wales": "Galles", "Hungary": "Ungheria", 
    "Turkey": "Turchia", "Albania": "Albania", "Serbia": "Serbia",
    "Finland": "Finlandia", "Belarus": "Bielorussia", "Czech Republic": "Repubblica Ceca",
    "Slovakia": "Slovacchia", "Slovenia": "Slovenia", "Romania": "Romania",
    "Bulgaria": "Bulgaria", "Greece": "Grecia", "Iceland": "Islanda",
    "Republic of Ireland": "Irlanda", "Northern Ireland": "Irlanda del Nord",
    "Bosnia and Herzegovina": "Bosnia ed Erzegovina", "Montenegro": "Montenegro",
    "North Macedonia": "Macedonia del Nord", "Georgia": "Georgia", "Ukraine": "Ucraina",
    "Lithuania": "Lituania", "Latvia": "Lettonia", "Estonia": "Estonia",
    "Cyprus": "Cipro", "Malta": "Malta", "Moldova": "Moldavia", "Andorra": "Andorra",
    "San Marino": "San Marino", "Liechtenstein": "Liechtenstein", "Luxembourg": "Lussemburgo",
    "Armenia": "Armenia", "Azerbaijan": "Azerbaigian", "Kazakhstan": "Kazakistan",
    "Kosovo": "Kosovo", "Israel": "Israele", "Faroe Islands": "Isole Faroe",
    "Gibraltar": "Gibilterra"
}

def traduci_squadra(nome_inglese):
    nome_pulito = nome_inglese.strip()
    return TRADUZIONI_NAZIONALI.get(nome_pulito, nome_pulito)

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
                    
                    squadra_casa_originale = ""
                    squadra_trasferta_originale = ""
                    for s in scores:
                        if traduci_squadra(s['name']) == p['squadra_casa']:
                            squadra_casa_originale = s['name']
                        if traduci_squadra(s['name']) == p['squadra_trasferta']:
                            squadra_trasferta_originale = s['name']
                            
                    score_casa = int(next((s['score'] for s in scores if s['name'] == squadra_casa_originale), 0))
                    score_trasferta = int(next((s['score'] for s in scores if s['name'] == squadra_trasferta_originale), 0))
                    
                    vinta = False
                    if p['pronostico'] == f"vittoria {p['squadra_casa']}":
                        vinta = score_casa > score_trasferta
                    elif p['pronostico'] == f"vittoria {p['squadra_trasferta']}":
                        vinta = score_trasferta > score_casa
                    elif p['pronostico'] == "pareggio":
                        vinta = score_casa == score_trasferta
                    elif p['pronostico'] == "over 2.5 gol":
                        vinta = (score_casa + score_trasferta) > 2
                    elif p['pronostico'] == "under 2.5 gol":
                        vinta = (score_casa + score_trasferta) < 3
                    elif p['pronostico'] == "gol (entrambe segnano)":
                        vinta = score_casa > 0 and score_trasferta > 0
                    elif p['pronostico'] == "no gol":
                        vinta = score_casa == 0 or score_trasferta == 0
                        
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
        # sistema di sicurezza a doppio binario per evitare il crash dell'api
        url_completo = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals,btts"
        res = requests.get(url_completo)
        
        if res.status_code != 200:
            url_sicuro = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals"
            res = requests.get(url_sicuro)
            if res.status_code != 200:
                continue
        
        for partita in res.json():
            data_ita = datetime.strptime(partita['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if oggi <= data_ita.date() <= fine_turno and partita.get('bookmakers'):
                for book in partita['bookmakers']:
                    if book['title'] in siti_italiani:
                        quota_max = 0
                        miglior_giocata = ""
                        
                        for mercato in book['markets']:
                            if mercato['key'] == 'h2h':
                                q1 = next((o['price'] for o in mercato['outcomes'] if o['name'] == partita['home_team']), 0)
                                if 1.45 <= q1 <= 1.95 and q1 > quota_max:
                                    quota_max, miglior_giocata = q1, f"vittoria {traduci_squadra(partita['home_team'])}"
                                    
                                q2 = next((o['price'] for o in mercato['outcomes'] if o['name'] == partita['away_team']), 0)
                                if 1.45 <= q2 <= 1.95 and q2 > quota_max:
                                    quota_max, miglior_giocata = q2, f"vittoria {traduci_squadra(partita['away_team'])}"
                                    
                                qx = next((o['price'] for o in mercato['outcomes'] if o['name'] == 'Draw'), 0)
                                if 1.45 <= qx <= 1.95 and qx > quota_max:
                                    quota_max, miglior_giocata = qx, "pareggio"
                                    
                            elif mercato['key'] == 'totals':
                                q_over = next((o['price'] for o in mercato['outcomes'] if o['name'] == 'Over' and o.get('point') == 2.5), 0)
                                if 1.45 <= q_over <= 1.95 and q_over > quota_max:
                                    quota_max, miglior_giocata = q_over, "over 2.5 gol"
                                    
                                q_under = next((o['price'] for o in mercato['outcomes'] if o['name'] == 'Under' and o.get('point') == 2.5), 0)
                                if 1.45 <= q_under <= 1.95 and q_under > quota_max:
                                    quota_max, miglior_giocata = q_under, "under 2.5 gol"
                                    
                            elif mercato['key'] == 'btts':
                                q_gol = next((o['price'] for o in mercato['outcomes'] if o['name'] == 'Yes'), 0)
                                if 1.45 <= q_gol <= 1.95 and q_gol > quota_max:
                                    quota_max, miglior_giocata = q_gol, "gol (entrambe segnano)"
                                    
                                q_nogol = next((o['price'] for o in mercato['outcomes'] if o['name'] == 'No'), 0)
                                if 1.45 <= q_nogol <= 1.95 and q_nogol > quota_max:
                                    quota_max, miglior_giocata = q_nogol, "no gol"
                        
                        if miglior_giocata:
                            giocate_selezionate.append({
                                'id_partita': partita['id'],
                                'data': data_ita.strftime("%d/%m %H:%M"),
                                'squadra_casa': traduci_squadra(partita['home_team']),
                                'squadra_trasferta': traduci_squadra(partita['away_team']),
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
    
    msg = f"📊 **NUOVA RICEVUTA SBR | MODELLO ALPHA**\ncapitale simulato: {importo}€ | quota totale: {quota_totale}\n\n"
    for p in top_4:
        msg += f"⚽ {p['data']} | {p['squadra_casa']} - {p['squadra_trasferta']}\n🎯 {p['pronostico']} (@{p['quota']})\n\n"
    msg += "**#SBR #PronosticiCalcio #ValueBetting #ModelloAlpha**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    db = carica_database()
    aggiorna_risultati(db)
    crea_schedina(db)
    salva_database(db)

if __name__ == "__main__":
    main()
