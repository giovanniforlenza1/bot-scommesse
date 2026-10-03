import requests
import json
import os
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

CAMPIONATI = [
    'soccer_uefa_nations_league', 'soccer_italy_serie_a', 'soccer_epl', 
    'soccer_spain_la_liga', 'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league'
]

# Il "DNA" dei campionati: coefficienti storici per adattare la matematica alla realtà del campo
MOLTIPLICATORI_LEGA = {
    'soccer_uefa_nations_league': {'cartellini': 1.05, 'angoli': 0.95}, # Partite nazionali tese, ritmi più lenti
    'soccer_italy_serie_a': {'cartellini': 1.15, 'angoli': 0.95},       # Molti falli tattici, arbitri severi
    'soccer_epl': {'cartellini': 0.80, 'angoli': 1.20},                 # Ritmi altissimi, molti angoli, arbitri permissivi
    'soccer_spain_la_liga': {'cartellini': 1.25, 'angoli': 0.90},       # Record europeo di cartellini rossi e gialli
    'soccer_germany_bundesliga': {'cartellini': 0.90, 'angoli': 1.10},  # Calcio offensivo, meno falli
    'soccer_france_ligue_one': {'cartellini': 1.10, 'angoli': 1.00},    # Molto fisica, cartellini sopra la media
    'soccer_uefa_champs_league': {'cartellini': 0.95, 'angoli': 1.05},  # Arbitraggi europei standardizzati
    'soccer_uefa_europa_league': {'cartellini': 1.05, 'angoli': 1.05}
}

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

def calcola_quota_reale(quote):
    prob_implicita = sum(1 / q for q in quote) 
    prob_reali = [(1 / q) / prob_implicita for q in quote]
    return prob_reali

def poisson_over_prob(lam, target):
    prob_under_or_equal = sum((math.exp(-lam) * (lam**k)) / math.factorial(k) for k in range(math.floor(target) + 1))
    return 1 - prob_under_or_equal

def calcola_kelly(prob_vincita, quota_offerta):
    # Criterio di Kelly per il money management: calcola la % di cassa da investire
    b = quota_offerta - 1.0
    p = prob_vincita
    q = 1.0 - p
    f_star = (b * p - q) / b
    
    # Kelly frazionato (es. 25% o 50%) per ridurre ulteriormente la volatilità e proteggere il capitale
    kelly_prudente = f_star * 0.25 
    
    if kelly_prudente <= 0: return 0
    # Limitiamo l'esposizione massima al 5% del bankroll per singola scommessa
    return round(min(kelly_prudente * 100, 5.0), 1)

def genera_analisi_esotica():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    limite_temporale = oggi + timedelta(days=2)
    
    database_beta = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "segnali": []}
    
    print("Avvio Modello Beta 2.0: Inferenza, League DNA e Criterio di Kelly...")
    
    for camp in CAMPIONATI:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        res = requests.get(url, timeout=10)
        
        if res.status_code != 200: continue
        matches = res.json()
        
        moltiplicatori = MOLTIPLICATORI_LEGA.get(camp, {'cartellini': 1.0, 'angoli': 1.0})
        
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
            prob_reali = calcola_quota_reale([avg_1, avg_x, avg_2])
            
            home_ita = traduci_squadra(m['home_team'])
            away_ita = traduci_squadra(m['away_team'])
            
            # MODELLO CARTELLINI integrato con il DNA della lega
            tensione_match = prob_reali[1] / 0.35 
            cartellini_attesi = (3.5 + (tensione_match * 2.5)) * moltiplicatori['cartellini']
            prob_over_4_5_cards = poisson_over_prob(cartellini_attesi, 4.5)
            
            # MODELLO ANGOLI integrato con il DNA della lega
            squilibrio = abs(prob_reali[0] - prob_reali[2])
            angoli_attesi = (8.5 + (squilibrio * 4.0)) * moltiplicatori['angoli']
            prob_over_9_5_corners = poisson_over_prob(angoli_attesi, 9.5)
            
            # Valutazione Cartellini
            if prob_over_4_5_cards > 0.55:
                quota_equa = round((1 / prob_over_4_5_cards) * 1.05, 2) 
                if 1.50 <= quota_equa <= 2.00:
                    stake_suggerito = calcola_kelly(prob_over_4_5_cards, quota_equa)
                    if stake_suggerito > 0:
                        database_beta["segnali"].append({
                            "match": f"{home_ita} - {away_ita}",
                            "data": data_partita.strftime("%d/%m %H:%M"),
                            "mercato": "Cartellini",
                            "pronostico": "Over 4.5 Cartellini Gialli/Rossi",
                            "probabilita": round(prob_over_4_5_cards * 100, 1),
                            "quota_ingresso_minima": quota_equa,
                            "stake_cassa_perc": stake_suggerito
                        })
                    
            # Valutazione Angoli
            if prob_over_9_5_corners > 0.55:
                quota_equa = round((1 / prob_over_9_5_corners) * 1.05, 2)
                if 1.50 <= quota_equa <= 2.00:
                    stake_suggerito = calcola_kelly(prob_over_9_5_corners, quota_equa)
                    if stake_suggerito > 0:
                        database_beta["segnali"].append({
                            "match": f"{home_ita} - {away_ita}",
                            "data": data_partita.strftime("%d/%m %H:%M"),
                            "mercato": "Calci d'Angolo",
                            "pronostico": "Over 9.5 Calci d'Angolo",
                            "probabilita": round(prob_over_9_5_corners * 100, 1),
                            "quota_ingresso_minima": quota_equa,
                            "stake_cassa_perc": stake_suggerito
                        })

    # Ordiniamo per valore di Stake (le puntate matematicamente più redditizie in cima)
    database_beta["segnali"] = sorted(database_beta["segnali"], key=lambda x: x["stake_cassa_perc"], reverse=True)
    
    with open('database_beta.json', 'w', encoding='utf-8') as f:
        json.dump(database_beta, f, indent=4, ensure_ascii=False)
        
    print(f"Modello Beta: Trovati {len(database_beta['segnali'])} segnali con Money Management applicato.")

if __name__ == "__main__":
    genera_analisi_esotica()
