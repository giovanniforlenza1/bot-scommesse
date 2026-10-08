import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus",
    "Hellas Verona": "Verona", "Bologna FC": "Bologna", "Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Venezia FC": "Venezia", "Parma Calcio 1913": "Parma",
    "Como 1907": "Como", "Manchester Utd": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham",
    "Newcastle Utd": "Newcastle", "Paris Saint Germain": "PSG",
    "Bayern Munich": "Bayern Monaco", "Bayer Leverkusen": "Bayer Leverkusen",
    "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad",
    "Athletic Club": "Athletic Bilbao"
}

def traduci_squadra(nome):
    nome_pulito = nome.strip()
    if nome_pulito in TRADUZIONI_NAZIONALI: return TRADUZIONI_NAZIONALI[nome_pulito]
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

def genera_multipla_quota5():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    # orizzonte temporale stretto a 3 giorni per evitare match troppo lontani
    limite_temporale = oggi + timedelta(days=3)
    
    database_alpha = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "schedine": []}
    tutte_le_partite = []
    
    for camp in CAMPIONATI:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu&markets=h2h"
        matches = esegui_richiesta_api(url_template)
        
        if not matches: continue
        
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
            if miglior_prob < 0.48: continue 
            
            home_ita = traduci_squadra(m['home_team'])
            away_ita = traduci_squadra(m['away_team'])
            
            if prob_1 > prob_2:
                pronostico = f"vittoria {home_ita}"
                quota_scelta = avg_1
            else:
                pronostico = f"vittoria {away_ita}"
                quota_scelta = avg_2
                
            if quota_scelta < 1.25: continue
                
            tutte_le_partite.append({
                "match": f"{home_ita} - {away_ita}",
                "squadra_casa": home_ita,
                "squadra_trasferta": away_ita,
                "data": data_partita.strftime("%d/%m %H:%M"),
                "pronostico": pronostico,
                "quota": round(quota_scelta, 2),
                "probabilita": round(miglior_prob * 100, 1),
                "lega": camp
            })

    # ordinamento vitale: priorità 0 per la Serie A, poi si ordina per probabilità decrescente
    tutte_le_partite = sorted(tutte_le_partite, key=lambda x: (0 if x['lega'] == 'soccer_italy_serie_a' else 1, -x['probabilita']))
    
    schedina_corrente = []
    quota_totale = 1.0
    
    for p in tutte_le_partite:
        schedina_corrente.append(p)
        quota_totale *= p['quota']
        
        # appena tocca quota 5 con un massimo di 5 eventi, salva l'unica schedina e si ferma
        if quota_totale >= 5.00:
            if len(schedina_corrente) <= 5:
                database_alpha["schedine"].append({
                    "lega": "MIX PRIORITÀ SERIE A",
                    "quota_totale": round(quota_totale, 2),
                    "partite": schedina_corrente
                })
            break

    with open('database_alpha.json', 'w', encoding='utf-8') as f:
        json.dump(database_alpha, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    genera_multipla_quota5()
