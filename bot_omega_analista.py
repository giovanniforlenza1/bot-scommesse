import requests
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_OMEGA_KEY")

LEGHE_TARGET = [5, 34, 4, 15, 135, 39, 140, 78, 61, 2, 3] 

def calcola_forma_da_stringa(forma_str):
    # Converte la stringa "WWDLW" in Punti Per Partita (PPG)
    if not forma_str: return 0.0
    pti = 0
    for char in forma_str:
        if char == 'W': pti += 3
        elif char == 'D': pti += 1
    return round(pti / len(forma_str), 2)

def genera_analisi_giornaliera():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    headers = {'x-apisports-key': API_FOOTBALL_KEY}
    
    database_analisi = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "analisi": []}
    partite_valide = []
    
    print("Ricerca partite (Club e Nazionali) per oggi e domani...")
    
    # 1. Troviamo le partite in programma
    for giorni_avanti in range(2):
        data_target = (oggi + timedelta(days=giorni_avanti)).strftime("%Y-%m-%d")
        res = requests.get(f"https://v3.football.api-sports.io/fixtures?date={data_target}", headers=headers)
        
        if res.status_code == 200:
            dati = res.json()
            for m in dati.get('response', []):
                if m['league']['id'] in LEGHE_TARGET:
                    partite_valide.append(m)

    partite_valide = partite_valide[:15]
    print(f"Trovate {len(partite_valide)} partite. Inizio estrazione classifiche in blocco...")
    
    # 2. Raggruppiamo le leghe uniche per minimizzare le chiamate API
    leghe_da_cercare = set()
    for m in partite_valide:
        leghe_da_cercare.add((m['league']['id'], m['league']['season']))
        
    statistiche_squadre = {}
    
    # 3. Scarichiamo le classifiche (aggirando il blocco API sulle singole squadre)
    for l_id, stagione in leghe_da_cercare:
        print(f"Scarico dati classifica per lega {l_id} (stagione {stagione})...")
        time.sleep(1) # Pausa di sicurezza minima
        res_std = requests.get(f"https://v3.football.api-sports.io/standings?league={l_id}&season={stagione}", headers=headers)
        dati_std = res_std.json()
        
        if dati_std.get('errors'):
            print(f"Errore Classifiche: {dati_std['errors']}")
            continue
            
        for league_data in dati_std.get('response', []):
            for standings_group in league_data.get('league', {}).get('standings', []):
                for team_rank in standings_group:
                    t_id = team_rank['team']['id']
                    giocate = team_rank['all']['played']
                    
                    if giocate > 0:
                        gf = team_rank['all']['goals']['for'] / giocate
                        gs = team_rank['all']['goals']['against'] / giocate
                        forma_val = calcola_forma_da_stringa(team_rank.get('form', ''))
                    else:
                        gf, gs, forma_val = 0.0, 0.0, 0.0
                        
                    statistiche_squadre[t_id] = {
                        "forma": forma_val,
                        "gol_fatti": round(gf, 2),
                        "gol_subiti": round(gs, 2)
                    }
                    
    # 4. Elaboriamo i testi per il database incrociando i dati salvati
    for m in partite_valide:
        home_id = m['teams']['home']['id']
        away_id = m['teams']['away']['id']
        home_name = m['teams']['home']['name']
        away_name = m['teams']['away']['name']
        
        # Peschiamo i dati dal dizionario locale (zero chiamate API aggiuntive!)
        stat_h = statistiche_squadre.get(home_id, {"forma": 0, "gol_fatti": 0, "gol_subiti": 0})
        stat_a = statistiche_squadre.get(away_id, {"forma": 0, "gol_fatti": 0, "gol_subiti": 0})
        
        print(f"Generazione report: {home_name} - {away_name}")
        
        testo = f"L'analisi algoritmica sul match {home_name}-{away_name} evidenzia "
        if stat_h['forma'] > stat_a['forma']:
            testo += f"un netto vantaggio per i padroni di casa (PPG {stat_h['forma']} vs {stat_a['forma']}). "
        elif stat_a['forma'] > stat_h['forma']:
            testo += f"un vantaggio per la squadra in trasferta (PPG {stat_a['forma']} vs {stat_h['forma']}). "
        else:
            testo += f"un sostanziale equilibrio tattico. "
            
        attesa_gol = stat_h['gol_fatti'] + stat_a['gol_subiti']
        if attesa_gol > 2.5:
            testo += "Il modello predittivo indica un'alta probabilità di Over 2.5 date le difese aperte."
            fair_odd = 1.50
            pick = "Over 2.5"
        else:
            testo += "I dati suggeriscono una partita bloccata tatticamente."
            fair_odd = 1.60
            pick = "Under 2.5"
            
        database_analisi["analisi"].append({
            "id_partita": str(m['fixture']['id']),
            "match": f"{home_name} - {away_name}",
            "data": m['fixture']['date'],
            "consiglio_algoritmo": pick,
            "quota_valore_minima": fair_odd,
            "report_testuale": testo
        })
        
    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump(database_analisi, f, indent=4, ensure_ascii=False)
        
    print(f"\nModello Omega Analista completato! {len(partite_valide)} partite elaborate in tempo record.")

if __name__ == "__main__":
    genera_analisi_giornaliera()
