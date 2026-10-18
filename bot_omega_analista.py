import requests
import json
import os
import random
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

campionati = [
    'soccer_italy_serie_a', 'soccer_italy_serie_b', 'soccer_epl', 'soccer_efl_champ',
    'soccer_spain_la_liga', 'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'soccer_uefa_nations_league'
]

campionati_espn = [
    'ita.1', 'ita.2', 'eng.1', 'eng.2', 'esp.1', 'ger.1', 
    'fra.1', 'ned.1', 'por.1', 'uefa.champions', 'uefa.europa'
]

COORDINATE_CAMPIONATI = {
    'soccer_italy_serie_a': (45.46, 9.19), 'soccer_italy_serie_b': (44.49, 11.34),
    'soccer_epl': (51.50, -0.12), 'soccer_efl_champ': (52.48, -1.89),
    'soccer_spain_la_liga': (40.41, -3.70), 'soccer_germany_bundesliga': (48.13, 11.58),
    'soccer_france_ligue_one': (48.85, 2.35), 'soccer_netherlands_eredivisie': (52.36, 4.90),
    'soccer_portugal_primeira_liga': (38.72, -9.13)
}

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
    "Inter Milan": "Inter", "Internazionale": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus",
    "Hellas Verona": "Verona", "Bologna FC": "Bologna", "Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Venezia FC": "Venezia", "Parma Calcio 1913": "Parma",
    "Como 1907": "Como", "US Lecce": "Lecce", "Cagliari Calcio": "Cagliari", "AC Monza": "Monza",
    "Atalanta BC": "Atalanta", "Manchester Utd": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham", "Tottenham Hotspur": "Tottenham",
    "Newcastle Utd": "Newcastle", "Newcastle United": "Newcastle", "Paris Saint Germain": "PSG",
    "Paris Saint-Germain": "PSG", "Bayern Munich": "Bayern Monaco", "Bayer Leverkusen": "Bayer Leverkusen",
    "Borussia Dortmund": "Dortmund", "RB Leipzig": "Lipsia", "Eintracht Frankfurt": "Francoforte",
    "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad", "Atletico Madrid": "Atletico Madrid",
    "Athletic Club": "Athletic Bilbao", "RB Salzburg": "Salisburgo", "FC Salzburg": "Salisburgo",
    "Sporting CP": "Sporting Lisbona", "PSV Eindhoven": "PSV", "Feyenoord Rotterdam": "Feyenoord",
    "Wolverhampton Wanderers": "Wolverhampton", "Wolves": "Wolverhampton"
}

def traduci_squadra(nome):
    nome_pulito = str(nome).strip()
    if nome_pulito in TRADUZIONI_NAZIONALI: return TRADUZIONI_NAZIONALI[nome_pulito]
    if nome_pulito in TRADUZIONI_SQUADRE: return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "").replace(" CF", "").replace(" SSC", "")

def normalizza_chiave_squadra(nome):
    n = traduci_squadra(nome).lower()
    for p in ["calcio", "fc", "ac", "sc", "cf", "united", "city", "sporting", "1907", "1913", "bc", "us", "ss", "cfc", "as"]:
        n = n.replace(f" {p}", "").replace(f"{p} ", "")
    return n.strip()

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

def controlla_meteo_avverso(lega):
    if lega not in COORDINATE_CAMPIONATI: return False
    lat, lon = COORDINATE_CAMPIONATI[lega]
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=precipitation,wind_speed_10m"
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            curr = res.json().get('current', {})
            if curr.get('precipitation', 0.0) > 5.0 or curr.get('wind_speed_10m', 0.0) > 40.0:
                return True
    except: pass
    return False

def scarica_motivazione_classifica():
    motivazioni = {}
    for lega in ['ita.1', 'eng.1', 'esp.1', 'ger.1', 'fra.1']:
        try:
            url = f"https://site.api.espn.com/apis/v2/sports/soccer/{lega}/standings"
            res = requests.get(url, timeout=5)
            if res.status_code != 200: continue
            children = res.json().get('children', [])
            if not children: continue
            entries = children[0].get('standings', {}).get('entries', [])
            tot = len(entries)
            for idx, ent in enumerate(entries):
                pos = idx + 1
                t_name = ent.get('team', {}).get('displayName', '')
                k_sq = normalizza_chiave_squadra(t_name)
                if pos <= 6 or pos >= (tot - 4): motivazioni[k_sq] = 1.02
                elif 9 <= pos <= 13: motivazioni[k_sq] = 0.98
                else: motivazioni[k_sq] = 1.0
        except: continue
    return motivazioni

def genera_database_studio_squadre(oggi):
    raw_stats = {}
    motivazioni_classifica = scarica_motivazione_classifica()
    date_studio = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(1, 13)]

    for lega in campionati_espn:
        for d_str in date_studio:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={d_str}"
            try:
                res = requests.get(url, timeout=5)
                if res.status_code != 200: continue
                for ev in res.json().get('events', []):
                    comp = ev.get('competitions', [{}])[0]
                    if not comp.get('status', {}).get('type', {}).get('completed', False): continue
                    data_match_str = ev.get('date', '')[:10]
                    teams = comp.get('competitors', [])
                    if len(teams) < 2: continue

                    info_t = []
                    for t in teams:
                        t_name = traduci_squadra(t.get('team', {}).get('displayName', ''))
                        t_key = normalizza_chiave_squadra(t_name)
                        score_str = str(t.get('score', '0')).strip()
                        gol = int(float(score_str)) if score_str.isdigit() else 0
                        tiri_porta = 0
                        for s in t.get('statistics', []):
                            if s.get('name') in ['shotsOnTarget', 'shotsOnGoal']:
                                val_s = str(s.get('displayValue', '0')).strip()
                                tiri_porta = int(float(val_s)) if val_s.replace('.', '', 1).isdigit() else 0
                        info_t.append({'key': t_key, 'nome': t_name, 'gol': gol, 'tiri_porta': tiri_porta if tiri_porta > 0 else max(1, gol * 2 + 1), 'is_home': (t.get('homeAway') == 'home')})

                    for idx in [0, 1]:
                        me, opp = info_t[idx], info_t[1 - idx]
                        punti = 3 if me['gol'] > opp['gol'] else (1 if me['gol'] == opp['gol'] else 0)
                        rec = raw_stats.setdefault(me['key'], {'nome_ufficiale': me['nome'], 'partite_lette': 0, 'gol_fatti': [], 'gol_subiti': [], 'tiri_porta_fatti': [], 'tiri_porta_subiti': [], 'punti_casa': [], 'punti_trasf': [], 'punti_tot': [], 'ultima_partita': data_match_str})
                        rec['partite_lette'] += 1
                        rec['gol_fatti'].append(me['gol'])
                        rec['gol_subiti'].append(opp['gol'])
                        rec['tiri_porta_fatti'].append(me['tiri_porta'])
                        rec['tiri_porta_subiti'].append(opp['tiri_porta'])
                        rec['punti_tot'].append(punti)
                        if me['is_home']: rec['punti_casa'].append(punti)
                        else: rec['punti_trasf'].append(punti)
                        if data_match_str > rec['ultima_partita']: rec['ultima_partita'] = data_match_str
            except: continue

    db_squadre = {}
    for k, v in raw_stats.items():
        n_gare = max(1, v['partite_lette'])
        media_gf = round(sum(v['gol_fatti']) / n_gare, 2)
        media_gs = round(sum(v['gol_subiti']) / n_gare, 2)
        media_tiri_f = round(sum(v['tiri_porta_fatti']) / n_gare, 2)
        media_tiri_s = round(sum(v['tiri_porta_subiti']) / n_gare, 2)
        media_punti = round(sum(v['punti_tot']) / n_gare, 2)
        media_casa = sum(v['punti_casa']) / len(v['punti_casa']) if v['punti_casa'] else media_punti
        media_trasf = sum(v['punti_trasf']) / len(v['punti_trasf']) if v['punti_trasf'] else media_punti
        
        bonus_sfortuna = 0.03 if (media_tiri_f >= 5.0 and media_gf <= 1.0) else 0.0
        mot_classifica = motivazioni_classifica.get(k, 1.0)
        base_rating = 1.0 + ((media_punti - 1.4) * 0.03) + ((media_tiri_f - media_tiri_s) * 0.01) + bonus_sfortuna
        rating_tattico = round(max(0.85, min(1.15, base_rating * mot_classifica)), 3)
        
        db_squadre[k] = {
            'nome': v['nome_ufficiale'], 'gare_analizzate': n_gare,
            'media_gol_fatti': media_gf, 'media_gol_subiti': media_gs,
            'media_tiri_porta': media_tiri_f, 'media_tiri_concessi': media_tiri_s,
            'ultima_partita': v['ultima_partita'], 'rating_tattico': rating_tattico,
            'rating_casa': round(rating_tattico + (media_casa - 1.5) * 0.02, 3),
            'rating_trasferta': round(rating_tattico + (media_trasf - 1.2) * 0.02, 3)
        }

    with open('database_squadre.json', 'w', encoding='utf-8') as f:
        json.dump({'ultimo_aggiornamento': oggi.strftime("%d/%m/%Y %H:%M"), 'totale_squadre_schedate': len(db_squadre), 'squadre': db_squadre}, f, indent=4, ensure_ascii=False)
    return db_squadre

def esegui_test_silenzioso_tennis(oggi):
    partite_tennis = esegui_richiesta_api("https://api.the-odds-api.com/v4/sports/tennis_atp_french_open/odds/?apiKey=API_KEY_SEGRETA&regions=eu&markets=h2h")
    if not partite_tennis: return
    test_picks = [{'match': f"{pt.get('home_team')} - {pt.get('away_team')}", 'data': oggi.strftime("%d/%m/%Y")} for pt in partite_tennis[:5]]
    with open('tennis_test.json', 'w', encoding='utf-8') as f: json.dump(test_picks, f, indent=2)

def cerca_dati_squadra(db_squadre, nome_ita):
    k_cerca = normalizza_chiave_squadra(nome_ita)
    if k_cerca in db_squadre: return db_squadre[k_cerca]
    for k, val in db_squadre.items():
        if k_cerca and (k_cerca in k or k in k_cerca): return val
    return None

def calcola_fattore_specifico(db_squadre, nome_ita, data_partita_dt, is_home=True):
    info = cerca_dati_squadra(db_squadre, nome_ita)
    if not info: return 1.0, False
    moltiplicatore = info.get('rating_casa' if is_home else 'rating_trasferta', info.get('rating_tattico', 1.0))
    stanca = False
    ultima_str = info.get('ultima_partita', '')
    if ultima_str:
        try:
            dt_ultima = datetime.strptime(ultima_str, "%Y-%m-%d").date()
            if 0 < (data_partita_dt.date() - dt_ultima).days <= 3:
                moltiplicatore *= 0.97 # Malus stanchezza leggero ed elastico
                stanca = True
        except: pass
    return moltiplicatore, stanca

def power_devig(q1, qx, q2):
    inv1, invx, inv2 = 1.0 / q1, 1.0 / qx, 1.0 / q2
    overround = inv1 + invx + inv2
    if overround <= 1.0: return inv1, invx, inv2
    esponente = 1.0 / (1.0 - (overround - 1.0) * 0.40)
    p1, px, p2 = (inv1 ** esponente), (invx ** esponente), (inv2 ** esponente)
    tot = p1 + px + p2
    return p1 / tot, px / tot, p2 / tot

def poisson_random(lmbda):
    L = math.exp(-lmbda)
    k, p = 0, 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1

def simulazione_monte_carlo_avanzata(prob_1, prob_x, prob_2, mult_casa, mult_trasf, meteo_avverso=False, n_sim=10000):
    xg_casa = max(0.45, (prob_1 * 2.65) + (prob_x * 0.82)) * (0.92 if meteo_avverso else 1.0) * (mult_casa / mult_trasf)
    xg_trasf = max(0.30, (prob_2 * 2.50) + (prob_x * 0.82)) * (0.92 if meteo_avverso else 1.0) * (mult_trasf / mult_casa)
    
    vitt_1, pareggi, vitt_2 = 0, 0, 0
    for _ in range(n_sim):
        gol_c = poisson_random(xg_casa)
        gol_t = poisson_random(xg_trasf)
        if (gol_c == 1 and gol_t == 0) or (gol_c == 0 and gol_t == 1):
            if random.random() < 0.06: gol_c = gol_t
        if gol_c > gol_t: vitt_1 += 1
        elif gol_c == gol_t: pareggi += 1
        else: vitt_2 += 1
        
    return (prob_1 * 0.60) + ((vitt_1 / n_sim) * 0.40), (prob_x * 0.60) + ((pareggi / n_sim) * 0.40), (prob_2 * 0.60) + ((vitt_2 / n_sim) * 0.40)

def esegui_analista():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    limite_temporale = oggi + timedelta(days=4)
    
    db_squadre = genera_database_studio_squadre(oggi)
    esegui_test_silenzioso_tennis(oggi)
    risultati_analisi = []
    
    for camp in campionati:
        meteo_brutto = controlla_meteo_avverso(camp)
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        partite = esegui_richiesta_api(url_template)
        if not partite: continue
        
        for p in partite:
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < oggi or data_ita > limite_temporale: continue
                
            casa_orig, trasf_orig = p['home_team'], p['away_team']
            casa_ita, trasf_ita = traduci_squadra(casa_orig), traduci_squadra(trasf_orig)
            
            quote_1, quote_x, quote_2 = [], [], []
            pinnacle_1, pinnacle_x, pinnacle_2 = None, None, None
            
            for book in p.get('bookmakers', []):
                key_b = book.get('key', '').lower()
                title_b = book.get('title', '').lower()
                if 'exchange' in title_b or 'betfair' in key_b or 'matchbook' in key_b: continue
                is_pin = 'pinnacle' in key_b
                for m in book.get('markets', []):
                    if m.get('key') == 'h2h':
                        q1, qx, q2 = None, None, None
                        for out in m.get('outcomes', []):
                            if out['name'] == casa_orig: q1 = out['price']
                            elif out['name'] == trasf_orig: q2 = out['price']
                            elif out['name'].lower() == 'draw': qx = out['price']
                        if q1 and qx and q2:
                            quote_1.append(q1); quote_x.append(qx); quote_2.append(q2)
                            if is_pin: pinnacle_1, pinnacle_x, pinnacle_2 = q1, qx, q2
                                
            if len(quote_1) < 3: continue
            
            rif_1 = (pinnacle_1 * 0.6 + (sum(quote_1)/len(quote_1)) * 0.4) if pinnacle_1 else (sum(quote_1) / len(quote_1))
            rif_x = (pinnacle_x * 0.6 + (sum(quote_x)/len(quote_x)) * 0.4) if pinnacle_x else (sum(quote_x) / len(quote_x))
            rif_2 = (pinnacle_2 * 0.6 + (sum(quote_2)/len(quote_2)) * 0.4) if pinnacle_2 else (sum(quote_2) / len(quote_2))
            
            prob_pura_1, prob_pura_x, prob_pura_2 = power_devig(rif_1, rif_x, rif_2)
            
            mult_casa, stanca_casa = calcola_fattore_specifico(db_squadre, casa_ita, data_ita, is_home=True)
            mult_trasf, stanca_trasf = calcola_fattore_specifico(db_squadre, trasf_ita, data_ita, is_home=False)
            
            mc_1, mc_x, mc_2 = simulazione_monte_carlo_avanzata(prob_pura_1, prob_pura_x, prob_pura_2, mult_casa, mult_trasf, meteo_brutto, 10000)
            
            prob_dnb_2 = mc_2 / max(0.01, (1.0 - mc_x))
            
            opzioni = [
                (f"Vittoria {casa_ita}", mc_1, mult_casa, rif_1),
                (f"Vittoria {trasf_ita}", mc_2, mult_trasf, rif_2)
            ]
            opzioni.sort(key=lambda x: x[1], reverse=True)
            scelta_migliore, prob_stimata, rating_sq, quota_apertura_pin = opzioni[0]
            
            # PARAMETRO MODIFICATO: Soglia confidenza minima abbassata da 54% a 51% per maggiore operatività
            if prob_stimata < 0.51: continue
                
            quota_equa = round(1.0 / prob_stimata, 2)
            quota_valore_minima = round(quota_equa * 1.005, 2) # Margine elastico
            
            if quota_valore_minima < 1.20 or quota_valore_minima > 2.10: continue
            
            risultati_analisi.append({
                'id_partita': p['id'], 'lega': camp, 'data': data_ita.strftime("%d/%m %H:%M"),
                'match': f"{casa_ita} - {trasf_ita}", 'consiglio_algoritmo': scelta_migliore,
                'probabilita_reale': round(prob_stimata * 100, 1), 'prob_dnb_trasferta': round(prob_dnb_2 * 100, 1),
                'rating_tattico': rating_sq, 'quota_apertura_rif': round(quota_apertura_pin, 2),
                'quota_equa': quota_equa, 'quota_valore_minima': quota_valore_minima, 'meteo_avverso': meteo_brutto
            })
            
    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump({'ultimo_aggiornamento': oggi.strftime("%d/%m/%Y %H:%M"), 'totale_partite_analizzate': len(risultati_analisi), 'analisi': risultati_analisi}, f, indent=4, ensure_ascii=False)
    print(f"Omega Analista completato: {len(risultati_analisi)} match salvati.")

if __name__ == "__main__":
    esegui_analista()
