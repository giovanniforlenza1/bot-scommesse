import requests
import json
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

campionati = [
    'soccer_uefa_nations_league',
    'soccer_italy_serie_a',
    'soccer_epl',
    'soccer_spain_la_liga',
    'soccer_germany_bundesliga',
    'soccer_france_ligue_one',
    'soccer_uefa_champs_league', 
    'soccer_uefa_europa_league'
]

siti_ammessi = ['Bet365', 'Snai', 'Sisal', 'Eurobet', 'PlanetWin365', 'GoldBet', 'Betfair', 'William Hill', 'Unibet']

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

def traduci_squadra(nome_inglese):
    return TRADUZIONI_NAZIONALI.get(nome_inglese.strip(), nome_inglese.strip())

def carica_database_analisi():
    if os.path.exists('database_analisi.json'):
        with open('database_analisi.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: 
            return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f: 
        json.dump(db, f, indent=4, ensure_ascii=False)

def esegui_cecchino():
    fuso_italia = ZoneInfo("Europe/Rome")
    db_analisi = carica_database_analisi()
    
    if not db_analisi or not db_analisi.get('analisi'):
        print("nessun database di analisi trovato o database vuoto.")
        return
        
    candidati_valore = []
    
    for camp in campionati:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
            res = requests.get(url, timeout=10)
            if res.status_code != 200: continue
            partite_live = res.json()
            
            for p_live in partite_live:
                nome_casa_ita = traduci_squadra(p_live['home_team'])
                nome_trasf_ita = traduci_squadra(p_live['away_team'])
                
                # cerchiamo se la partita è tra quelle selezionate dall'analista
                analisi_match = next((a for a in db_analisi['analisi'] if nome_casa_ita in a['match']), None)
                if not analisi_match: continue
                
                pronostico_richiesto = analisi_match['consiglio_algoritmo']
                quota_minima = analisi_match['quota_valore_minima']
                
                miglior_quota = 0.0
                book_vincente = ""
                
                for book in p_live.get('bookmakers', []):
                    if not any(sb.lower() in book.get('title', '').lower() for sb in siti_ammessi): continue
                    
                    for mercato in book.get('markets', []):
                        for out in mercato.get('outcomes', []):
                            q_attuale = out.get('price', 0)
                            nome_esito_originale = out.get('name', '')
                            is_match = False
                            
                            # logica avanzata per riconoscere il pareggio
                            if "pareggio" in pronostico_richiesto.lower():
                                if nome_esito_originale.lower() == 'draw':
                                    is_match = True
                            
                            # logica avanzata per riconoscere le vittorie (con traduzione dinamica dell'esito)
                            elif "vittoria" in pronostico_richiesto.lower():
                                squadra_vincente_ita = pronostico_richiesto.lower().replace("vittoria ", "").strip()
                                nome_esito_ita = traduci_squadra(nome_esito_originale).lower()
                                if squadra_vincente_ita == nome_esito_ita:
                                    is_match = True
                                
                            if is_match and q_attuale > miglior_quota:
                                miglior_quota = q_attuale
                                book_vincente = book.get('title', '')
                                
                # il cecchino spara solo se il mercato offre una quota uguale o superiore al vantaggio matematico
                if miglior_quota >= quota_minima:
                    data_ita = datetime.strptime(p_live['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
                    candidati_valore.append({
                        'id_partita': p_live['id'],
                        'data': data_ita.strftime("%d/%m %H:%M"),
                        'squadra_casa': nome_casa_ita,
                        'squadra_trasferta': nome_trasf_ita,
                        'pronostico': pronostico_richiesto,
                        'quota': miglior_quota,
                        'bookmaker': book_vincente,
                        'score': miglior_quota - quota_minima, # il nostro vantaggio sul mercato
                        'stato': 'in attesa',
                        'risultato_reale': ''
                    })
        except:
            continue
            
    if not candidati_valore:
        print("il mercato non sta offrendo le quote minime richieste. nessuna giocata effettuata per preservare il capitale.")
        return
        
    # selezioniamo i 3 eventi con il vantaggio matematico più largo in assoluto
    finalisti = sorted(candidati_valore, key=lambda x: x['score'], reverse=True)[:3]
    
    quota_totale = 1.0
    for c in finalisti: quota_totale *= c['quota']
    quota_totale = round(quota_totale, 2)
    
    if len(finalisti) < 2 or quota_totale < 2.00:
        print("giocata annullata: eventi di valore insufficienti o quota combinata troppo bassa.")
        return
        
    db_principale = carica_database_principale()
    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'modello': 'omega',
        'data_creazione': datetime.now(fuso_italia).strftime("%d/%m/%Y"),
        'importo': 10.0,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(10.0 * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'partite': finalisti
    })
    salva_database_principale(db_principale)
    
    # generazione del copy social in ottica SEO
    msg = f"🎯 **OMEGA / ETL predittiva**\n\n"
    msg += "I bookmaker stanno sottovalutando queste probabilità.\n\n"
    msg += f"📊 **quota totale**: {quota_totale}\n💰 **stake simulato**: 10.0€\n\n"
    
    for c in finalisti:
        msg += f"⚽ **{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}**\n"
        msg += f"🎯 **giocata**: {c['pronostico']} (@{c['quota']})\n"
        msg += f"🏦 **trovata su**: {c['bookmaker']}\n\n"
        
    msg += "tutti i dati e i calcoli di de-vigging sono registrati e visibili in trasparenza sulla nostra dashboard pubblica.\n\n"
    msg += "**#PronosticiCalcio #ValueBetting #TradingSportivo #Betting**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    print("giocata piazzata con successo. il vantaggio è nostro.")

if __name__ == "__main__":
    esegui_cecchino()
