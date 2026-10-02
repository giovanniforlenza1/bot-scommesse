import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_OMEGA_KEY")
LEGHE_TARGET = [5, 34, 4, 15, 135, 39, 140, 78, 61, 2, 3] 

def genera_analisi_giornaliera():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    headers = {'x-apisports-key': API_FOOTBALL_KEY}
    
    database_analisi = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "analisi": []}
    partite_valide = []
    
    print("Ricerca calendario top match (Club e Nazionali) per oggi e domani...")
    
    for giorni_avanti in range(2):
        data_target = (oggi + timedelta(days=giorni_avanti)).strftime("%Y-%m-%d")
        res = requests.get(f"https://v3.football.api-sports.io/fixtures?date={data_target}", headers=headers)
        
        if res.status_code == 200:
            dati = res.json()
            for m in dati.get('response', []):
                if m['league']['id'] in LEGHE_TARGET:
                    partite_valide.append(m)

    partite_valide = partite_valide[:15]
    print(f"Isolate {len(partite_valide)} partite di cartello.")
    
    for m in partite_valide:
        home_name = m['teams']['home']['name']
        away_name = m['teams']['away']['name']
        
        # Non potendo estrarre statistiche gratuite, passiamo il match al Cecchino
        # impostando una ricerca generica per quote di valore sugli Over 2.5
        
        testo = f"Top match internazionale individuato: {home_name}-{away_name}. Il modello Omega delega la valutazione esclusivamente al tracking delle quote in tempo reale."
        
        database_analisi["analisi"].append({
            "id_partita": str(m['fixture']['id']),
            "match": f"{home_name} - {away_name}",
            "data": m['fixture']['date'],
            "consiglio_algoritmo": "Over 2.5",
            "quota_valore_minima": 1.65,
            "report_testuale": testo
        })
        
    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump(database_analisi, f, indent=4, ensure_ascii=False)
        
    print(f"\nModello Omega Analista: calendario compilato. {len(partite_valide)} partite pronte per il Cecchino.")

if __name__ == "__main__":
    genera_analisi_giornaliera()
