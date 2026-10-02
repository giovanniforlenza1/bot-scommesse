import requests
import json
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")

# id leghe su api-football: nations league (5), qualificazioni (34), mondiali/europei etc.
# club: serie a (135), epl (39), liga (140), bundesliga (78), ligue 1 (61), champions (2), europa (3)
LEGHE_TARGET = [5, 34, 135, 39, 140, 78, 61, 2, 3]

TRADUZIONI_NAZIONALI = {
    "Italy": "Italia", "France": "Francia", "Germany": "Germania", 
    "Spain": "Spagna", "England": "Inghilterra", "Netherlands": "Olanda", 
    "Belgium": "Belgio", "Portugal": "Portogallo", "Croatia": "Croazia", 
    "Switzerland": "Svizzera", "Poland": "Polonia", "Denmark": "Danimarca", 
    "Sweden": "Svezia", "Norway": "Norvegia", "Austria": "Austria"
}

def traduci_squadra(nome_inglese):
    return TRADUZIONI_NAZIONALI.get(nome_inglese.strip(), nome_inglese.strip())

def carica_database():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: 
            return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database(db):
    with open('database.json', 'w', encoding='utf-8') as f: 
        json.dump(db, f, indent=4, ensure_ascii=False)

def cerca_value_corners():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia).date()
    
    candidati = []
    errori_api = []
    partite_totali = 0
    
    headers = {'x-apisports-key': API_FOOTBALL_KEY}
    
    # scansioniamo le quote per i prossimi 3 giorni
    for giorni_avanti in range(4):
        data_target = (oggi + timedelta(days=giorni_avanti)).strftime("%Y-%m-%d")
        
        # interroghiamo api-football per le quote di bet365 (bookmaker id 8)
        url = f"https://v3.football.api-sports.io/odds?date={data_target}&bookmaker=8"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                errori_api.append(str(res.status_code))
                continue
            
            dati = res.json().get('response', [])
        except:
            errori_api.append("timeout")
            continue
            
        for match in dati:
            lega_id = match['league']['id']
            if lega_id not in LEGHE_TARGET:
                continue
                
            partite_totali += 1
            fixture_data = match['fixture']
            match_date = datetime.strptime(fixture_data['date'], "%Y-%m-%dT%H:%M:%S%z").astimezone(fuso_italia)
            
            casa = traduci_squadra(match['league']['name'] if 'league' in match else fixture_data.get('home_team', 'Casa')) 
            # estrazione nomi corretti
            casa = traduci_squadra(match.get('fixture', {}).get('teams', {}).get('home', {}).get('name', 'Casa'))
            trasferta = traduci_squadra(match.get('fixture', {}).get('teams', {}).get('away', {}).get('name', 'Trasferta'))
            
            for book in match.get('bookmakers', []):
                for mercato in book.get('markets', []):
                    # cerchiamo il mercato dei calci d'angolo (di solito id 45 o nome corners)
                    nome_mercato = mercato.get('name', '').lower()
                    if 'corner' in nome_mercato or mercato.get('id') == 45:
                        for out in mercato.get('values', []):
                            valore = out.get('value', str(out.get('name', '')))
                            quota = float(out.get('odd', 0))
                            
                            # peschiamo le linee over sui corner a quote di valore
                            if 'over' in valore.lower() and 1.45 <= quota <= 2.20:
                                punteggio = 1.0 / quota # base di ranking 
                                candidati.append({
                                    'id_partita': fixture_data['id'],
                                    'data_oggetto': str(match_date.date()),
                                    'data': match_date.strftime("%d/%m %H:%M"),
                                    'squadra_casa': casa,
                                    'squadra_trasferta': trasferta,
                                    'pronostico': f"calci d'angolo: {valore.lower()}",
                                    'quota': quota,
                                    'score': punteggio,
                                    'stato': 'in attesa',
                                    'risultato_reale': ''
                                })
                        break

    if not candidati:
        msg_err = f"⚠️ **SBR ALERT DI SISTEMA - MODELLO BETA**\n\n**nessuna giocata sui corner elaborata oggi**. il sistema non ha individuato mercati aperti o quote di valore sulle {partite_totali} partite valide."
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg_err, "parse_mode": "Markdown"})
        return
        
    unici = {}
    for c in sorted(candidati, key=lambda x: x['score'], reverse=True):
        if c['id_partita'] not in unici:
            unici[c['id_partita']] = c
            
    finalisti = []
    quota_totale = 1.0
    for c in sorted(unici.values(), key=lambda x: x['score'], reverse=True):
        if len(finalisti) >= 3:
            break
        finalisti.append(c)
        quota_totale *= c['quota']
        
    quota_totale = round(quota_totale, 2)
    
    if len(finalisti) < 2 or quota_totale < 1.80:
        return # fermiamo le giocate non sufficientemente profittevoli
        
    db = carica_database()
    db['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'data_creazione': datetime.now(fuso_italia).strftime("%d/%m/%Y"),
        'importo': 10.0,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(10.0 * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'partite': finalisti
    })
    salva_database(db)
    
    # copy ottimizzato in ottica seo social
    msg = f"🔍 **esclusiva modello beta: analisi mercati speciali**\n\nil nostro algoritmo statistico ha scansionato le linee sui calci d'angolo, individuando un'inefficienza sulle lavagne attuali.\n\n"
    msg += f"📊 quota totale: {quota_totale}\n💰 stake simulato: 10.0€\n\n"
    for c in finalisti:
        msg += f"⚽ **{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}**\n🎯 {c['pronostico']} (@{c['quota']})\n\n"
    msg += "l'andamento dei nostri modelli quantitativi è sempre verificabile sul portale.\n\n"
    msg += "**#PronosticiCalcio #ValueBetting #ScommesseSportive #CornerBetting #SportTrading**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    cerca_value_corners()
