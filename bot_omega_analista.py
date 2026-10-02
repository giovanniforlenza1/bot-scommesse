import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

# campionati supportati da The Odds API (club e nazionali)
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
    # converte le quote del mercato nelle probabilità pure calcolando l'aggio
    prob_implicita = sum(1 / q for q in quote) 
    prob_reali = [(1 / q) / prob_implicita for q in quote]
    quote_reali = [1 / p for p in prob_reali]
    return quote_reali, prob_reali, prob_implicita

def genera_analisi_quantitativa():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    
    # limite temporale impostato a 4 giorni da oggi
    limite_temporale = oggi + timedelta(days=4)
    
    database_analisi = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "analisi": []}
    
    print("avvio modello Omega (analisi quantitativa con filtro temporale e quote medie)...")
    
    for camp in CAMPIONATI:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        res = requests.get(url, timeout=10)
        
        if res.status_code != 200: continue
        matches = res.json()
        
        for m in matches:
            # parsing della data della partita e applicazione del filtro temporale
            data_partita_utc = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
            data_partita_ita = data_partita_utc.astimezone(fuso)
            
            if data_partita_ita > limite_temporale:
                continue # scartiamo le partite che si giocano tra più di 4 giorni
            
            q_1_list, q_x_list, q_2_list = [], [], []
            
            for book in m.get('bookmakers', []):
                for market in book.get('markets', []):
                    if market['key'] == 'h2h':
                        for out in market['outcomes']:
                            if out['name'] == m['home_team']: q_1_list.append(out['price'])
                            elif out['name'] == m['away_team']: q_2_list.append(out['price'])
                            elif out['name'] == 'Draw': q_x_list.append(out['price'])
                            
            if not q_1_list or not q_x_list or not q_2_list: continue
            
            # quota media del mercato globale
            avg_1 = sum(q_1_list) / len(q_1_list)
            avg_x = sum(q_x_list) / len(q_x_list)
            avg_2 = sum(q_2_list) / len(q_2_list)
            
            # estrazione quota reale eliminando il margine del banco
            quote_reali, prob_reali, aggio = calcola_quota_reale([avg_1, avg_x, avg_2])
            margine_perc = round((aggio - 1) * 100, 2)
            
            home_ita = traduci_squadra(m['home_team'])
            away_ita = traduci_squadra(m['away_team'])
            
            # selezioniamo l'esito con la probabilità più alta in assoluto
            miglior_prob = max(prob_reali)
            indice_migliore = prob_reali.index(miglior_prob)
                
            pronostico_str = f"vittoria {home_ita}" if indice_migliore == 0 else (f"vittoria {away_ita}" if indice_migliore == 2 else "pareggio")
            quota_pura_fiera = round(quote_reali[indice_migliore], 2)
            
            # applichiamo il vantaggio matematico del 4% sulla quota
            quota_valore_richiesta = round(quota_pura_fiera * 1.04, 2)
            
            # filtro rigido per alta probabilità: accettiamo solo quote finali comprese esattamente tra 1.50 e 2.00
            if not (1.50 <= quota_valore_richiesta <= 2.00):
                continue
            
            testo_report = (
                f"analisi quantitativa del mercato: i bookmaker applicano un aggio del {margine_perc}%. "
                f"la probabilità matematica di successo per la {pronostico_str} è del {round(miglior_prob*100, 1)}%, "
                f"corrispondente a una quota equa di @{quota_pura_fiera}. "
                f"il modello Omega esige l'ingresso a una quota minima di @{quota_valore_richiesta} per mantenere il vantaggio statistico in questo range di sicurezza."
            )
            
            database_analisi["analisi"].append({
                "id_partita": m['id'],
                "match": f"{home_ita} - {away_ita}",
                "data": m['commence_time'],
                "consiglio_algoritmo": pronostico_str,
                "quota_valore_minima": quota_valore_richiesta,
                "report_testuale": testo_report
            })

    # ordiniamo gli eventi in base alla quota dalla più bassa e sicura alla più alta nel range
    database_analisi["analisi"] = sorted(database_analisi["analisi"], key=lambda x: x["quota_valore_minima"])
    
    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump(database_analisi, f, indent=4, ensure_ascii=False)
        
    print(f"modello Omega aggiornato: elaborate {len(database_analisi['analisi'])} partite ottimali nei prossimi 4 giorni.")

if __name__ == "__main__":
    genera_analisi_quantitativa()
