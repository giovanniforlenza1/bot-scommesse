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

def aggiorna_risultati():
    print("Avvio Arbitro SBR: Controllo risultati in corso...")
    
    if not os.path.exists('database.json'):
        print("Nessun database trovato.")
        return
        
    with open('database.json', 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    schedine_in_attesa = [s for s in db.get('schedine', []) if s['stato_schedina'] == 'in attesa']
    
    if not schedine_in_attesa:
        print("Nessuna schedina in attesa da aggiornare.")
        return
        
    # Raccogliamo i risultati degli ultimi 3 giorni per coprire i ritardi
    risultati_api = []
    for camp in CAMPIONATI:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{camp}/scores/?apiKey={ODDS_API_KEY}&daysFrom=3"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                risultati_api.extend(res.json())
        except Exception as e:
            print(f"Errore caricamento {camp}: {e}")
            
    modificato = False
    
    for schedina in schedine_in_attesa:
        # L'API non copre cartellini e angoli, saltiamo Beta che andrà chiusa a mano
        if schedina['modello'] == 'beta':
            continue 
            
        tutte_concluse = True
        almeno_una_persa = False
        
        for p in schedina['partite']:
            if p['stato'] != 'in attesa':
                if p['stato'] == 'persa': almeno_una_persa = True
                continue
                
            # Cerchiamo il match nei risultati
            match_trovato = False
            for r in risultati_api:
                if not r['completed'] or not r.get('scores'): continue
                
                casa_ita = traduci_squadra(r['home_team'])
                trasf_ita = traduci_squadra(r['away_team'])
                
                if p['squadra_casa'] == casa_ita and p['squadra_trasferta'] == trasf_ita:
                    match_trovato = True
                    # Estraiamo i gol
                    gol_casa, gol_trasf = 0, 0
                    for score in r['scores']:
                        if score['name'] == r['home_team']: gol_casa = int(score['score'])
                        if score['name'] == r['away_team']: gol_trasf = int(score['score'])
                        
                    p['risultato_reale'] = f"{gol_casa}-{gol_trasf}"
                    
                    # Definiamo l'esito reale
                    if gol_casa > gol_trasf: esito_reale = f"vittoria {casa_ita.lower()}"
                    elif gol_trasf > gol_casa: esito_reale = f"vittoria {trasf_ita.lower()}"
                    else: esito_reale = "pareggio"
                    
                    # Confrontiamo pronostico ed esito
                    if p['pronostico'].lower() == esito_reale:
                        p['stato'] = 'vinta'
                    else:
                        p['stato'] = 'persa'
                        almeno_una_persa = True
                        
                    modificato = True
                    break
            
            if not match_trovato or p['stato'] == 'in attesa':
                tutte_concluse = False
                
        # Chiudiamo la schedina intera se tutte le partite sono state definite
        if tutte_concluse or almeno_una_persa:
            schedina['stato_schedina'] = 'persa' if almeno_una_persa else 'vinta'
            modificato = True

    if modificato:
        with open('database.json', 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        print("Database aggiornato con i nuovi risultati.")
    else:
        print("Nessun nuovo risultato definitivo trovato.")

if __name__ == "__main__":
    aggiorna_risultati()
