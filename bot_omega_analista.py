import requests
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Usiamo la nuova API
FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_KEY")

# Codici competizioni gratuite su Football-Data.org
LEGHE_TARGET = ['SA', 'PL', 'PD', 'BL1', 'FL1', 'CL', 'EL', 'DED'] 

def analizza_statistiche(team_id, headers):
    try:
        # Chiede le ultime partite terminate della squadra
        url = f"https://api.football-data.org/v4/teams/{team_id}/matches?status=FINISHED"
        res = requests.get(url, headers=headers, timeout=10)
        
        dati = res.json()
        if 'matches' not in dati:
            return {"forma": 0, "gol_fatti": 0, "gol_subiti": 0}
            
        # Prendiamo esattamente le ultime 5 partite
        ultime_5 = dati['matches'][-5:]
        if not ultime_5: 
            return {"forma": 0, "gol_fatti": 0, "gol_subiti": 0}
            
        pti, gf, gs = 0, 0, 0
        for f in ultime_5:
            is_home = f['homeTeam']['id'] == team_id
            g_pro = f['score']['fullTime']['home'] if is_home else f['score']['fullTime']['away']
            g_con = f['score']['fullTime']['away'] if is_home else f['score']['fullTime']['home']
            
            if g_pro is None: continue
            
            gf += g_pro
            gs += g_con
            pti += 3 if g_pro > g_con else (1 if g_pro == g_con else 0)
            
        return {"forma": round(pti/len(ultime_5), 2), "gol_fatti": round(gf/len(ultime_5), 2), "gol_subiti": round(gs/len(ultime_5), 2)}
    except:
        return {"forma": 0, "gol_fatti": 0, "gol_subiti": 0}

def genera_analisi_giornaliera():
    fuso = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso)
    headers = {'X-Auth-Token': FOOTBALL_DATA_KEY}
    
    database_analisi = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "analisi": []}
    partite_totali = 0
    
    data_inizio = oggi.strftime("%Y-%m-%d")
    data_fine = (oggi + timedelta(days=2)).strftime("%Y-%m-%d")
    
    print(f"Scansione palinsesti da {data_inizio} a {data_fine} tramite Football-Data.org...")
    
    # Unica chiamata per scaricare tutto il palinsesto dei prossimi 3 giorni
    url_matches = f"https://api.football-data.org/v4/matches?dateFrom={data_inizio}&dateTo={data_fine}"
    res_matches = requests.get(url_matches, headers=headers)
    
    if res_matches.status_code != 200:
        print(f"Errore API principale: {res_matches.status_code} - {res_matches.text}")
        return
        
    tutte_partite = res_matches.json().get('matches', [])
    matches_validi = [m for m in tutte_partite if m['competition']['code'] in LEGHE_TARGET]
    
    print(f"Trovate {len(matches_validi)} partite di cartello. Inizio analisi profonda...")
    
    for m in matches_validi:
        home_id = m['homeTeam']['id']
        away_id = m['awayTeam']['id']
        home_name = m['homeTeam']['name']
        away_name = m['awayTeam']['name']
        data_match = m['utcDate']
        
        print(f"Analisi tattica in corso: {home_name} - {away_name}")
        
        # Pausa di sicurezza: Football-Data ammette max 10 richieste al minuto (1 ogni 6 secondi)
        time.sleep(6.5)
        stat_h = analizza_statistiche(home_id, headers)
        time.sleep(6.5)
        stat_a = analizza_statistiche(away_id, headers)
        
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
            "id_partita": str(m['id']),
            "match": f"{home_name} - {away_name}",
            "data": data_match,
            "consiglio_algoritmo": pick,
            "quota_valore_minima": fair_odd,
            "report_testuale": testo
        })
        partite_totali += 1
        
    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump(database_analisi, f, indent=4, ensure_ascii=False)
        
    print(f"\nModello Omega Analista: elaborate {partite_totali} partite e salvate in database_analisi.json.")

if __name__ == "__main__":
    genera_analisi_giornaliera()
