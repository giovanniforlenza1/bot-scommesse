import requests
import json
import os
import uuid
import random
import math
import html
import base64
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Usa esattamente gli stessi parametri Telegram di Bot Beta
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")
CHAT_ID = os.environ.get("CHAT_ID")

MAPPA_BOOKMAKER_ITALIA = {
    "unibet": "Unibet / Eurobet", "leovegas": "LeoVegas / Eurobet", "casumo": "Eurobet",
    "bwin": "Sisal / Bwin", "betsson": "Sisal / Betsson", "nordicbet": "Sisal / GoldBet",
    "williamhill": "William Hill", "888sport": "888sport", "betway": "Betway",
    "marathonbet": "Snai / Bet365", "pinnacle": "Bet365 / Snai", "coolbet": "GoldBet / PlanetWin365",
    "suprabets": "PlanetWin365", "everygame": "Snai", "betonlineag": "Bet365",
    "coral": "Eurobet", "ladbrokes": "Sisal", "paddypower": "Betfair Sport", "skybet": "SkyBet / Sisal"
}

def ottieni_pool_chiavi():
    nomi_secrets = [
        "CHIAVE_A", "CHIAVE_B", "CHIAVE_C", 
        "ODDS_API_KEY", "API_KEY_ALPHA", "API_KEY_ARBITRO",
        "API_FOOTBALL_OMEGA_KEY", "API_FOOTBALL_KEY", "FOOTBALL_DATA_KEY"
    ]
    pool = []
    for nome in nomi_secrets:
        val = os.environ.get(nome, "")
        for k in val.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in pool:
                pool.append(k_clean)
    return pool

def esegui_richiesta_api(url_template):
    chiavi = ottieni_pool_chiavi()
    if not chiavi: return None
    for idx, chiave in enumerate(chiavi):
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=12)
            if res.status_code == 200:
                return res.json()
        except:
            pass
    return None

def formatta_nome_bookmaker(key_book, title_book):
    k = key_book.lower()
    for chiave, nome_ita in MAPPA_BOOKMAKER_ITALIA.items():
        if chiave in k or chiave in title_book.lower():
            return nome_ita
    return title_book

def cripta_dati_sensibili(lista_partite):
    raw_bytes = json.dumps(lista_partite, ensure_ascii=False).encode('utf-8')
    key_hash = hashlib.sha256(TELEGRAM_TOKEN.encode('utf-8')).digest()
    xored = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(raw_bytes)])
    return base64.b64encode(xored).decode('ascii')

def crea_partite_offuscate_per_sito(lista_partite):
    return [{
        'id_partita': 'protetto',
        'data': p.get('data', ''),
        'squadra_casa': '🔒 Singola Tennis',
        'squadra_trasferta': 'In Corso',
        'pronostico': 'ATP/WTA Riservato',
        'quota': p.get('quota', 1.0),
        'stato': 'in attesa',
        'risultato_reale': ''
    } for p in lista_partite]

def trova_tornei_tennis_attivi():
    dati = esegui_richiesta_api("https://api.the-odds-api.com/v4/sports/?apiKey=API_KEY_SEGRETA")
    if not dati: return []
    tornei = [
        s['key'] for s in dati 
        if s.get('active') and 'tennis' in s.get('key', '').lower()
    ]
    return tornei[:8]

def devig_2way_accurato(q1, q2):
    inv1, inv2 = 1.0 / q1, 1.0 / q2
    tot = inv1 + inv2
    return inv1 / tot, inv2 / tot

def simulazione_monte_carlo_tennis(prob_1, n_sim=10000):
    p_set = max(0.15, min(0.85, (prob_1 * 0.94) + 0.03))
    vittorie_p1 = 0
    for _ in range(n_sim):
        set_1, set_2 = 0, 0
        while set_1 < 2 and set_2 < 2:
            if random.random() < p_set:
                set_1 += 1
            else:
                set_2 += 1
        if set_1 == 2:
            vittorie_p1 += 1
    p1_mc = (prob_1 * 0.75) + ((vittorie_p1 / n_sim) * 0.25)
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
    data_oggi_str = oggi.strftime("%d/%m/%Y")
    inizio_finestra = oggi - timedelta(hours=2)
    limite_temporale = oggi + timedelta(days=3)

    db_principale = carica_database_principale()

    # Rimuove eventuali vecchie schedine Sigma di oggi create senza invio Telegram
    db_principale['schedine'] = [
        s for s in db_principale.get('schedine', [])
        if not (s.get('modello') == 'sigma' and s.get('data_creazione') == data_oggi_str and not s.get('telegram_inviato'))
    ]

    for s in db_principale.get('schedine', []):
        if s.get('modello') == 'sigma' and s.get('data_creazione') == data_oggi_str and s.get('telegram_inviato'):
            print("Sigma Tennis: Operazione già inviata su Telegram oggi.")
            return

    tornei_attivi = trova_tornei_tennis_attivi()
    if not tornei_attivi:
        print("Sigma Tennis: Nessun torneo attivo restituito dall'API.")
        return

    candidati_valore = []

    for torneo in tornei_attivi:
        url_template = f"https://api.the-odds-api.com/v4/sports/{torneo}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk,us&markets=h2h"
        partite = esegui_richiesta_api(url_template)
        if not partite: continue

        for p in partite:
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < inizio_finestra or data_ita > limite_temporale:
                continue

            giocatore_1 = p['home_team'].strip()
            giocatore_2 = p['away_team'].strip()

            quote_1, quote_2 = [], []
            miglior_q1, miglior_q2 = 0.0, 0.0
            book_1, book_2 = "Bet365 / Snai", "Bet365 / Snai"

            for book in p.get('bookmakers', []):
                key_b = book.get('key', '').lower()
                title_b = book.get('title', '')
                if 'exchange' in title_b.lower() or 'betfair' in key_b or 'matchbook' in key_b: continue
                for m in book.get('markets', []):
                    if m.get('key') == 'h2h':
                        q1, q2 = None, None
                        for out in m.get('outcomes', []):
                            if out['name'] == p['home_team']: q1 = out['price']
                            elif out['name'] == p['away_team']: q2 = out['price']
                        if q1 and q2:
                            quote_1.append(q1); quote_2.append(q2)
                            if q1 > miglior_q1:
                                miglior_q1 = q1
                                book_1 = formatta_nome_bookmaker(key_b, title_b)
                            if q2 > miglior_q2:
                                miglior_q2 = q2
                                book_2 = formatta_nome_bookmaker(key_b, title_b)

            if not quote_1: continue

            rif_1 = sum(quote_1) / len(quote_1)
            rif_2 = sum(quote_2) / len(quote_2)

            p1_pura, p2_pura = devig_2way_accurato(rif_1, rif_2)
            mc_1, mc_2 = simulazione_monte_carlo_tennis(p1_pura, 10000)

            opzioni = [
                (f"Vittoria {giocatore_1}", mc_1, miglior_q1, book_1),
                (f"Vittoria {giocatore_2}", mc_2, miglior_q2, book_2)
            ]
            opzioni.sort(key=lambda x: x[1], reverse=True)
            pronostico, prob_reale, quota_top, book_top = opzioni[0]

            if 1.30 <= quota_top <= 2.30 and prob_reale >= 0.45:
                ev = max(0.01, (prob_reale * quota_top) - 1.0)
                score = (ev * 0.55) + (prob_reale * 0.45)
                giorni_attesa = max(0, (data_ita.date() - oggi.date()).days)
                candidati_valore.append({
                    'id_partita': p['id'],
                    'data': data_ita.strftime("%d/%m %H:%M"),
                    'giorni_attesa': giorni_attesa,
                    'squadra_casa': giocatore_1,
                    'squadra_trasferta': giocatore_2,
                    'pronostico': pronostico,
                    'quota': round(quota_top, 2),
                    'bookmaker': book_top,
                    'score': round(score, 4),
                    'ev': round(ev, 3),
                    'lega': torneo,
                    'stato': 'in attesa',
                    'risultato_reale': ''
                })

    if not candidati_valore:
        print("Sigma Tennis: Nessun match disponibile.")
        return

    ordinati = sorted(candidati_valore, key=lambda x: (x['giorni_attesa'], -x['score']))
    finalisti = [ordinati[0]] if ordinati[0]['quota'] >= 1.50 or len(ordinati) == 1 else [ordinati[0], ordinati[1]]

    q_tot = 1.0
    for f in finalisti:
        q_tot *= f['quota']
    quota_totale = round(q_tot, 2)

    cassa_sigma = calcola_cassa_sigma(db_principale)
    ev_medio = sum(c['ev'] for c in finalisti) / len(finalisti)
    stake_kelly = round(cassa_sigma * min(0.10, max(0.05, 0.05 + (ev_medio * 0.40))), 1)

    partite_reali = [{k: v for k, v in c.items() if k not in ['score', 'ev', 'giorni_attesa']} for c in finalisti]

    msg = "<b>🎾 MODELLO SIGMA | TENNIS ATP & WTA</b>\n\n"
    for c in partite_reali:
        c_casa = html.escape(c['squadra_casa'])
        c_trasf = html.escape(c['squadra_trasferta'])
        c_pron = html.escape(c['pronostico'])
        c_book = html.escape(c['bookmaker'])
        msg += f"🎾 <b>{c['data']} | {c_casa} - {c_trasf}</b>\n"
        msg += f"🎯 <b>Giocata</b>: {c_pron} (@{c['quota']})\n"
        msg += f"🏦 <b>Bookmaker</b>: {c_book}\n\n"
    msg += f"📊 <b>Quota Totale</b>: @{quota_totale}\n"
    msg += f"💰 <b>Stake Kelly</b>: {stake_kelly}€\n\n"
    msg += "<b>#ModelloSigma #TennisBetting #ValueBetting</b>"

    res_tg = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
        timeout=10
    )
    print(f"Sigma Tennis Telegram Status: {res_tg.status_code}")

    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'modello': 'sigma',
        'data_creazione': data_oggi_str,
        'importo': stake_kelly,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(stake_kelly * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'telegram_inviato': True,
        'payload_criptato': cripta_dati_sensibili(partite_reali),
        'partite': crea_partite_offuscate_per_sito(partite_reali)
    })
    salva_database_principale(db_principale)
    print(f"Sigma Tennis: Schedina SALVATA e INVIATA su Telegram! Quota {quota_totale}")

if __name__ == "__main__":
    esegui_sigma_tennis()
