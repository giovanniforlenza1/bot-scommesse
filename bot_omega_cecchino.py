import requests
import json
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# Usa il canale dedicato a Omega se esiste, altrimenti ripiega su quello standard
OMEGA_CHAT_ID = os.environ.get("OMEGA_CHAT_ID") or os.environ.get("CHAT_ID")

campionati = [
    'soccer_uefa_nations_league', 'soccer_italy_serie_a', 'soccer_epl',
    'soccer_spain_la_liga', 'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league'
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
    "Kosovo": "Kosovo", "North Macedonia": "Macedonia del Nord"
}

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus",
    "Hellas Verona": "Verona", "Bologna FC": "Bologna", "Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Venezia FC": "Venezia", "Parma Calcio 1913": "Parma",
    "Como 1907": "Como", "Manchester Utd": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham",
    "Newcastle Utd": "Newcastle", "Paris Saint Germain": "PSG",
    "Bayern Munich": "Bayern Monaco", "Bayer Leverkusen": "Bayer Leverkusen",
    "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad",
    "Athletic Club": "Athletic Bilbao"
}

def traduci_squadra(nome):
    nome_pulito = nome.strip()
    if nome_pulito in TRADUZIONI_NAZIONALI: return TRADUZIONI_NAZIONALI[nome_pulito]
    if nome_pulito in TRADUZIONI_SQUADRE: return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "")

def esegui_richiesta_api(url_template):
    chiavi = [k.strip() for k in os.environ.get("ODDS_API_KEY", "").split(",") if k.strip()]
    if not chiavi: return None
    for chiave in chiavi:
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200: return res.json()
        except: pass
    return None

def carica_database_analisi():
    if os.path.exists('database_analisi.json'):
        with open('database_analisi.json', 'r', encoding='utf-8') as f: return json.load(f)
    return None

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f: 
        json.dump(db, f, indent=4, ensure_ascii=False)

def esegui_cecchino():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    # IL DOPPIO MURO: Il Cecchino ignora fisicamente qualsiasi quota oltre i 4 giorni
    limite_temporale = oggi + timedelta(days=4)
    
    db_analisi = carica_database_analisi()
    if not db_analisi or not db_analisi.get('analisi'): return
        
    candidati_valore = []
    
    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu&markets=h2h"
        partite_live = esegui_richiesta_api(url_template)
        if not partite_live: continue
            
        for p_live in partite_live:
            data_ita = datetime.strptime(p_live['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            
            # Barriera insormontabile
            if data_ita > limite_temporale:
                continue

            nome_casa_ita = traduci_squadra(p_live['home_team'])
            nome_trasf_ita = traduci_squadra(p_live['away_team'])
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
                        
                        if "pareggio" in pronostico_richiesto.lower():
                            if nome_esito_originale.lower() == 'draw': is_match = True
                        elif "vittoria" in pronostico_richiesto.lower():
                            squadra_vincente_ita = pronostico_richiesto.lower().replace("vittoria ", "").strip()
                            nome_esito_ita = traduci_squadra(nome_esito_originale).lower()
                            if squadra_vincente_ita == nome_esito_ita: is_match = True
                                
                        if is_match and q_attuale > miglior_quota:
                            miglior_quota = q_attuale
                            book_vincente = book.get('title', '')
                            
            if miglior_quota >= quota_minima:
                candidati_valore.append({
                    'id_partita': p_live['id'],
                    'data': data_ita.strftime("%d/%m %H:%M"),
                    'squadra_casa': nome_casa_ita,
                    'squadra_trasferta': nome_trasf_ita,
                    'pronostico': pronostico_richiesto,
                    'quota': miglior_quota,
                    'bookmaker': book_vincente,
                    'score': miglior_quota - quota_minima,
                    'lega': camp,
                    'stato': 'in attesa',
                    'risultato_reale': ''
                })
                
    if not candidati_valore: 
        print("Nessuna giocata valida trovata nei prossimi 4 giorni.")
        return
    
    finalisti = sorted(candidati_valore, key=lambda x: (0 if x['lega'] == 'soccer_italy_serie_a' else 1, -x['score']))[:3]
    
    quota_totale = 1.0
    for c in finalisti: quota_totale *= c['quota']
    quota_totale = round(quota_totale, 2)
    
    if quota_totale < 1.50: return
        
    db_principale = carica_database_principale()
    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'modello': 'omega',
        'data_creazione': oggi.strftime("%d/%m/%Y"),
        'importo': 10.0,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(10.0 * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'partite': finalisti
    })
    
    msg = "**MODELLO OMEGA**\n\n"
    msg += "**Schedina quantitativa.**\n\n"
    msg += f"📊 **Quota totale**: {quota_totale}\n"
    msg += f"💰 **Stake simulato**: 10.0€\n\n"
    
    for c in finalisti:
        msg += f"⚽ **{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}**\n"
        msg += f"🎯 **Giocata**: {c['pronostico'].lower()} (@{c['quota']})\n"
        msg += f"🏦 **Bookmaker**: {c['bookmaker']}\n\n"
        
    msg += "**#TradingSportivo #ValueBetting #ScommesseSportive**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": OMEGA_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    salva_database_principale(db_principale)

if __name__ == "__main__":
    esegui_cecchino()
