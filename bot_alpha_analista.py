import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

CAMPIONATI = [
    'soccer_uefa_nations_league', 'soccer_italy_serie_a', 'soccer_epl', 
    'soccer_spain_la_liga', 'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league'
]

TRADUZIONI_NAZIONALI = {
    "Italy": "Italia", "France": "Francia", "Germany": "Germania", 
    "Spain": "Spagna", "England": "Inghilterra", "Netherlands": "Olanda", 
    "Belgium": "Belgio", "Portugal": "Portogallo", "Croatia": "Croazia", 
    "Switzerland": "Svizzera", "Poland": "Polonia", "Denmark": "Danimarca", 
    "Sweden": "Svezia", "Norway": "Norvegia", "Austria": "Austria",
    "Scotland": "Scozia", "Wales": "Galles", "Hungary": "Ungheria",
    "Turkey": "Turchia", "Albania": "Albania", "Serbia": "Serbia"
}

def traduci_squadra(nome):
    return TRADUZIONI_NAZIONALI.get(nome.strip(), nome.strip())

def genera_raddoppio_cassaforte():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    limite_temporale = oggi + timedelta(days=5)
    
    database_alpha = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "schedine": []}
    
    partite_sicure = []
    
    for camp in CAMPIONATI:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        res = requests.get(url, timeout=10)
        
        if res.status_code != 200: continue
        matches = res.json()
        
        for m in matches:
            data_partita = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso)
            if data_partita > limite_temporale: continue
            
            q_1_list, q_x_list, q_2_list = [], [], []
            for book in m.get('bookmakers', []):
                for market in book.get('markets', []):
                    if market['key'] == 'h2h':
                        for out in market['outcomes']:
                            if out['name'] == m['home_team']: q_1_list.append(out['price'])
                            elif out['name'] == m['away_team']: q_2_list.append(out['price'])
                            elif out['name'] == 'Draw': q_x_list.append(out['price'])
                            
            if not q_1_list or not q_x_list or not q_2_list: continue
            
            avg_1 = sum(q_1_list)/len(q_1_list)
            avg_x = sum(q_x_list)/len(q_x_list)
            avg_2 = sum(q_2_list)/len(q_2_list)
            
            prob_implicita = (1/avg_1) + (1/avg_x) + (1/avg_2)
            prob_1 = (1/avg_1) / prob_implicita
            prob_2 = (1/avg_2) / prob_implicita
            
            miglior_prob = max(prob_1, prob_2)
            if miglior_prob < 0.60: continue 
            
            home_ita = traduci_squadra(m['home_team'])
            away_ita = traduci_squadra(m['away_team'])
            
            if prob_1 > prob_2:
                pronostico = f"vittoria {home_ita}"
                quota_scelta = avg_1
            else:
                pronostico = f"vittoria {away_ita}"
                quota_scelta = avg_2
                
            if quota_scelta < 1.25: continue
                
            partite_sicure.append({
                "match": f"{home_ita} - {away_ita}",
                "squadra_casa": home_ita,
                "squadra_trasferta": away_ita,
                "data": data_partita.strftime("%d/%m %H:%M"),
                "pronostico": pronostico,
                "quota": round(quota_scelta, 2),
                "probabilita": round(miglior_prob * 100, 1)
            })

    partite_sicure = sorted(partite_sicure, key=lambda x: x["probabilita"], reverse=True)
    
    schedina_corrente = []
    quota_totale = 1.0
    
    for p in partite_sicure:
        schedina_corrente.append(p)
        quota_totale *= p['quota']
        
        if quota_totale >= 1.80:
            if len(schedina_corrente) <= 5:
                database_alpha["schedine"].append({
                    "quota_totale": round(quota_totale, 2),
                    "partite": schedina_corrente
                })
            schedina_corrente = []
            quota_totale = 1.0

    with open('database_alpha.json', 'w', encoding='utf-8') as f:
        json.dump(database_alpha, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    genera_raddoppio_cassaforte()
