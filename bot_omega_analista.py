import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
LEGHE_TARGET = [135, 39, 140, 78, 61] 

def analizza_statistiche(team_id, headers):
    try:
        res = requests.get(f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5", headers=headers, timeout=10)
        fixtures = res.json().get('response', [])
        if not fixtures: return {"forma": 0, "gol_fatti": 0, "gol_subiti": 0}
        
        pti, gf, gs = 0, 0, 0
        for f in fixtures:
            is_home = f['teams']['home']['id'] == team_id
            g_pro = f['goals']['home'] if is_home else f['goals']['away']
            g_con = f['goals']['away'] if is_home else f['goals']['home']
            if g_pro is None: continue
            gf += g_pro
            gs += g_con
            pti += 3 if g_pro > g_con else (1 if g_pro == g_con else 0)
            
        return {"forma": round(pti/5, 2), "gol_fatti": round(gf/5, 2), "gol_subiti": round(gs/5, 2)}
    except:
        return {"forma": 0, "gol_fatti": 0, "gol_subiti": 0}

def genera_analisi_giornaliera():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    data_target = (oggi + timedelta(days=1)).strftime("%Y-%m-%d")
    
    headers = {'x-apisports-key': API_FOOTBALL_KEY}
    res = requests.get(f"https://v3.football.api-sports.io/fixtures?date={data_target}", headers=headers)
    
    matches = [m for m in res.json().get('response', []) if m['league']['id'] in LEGHE_TARGET]
    
    database_analisi = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "analisi": []}
    
    for m in matches:
        home_name = m['teams']['home']['name']
        away_name = m['teams']['away']['name']
        
        stat_h = analizza_statistiche(m['teams']['home']['id'], headers)
        stat_a = analizza_statistiche(m['teams']['away']['id'], headers)
        
        testo = f"L'analisi algoritmica sul match {home_name}-{away_name} evidenzia "
        if stat_h['forma'] > stat_a['forma']:
            testo += f"un netto vantaggio per i padroni di casa (PPG {stat_h['forma']} vs {stat_a['forma']}). "
        else:
            testo += f"un equilibrio tattico o una spinta ospite. "
            
        attesa_gol = stat_h['gol_fatti'] + stat_a['gol_subiti']
        if attesa_gol > 2.5:
            testo += "Il modello predittivo indica un'alta probabilità di Over 2.5 date le difese aperte."
            fair_odd = 1.50
            pick = "Over 2.5"
        else:
            testo += "I dati suggeriscono una partita bloccata tatticamente."
            fair_odd = 1.65
            pick = "Under 2.5"
            
        database_analisi["analisi"].append({
            "id_partita": m['fixture']['id'],
            "match": f"{home_name} - {away_name}",
            "data": m['fixture']['date'],
            "consiglio_algoritmo": pick,
            "quota_valore_minima": fair_odd,
            "report_testuale": testo
        })
        
    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump(database_analisi, f, indent=4, ensure_ascii=False)
        
    print(f"Modello Omega Analista: elaborate {len(matches)} partite e salvate in database_analisi.json.")

if __name__ == "__main__":
    genera_analisi_giornaliera()
