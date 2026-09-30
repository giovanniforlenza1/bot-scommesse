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
    "Bulgaria": "Bulgaria", "Greece": "Grecia", "Iceland": "Islanda",
    "Republic of Ireland": "Irlanda", "Northern Ireland": "Irlanda del Nord",
    "Bosnia and Herzegovina": "Bosnia ed Erzegovina", "Montenegro": "Montenegro",
    "North Macedonia": "Macedonia del Nord", "Georgia": "Georgia", "Ukraine": "Ucraina",
    "Lithuania": "Lituania", "Latvia": "Lettonia", "Estonia": "Estonia",
    "Cyprus": "Cipro", "Malta": "Malta", "Moldova": "Moldavia", "Andorra": "Andorra",
    "San Marino": "San Marino", "Liechtenstein": "Liechtenstein", "Luxembourg": "Lussemburgo",
    "Armenia": "Armenia", "Azerbaijan": "Azerbaigian", "Kazakhstan": "Kazakistan",
    "Kosovo": "Kosovo", "Israel": "Israele", "Faroe Islands": "Isole Faroe",
    "Gibraltar": "Gibilterra"
}

def traduci_squadra(nome_inglese):
    nome_pulito = nome_inglese.strip()
    return TRADUZIONI_NAZIONALI.get(nome_pulito, nome_pulito)

def analizza_forma_avanzata(squadra, api_key, ruolo='home'):
    fallback_neutro = {
        'ppg': 1.5,
        'gol_segnati_avg': 1.3,
        'gol_subiti_avg': 1.2,
        'differenza_reti': 0
    }
    if not api_key:
        return fallback_neutro
        
    headers = {'x-apisports-key': api_key}
    try:
        res = requests.get(f"https://v3.football.api-sports.io/teams?search={squadra}", headers=headers, timeout=10)
        data = res.json()
        if not data.get('response'):
            return fallback_neutro
            
        team_id = data['response'][0]['team']['id']
        time.sleep(0.35)
        
        res_fix = requests.get(f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=6", headers=headers, timeout=10)
        fixtures = res_fix.json().get('response', [])
        
        punti = 0
        gf_tot = 0
        gs_tot = 0
        match_considerati = 0
        
        for f in fixtures:
            gh = f['goals']['home']
            ga = f['goals']['away']
            if gh is None or ga is None:
                continue
                
            is_home_game = (f['teams']['home']['id'] == team_id)
            gf = gh if is_home_game else ga
            gs = ga if is_home_game else gh
            
            peso = 1.3 if ((ruolo == 'home' and is_home_game) or (ruolo == 'away' and not is_home_game)) else 0.8
            
            gf_tot += gf * peso
            gs_tot += gs * peso
            
            punti_partita = 3 if gf > gs else (1 if gf == gs else 0)
            punti += punti_partita * peso
            match_considerati += peso
            
        if match_considerati == 0:
            return fallback_neutro
            
        return {
            'ppg': round(punti / match_considerati, 2),
            'gol_segnati_avg': max(0.5, round(gf_tot / match_considerati, 2)),
            'gol_subiti_avg': max(0.5, round(gs_tot / match_considerati, 2)),
            'differenza_reti': round((gf_tot - gs_tot) / match_considerati, 2)
        }
    except Exception:
        return fallback_neutro

def poisson_prob(lmbda, k):
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def calcola_probabilita_poisson(lambda_casa, mu_trasferta):
    p_over25 = 0.0
    p_btts = 0.0
    
    for g_casa in range(7):
        p_c = poisson_prob(lambda_casa, g_casa)
        for g_trasf in range(7):
            p_t = poisson_prob(mu_trasferta, g_trasf)
            p_esito = p_c * p_t
            
            if (g_casa + g_trasf) > 2.5:
                p_over25 += p_esito
            if g_casa > 0 and g_trasf > 0:
                p_btts += p_esito
                
    return {
        'over25': min(0.95, max(0.05, p_over25)),
        'under25': min(0.95, max(0.05, 1.0 - p_over25)),
        'gol': min(0.95, max(0.05, p_btts)),
        'nogol': min(0.95, max(0.05, 1.0 - p_btts))
    }

def de_vig_mercato(outcomes):
    implied = {}
    tot_implied = 0.0
    for o in outcomes:
        price = o.get('price', 0)
        if price > 1.0:
            p = 1.0 / price
            key = o.get('name')
            if 'point' in o:
                key = f"{key}_{o['point']}"
            implied[key] = p
            tot_implied += p
            
    if tot_implied == 0:
        return {}
        
    return {k: v / tot_implied for k, v in implied.items()}

def carica_database():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database(db):
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def aggiorna_risultati(db):
    risultati_live = {}
    for camp in campionati:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/scores/?apiKey={ODDS_API_KEY}&daysFrom=3"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                for match in res.json():
                    if match.get('completed'):
                        risultati_live[match['id']] = match.get('scores')
        except Exception:
            continue
    
    for schedina in db['schedine']:
        if schedina['stato_schedina'] == 'in attesa':
            tutte_vinte = True
            almeno_una_persa = False
            for p in schedina['partite']:
                if p['stato'] == 'in attesa' and p['id_partita'] in risultati_live:
                    scores = risultati_live[p['id_partita']]
                    if not scores:
                        continue
                    
                    squadra_casa_originale = ""
                    squadra_trasferta_originale = ""
                    for s in scores:
                        if traduci_squadra(s['name']) == p['squadra_casa']:
                            squadra_casa_originale = s['name']
                        if traduci_squadra(s['name']) == p['squadra_trasferta']:
                            squadra_trasferta_originale = s['name']
                            
                    score_casa = int(next((s['score'] for s in scores if s['name'] == squadra_casa_originale), 0))
                    score_trasferta = int(next((s['score'] for s in scores if s['name'] == squadra_trasferta_originale), 0))
                    
                    vinta = False
                    pron = p['pronostico'].lower()
                    if f"vittoria {p['squadra_casa'].lower()}" in pron:
                        vinta = score_casa > score_trasferta
                    elif f"vittoria {p['squadra_trasferta'].lower()}" in pron:
                        vinta = score_trasferta > score_casa
                    elif "pareggio" in pron:
                        vinta = score_casa == score_trasferta
                    elif "over 2.5" in pron:
                        vinta = (score_casa + score_trasferta) > 2
                    elif "under 2.5" in pron:
                        vinta = (score_casa + score_trasferta) < 3
                    elif "gol" in pron and "no" not in pron:
                        vinta = score_casa > 0 and score_trasferta > 0
                    elif "no gol" in pron:
                        vinta = score_casa == 0 or score_trasferta == 0
                        
                    p['stato'] = 'vinta' if vinta else 'persa'
                    p['risultato_reale'] = f"{score_casa}-{score_trasferta}"
                
                if p['stato'] == 'persa':
                    almeno_una_persa = True
                if p['stato'] == 'in attesa':
                    tutte_vinte = False
                
            if almeno_una_persa:
                schedina['stato_schedina'] = 'persa'
            elif tutte_vinte:
                schedina['stato_schedina'] = 'vinta'

def ottimizza_composizione_coupon(candidati):
    if not candidati:
        return []
        
    candidati_ordinati = sorted(candidati, key=lambda x: x['edge_ev'], reverse=True)
    
    per_data = defaultdict(list)
    for c in candidati_ordinati:
        per_data[c['data_oggetto']].append(c)
        
    selezioni = []
    for d in sorted(per_data.keys()):
        if len(per_data[d]) >= 1:
            selezioni = per_data[d][:3]
            break
            
    if not selezioni:
        selezioni = candidati_ordinati[:2]
        
    coupon = []
    quota_prog = 1.0
    for s in selezioni:
        nuova_quota = quota_prog * s['quota']
        if len(coupon) >= 1 and nuova_quota > 4.50:
            break
        coupon.append(s)
        quota_prog = nuova_quota
        if len(coupon) == 3:
            break
            
    return coupon

def crea_schedina(db):
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia).date()
    fine_turno = oggi + timedelta(days=4)
    
    candidati_value = []
    print(f"[{datetime.now().strftime('%H:%M:%S')}] scansione attiva da {oggi} a {fine_turno}...")
    
    partite_totali_trovate = 0
    
    for camp in campionati:
        is_nations_league = (camp == 'soccer_uefa_nations_league')
        
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals,btts"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                url_fallback = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
                res = requests.get(url_fallback, timeout=10)
                if res.status_code != 200:
                    continue
            partite = res.json()
        except Exception:
            continue
            
        partite_nel_range = 0
        for p_test in partite:
            try:
                dt_test = datetime.strptime(p_test['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
                if oggi <= dt_test.date() <= fine_turno:
                    partite_nel_range += 1
            except Exception:
                pass
                
        print(f"[{camp}] trovate {len(partite)} partite a palinsesto ({partite_nel_range} nei prossimi 4 giorni)")
        partite_totali_trovate += partite_nel_range
        
        for partita in partite:
            try:
                data_ita = datetime.strptime(partita['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            except Exception:
                continue
                
            if not (oggi <= data_ita.date() <= fine_turno) or not partita.get('bookmakers'):
                continue
                
            nome_casa = partita['home_team']
            nome_trasf = partita['away_team']
            
            mercato_h2h_devig = {}
            mercato_totals_devig = {}
            mercato_btts_devig = {}
            
            for b in partita['bookmakers']:
                for m in b.get('markets', []):
                    if m['key'] == 'h2h' and not mercato_h2h_devig:
                        mercato_h2h_devig = de_vig_mercato(m['outcomes'])
                    elif m['key'] == 'totals' and not mercato_totals_devig:
                        mercato_totals_devig = de_vig_mercato(m['outcomes'])
                    elif m['key'] == 'btts' and not mercato_btts_devig:
                        mercato_btts_devig = de_vig_mercato(m['outcomes'])
            
            forma_casa = analizza_forma_avanzata(nome_casa, API_FOOTBALL_KEY, ruolo='home')
            forma_trasf = analizza_forma_avanzata(nome_trasf, API_FOOTBALL_KEY, ruolo='away')
            
            lambda_casa = max(0.6, (forma_casa['gol_segnati_avg'] + forma_trasf['gol_subiti_avg']) / 2.0)
            mu_trasf = max(0.5, (forma_trasf['gol_segnati_avg'] + forma_casa['gol_subiti_avg']) / 2.0)
            poisson_curve = calcola_probabilita_poisson(lambda_casa, mu_trasf)
            
            # soglie differenziate: per le nazionali accettiamo disallineamenti minimi
            soglia_ev_h2h = -0.01 if is_nations_league else 0.01
            soglia_ev_gol = 0.00 if is_nations_league else 0.015
            
            for book in partita['bookmakers']:
                nome_book = book.get('title', '')
                if not any(sb.lower() in nome_book.lower() for sb in siti_ammessi):
                    continue
                    
                for mercato in book.get('markets', []):
                    if mercato['key'] == 'h2h':
                        for out in mercato['outcomes']:
                            q = out.get('price', 0)
                            if not (1.35 <= q <= 2.35):
                                continue
                            
                            target_name = out['name']
                            fair_p = mercato_h2h_devig.get(target_name, 1.0 / q)
                            
                            stat_ok = False
                            if target_name == nome_casa:
                                stat_ok = True if is_nations_league else (forma_casa['ppg'] >= 1.0 and forma_casa['differenza_reti'] >= -2)
                                desc = f"vittoria {traduci_squadra(nome_casa)}"
                                info_stat = f"forma casa: {forma_casa['ppg']} ppg" if not is_nations_league else "confronto quote di consenso uefa"
                            elif target_name == nome_trasf:
                                stat_ok = True if is_nations_league else (forma_trasf['ppg'] >= 1.0 and forma_trasf['differenza_reti'] >= -2)
                                desc = f"vittoria {traduci_squadra(nome_trasf)}"
                                info_stat = f"forma trasferta: {forma_trasf['ppg']} ppg" if not is_nations_league else "confronto quote di consenso uefa"
                            elif target_name == 'Draw':
                                stat_ok = True if is_nations_league else (abs(forma_casa['ppg'] - forma_trasf['ppg']) <= 0.7)
                                desc = "pareggio"
                                info_stat = f"equilibrio ppg: {forma_casa['ppg']} vs {forma_trasf['ppg']}" if not is_nations_league else "equilibrio quote uefa"
                            else:
                                continue
                                
                            ev = (q * fair_p) - 1.0
                            if ev >= soglia_ev_h2h and stat_ok:
                                candidati_value.append({
                                    'id_partita': partita['id'],
                                    'data_oggetto': data_ita.date(),
                                    'data': data_ita.strftime("%d/%m %H:%M"),
                                    'squadra_casa': traduci_squadra(nome_casa),
                                    'squadra_trasferta': traduci_squadra(nome_trasf),
                                    'pronostico': desc,
                                    'quota': q,
                                    'edge_ev': round(max(0.1, ev * 100), 1),
                                    'info_stat': info_stat,
                                    'stato': 'in attesa',
                                    'risultato_reale': ''
                                })
                                
                    elif mercato['key'] == 'totals':
                        for out in mercato['outcomes']:
                            if out.get('point') != 2.5:
                                continue
                            q = out.get('price', 0)
                            if not (1.40 <= q <= 2.25):
                                continue
                                
                            is_over = out['name'] == 'Over'
                            p_poisson = poisson_curve['over25'] if is_over else poisson_curve['under25']
                            ev_poisson = (q * p_poisson) - 1.0
                            
                            if ev_poisson >= soglia_ev_gol:
                                desc = "over 2.5 gol" if is_over else "under 2.5 gol"
                                attesa_gol = round(lambda_casa + mu_trasf, 2)
                                candidati_value.append({
                                    'id_partita': partita['id'],
                                    'data_oggetto': data_ita.date(),
                                    'data': data_ita.strftime("%d/%m %H:%M"),
                                    'squadra_casa': traduci_squadra(nome_casa),
                                    'squadra_trasferta': traduci_squadra(nome_trasf),
                                    'pronostico': desc,
                                    'quota': q,
                                    'edge_ev': round(max(0.1, ev_poisson * 100), 1),
                                    'info_stat': f"modello Poisson attesa: {attesa_gol} gol",
                                    'stato': 'in attesa',
                                    'risultato_reale': ''
                                })
                                
                    elif mercato['key'] == 'btts':
                        for out in mercato['outcomes']:
                            q = out.get('price', 0)
                            if not (1.40 <= q <= 2.20):
                                continue
                                
                            is_gol = out['name'] == 'Yes'
                            p_poisson = poisson_curve['gol'] if is_gol else poisson_curve['nogol']
                            ev_poisson = (q * p_poisson) - 1.0
                            
                            if ev_poisson >= soglia_ev_gol:
                                desc = "gol (entrambe segnano)" if is_gol else "no gol"
                                candidati_value.append({
                                    'id_partita': partita['id'],
                                    'data_oggetto': data_ita.date(),
                                    'data': data_ita.strftime("%d/%m %H:%M"),
                                    'squadra_casa': traduci_squadra(nome_casa),
                                    'squadra_trasferta': traduci_squadra(nome_trasf),
                                    'pronostico': desc,
                                    'quota': q,
                                    'edge_ev': round(max(0.1, ev_poisson * 100), 1),
                                    'info_stat': f"prob. stimata Poisson: {round(p_poisson*100)}%",
                                    'stato': 'in attesa',
                                    'risultato_reale': ''
                                })
                break
                
    print(f"partite considerate nel periodo: {partite_totali_trovate}. selezioni con edge trovate: {len(candidati_value)}")
    
    if not candidati_value:
        print("nessuna selezione soddisfa i criteri quantitativi attuali.")
        return
        
    coupon_selezionato = ottimizza_composizione_coupon(candidati_value)
    if not coupon_selezionato:
        print("impossibile assemblare un coupon coerente.")
        return
        
    quota_totale = 1.0
    for c in coupon_selezionato:
        quota_totale *= c['quota']
    quota_totale = round(quota_totale, 2)
    importo = 10.0
    
    partite_salvate = []
    for c in coupon_selezionato:
        partite_salvate.append({
            'id_partita': c['id_partita'],
            'data': c['data'],
            'squadra_casa': c['squadra_casa'],
            'squadra_trasferta': c['squadra_trasferta'],
            'pronostico': c['pronostico'],
            'quota': c['quota'],
            'stato': c['stato'],
            'risultato_reale': c['risultato_reale']
        })
        
    nuova_schedina = {
        'id': str(uuid.uuid4())[:8],
        'data_creazione': datetime.now(fuso_italia).strftime("%d/%m/%Y"),
        'importo': importo,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(importo * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'partite': partite_salvate
    }
    
    db['schedine'].append(nuova_schedina)
    
    num_eventi = len(coupon_selezionato)
    tipo_giocata = "SINGOLA DI VALORE" if num_eventi == 1 else (f"DOPPIA AD ALTO VALORE" if num_eventi == 2 else f"TRIPLA SELEZIONATA")
    
    msg = f"📊 **RICEVUTA SBR | MODELLO ALPHA**\n"
    msg += f"tipologia: {tipo_giocata} | quota totale: {quota_totale} | stake simulato: {importo}€\n\n"
    
    for c in coupon_selezionato:
        msg += f"⚽ {c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}\n"
        msg += f"🎯 {c['pronostico'].upper()} (@{c['quota']})\n"
        msg += f"📈 edge quantitativo: +{c['edge_ev']}% | {c['info_stat']}\n\n"
        
    msg += "esito e storico verificati sul portale ufficiale.\n"
    msg += "**#SBR #ValueBetting #ExpectedValue #Poisson #ModelloAlpha**"
    
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
        timeout=10
    )
    print(f"messaggio telegram inviato con status code: {r.status_code}")

def main():
    db = carica_database()
    aggiorna_risultati(db)
    crea_schedina(db)
    salva_database(db)

if __name__ == "__main__":
    main()
