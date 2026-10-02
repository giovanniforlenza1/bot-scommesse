import requests
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Il bot ora cerca specificamente la sua chiave isolata
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_OMEGA_KEY")

# 5: Nations League, 34: Qualificazioni Mondiali, 4: Europei, 15: Mondiali
# 135: Serie A, 39: Premier, 140: Liga, 78: Bundesliga, 61: Ligue 1, 2: Champions, 3: Europa League
LEGHE_TARGET = [5, 34, 4, 15, 135, 39, 140, 78, 61, 2, 3] 

def analizza_statistiche(team_id, headers):
    try:
        res = requests.get(f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5", headers=headers, timeout=10)
        
        dati_json = res.json()
        if dati_json.get('errors'):
            print(f"Errore API sul team {team_id}: {dati_json.get('errors')}")
            
        fixtures = dati_json.get('response', [])
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
    headers = {'x-apisports-key': API_FOOTBALL_KEY}
    
    database_analisi = {"ultimo_aggiornamento": oggi.strftime("%Y-%m-%d %H:%M"), "analisi": []}
    
    partite_valide = []
    
    print("Ricerca partite (Club e Nazionali) per i prossimi 3 giorni con chiave Omega dedicata...")
    
    for giorni_avanti in range(3):
        data_target = (oggi + timedelta(days=giorni_avanti)).strftime("%Y-%m-%d")
        res = requests.get(f"https://v3.football.api-sports.io/fixtures?date={data_target}", headers=headers)
        
        if res.status_code == 200:
            dati = res.json()
            if dati.get('errors'):
                print(f"Avviso API-Football: {dati['errors']}")
                
            for m in dati.get('response', []):
                if m['league']['id'] in LEGHE_TARGET:
                    partite_valide.append(m)

    # Limite alzato a 15 partite grazie alla chiave API separata
    partite_valide = partite_valide[:15]
    print(f"Trovate e selezionate {len(partite_valide)} partite di cartello per l'analisi profonda.")
    
    for m in partite_valide:
        home_name = m['teams']['home']['name']
        away_name = m['teams']['away']['name']
        
        print(f"Elaborazione tattica: {home_name} - {away_name}")
        
        time.sleep(0.5)
        stat_h = analizza_statistiche(m['teams']['home']['id'], headers)
        time.sleep(0.5)
        stat_a = analizza_statistiche(m['teams']['away']['id'], headers)
        
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
        
    print(f"\nModello Omega Analista: elaborate {len(partite_valide)} partite e salvate in database_analisi.json.")

if __name__ == "__main__":
    genera_analisi_giornaliera()
