import requests
import json
import os
import uuid
import random
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

MAPPA_BOOKMAKER_ITALIA = {
    "unibet": "Unibet / Eurobet", "leovegas": "LeoVegas / Eurobet", "casumo": "Eurobet",
    "bwin": "Sisal / Bwin", "betsson": "Sisal / Betsson", "nordicbet": "Sisal / GoldBet",
    "williamhill": "William Hill", "888sport": "888sport", "betway": "Betway",
    "marathonbet": "Snai / Bet365", "pinnacle": "Bet365 / Snai", "coolbet": "GoldBet / PlanetWin365",
    "suprabets": "PlanetWin365", "everygame": "Snai", "betonlineag": "Bet365",
    "coral": "Eurobet", "ladbrokes": "Sisal", "paddypower": "Betfair Sport", "skybet": "SkyBet / Sisal"
}

def formatta_nome_bookmaker(key_book, title_book):
    k = key_book.lower()
    for chiave, nome_ita in MAPPA_BOOKMAKER_ITALIA.items():
        if chiave in k or chiave in title_book.lower():
            return nome_ita
    return title_book

def esegui_richiesta_api(url_template):
    chiavi = [k.strip() for k in os.environ.get("ODDS_API_KEY", "").split(",") if k.strip()]
    if not chiavi: return None
    for chiave in chiavi:
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json()
        except:
            pass
    return None

def trova_tornei_tennis_attivi():
    dati = esegui_richiesta_api("https://api.the-odds-api.com/v4/sports/?apiKey=API_KEY_SEGRETA")
    if not dati: return []
    tornei = [
        s['key'] for s in dati 
        if s.get('active') and (s['key'].startswith('tennis_atp_') or s['key'].startswith('tennis_wta_'))
    ]
    return tornei[:6]

def power_devig_2way(q1, q2):
    inv1, inv2 = 1.0 / q1, 1.0 / q2
    overround = inv1 + inv2
    if overround <= 1.0:
        return inv1, inv2
    esponente = 1.0 / (1.0 - (overround - 1.0) * 0.40)
    p1, p2 = (inv1 ** esponente), (inv2 ** esponente)
    tot = p1 + p2
    return p1 / tot, p2 / tot

def simulazione_monte_carlo_tennis(prob_1, n_sim=10000):
    p_set = max(0.15, min(0.85, (prob_1 * 0.92) + 0.04))
    vittorie_p1 = 0
    for _ in range(n_sim):
        set_1, set_2 = 0, 0
        while set_1 < 2 and set_2 < 2:
            if random.random() < p_set: set_1 += 1
            else: set_2 += 1
        if set_1 == 2: vittorie_p1 += 1
    p1_mc = (prob_1 * 0.70) + ((vittorie_p1 / n_sim) * 0.30)
    return p1_mc, (1.0 - p1_mc)

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def calcola_cassa_sigma(db):
    cassa = 200.0
    for s in db.get('schedine', []):
        if s.get('modello') == 'sigma' and s.get('stato_schedina') in ['vinta', 'persa']:
            imp = float(s.get('importo', 10.0))
            rit = float(s.get('ritorno_potenziale', 0.0))
            cassa += (rit - imp) if s['stato_schedina'] == 'vinta' else -imp
    return max(120.0, cassa)

def esegui_sigma_tennis():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    inizio_oggi = oggi.replace(hour=0, minute=0, second=0, microsecond=0)
    limite_temporale = inizio_oggi + timedelta(days=5)
    if data_ita < inizio_oggi or data_ita > limite_temporale: continue
    data_oggi_str = oggi.strftime("%d/%m/%Y")
    limite_temporale = oggi + timedelta(days=3)

    db_principale = carica_database_principale()

    for s in db_principale.get('schedine', []):
        if s.get('modello') == 'sigma' and s.get('data_creazione') == data_oggi_str:
            print("Sigma Tennis: Operazione già registrata oggi sul sito.")
            return

    id_gia_giocati = {
        p['id_partita'] for s in db_principale.get('schedine', [])
        if s.get('modello') == 'sigma' and s.get('stato_schedina') == 'in attesa'
        for p in s.get('partite', [])
    }

    tornei_attivi = trova_tornei_tennis_attivi()
    if not tornei_attivi:
        print("Sigma Tennis: Nessun torneo ATP/WTA quotato al momento.")
        return

    candidati_valore = []
    for torneo in tornei_attivi:
        url_template = f"https://api.the-odds-api.com/v4/sports/{torneo}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        partite = esegui_richiesta_api(url_template)
        if not partite: continue

        for p in partite:
            if p['id'] in id_gia_giocati: continue
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < oggi or data_ita > limite_temporale: continue

            giocatore_1 = p['home_team'].strip()
            giocatore_2 = p['away_team'].strip()

            quote_1, quote_2 = [], []
            pin_1, pin_2 = None, None
            miglior_q1, miglior_q2 = 0.0, 0.0
            book_1, book_2 = "", ""

            for book in p.get('bookmakers', []):
                key_b = book.get('key', '').lower()
                title_b = book.get('title', '')
                if 'exchange' in title_b.lower() or 'betfair' in key_b or 'matchbook' in key_b: continue
                is_pin = 'pinnacle' in key_b
                for m in book.get('markets', []):
                    if m.get('key') == 'h2h':
                        q1, q2 = None, None
                        for out in m.get('outcomes', []):
                            if out['name'] == p['home_team']: q1 = out['price']
                            elif out['name'] == p['away_team']: q2 = out['price']
                        if q1 and q2 and q1 <= 3.80 and q2 <= 3.80:
                            quote_1.append(q1); quote_2.append(q2)
                            if is_pin: pin_1, pin_2 = q1, q2
                            if q1 > miglior_q1: miglior_q1 = q1; book_1 = formatta_nome_bookmaker(key_b, title_b)
                            if q2 > miglior_q2: miglior_q2 = q2; book_2 = formatta_nome_bookmaker(key_b, title_b)

            if len(quote_1) < 2: continue

            rif_1 = (pin_1 * 0.65 + (sum(quote_1)/len(quote_1)) * 0.35) if pin_1 else (sum(quote_1)/len(quote_1))
            rif_2 = (pin_2 * 0.65 + (sum(quote_2)/len(quote_2)) * 0.35) if pin_2 else (sum(quote_2)/len(quote_2))

            p1_pura, p2_pura = power_devig_2way(rif_1, rif_2)
            mc_1, mc_2 = simulazione_monte_carlo_tennis(p1_pura, 10000)

            opzioni = [
                (f"Vittoria {giocatore_1}", mc_1, miglior_q1, book_1),
                (f"Vittoria {giocatore_2}", mc_2, miglior_q2, book_2)
            ]
            opzioni.sort(key=lambda x: x[1], reverse=True)
            pronostico, prob_reale, quota_top, book_top = opzioni[0]

            # PARAMETRO MODIFICATO: Confidenza minima abbassata dal 56% al 52% per maggiore operatività sul Tennis
            if prob_reale < 0.52: continue
            quota_equa = round(1.0 / prob_reale, 2)
            quota_minima = round(quota_equa * 1.005, 2)
            tetto_max = min(2.10, round(quota_equa * 1.22, 2))

            if quota_minima <= quota_top <= tetto_max:
                ev = (prob_reale * quota_top) - 1.0
                score = (ev * 0.65) + (prob_reale * 0.35)
                candidati_valore.append({
                    'id_partita': p['id'], 'data': data_ita.strftime("%d/%m %H:%M"),
                    'squadra_casa': giocatore_1, 'squadra_trasferta': giocatore_2,
                    'pronostico': pronostico, 'quota': round(quota_top, 2), 'bookmaker': book_top,
                    'score': round(score, 4), 'ev': round(ev, 3), 'lega': torneo,
                    'stato': 'in attesa', 'risultato_reale': ''
                })

    if not candidati_valore:
        print("Sigma Tennis: Nessuna value bet trovata oggi.")
        return

    ordinati = sorted(candidati_valore, key=lambda x: -x['score'])
    finalisti = [ordinati[0]] if ordinati[0]['quota'] >= 1.42 or len(ordinati) == 1 else [ordinati[0], ordinati[1]]

    q_tot = 1.0
    for f in finalisti: q_tot *= f['quota']
    quota_totale = round(q_tot, 2)

    cassa_sigma = calcola_cassa_sigma(db_principale)
    ev_medio = sum(c['ev'] for c in finalisti) / len(finalisti)
    stake_kelly = round(cassa_sigma * min(0.10, max(0.05, 0.05 + (ev_medio * 0.40))), 1)

    partite_db = [{k: v for k, v in c.items() if k not in ['score', 'ev']} for c in finalisti]

    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'modello': 'sigma',
        'data_creazione': data_oggi_str,
        'importo': stake_kelly,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(stake_kelly * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'partite': partite_db
    })
    salva_database_principale(db_principale)
    print(f"Sigma Tennis: Schedina salvata sul sito (Quota {quota_totale} | Stake {stake_kelly}€) - Zero Telegram.")

if __name__ == "__main__":
    esegui_sigma_tennis()
