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

def ottieni_partite_gia_giocate(db, modello_target):
    """Restituisce gli ID e i nomi delle partite già giocate da questo modello nei giorni scorsi"""
    id_giocati = set()
    match_giocati = set()
    for s in db.get('schedine', []):
        if s.get('modello') == modello_target:
            for p in s.get('partite', []):
                if p.get('id_partita'):
                    id_giocati.add(str(p.get('id_partita')))
                c = str(p.get('squadra_casa', '')).lower().strip()
                t = str(p.get('squadra_trasferta', '')).lower().strip()
                if c and t:
                    match_giocati.add(f"{c} - {t}")
    return id_giocati, match_giocati

def esegui_sigma_tennis():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    data_oggi_str = oggi.strftime("%d/%m/%Y")

    inizio_minimo = oggi + timedelta(minutes=30)
    limite_massimo = oggi + timedelta(hours=36)

    db_principale = carica_database_principale()

    if any(s.get('modello') == 'sigma' and s.get('data_creazione') == data_oggi_str for s in db_principale.get('schedine', [])):
        print(f"[SIGMA] Giocata del {data_oggi_str} già presente nel database. Salto.")
        return

    id_gia_giocati, match_gia_giocati = ottieni_partite_gia_giocate(db_principale, 'sigma')

    dati_sport = esegui_richiesta_api("https://api.the-odds-api.com/v4/sports/?apiKey=API_KEY_SEGRETA")
    tornei_tennis = [s['key'] for s in (dati_sport or []) if 'tennis' in s.get('key', '').lower() and s.get('active')]

    partita_scelta = None
    for torneo in tornei_tennis:
        url_odds = f"https://api.the-odds-api.com/v4/sports/{torneo}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        dati_odds = esegui_richiesta_api(url_odds)
        if dati_odds:
            for m_curr in dati_odds:
                data_ita = datetime.strptime(m_curr['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
                if data_ita < inizio_minimo or data_ita > limite_massimo:
                    continue

                g1 = m_curr.get('home_team', '')
                g2 = m_curr.get('away_team', '')
                match_intero = f"{g1} - {g2}".lower()

                # BLOCCO ANTI-RIPETIZIONE: Salta il match se è già stato giocato da Sigma nei giorni scorsi!
                if str(m_curr.get('id')) in id_gia_giocati or match_intero in match_gia_giocati:
                    print(f"[SIGMA SKIP] Partita tennis già giocata in precedenza: {g1} - {g2}")
                    continue

                for book in m_curr.get('bookmakers', []):
                    for m in book.get('markets', []):
                        if m.get('key') == 'h2h':
                            for out in m.get('outcomes', []):
                                q = float(out.get('price', 0))
                                if 1.40 <= q <= 2.10:
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
        print("Sigma Tennis: Nessun match futuro nuovo nelle prossime 36 ore.")
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
    print(f"SIGMA TENNIS SALVATO IN DATABASE.JSON: {partita_scelta['data']} {partita_scelta['squadra_casa']} - {partita_scelta['squadra_trasferta']}")

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
