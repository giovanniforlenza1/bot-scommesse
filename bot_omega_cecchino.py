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
    'soccer_france_ligue_one'
]

siti_ammessi = ['Bet365', 'Snai', 'Sisal', 'Eurobet', 'PlanetWin365', 'GoldBet', 'Betfair', 'William Hill', 'Unibet']

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
        print("nessun database di analisi trovato o database vuoto: l'analista deve girare prima del cecchino.")
        return
        
    candidati_valore = []
    
    # recuperiamo le quote live per incrociarle con le nostre analisi
    for camp in campionati:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals"
            res = requests.get(url, timeout=10)
            if res.status_code != 200: continue
            partite_live = res.json()
            
            for p_live in partite_live:
                # cerchiamo se questa partita è nel nostro database di analisi
                match_id_live = str(p_live['id'])
                analisi_match = next((a for a in db_analisi['analisi'] if str(a.get('id_partita')) == match_id_live or (p_live['home_team'] in a['match'])), None)
                
                if not analisi_match: continue
                
                pronostico_richiesto = analisi_match['consiglio_algoritmo']
                quota_minima = analisi_match['quota_valore_minima']
                
                # cerchiamo la quota migliore tra i bookmaker ammessi
                miglior_quota = 0.0
                for book in p_live.get('bookmakers', []):
                    if not any(sb.lower() in book.get('title', '').lower() for sb in siti_ammessi): continue
                    
                    for mercato in book.get('markets', []):
                        for out in mercato.get('outcomes', []):
                            q_attuale = out.get('price', 0)
                            
                            # traduzione del pronostico per fare il match
                            nome_esito = out.get('name', '')
                            is_match = False
                            
                            if "Over 2.5" in pronostico_richiesto and mercato['key'] == 'totals' and nome_esito == 'Over' and out.get('point') == 2.5:
                                is_match = True
                            elif "Under 2.5" in pronostico_richiesto and mercato['key'] == 'totals' and nome_esito == 'Under' and out.get('point') == 2.5:
                                is_match = True
                            elif "vittoria" in pronostico_richiesto.lower() and mercato['key'] == 'h2h':
                                squadra_vincente = pronostico_richiesto.lower().replace("vittoria ", "")
                                if squadra_vincente in nome_esito.lower(): is_match = True
                                
                            if is_match and q_attuale > miglior_quota:
                                miglior_quota = q_attuale
                                
                # se la quota live è maggiore di quella minima richiesta dall'analista, è una value bet
                if miglior_quota >= quota_minima:
                    data_ita = datetime.strptime(p_live['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
                    candidati_valore.append({
                        'id_partita': p_live['id'],
                        'data': data_ita.strftime("%d/%m %H:%M"),
                        'squadra_casa': p_live['home_team'],
                        'squadra_trasferta': p_live['away_team'],
                        'pronostico': pronostico_richiesto,
                        'quota': miglior_quota,
                        'score': miglior_quota - quota_minima, # il margine di vantaggio
                        'stato': 'in attesa',
                        'risultato_reale': ''
                    })
        except:
            continue
            
    if not candidati_valore:
        print("il cecchino non ha trovato quote sul mercato che soddisfano i requisiti dell'analista.")
        return
        
    # prendiamo le 3 giocate con il margine di vantaggio più alto
    finalisti = sorted(candidati_valore, key=lambda x: x['score'], reverse=True)[:3]
    
    quota_totale = 1.0
    for c in finalisti: quota_totale *= c['quota']
    quota_totale = round(quota_totale, 2)
    
    if len(finalisti) < 2 or quota_totale < 2.00:
        print("giocata annullata: eventi insufficienti o quota troppo bassa.")
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
    
    msg = f"🎯 **esecuzione modello omega completata**\n\n"
    msg += "il cecchino ha elaborato il database delle analisi predittive e ha intercettato le quote live sui bookmaker: abbiamo un picco di valore matematico.\n\n"
    msg += f"📊 quota totale: {quota_totale}\n💰 stake simulato: 10.0€\n\n"
    for c in finalisti:
        msg += f"⚽ **{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}**\n"
        msg += f"🎯 giocata: {c['pronostico']} (@{c['quota']})\n\n"
        
    msg += "l'operazione è stata registrata con successo sulla dashboard pubblica.\n\n"
    msg += "**#SBR #PronosticiCalcio #ValueBetting #SportTrading**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    print("giocata omega piazzata con successo.")

if __name__ == "__main__":
    esegui_cecchino()
