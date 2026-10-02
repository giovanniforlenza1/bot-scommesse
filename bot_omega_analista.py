import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

# Campionati supportati da The Odds API (Club e Nazionali)
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
    "Bulgaria": "Bulgaria", "Estonia": "Estonia", "Luxembourg": "Lussemburgo",
    "Israel": "Israele", "Czech Republic": "Repubblica Ceca", "Slovenia": "Slovenia",
    "Greece": "Grecia", "Ireland": "Irlanda", "Lithuania": "Lituania",
    "Kosovo": "Kosovo", "North Macedonia": "Macedonia del Nord"
}

def traduci_squadra(nome):
    return TRADUZIONI_NAZIONALI.get(nome.strip(), nome.strip())

def calcola_quota_reale(quote):
    # Converte le quote del mercato nelle probabilità pure (De-vigging)
    prob_implicita = sum(1 / q for q in quote) # Questa è la lavagna (es. 1.05 = 5% di aggio)
    prob_reali = [(1 / q) / prob_implicita for q in quote]
    quote_reali = [1 / p for p in prob_reali]
    return quote_reali, prob_reali, prob_implicita

def genera_analisi_quantitativa():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    
    database_analisi = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "analisi": []}
    
    print("Avvio Modello Omega (Analisi Quantitativa e De-Vigging del Mercato)...")
    
    for camp in CAMPIONATI:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        res = requests.get(url, timeout=10)
        
        if res.status_code != 200: continue
        matches = res.json()
        
        for m in matches:
            # Calcoliamo la media del mercato globale per avere dati stabili
            q_1_list, q_x_list, q_2_list = [], [], []
            
            for book in m.get('bookmakers', []):
                for market in book.get('markets', []):
                    if market['key'] == 'h2h':
                        for out in market['outcomes']:
                            if out['name'] == m['home_team']: q_1_list.append(out['price'])
                            elif out['name'] == m['away_team']: q_2_list.append(out['price'])
                            elif out['name'] == 'Draw': q_x_list.append(out['price'])
                            
            if not q_1_list or not q_x_list or not q_2_list: continue
            
            # Quota media del mercato globale
            avg_1 = sum(q_1_list) / len(q_1_list)
            avg_x = sum(q_x_list) / len(q_x_list)
            avg_2 = sum(q_2_list) / len(q_2_list)
            
            # Matematica pura: estraiamo la quota reale senza l'aggio del bookmaker
            quote_reali, prob_reali, aggio = calcola_quota_reale([avg_1, avg_x, avg_2])
            margine_perc = round((aggio - 1) * 100, 2)
            
            home_ita = traduci_squadra(m['home_team'])
            away_ita = traduci_squadra(m['away_team'])
            
            # Selezioniamo l'esito con la probabilità reale più alta
            miglior_prob = max(prob_reali)
            indice_migliore = prob_reali.index(miglior_prob)
            
            # Filtro di sicurezza: operiamo solo su eventi con almeno il 50% di probabilità matematica
            if miglior_prob < 0.50:
                continue
                
            pronostico_str = f"vittoria {home_ita}" if indice_migliore == 0 else (f"vittoria {away_ita}" if indice_migliore == 2 else "Pareggio")
            quota_pura_fiera = round(quote_reali[indice_migliore], 2)
            
            # APPLICHIAMO L'EDGE (VANTAGGIO): Chiediamo al Cecchino di trovare una quota superiore del +4% rispetto alla quota pura matematica
            quota_valore_richiesta = round(quota_pura_fiera * 1.04, 2)
            
            testo_report = (
                f"Analisi Quantitativa (De-Vig): Il mercato applica un aggio del {margine_perc}%. "
                f"La probabilità matematica reale calcolata per la {pronostico_str} è del {round(miglior_prob*100, 1)}%, "
                f"che corrisponde a una Quota Equa (Fair Odd) di @{quota_pura_fiera}. "
                f"Per garantire un vantaggio statistico (+EV), il Modello Omega esige una Value Bet minima di @{quota_valore_richiesta}."
            )
            
            database_analisi["analisi"].append({
                "id_partita": m['id'],
                "match": f"{home_ita} - {away_ita}",
                "data": m['commence_time'],
                "consiglio_algoritmo": pronostico_str,
                "quota_valore_minima": quota_valore_richiesta,
                "report_testuale": testo_report
            })

    # Ordiniamo per probabilità (i match più sicuri in alto)
    database_analisi["analisi"] = sorted(database_analisi["analisi"], key=lambda x: x["quota_valore_minima"])
    
    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump(database_analisi, f, indent=4, ensure_ascii=False)
        
    print(f"Modello Quantitativo Omega: elaborate {len(database_analisi['analisi'])} opportunità di Value Betting.")

if __name__ == "__main__":
    genera_analisi_quantitativa()
