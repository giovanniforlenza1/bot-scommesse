import requests
import json
import os
import uuid
import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")
CHAT_ID = os.environ.get("CHAT_ID") or os.environ.get("OMEGA_CHAT_ID")

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
    for chiave in ottieni_pool_chiavi():
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=12)
            if res.status_code == 200: return res.json()
        except:
            pass
    return None

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def esegui_sigma_tennis():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    data_oggi_str = oggi.strftime("%d/%m/%Y")

    db_principale = carica_database_principale()
    db_principale['schedine'] = [
        s for s in db_principale.get('schedine', [])
        if not (s.get('modello') == 'sigma' and s.get('data_creazione') == data_oggi_str and s.get('stato_schedina') == 'in attesa')
    ]

    dati_sport = esegui_richiesta_api("https://api.the-odds-api.com/v4/sports/?apiKey=API_KEY_SEGRETA")
    tornei_tennis = [s['key'] for s in (dati_sport or []) if 'tennis' in s.get('key', '').lower() and s.get('active')]

    partita_scelta = None
    for torneo in tornei_tennis:
        url_odds = f"https://api.the-odds-api.com/v4/sports/{torneo}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        dati_odds = esegui_richiesta_api(url_odds)
        if dati_odds:
            for m_curr in dati_odds:
                data_ita = datetime.strptime(m_curr['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
                if data_ita < oggi - timedelta(hours=2):
                    continue
                g1 = m_curr.get('home_team', '')
                g2 = m_curr.get('away_team', '')
                for book in m_curr.get('bookmakers', []):
                    for m in book.get('markets', []):
                        if m.get('key') == 'h2h':
                            for out in m.get('outcomes', []):
                                q = float(out.get('price', 0))
                                if 1.38 <= q <= 2.15:
                                    partita_scelta = {
                                        'id_partita': m_curr.get('id'),
                                        'data': data_ita.strftime("%d/%m %H:%M"),
                                        'squadra_casa': g1,
                                        'squadra_trasferta': g2,
                                        'pronostico': f"Vittoria {out.get('name')}",
                                        'quota': round(q, 2),
                                        'bookmaker': book.get('title', 'Bet365 / Snai'),
                                        'lega': torneo,
                                        'stato': 'in attesa',
                                        'risultato_reale': ''
                                    }
                                    break
                        if partita_scelta: break
                    if partita_scelta: break
                if partita_scelta: break
        if partita_scelta: break

    if not partita_scelta:
        print("Sigma Tennis: Nessun match ATP/WTA attivo in questo momento.")
        return

    quota_totale = partita_scelta['quota']
    stake_kelly = 15.0

    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'modello': 'sigma',
        'data_creazione': data_oggi_str,
        'importo': stake_kelly,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(stake_kelly * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'telegram_inviato': True,
        'partite': [partita_scelta]
    })
    salva_database_principale(db_principale)
    print("SIGMA TENNIS SALVATO IN DATABASE.JSON!")

    msg = "<b>🎾 MODELLO SIGMA | TENNIS ATP & WTA</b>\n\n"
    msg += f"🎾 <b>{partita_scelta['data']} | {html.escape(partita_scelta['squadra_casa'])} - {html.escape(partita_scelta['squadra_trasferta'])}</b>\n"
    msg += f"🎯 <b>Giocata</b>: {html.escape(partita_scelta['pronostico'])} (@{partita_scelta['quota']})\n"
    msg += f"🏦 <b>Bookmaker</b>: {html.escape(partita_scelta['bookmaker'])}\n\n"
    msg += f"📊 <b>Quota Totale</b>: @{quota_totale}\n"
    msg += f"💰 <b>Stake Kelly</b>: {stake_kelly}€\n\n"
    msg += "<b>#ModelloSigma #TennisBetting #ValueBetting</b>"

    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Errore Telegram Sigma: {e}")

if __name__ == "__main__":
    esegui_sigma_tennis()
