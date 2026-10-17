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
    "Athletic Club": "Athletic Bilbao", "Wolverhampton Wanderers": "Wolverhampton"
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

def power_devig(q1, qx, q2):
    """Metodo di Potenza (Shin/Power): rimuove l'aggio tenendo conto che il banco tassa di più i pareggi e le sfavorite"""
    inv1, invx, inv2 = 1.0 / q1, 1.0 / qx, 1.0 / q2
    overround = inv1 + invx + inv2
    if overround <= 1.0:
        return inv1, invx, inv2
    # Esponente di correzione per penalizzare le quote lunghe e premiare la vera probabilità della favorita
    k = math.log(3.0) / math.log(3.0 * overround)
    p1 = (inv1 ** (1.0 / (1.0 - (overround - 1.0) * 0.45)))
    px = (invx ** (1.0 / (1.0 - (overround - 1.0) * 0.45)))
    p2 = (inv2 ** (1.0 / (1.0 - (overround - 1.0) * 0.45)))
    tot = p1 + px + p2
    return p1 / tot, px / tot, p2 / tot

def poisson_random(lmbda):
    L = math.exp(-lmbda)
    k, p = 0, 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1

def simulazione_monte_carlo_dixon_coles(prob_1, prob_x, prob_2, n_sim=10000):
    xg_casa = max(0.45, (prob_1 * 2.65) + (prob_x * 0.82))
    xg_trasf = max(0.30, (prob_2 * 2.50) + (prob_x * 0.82))
    
    vitt_1, pareggi, vitt_2 = 0, 0, 0
    for _ in range(n_sim):
        gol_c = poisson_random(xg_casa)
        gol_t = poisson_random(xg_trasf)
        # Correzione Dixon-Coles sui punteggi bloccati (1-0, 0-1, 0-0)
        if (gol_c == 1 and gol_t == 0) or (gol_c == 0 and gol_t == 1):
            if random.random() < 0.06:
                gol_c = gol_t
        if gol_c > gol_t: vitt_1 += 1
        elif gol_c == gol_t: pareggi += 1
        else: vitt_2 += 1
        
    p1_f = (prob_1 * 0.75) + ((vitt_1 / n_sim) * 0.25)
    px_f = (prob_x * 0.75) + ((pareggi / n_sim) * 0.25)
    p2_f = (prob_2 * 0.75) + ((vitt_2 / n_sim) * 0.25)
    return p1_f, px_f, p2_f

def esegui_analista():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    limite_temporale = oggi + timedelta(days=4)
    
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
            
            # Usa Pinnacle (il bookmaker più preciso al mondo) se presente, altrimenti la media pesata
            rif_1 = (pinnacle_1 * 0.6 + (sum(quote_1)/len(quote_1)) * 0.4) if pinnacle_1 else (sum(quote_1) / len(quote_1))
            rif_x = (pinnacle_x * 0.6 + (sum(quote_x)/len(quote_x)) * 0.4) if pinnacle_x else (sum(quote_x) / len(quote_x))
            rif_2 = (pinnacle_2 * 0.6 + (sum(quote_2)/len(quote_2)) * 0.4) if pinnacle_2 else (sum(quote_2) / len(quote_2))
            
            prob_pura_1, prob_pura_x, prob_pura_2 = power_devig(rif_1, rif_x, rif_2)
            mc_1, mc_x, mc_2 = simulazione_monte_carlo_dixon_coles(prob_pura_1, prob_pura_x, prob_pura_2, 10000)
            
            # Escludiamo i pareggi secchi da Omega: cerchiamo solo Favorite Solide ad alta probabilità
            opzioni = [
                (f"Vittoria {casa_ita}", mc_1),
                (f"Vittoria {trasf_ita}", mc_2)
            ]
            opzioni.sort(key=lambda x: x[1], reverse=True)
            scelta_migliore, prob_stimata = opzioni[0]
            
            # FILTRO ALTA PROBABILITÀ: Accetta solo match con probabilità reale >= 54% (quote eque <= 1.85)
            # Questo abbatte le serie di sconfitte consecutive e alza drasticamente il Win Rate
            if prob_stimata < 0.54:
                continue
                
            quota_equa = round(1.0 / prob_stimata, 2)
            # Richiede un vantaggio reale di almeno l'1.2% sopra la quota equa
            quota_valore_minima = round(quota_equa * 1.012, 2)
            
            if quota_valore_minima < 1.22 or quota_valore_minima > 1.90:
                continue
            
            risultati_analisi.append({
                'id_partita': p['id'],
                'lega': camp,
                'data': data_ita.strftime("%d/%m %H:%M"),
                'match': f"{casa_ita} - {trasf_ita}",
                'consiglio_algoritmo': scelta_migliore,
                'probabilita_reale': round(prob_stimata * 100, 1),
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
    print(f"Omega Analista completato: {len(risultati_analisi)} match ad alta probabilità salvati.")

if __name__ == "__main__":
    esegui_analista()
