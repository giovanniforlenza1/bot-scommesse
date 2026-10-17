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
    nome_pulito = nome.strip()
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

def genera_database_studio_squadre(oggi):
    """Scansiona i match reali su ESPN per calcolare Tiri in Porta, Forma, Gol e Giorni di Riposo di ogni squadra"""
    print("Avvio Studio Tattico Squadre (Tiri nello specchio, Forma e Stanchezza) da ESPN...")
    raw_stats = {}
    # Scansiona un campione degli ultimi 12 giorni (weekend + turno infrasettimanale di coppa)
    date_studio = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(1, 13)]

    for lega in campionati_espn:
        for d_str in date_studio:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={d_str}"
            try:
                res = requests.get(url, timeout=5)
                if res.status_code != 200: continue
                events = res.json().get('events', [])
                for ev in events:
                    comp = ev.get('competitions', [{}])[0]
                    if not comp.get('status', {}).get('type', {}).get('completed', False):
                        continue
                    
                    data_match_str = ev.get('date', '')[:10] # YYYY-MM-DD
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
                        
                        info_t.append({
                            'key': t_key,
                            'nome': t_name,
                            'gol': gol,
                            'tiri_porta': tiri_porta if tiri_porta > 0 else max(1, gol * 2 + 1),
                            'is_home': (t.get('homeAway') == 'home')
                        })

                    # Registra i dati incrociati (fatti e subiti) per entrambe le squadre
                    for idx in [0, 1]:
                        me = info_t[idx]
                        opp = info_t[1 - idx]
                        punti = 3 if me['gol'] > opp['gol'] else (1 if me['gol'] == opp['gol'] else 0)
                        
                        rec = raw_stats.setdefault(me['key'], {
                            'nome_ufficiale': me['nome'],
                            'partite_lette': 0,
                            'gol_fatti': [],
                            'gol_subiti': [],
                            'tiri_porta_fatti': [],
                            'tiri_porta_subiti': [],
                            'punti': [],
                            'ultima_partita': data_match_str
                        })
                        rec['partite_lette'] += 1
                        rec['gol_fatti'].append(me['gol'])
                        rec['gol_subiti'].append(opp['gol'])
                        rec['tiri_porta_fatti'].append(me['tiri_porta'])
                        rec['tiri_porta_subiti'].append(opp['tiri_porta'])
                        rec['punti'].append(punti)
                        if data_match_str > rec['ultima_partita']:
                            rec['ultima_partita'] = data_match_str
            except:
                continue

    db_squadre = {}
    for k, v in raw_stats.items():
        n_gare = max(1, v['partite_lette'])
        media_gf = round(sum(v['gol_fatti']) / n_gare, 2)
        media_gs = round(sum(v['gol_subiti']) / n_gare, 2)
        media_tiri_f = round(sum(v['tiri_porta_fatti']) / n_gare, 2)
        media_tiri_s = round(sum(v['tiri_porta_subiti']) / n_gare, 2)
        media_punti = round(sum(v['punti']) / n_gare, 2)

        # Indice sintetico di Potenza Tattica (0.85 = squadra in crisi, 1.00 = neutra, 1.15 = squadra dominante)
        rating_tattico = 1.0 + ((media_punti - 1.4) * 0.04) + ((media_tiri_f - media_tiri_s) * 0.012) + ((media_gf - media_gs) * 0.025)
        rating_tattico = round(max(0.88, min(1.14, rating_tattico)), 3)

        db_squadre[k] = {
            'nome': v['nome_ufficiale'],
            'gare_analizzate': n_gare,
            'media_gol_fatti': media_gf,
            'media_gol_subiti': media_gs,
            'media_tiri_porta': media_tiri_f,
            'media_tiri_concessi': media_tiri_s,
            'media_punti_forma': media_punti,
            'ultima_partita': v['ultima_partita'],
            'rating_tattico': rating_tattico
        }

    with open('database_squadre.json', 'w', encoding='utf-8') as f:
        json.dump({
            'ultimo_aggiornamento': oggi.strftime("%d/%m/%Y %H:%M"),
            'totale_squadre_schedate': len(db_squadre),
            'squadre': db_squadre
        }, f, indent=4, ensure_ascii=False)
        
    print(f"Database Studio Squadre aggiornato: {len(db_squadre)} club analizzati.")
    return db_squadre

def cerca_dati_squadra(db_squadre, nome_ita):
    k_cerca = normalizza_chiave_squadra(nome_ita)
    if k_cerca in db_squadre:
        return db_squadre[k_cerca]
    for k, val in db_squadre.items():
        if k_cerca and (k_cerca in k or k in k_cerca):
            return val
    return None

def calcola_fattore_campo_e_stanchezza(db_squadre, nome_ita, data_partita_dt):
    """Restituisce il moltiplicatore di forza reale basato su Tiri, Forma e Giorni di Riposo"""
    info = cerca_dati_squadra(db_squadre, nome_ita)
    if not info:
        return 1.0, False
    
    moltiplicatore = info.get('rating_tattico', 1.0)
    stanca = False
    
    ultima_str = info.get('ultima_partita', '')
    if ultima_str:
        try:
            dt_ultima = datetime.strptime(ultima_str, "%Y-%m-%d").date()
            giorni_riposo = (data_partita_dt.date() - dt_ultima).days
            # Se ha giocato meno di 3 giorni fa (es. Coppa mercoledì -> Campionato sabato), applica Malus Stanchezza (-6%)
            if 0 < giorni_riposo <= 3:
                moltiplicatore *= 0.94
                stanca = True
        except:
            pass
            
    return moltiplicatore, stanca

def power_devig(q1, qx, q2):
    inv1, invx, inv2 = 1.0 / q1, 1.0 / qx, 1.0 / q2
    overround = inv1 + invx + inv2
    if overround <= 1.0:
        return inv1, invx, inv2
    esponente = 1.0 / (1.0 - (overround - 1.0) * 0.45)
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

def simulazione_monte_carlo_avanzata(prob_1, prob_x, prob_2, mult_casa, mult_trasf, n_sim=10000):
    """Simula 10.000 volte la partita integrando le quote con il Rating Tattico (Tiri in Porta + Forma + Riposo)"""
    xg_casa_base = max(0.45, (prob_1 * 2.65) + (prob_x * 0.82))
    xg_trasf_base = max(0.30, (prob_2 * 2.50) + (prob_x * 0.82))
    
    # Iniezione dello studio reale delle squadre sugli Expected Goals (xG)
    xg_casa = xg_casa_base * (mult_casa / mult_trasf)
    xg_trasf = xg_trasf_base * (mult_trasf / mult_casa)
    
    vitt_1, pareggi, vitt_2 = 0, 0, 0
    for _ in range(n_sim):
        gol_c = poisson_random(xg_casa)
        gol_t = poisson_random(xg_trasf)
        if (gol_c == 1 and gol_t == 0) or (gol_c == 0 and gol_t == 1):
            if random.random() < 0.06:
                gol_c = gol_t
        if gol_c > gol_t: vitt_1 += 1
        elif gol_c == gol_t: pareggi += 1
        else: vitt_2 += 1
        
    # Pesa 65% la probabilità pura di mercato e 35% la simulazione tattica basata sui dati reali ESPN
    p1_f = (prob_1 * 0.65) + ((vitt_1 / n_sim) * 0.35)
    px_f = (prob_x * 0.65) + ((pareggi / n_sim) * 0.35)
    p2_f = (prob_2 * 0.65) + ((vitt_2 / n_sim) * 0.35)
    return p1_f, px_f, p2_f

def esegui_analista():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    limite_temporale = oggi + timedelta(days=4)
    
    # 1. Aggiorna e carica il nuovo Database di Studio Tattico delle Squadre
    db_squadre = genera_database_studio_squadre(oggi)
    
    risultati_analisi = []
    
    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        partite = esegui_richiesta_api(url_template)
        if not partite: continue
        
        for p in partite:
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < oggi or data_ita > limite_temporale:
                continue
                
            casa_orig, trasf_orig = p['home_team'], p['away_team']
            casa_ita, trasf_ita = traduci_squadra(casa_orig), traduci_squadra(trasf_orig)
            
            quote_1, quote_x, quote_2 = [], [], []
            pinnacle_1, pinnacle_x, pinnacle_2 = None, None, None
            
            for book in p.get('bookmakers', []):
                key_b = book.get('key', '').lower()
                title_b = book.get('title', '').lower()
                if 'exchange' in title_b or 'betfair' in key_b or 'matchbook' in key_b or 'smarkets' in key_b:
                    continue
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
                            if is_pin:
                                pinnacle_1, pinnacle_x, pinnacle_2 = q1, qx, q2
                                
            if len(quote_1) < 3: continue
            
            rif_1 = (pinnacle_1 * 0.6 + (sum(quote_1)/len(quote_1)) * 0.4) if pinnacle_1 else (sum(quote_1) / len(quote_1))
            rif_x = (pinnacle_x * 0.6 + (sum(quote_x)/len(quote_x)) * 0.4) if pinnacle_x else (sum(quote_x) / len(quote_x))
            rif_2 = (pinnacle_2 * 0.6 + (sum(quote_2)/len(quote_2)) * 0.4) if pinnacle_2 else (sum(quote_2) / len(quote_2))
            
            prob_pura_1, prob_pura_x, prob_pura_2 = power_devig(rif_1, rif_x, rif_2)
            
            # 2. Estrae i coefficienti tattici e di stanchezza dal Database Squadre
            mult_casa, stanca_casa = calcola_fattore_campo_e_stanchezza(db_squadre, casa_ita, data_ita)
            mult_trasf, stanca_trasf = calcola_fattore_campo_e_stanchezza(db_squadre, trasf_ita, data_ita)
            
            mc_1, mc_x, mc_2 = simulazione_monte_carlo_avanzata(
                prob_pura_1, prob_pura_x, prob_pura_2, mult_casa, mult_trasf, 10000
            )
            
            opzioni = [
                (f"Vittoria {casa_ita}", mc_1, stanca_casa, mult_casa),
                (f"Vittoria {trasf_ita}", mc_2, stanca_trasf, mult_trasf)
            ]
            opzioni.sort(key=lambda x: x[1], reverse=True)
            scelta_migliore, prob_stimata, is_stanca, rating_sq = opzioni[0]
            
            # FILTRO SALVA-CASSA: Se la favorita è stanca per le coppe e non ha almeno il 60% di prob, la scarta!
            if is_stanca and prob_stimata < 0.60:
                continue
            if prob_stimata < 0.54:
                continue
                
            quota_equa = round(1.0 / prob_stimata, 2)
            quota_valore_minima = round(quota_equa * 1.01, 2)
            
            if quota_valore_minima < 1.22 or quota_valore_minima > 1.90:
                continue
            
            risultati_analisi.append({
                'id_partita': p['id'],
                'lega': camp,
                'data': data_ita.strftime("%d/%m %H:%M"),
                'match': f"{casa_ita} - {trasf_ita}",
                'consiglio_algoritmo': scelta_migliore,
                'probabilita_reale': round(prob_stimata * 100, 1),
                'rating_tattico': rating_sq,
                'quota_equa': quota_equa,
                'quota_valore_minima': quota_valore_minima
            })
            
    db_out = {
        'ultimo_aggiornamento': oggi.strftime("%d/%m/%Y %H:%M"),
        'totale_partite_analizzate': len(risultati_analisi),
        'analisi': risultati_analisi
    }
    
    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump(db_out, f, indent=4, ensure_ascii=False)
    print(f"Omega Analista completato: {len(risultati_analisi)} match super-filtrati salvati.")

if __name__ == "__main__":
    esegui_analista()
