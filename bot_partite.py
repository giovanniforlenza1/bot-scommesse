import requests
import json
import os
import uuid
import time
import math
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
    fallback_neutro = {'ppg': 1.2, 'gol_segnati_avg': 1.2, 'gol_subiti_avg': 1.2, 'differenza_reti': 0}
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
        punti, gf_tot, gs_tot, match_considerati = 0, 0, 0, 0
        for f in fixtures:
            gh = f['goals']['home']
            ga = f['goals']['away']
            if gh is None or ga is None: continue
            is_home = (f['teams']['home']['id'] == team_id)
            gf = gh if is_home else ga
            gs = ga if is_home else gh
            peso = 1.2 if ((ruolo == 'home' and is_home) or (ruolo == 'away' and not is_home)) else 0.8
            gf_tot += gf * peso
            gs_tot += gs * peso
            punti += (3 if gf > gs else (1 if gf == gs else 0)) * peso
            match_considerati += peso
        if match_considerati == 0: return fallback_neutro
        return {
            'ppg': round(punti / match_considerati, 2),
            'gol_segnati_avg': max(0.5, round(gf_tot / match_considerati, 2)),
            'gol_subiti_avg': max(0.5, round(gs_tot / match_considerati, 2)),
            'differenza_reti': round((gf_tot - gs_tot) / match_considerati, 2)
        }
    except:
        return fallback_neutro

def poisson_prob(lmbda, k):
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def calcola_probabilita_poisson(lambda_casa, mu_trasferta):
    p_over25, p_btts = 0.0, 0.0
    for g_casa in range(7):
        for g_trasf in range(7):
            p_esito = poisson_prob(lambda_casa, g_casa) * poisson_prob(mu_trasferta, g_trasf)
            if (g_casa + g_trasf) > 2.5: p_over25 += p_esito
            if g_casa > 0 and g_trasf > 0: p_btts += p_esito
    return {'over25': p_over25, 'under25': 1.0 - p_over25, 'gol': p_btts, 'nogol': 1.0 - p_btts}

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
                    elif "over 2.5" in pron: vinta = (sc_casa + sc_trasf) > 2
                    elif "under 2.5" in pron: vinta = (sc_casa + sc_trasf) < 3
                    elif "gol" in pron and "no" not in pron: vinta = sc_casa > 0 and sc_trasf > 0
                    elif "no gol" in pron: vinta = sc_casa == 0 or sc_trasf == 0
                    p['stato'], p['risultato_reale'] = ('vinta' if vinta else 'persa'), f"{sc_casa}-{sc_trasf}"
                if p['stato'] == 'persa': perse = True
                if p['stato'] == 'in attesa': vinte = False
            sc['stato_schedina'] = 'persa' if perse else ('vinta' if vinte else 'in attesa')

def crea_schedina(db):
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia).date()
    fine_turno = oggi + timedelta(days=5)
    candidati = []
    
    for camp in campionati:
        try:
            res = requests.get(f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals,btts", timeout=10)
            if res.status_code != 200: continue
            partite = res.json()
        except: continue
        
        for partita in partite:
            try:
                data_ita = datetime.strptime(partita['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
                if not (oggi <= data_ita.date() <= fine_turno): continue
            except: continue
            
            nome_casa, nome_trasf = partita['home_team'], partita['away_team']
            mercato_h2h, mercato_tot, mercato_btts = {}, {}, {}
            
            for b in partita['bookmakers']:
                if not any(sb.lower() in b.get('title', '').lower() for sb in siti_ammessi): continue
                for m in b.get('markets', []):
                    if m['key'] == 'h2h': mercato_h2h = de_vig_mercato(m['outcomes'])
                    elif m['key'] == 'totals': mercato_tot = de_vig_mercato(m['outcomes'])
                    elif m['key'] == 'btts': mercato_btts = de_vig_mercato(m['outcomes'])
            
            fc = analizza_forma_avanzata(nome_casa, API_FOOTBALL_KEY, 'home')
            ft = analizza_forma_avanzata(nome_trasf, API_FOOTBALL_KEY, 'away')
            poisson_curve = calcola_probabilita_poisson(max(0.6, (fc['gol_segnati_avg'] + ft['gol_subiti_avg']) / 2.0), max(0.5, (ft['gol_segnati_avg'] + fc['gol_subiti_avg']) / 2.0))
            
            for b in partita['bookmakers']:
                if not any(sb.lower() in b.get('title', '').lower() for sb in siti_ammessi): continue
                for m in b.get('markets', []):
                    for out in m['outcomes']:
                        q = out.get('price', 0)
                        if not (1.30 <= q <= 2.60): continue
                        
                        ev, score, desc = -1.0, 0, ""
                        if m['key'] == 'h2h':
                            fair_p = mercato_h2h.get(out['name'], 1.0 / q)
                            ev = (q * fair_p) - 1.0
                            if out['name'] == nome_casa and fc['ppg'] >= 0.8: desc = f"vittoria {traduci_squadra(nome_casa)}"
                            elif out['name'] == nome_trasf and ft['ppg'] >= 0.8: desc = f"vittoria {traduci_squadra(nome_trasf)}"
                            elif out['name'] == 'Draw' and abs(fc['ppg'] - ft['ppg']) <= 1.0: desc = "pareggio"
                        elif m['key'] == 'totals' and out.get('point') == 2.5:
                            fair_p = poisson_curve['over25'] if out['name'] == 'Over' else poisson_curve['under25']
                            ev = (q * fair_p) - 1.0
                            desc = "over 2.5 gol" if out['name'] == 'Over' else "under 2.5 gol"
                        elif m['key'] == 'btts':
                            fair_p = poisson_curve['gol'] if out['name'] == 'Yes' else poisson_curve['nogol']
                            ev = (q * fair_p) - 1.0
                            desc = "gol (entrambe segnano)" if out['name'] == 'Yes' else "no gol"
                            
                        if desc and ev > -0.05:
                            score = fair_p + (ev * 2.0)
                            candidati.append({
                                'id_partita': partita['id'], 'data_oggetto': data_ita.date(), 'data': data_ita.strftime("%d/%m %H:%M"),
                                'squadra_casa': traduci_squadra(nome_casa), 'squadra_trasferta': traduci_squadra(nome_trasf),
                                'pronostico': desc, 'quota': q, 'score': score, 'stato': 'in attesa', 'risultato_reale': ''
                            })
                break 

    if not candidati: return
    
    unici = {}
    for c in sorted(candidati, key=lambda x: x['score'], reverse=True):
        if c['id_partita'] not in unici: unici[c['id_partita']] = c
        
    finalisti = sorted(unici.values(), key=lambda x: x['score'], reverse=True)[:3]
    quota_totale = round(math.prod([c['quota'] for c in finalisti]), 2)
    
    db['schedine'].append({
        'id': str(uuid.uuid4())[:8], 'data_creazione': datetime.now(fuso_italia).strftime("%d/%m/%Y"),
        'importo': 10.0, 'quota_totale': quota_totale, 'ritorno_potenziale': round(10.0 * quota_totale, 2),
        'stato_schedina': 'in attesa', 'partite': finalisti
    })
    
    msg = f"📊 **RICEVUTA SBR | MODELLO ALPHA**\nselezione ibrida | quota totale: {quota_totale} | stake simulato: 10.0€\n\n"
    for c in finalisti: msg += f"⚽ {c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}\n🎯 {c['pronostico'].upper()} (@{c['quota']})\n\n"
    msg += "esito e storico verificati sul portale ufficiale.\n**#SBR #PronosticiCalcio #ValueBetting #ModelloAlpha**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    db = carica_database()
    aggiorna_risultati(db)
    crea_schedina(db)
    salva_database(db)

if __name__ == "__main__":
    main()
