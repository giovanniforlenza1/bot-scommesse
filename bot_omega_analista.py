import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
# L'importazione che fonde l'Analista con il nuovo Simulatore
from bot_simulatore_montecarlo import simula_partita_montecarlo

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
    quote_reali = [1 / p for p in prob_reali]
    return quote_reali, prob_reali, prob_implicita

def genera_analisi_quantitativa():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    limite_temporale = oggi + timedelta(days=4)
    
    database_analisi = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "analisi": []}
    
    print("Avvio Modello Omega: Analisi Mercato + Simulazione Monte Carlo...")
    
    for camp in CAMPIONATI:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        res = requests.get(url, timeout=10)
        
        if res.status_code != 200: continue
        matches = res.json()
        
        for m in matches:
            data_partita_utc = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
            data_partita_ita = data_partita_utc.astimezone(fuso)
            if data_partita_ita > limite_temporale: continue
            
            q_1_list, q_x_list, q_2_list = [], [], []
            for book in m.get('bookmakers', []):
                for market in book.get('markets', []):
                    if market['key'] == 'h2h':
                        for out in market['outcomes']:
                            if out['name'] == m['home_team']: q_1_list.append(out['price'])
                            elif out['name'] == m['away_team']: q_2_list.append(out['price'])
                            elif out['name'] == 'Draw': q_x_list.append(out['price'])
                            
            if not q_1_list or not q_x_list or not q_2_list: continue
            
            avg_1 = sum(q_1_list) / len(q_1_list)
            avg_x = sum(q_x_list) / len(q_x_list)
            avg_2 = sum(q_2_list) / len(q_2_list)
            
            quote_reali, prob_reali, aggio = calcola_quota_reale([avg_1, avg_x, avg_2])
            
            home_ita = traduci_squadra(m['home_team'])
            away_ita = traduci_squadra(m['away_team'])
            
            # Traduciamo le probabilità in forza d'attacco (xG stimati) per il simulatore
            xg_casa = prob_reali[0] * 2.5
            xg_trasferta = prob_reali[2] * 2.5
            
            # Lanciamo il motore Monte Carlo su 10.000 universi paralleli
            esito_montecarlo = simula_partita_montecarlo(
                gol_fatti_casa=xg_casa, gol_subiti_casa=xg_trasferta, 
                gol_fatti_trasferta=xg_trasferta, gol_subiti_trasferta=xg_casa, 
                modulo_casa="equilibrato", modulo_trasferta="equilibrato", 
                num_simulazioni=10000
            )
            
            # Uniamo i dati: la probabilità della simulazione e la quota del mercato
            miglior_prob = max(esito_montecarlo['prob_1'], esito_montecarlo['prob_x'], esito_montecarlo['prob_2'])
            
            if miglior_prob == esito_montecarlo['prob_1']:
                pronostico_str = f"vittoria {home_ita}"
                quota_pura_fiera = round(1 / esito_montecarlo['prob_1'], 2) if esito_montecarlo['prob_1'] > 0 else 0
            elif miglior_prob == esito_montecarlo['prob_2']:
                pronostico_str = f"vittoria {away_ita}"
                quota_pura_fiera = round(1 / esito_montecarlo['prob_2'], 2) if esito_montecarlo['prob_2'] > 0 else 0
            else:
                pronostico_str = "pareggio"
                quota_pura_fiera = round(1 / esito_montecarlo['prob_x'], 2) if esito_montecarlo['prob_x'] > 0 else 0
                
            # Applichiamo il vantaggio matematico sulla quota fiera calcolata da Monte Carlo
            quota_valore_richiesta = round(quota_pura_fiera * 1.04, 2)
            
            # Filtro rigido: accettiamo solo quote finali comprese tra 1.50 e 2.00
            if not (1.50 <= quota_valore_richiesta <= 2.00):
                continue
            
            testo_report = (
                f"Analisi Ibrida completata. Dopo 10.000 simulazioni Monte Carlo sul match, "
                f"l'algoritmo rileva una probabilità di {pronostico_str} del {round(miglior_prob*100, 1)}%. "
                f"La simulazione genera una quota equa di @{quota_pura_fiera}. Il Cecchino ha l'ordine di "
                f"piazzare la giocata solo se il mercato copre la Value Bet minima di @{quota_valore_richiesta}."
            )
            
            database_analisi["analisi"].append({
                "id_partita": m['id'],
                "match": f"{home_ita} - {away_ita}",
                "data": m['commence_time'],
                "consiglio_algoritmo": pronostico_str,
                "quota_valore_minima": quota_valore_richiesta,
                "report_testuale": testo_report
            })

    database_analisi["analisi"] = sorted(database_analisi["analisi"], key=lambda x: x["quota_valore_minima"])
    
    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump(database_analisi, f, indent=4, ensure_ascii=False)
        
    print(f"Modello Omega completato: salvate {len(database_analisi['analisi'])} partite validate da Monte Carlo.")

if __name__ == "__main__":
    genera_analisi_quantitativa()
