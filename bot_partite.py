import requests
import json
import os
import uuid
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")

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

siti_ammessi = [
    'Bet365', 'Snai', 'Sisal', 'Eurobet', 'PlanetWin365', 'GoldBet', 
    'Lottomatica', 'Betfair', 'William Hill', 'Unibet', 'Bwin', 'Pinnacle'
]

TRADUZIONI_NAZIONALI = {
    "Italy": "Italia", "France": "Francia", "Germany": "Germania", 
    "Spain": "Spagna", "England": "Inghilterra", "Netherlands": "Olanda", 
    "Belgium": "Belgio", "Portugal": "Portogallo", "Croatia": "Croazia", 
    "Switzerland": "Svizzera", "Poland": "Polonia", "Denmark": "Danimarca", 
    "Sweden": "Svezia", "Norway": "Norvegia", "Austria": "Austria", 
    "Scotland": "Scozia", "Wales": "Galles", "Hungary": "Ungheria", 
    "Turkey": "Turchia", "Albania": "Albania", "Serbia": "Serbia",
    "Finland": "Finlandia", "Belarus": "Bielorussia", "Czech Republic": "Repubblica Ceca",
    "Slovakia": "Slovacchia", "Slovenia": "Slovenia", "Romania": "Romania",
    "Bulgaria": "Bulgaria", "Greece": "Grecia", "Iceland": "Islanda"
}

def traduci_squadra(nome_inglese):
    return TRADUZIONI_NAZIONALI.get(nome_inglese.strip(), nome_inglese.strip())

def analizza_forma_avanzata(squadra, api_key, ruolo='home'):
    fallback_neutro = {'ppg': 1.0, 'gol_segnati_avg': 1.0, 'gol_subiti_avg': 1.0, 'differenza_reti': 0}
    if not api_key: return fallback_neutro
    try:
        headers = {'x-apisports-key': api_key}
        res = requests.get(f"https://v3.football.api-sports.io/teams?search={squadra}", headers=headers, timeout=10)
        data = res.json()
        if not data.get('response'): return fallback_neutro
        team_id = data['response'][0]['team']['id']
        time.sleep(0.35)
        res_fix = requests.get(f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5", headers=headers, timeout=10)
        fixtures = res_fix.json().get('response', [])
        punti, match_considerati = 0, 0
        for f in fixtures:
            gh = f['goals']['home']
            ga = f['goals']['away']
            if gh is None or ga is None: continue
            is_home = (f['teams']['home']['id'] == team_id)
            gf = gh if is_home else ga
            gs = ga if is_home else gh
            peso = 1.2 if ((ruolo == 'home' and is_home) or (ruolo == 'away' and not is_home)) else 0.8
            punti += (3 if gf > gs else (1 if gf == gs else 0)) * peso
            match_considerati += peso
        if match_considerati == 0: return fallback_neutro
        return {'ppg': round(punti / match_considerati, 2)}
    except:
        return fallback_neutro

def de_vig_mercato(outcomes):
    implied = {o.get('name') if 'point' not in o else f"{o.get('name')}_{o['point']}": 1.0 / o.get('price', 1) for o in outcomes if o.get('price', 0) > 1.0}
    tot = sum(implied.values())
    return {k: v / tot for k, v in implied.items()} if tot > 0 else {}

def carica_database():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database(db):
    with open('database.json', 'w', encoding='utf-8') as f: json.dump(db, f, indent=4, ensure_ascii=False)

def aggiorna_risultati(db):
    live = {}
    for camp in campionati:
        try:
            res = requests.get(f"https://api.the-odds-api.com/v4/sports/{camp}/scores/?apiKey={ODDS_API_KEY}&daysFrom=3", timeout=10)
            if res.status_code == 200:
                for m in res.json():
                    if m.get('completed'): live[m['id']] = m.get('scores')
        except: pass
    for sc in db['schedine']:
        if sc['stato_schedina'] == 'in attesa':
            vinte, perse = True, False
            for p in sc['partite']:
                if p['stato'] == 'in attesa' and p['id_partita'] in live and live[p['id_partita']]:
                    sc_casa = next((s['score'] for s in live[p['id_partita']] if traduci_squadra(s['name']) == p['squadra_casa']), 0)
                    sc_trasf = next((s['score'] for s in live[p['id_partita']] if traduci_squadra(s['name']) == p['squadra_trasferta']), 0)
                    sc_casa, sc_trasf = int(sc_casa), int(sc_trasf)
                    pron = p['pronostico'].lower()
                    vinta = False
                    if "vittoria " + p['squadra_casa'].lower() in pron: vinta = sc_casa > sc_trasf
                    elif "vittoria " + p['squadra_trasferta'].lower() in pron: vinta = sc_trasf > sc_casa
                    elif "pareggio" in pron: vinta = sc_casa == sc_trasf
                    p['stato'], p['risultato_reale'] = ('vinta' if vinta else 'persa'), f"{sc_casa}-{sc_trasf}"
                if p['stato'] == 'persa': perse = True
                if p['stato'] == 'in attesa': vinte = False
            sc['stato_schedina'] = 'persa' if perse else ('vinta' if vinte else 'in attesa')

def crea_schedina(db):
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia).date()
    fine_turno = oggi + timedelta(days=6)
    candidati = []
    
    errori_api = []
    partite_totali = 0
    
    for camp in campionati:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                errori_api.append(f"{camp} ({res.status_code})")
                continue
            partite = res.json()
        except: 
            errori_api.append(f"{camp} (timeout)")
            continue
        
        for partita in partite:
            try:
                data_ita = datetime.strptime(partita['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
                if not (oggi <= data_ita.date() <= fine_turno): continue
            except: continue
            
            partite_totali += 1
            nome_casa, nome_trasf = partita['home_team'], partita['away_team']
            mercato_h2h = {}
            
            for b in partita['bookmakers']:
                if not any(sb.lower() in b.get('title', '').lower() for sb in siti_ammessi): continue
                for m in b.get('markets', []):
                    if m['key'] == 'h2h': mercato_h2h = de_vig_mercato(m['outcomes'])
            
            fc = analizza_forma_avanzata(nome_casa, API_FOOTBALL_KEY, 'home')
            ft = analizza_forma_avanzata(nome_trasf, API_FOOTBALL_KEY, 'away')
            
            for b in partita['bookmakers']:
                if not any(sb.lower() in b.get('title', '').lower() for sb in siti_ammessi): continue
                for m in b.get('markets', []):
                    if m['key'] == 'h2h':
                        for out in m['outcomes']:
                            q = out.get('price', 0)
                            if not (1.20 <= q <= 2.80): continue
                            
                            fair_p = mercato_h2h.get(out['name'], 1.0 / q)
                            ev = (q * fair_p) - 1.0
                            desc = ""
                            
                            if out['name'] == nome_casa and fc['ppg'] >= 0.5: desc = f"vittoria {traduci_squadra(nome_casa)}"
                            elif out['name'] == nome_trasf and ft['ppg'] >= 0.5: desc = f"vittoria {traduci_squadra(nome_trasf)}"
                            elif out['name'] == 'Draw' and abs(fc['ppg'] - ft['ppg']) <= 1.0: desc = "pareggio"
                            
                            if desc and ev > -0.10:
                                score = fair_p + (ev * 2.0)
                                candidati.append({
                                    'id_partita': partita['id'], 
                                    'data_oggetto': str(data_ita.date()), 
                                    'data': data_ita.strftime("%d/%m %H:%M"),
                                    'squadra_casa': traduci_squadra(nome_casa), 'squadra_trasferta': traduci_squadra(nome_trasf),
                                    'pronostico': desc, 'quota': q, 'score': score, 'stato': 'in attesa', 'risultato_reale': ''
                                })
                break 

    if not candidati:
        msg_err = f"⚠️ **SBR ALERT DI SISTEMA**\n\n**Nessuna giocata elaborata oggi**. Ecco il report diagnostico:\n\n"
        msg_err += f"• **Partite scansionate valide**: {partite_totali}\n"
        if errori_api:
            msg_err += f"• **Errori API rilevati**: {', '.join(errori_api)}\n"
            msg_err += "*nota: se leggi l'errore 429 significa che hai superato il limite di chiamate gratuite mensili di The Odds API.*"
        else:
            msg_err += "• **Motivazione**: le quote attuali non garantiscono il livello minimo di sicurezza statistica."
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg_err, "parse_mode": "Markdown"})
        return
    
    unici = {}
    for c in sorted(candidati, key=lambda x: x['score'], reverse=True):
        if c['id_partita'] not in unici: unici[c['id_partita']] = c
        
    finalisti = sorted(unici.values(), key=lambda x: x['score'], reverse=True)[:3]
    quota_totale = 1.0
    for c in finalisti: quota_totale *= c['quota']
    quota_totale = round(quota_totale, 2)
    
    db['schedine'].append({
        'id': str(uuid.uuid4())[:8], 'data_creazione': datetime.now(fuso_italia).strftime("%d/%m/%Y"),
        'importo': 10.0, 'quota_totale': quota_totale, 'ritorno_potenziale': round(10.0 * quota_totale, 2),
        'stato_schedina': 'in attesa', 'partite': finalisti
    })
    
    msg = f"🚀 **nuova opportunità di valore individuata**\n\n**Modello Alpha** ha appena elaborato e certificato una nuova selezione ibrida.\n\n"
    msg += f"📊 quota totale: {quota_totale}\n💰 stake simulato: 10.0€\n\n"
    for c in finalisti: 
        msg += f"⚽ **{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}**\n🎯 {c['pronostico'].upper()} (@{c['quota']})\n\n"
    msg += "puoi verificare l'esito e l'andamento storico della cassa direttamente sul nostro portale ufficiale.\n\n"
    msg += "**#SBR #PronosticiCalcio #ValueBetting #IntelligenzaArtificiale #SportTrading**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    db = carica_database()
    aggiorna_risultati(db)
    crea_schedina(db)
    salva_database(db)

if __name__ == "__main__":
    main()
