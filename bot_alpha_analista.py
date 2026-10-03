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
    "Turkey": "Turchia", "Albania": "Albania", "Serbia": "Serbia",
    "Kazakhstan": "Kazakistan", "Moldova": "Moldavia", "Cyprus": "Cipro",
    "Armenia": "Armenia", "Latvia": "Lettonia", "Montenegro": "Montenegro",
    "Georgia": "Georgia", "Ukraine": "Ucraina", "Northern Ireland": "Irlanda del Nord",
    "Romania": "Romania", "Bosnia & Herzegovina": "Bosnia Erzegovina",
    "Faroe Islands": "Isole Faroe", "Slovakia": "Slovacchia", "Finland": "Finlandia",
    "Belarus": "Bielorussia", "San Marino": "San Marino", "Iceland": "Islanda",
    "Bulgaria": "Bulgaria", "Estonia": "Estonia", "Luxembourg": "Lussemburgo"
}

def traduci_squadra(nome):
    return TRADUZIONI_NAZIONALI.get(nome.strip(), nome.strip())

def calcola_quota_reale(quote):
    prob_implicita = sum(1 / q for q in quote) 
    prob_reali = [(1 / q) / prob_implicita for q in quote]
    return prob_reali, quote

def calcola_dutching_dnb(quota_favorita, quota_pareggio):
    # calcoliamo la percentuale di cassa da mettere sulla X per avere il rimborso totale
    stake_copertura_x = 1 / quota_pareggio
    # il resto va sulla vittoria della favorita
    stake_vittoria = 1 - stake_copertura_x
    
    # la quota sintetica reale che otteniamo al netto della copertura
    quota_sintetica_dnb = (stake_vittoria * quota_favorita)
    return round(quota_sintetica_dnb, 2), round(stake_vittoria * 100, 1), round(stake_copertura_x * 100, 1)

def genera_analisi_sicurezza():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    limite_temporale = oggi + timedelta(days=2)
    
    database_alpha = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "cassaforte": []}
    
    print("avvio Modello Alpha: costruzione quote sintetiche protette (Dutching)...")
    
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
            
            avg_1, avg_x, avg_2 = sum(q_1_list)/len(q_1_list), sum(q_x_list)/len(q_x_list), sum(q_2_list)/len(q_2_list)
            prob_reali, quote_medie = calcola_quota_reale([avg_1, avg_x, avg_2])
            
            # alpha interviene solo se c'è una favorita con almeno il 50% di probabilità pura
            miglior_prob = max(prob_reali[0], prob_reali[2])
            if miglior_prob < 0.50: continue
            
            home_ita = traduci_squadra(m['home_team'])
            away_ita = traduci_squadra(m['away_team'])
            
            if prob_reali[0] > prob_reali[2]:
                squadra_fav = home_ita
                q_fav = avg_1
                pronostico = "1 DNB Sintetico"
            else:
                squadra_fav = away_ita
                q_fav = avg_2
                pronostico = "2 DNB Sintetico"
                
            quota_sintetica, split_fav, split_x = calcola_dutching_dnb(q_fav, avg_x)
            
            # operiamo solo se la quota sintetica pulita vale almeno 1.15
            if quota_sintetica >= 1.15:
                database_alpha["cassaforte"].append({
                    "match": f"{home_ita} - {away_ita}",
                    "data": data_partita.strftime("%d/%m %H:%M"),
                    "favorita": squadra_fav,
                    "pronostico": pronostico,
                    "quota_protetta": quota_sintetica,
                    "probabilita_vittoria": round(miglior_prob * 100, 1),
                    "split_cassa_vittoria": split_fav,
                    "split_cassa_pareggio": split_x
                })

    # ordiniamo dalla più probabile alla meno probabile per blindare il profitto
    database_alpha["cassaforte"] = sorted(database_alpha["cassaforte"], key=lambda x: x["probabilita_vittoria"], reverse=True)
    
    with open('database_alpha.json', 'w', encoding='utf-8') as f:
        json.dump(database_alpha, f, indent=4, ensure_ascii=False)
        
    print(f"Modello Alpha: generate {len(database_alpha['cassaforte'])} roccaforti matematiche.")

if __name__ == "__main__":
    genera_analisi_sicurezza()
