import requests
import json
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

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

def esegui_richiesta_api(url_template):
    chiavi = [k.strip() for k in os.environ.get("ODDS_API_KEY", "").split(",") if k.strip()]
    if not chiavi: 
        print("Nessuna chiave API trovata.")
        return None
        
    for chiave in chiavi:
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 429:
                print(f"Chiave {chiave[:4]}... esaurita (429). passo alla successiva.")
                continue
            elif res.status_code == 401:
                print(f"Chiave {chiave[:4]}... non valida (401). passo alla successiva.")
                continue
            else:
                print(f"Errore {res.status_code} con chiave {chiave[:4]}...")
        except Exception as e:
            print(f"Eccezione connessione api: {e}")
            
    print("Tutte le chiavi API a disposizione sono esaurite o bloccate.")
    return None

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
        print("Nessuna analisi Monte Carlo trovata.")
        return
        
    partite_per_lega = {camp: [] for camp in campionati}
    
    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu&markets=h2h"
        partite_live = esegui_richiesta_api(url_template)
        
        if not partite_live:
            continue
            
        for p_live in partite_live:
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
                            if nome_esito_originale.lower() == 'draw':
                                is_match = True
                        elif "vittoria" in pronostico_richiesto.lower():
                            squadra_vincente_ita = pronostico_richiesto.lower().replace("vittoria ", "").strip()
                            nome_esito_ita = traduci_squadra(nome_esito_originale).lower()
                            if squadra_vincente_ita == nome_esito_ita:
                                is_match = True
                                
                        if is_match and q_attuale > miglior_quota:
                            miglior_quota = q_attuale
                            book_vincente = book.get('title', '')
                            
            if miglior_quota >= quota_minima:
                data_ita = datetime.strptime(p_live['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
                partite_per_lega[camp].append({
                    'id_partita': p_live['id'],
                    'data': data_ita.strftime("%d/%m %H:%M"),
                    'squadra_casa': nome_casa_ita,
                    'squadra_trasferta': nome_trasf_ita,
                    'pronostico': pronostico_richiesto,
                    'quota': miglior_quota,
                    'bookmaker': book_vincente,
                    'score': miglior_quota - quota_minima,
                    'stato': 'in attesa',
                    'risultato_reale': ''
                })
                
    tickets_creati = []
    priorita = ['soccer_italy_serie_a', 'soccer_epl', 'soccer_spain_la_liga']
    altri = [c for c in campionati if c not in priorita]
    
    def crea_ticket_da_lega(nome_lega):
        if not partite_per_lega[nome_lega]: return None
        finalisti = sorted(partite_per_lega[nome_lega], key=lambda x: x['score'], reverse=True)[:3]
        
        quota_totale = 1.0
        for c in finalisti: quota_totale *= c['quota']
        quota_totale = round(quota_totale, 2)
        
        if quota_totale < 1.50:
            return None
            
        return {
            'quota_totale': quota_totale,
            'partite': finalisti,
            'lega': nome_lega
        }

    for lega in priorita:
        ticket = crea_ticket_da_lega(lega)
        if ticket: tickets_creati.append(ticket)
        if len(tickets_creati) == 3: break
        
    if len(tickets_creati) < 3:
        for lega in altri:
            ticket = crea_ticket_da_lega(lega)
            if ticket: tickets_creati.append(ticket)
            if len(tickets_creati) == 3: break
            
    if not tickets_creati:
        print("nessuna schedina ha superato i filtri minimi.")
        return
        
    db_principale = carica_database_principale()
    
    for ticket in tickets_creati:
        db_principale['schedine'].append({
            'id': str(uuid.uuid4())[:8],
            'modello': 'omega',
            'data_creazione': datetime.now(fuso_italia).strftime("%d/%m/%Y"),
            'importo': 10.0,
            'quota_totale': ticket['quota_totale'],
            'ritorno_potenziale': round(10.0 * ticket['quota_totale'], 2),
            'stato_schedina': 'in attesa',
            'partite': ticket['partite']
        })
        
        nome_lega_formattato = ticket['lega'].replace("soccer_", "").replace("_", " ").upper()
        msg = f"**MODELLO OMEGA | {nome_lega_formattato}**\n\n"
        msg += "**schedina quantitativa mirata.**\n\n"
        msg += f"📊 **quota totale**: {ticket['quota_totale']}\n"
        msg += f"💰 **stake simulato**: 10.0€\n\n"
        
        for c in ticket['partite']:
            msg += f"⚽ **{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}**\n"
            msg += f"🎯 **giocata**: {c['pronostico'].lower()} (@{c['quota']})\n"
            msg += f"🏦 **bookmaker**: {c['bookmaker']}\n\n"
            
        msg += "**#AlgoritmiPredittivi #ValueBetting #TradingSportivo**"
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        
    salva_database_principale(db_principale)
    print(f"cecchino Omega: inviate {len(tickets_creati)} schedine con successo.")

if __name__ == "__main__":
    esegui_cecchino()
