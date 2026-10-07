import requests
import json
import os
from datetime import datetime
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
    "Romania": "Romania", "Bosnia & Herzegovina": "Bosnia ed Erzegovina",
    "Faroe Islands": "Isole Faroe", "Slovakia": "Slovacchia", "Finland": "Finlandia",
    "Belarus": "Bielorussia", "San Marino": "San Marino", "Iceland": "Islanda",
    "Bulgaria": "Bulgaria", "Estonia": "Estonia", "Luxembourg": "Lussemburgo",
    "Israel": "Israele", "Czech Republic": "Repubblica Ceca", "Slovenia": "Slovenia",
    "Greece": "Grecia", "Ireland": "Irlanda", "Lithuania": "Lituania",
    "Kosovo": "Kosovo", "North Macedonia": "Macedonia del Nord", 
    "Liechtenstein": "Liechtenstein", "Gibraltar": "Gibilterra", 
    "Andorra": "Andorra", "Malta": "Malta", "Azerbaijan": "Azerbaigian"
}

def traduci_squadra(nome):
    return TRADUZIONI_NAZIONALI.get(nome.strip(), nome.strip())

def confronta_squadre(sq_db, sq_api):
    if not sq_db or not sq_api: return False
    s1 = str(sq_db).lower().strip()
    s2_eng = str(sq_api).lower().strip()
    s2_ita = traduci_squadra(str(sq_api)).lower().strip()
    return s1 == s2_eng or s1 == s2_ita

def aggiorna_risultati():
    print("Avvio Arbitro SBR: controllo e auto-guarigione in corso...")
    
    if not os.path.exists('database.json'):
        print("Nessun database trovato.")
        return
        
    with open('database.json', 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    modificato = False
    
    for schedina in db.get('schedine', []):
        if schedina.get('modello') == 'beta':
            continue
            
        for p in schedina.get('partite', []):
            if p.get('risultato_reale') and '-' in p['risultato_reale']:
                try:
                    risultato_pulito = p['risultato_reale'].replace('[', '').replace(']', '').strip()
                    gol_casa, gol_trasf = map(int, risultato_pulito.split('-'))
                    pron_pulito = str(p.get('pronostico', '')).lower().strip()
                    c_db = str(p.get('squadra_casa', '')).lower().strip()
                    t_db = str(p.get('squadra_trasferta', '')).lower().strip()
                    
                    vinta = False
                    if gol_casa > gol_trasf and (pron_pulito == "1" or pron_pulito == f"vittoria {c_db}"): vinta = True
                    elif gol_trasf > gol_casa and (pron_pulito == "2" or pron_pulito == f"vittoria {t_db}"): vinta = True
                    elif gol_casa == gol_trasf and (pron_pulito == "x" or pron_pulito == "pareggio"): vinta = True
                    
                    nuovo_stato_partita = 'vinta' if vinta else 'persa'
                    if p.get('stato') != nuovo_stato_partita:
                        p['stato'] = nuovo_stato_partita
                        modificato = True
                except:
                    pass
                    
    schedine_in_attesa = [s for s in db.get('schedine', []) if s.get('stato_schedina') in ['in attesa', 'persa']]
    
    if schedine_in_attesa:
        risultati_api = []
        for camp in CAMPIONATI:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/{camp}/scores/?apiKey={ODDS_API_KEY}&daysFrom=3"
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    risultati_api.extend(res.json())
            except Exception as e:
                print(f"Errore caricamento {camp}: {e}")
                
        for schedina in schedine_in_attesa:
            if schedina.get('modello') == 'beta': continue
            
            for p in schedina.get('partite', []):
                if p.get('stato') != 'in attesa': continue
                
                for r in risultati_api:
                    if not r.get('completed') or not r.get('scores'): continue
                    
                    if confronta_squadre(p.get('squadra_casa'), r.get('home_team')) and confronta_squadre(p.get('squadra_trasferta'), r.get('away_team')):
                        gol_casa, gol_trasf = 0, 0
                        for score in r['scores']:
                            if score.get('name') == r.get('home_team'): gol_casa = int(score.get('score', 0))
                            if score.get('name') == r.get('away_team'): gol_trasf = int(score.get('score', 0))
                            
                        p['risultato_reale'] = f"{gol_casa}-{gol_trasf}"
                        
                        pron_pulito = str(p.get('pronostico', '')).lower().strip()
                        c_db = str(p.get('squadra_casa', '')).lower().strip()
                        t_db = str(p.get('squadra_trasferta', '')).lower().strip()
                        
                        vinta = False
                        if gol_casa > gol_trasf and (pron_pulito == "1" or pron_pulito == f"vittoria {c_db}"): vinta = True
                        elif gol_trasf > gol_casa and (pron_pulito == "2" or pron_pulito == f"vittoria {t_db}"): vinta = True
                        elif gol_casa == gol_trasf and (pron_pulito == "x" or pron_pulito == "pareggio"): vinta = True
                        
                        p['stato'] = 'vinta' if vinta else 'persa'
                        modificato = True
                        break
                        
    for schedina in db.get('schedine', []):
        if schedina.get('modello') == 'beta': continue
        
        almeno_una_persa = any(p.get('stato') == 'persa' for p in schedina.get('partite', []))
        tutte_concluse = all(p.get('stato') != 'in attesa' for p in schedina.get('partite', []))
        
        if almeno_una_persa:
            nuovo_stato = 'persa'
        elif tutte_concluse:
            nuovo_stato = 'vinta'
        else:
            nuovo_stato = 'in attesa'
            
        if schedina.get('stato_schedina') != nuovo_stato:
            schedina['stato_schedina'] = nuovo_stato
            modificato = True

    if modificato:
        with open('database.json', 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        print("Database aggiornato con successo.")
    else:
        print("Nessuna modifica necessaria.")

if __name__ == "__main__":
    aggiorna_risultati()
