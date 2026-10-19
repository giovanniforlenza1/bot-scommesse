import requests
import json
import os
import uuid
import html
import base64
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")
CHAT_ID = os.environ.get("CHAT_ID")

campionati = [
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'soccer_uefa_europa_conference_league',
    'soccer_italy_serie_a', 'soccer_epl', 'soccer_spain_la_liga', 
    'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga'
]

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "AC Milan": "Milan", "AS Roma": "Roma", "SSC Napoli": "Napoli",
    "SS Lazio": "Lazio", "Juventus FC": "Juventus", "Hellas Verona": "Verona", "Bologna FC": "Bologna",
    "Fiorentina": "Fiorentina", "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Parma Calcio 1913": "Parma", "Como 1907": "Como",
    "Manchester Utd": "Manchester United", "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham",
    "Newcastle Utd": "Newcastle", "Paris Saint Germain": "PSG", "Bayern Munich": "Bayern Monaco",
    "Bayer Leverkusen": "Bayer Leverkusen", "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad",
    "Athletic Club": "Athletic Bilbao", "Wolverhampton Wanderers": "Wolverhampton"
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
    for chiave in chiavi:
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=12)
            if res.status_code == 200: return res.json()
        except:
            pass
    return None

def cripta_dati_sensibili(lista_partite):
    raw_bytes = json.dumps(lista_partite, ensure_ascii=False).encode('utf-8')
    key_hash = hashlib.sha256(TELEGRAM_TOKEN.encode('utf-8')).digest()
    xored = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(raw_bytes)])
    return base64.b64encode(xored).decode('ascii')

def crea_partite_offuscate_per_sito(lista_partite):
    return [{
        'id_partita': 'protetto', 'data': p.get('data', ''),
        'squadra_casa': '🔒 Operazione', 'squadra_trasferta': 'In Corso',
        'pronostico': 'Dettagli sul Canale Telegram', 'quota': p.get('quota', 1.0),
        'stato': 'in attesa', 'risultato_reale': ''
    } for p in lista_partite]

def traduci_squadra(nome):
    nome_pulito = str(nome).strip()
    if nome_pulito in TRADUZIONI_SQUADRE: return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "")

def carica_id_omega_oggi():
    if os.path.exists('omega_oggi.json'):
        try:
            with open('omega_oggi.json', 'r', encoding='utf-8') as f: return set(json.load(f))
        except:
            pass
    return set()

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f: json.dump(db, f, indent=4, ensure_ascii=False)

def priorita_lega(lega):
    if 'uefa' in lega or 'italy_serie_a' in lega:
        return 0
    return 1

def esegui_alpha():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    data_oggi_str = oggi.strftime("%d/%m/%Y")
    inizio_finestra = oggi - timedelta(hours=2)
    limite_temporale = oggi + timedelta(days=3)
    
    db_principale = carica_database_principale()
    for s in db_principale['schedine']:
        if s.get('modello') == 'alpha' and s.get('data_creazione') == data_oggi_str:
            print("Alpha: Schedina odierna già presente.")
            return

    id_esclusi_omega = carica_id_omega_oggi()
    candidati_alpha = []

    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        partite = esegui_richiesta_api(url_template)
        if not partite: continue

        for p in partite:
            if p['id'] in id_esclusi_omega: continue
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < inizio_finestra or data_ita > limite_temporale:
                continue

            casa_orig, trasf_orig = p['home_team'], p['away_team']
            casa_ita, trasf_ita = traduci_squadra(casa_orig), traduci_squadra(trasf_orig)

            opzioni_match = {}
            for book in p.get('bookmakers', []):
                titolo_book = book.get('title', '')
                if 'exchange' in titolo_book.lower() or 'betfair' in book.get('key', '').lower(): continue
                
                for m in book.get('markets', []):
                    if m['key'] == 'h2h':
                        q1, qx, q2 = None, None, None
                        for out in m['outcomes']:
                            if out['name'] == casa_orig: q1 = out['price']
                            elif out['name'] == trasf_orig: q2 = out['price']
                            elif out['name'].lower() == 'draw': qx = out['price']
                        
                        if q1 and 1.35 <= q1 <= 1.95: opzioni_match.setdefault(f"Vittoria {casa_ita}", []).append(q1)
                        if q2 and 1.35 <= q2 <= 1.95: opzioni_match.setdefault(f"Vittoria {trasf_ita}", []).append(q2)
                        if q1 and qx and q2:
                            dc_1x = round(1.0 / ((1.0/q1) + (1.0/qx)) * 0.96, 2)
                            dc_x2 = round(1.0 / ((1.0/q2) + (1.0/qx)) * 0.96, 2)
                            if 1.32 <= dc_1x <= 1.75: opzioni_match.setdefault(f"Doppia Chance 1X ({casa_ita})", []).append(dc_1x)
                            if 1.32 <= dc_x2 <= 1.75: opzioni_match.setdefault(f"Doppia Chance X2 ({trasf_ita})", []).append(dc_x2)
                            if qx >= 3.10:
                                q_over15 = round(max(1.32, min(1.65, 1.85 / (qx * 0.44))), 2)
                                opzioni_match.setdefault("Over 1.5 Gol", []).append(q_over15)

            miglior_pick, miglior_score, quota_scelta = None, 0.0, 0.0
            for pick, quote_list in opzioni_match.items():
                if not quote_list: continue
                q_media = sum(quote_list) / len(quote_list)
                if 1.32 <= q_media <= 1.88:
                    bonus = 0.10 if ("Doppia Chance" in pick or "Over 1.5" in pick) else 0.0
                    score = (1.0 / q_media) + bonus
                    if score > miglior_score:
                        miglior_score = score
                        miglior_pick = pick
                        quota_scelta = round(max(quote_list), 2)

            if miglior_pick:
                giorni_attesa = max(0, (data_ita.date() - oggi.date()).days)
                candidati_alpha.append({
                    'id_partita': p['id'], 'data': data_ita.strftime("%d/%m %H:%M"),
                    'giorni_attesa': giorni_attesa,
                    'squadra_casa': casa_ita, 'squadra_trasferta': trasf_ita,
                    'pronostico': miglior_pick, 'quota': min(1.90, quota_scelta), 'score': miglior_score,
                    'lega': camp, 'stato': 'in attesa', 'risultato_reale': ''
                })

    if not candidati_alpha: return

    # ORDINE INTELLIGENTE: Prima le partite entro 24/48h (Coppe in settimana), poi Serie A/Coppe a parità di data
    ordinati = sorted(candidati_alpha, key=lambda x: (1 if x['giorni_attesa'] > 1 else 0, priorita_lega(x['lega']), -x['score']))

    selezionati = []
    quota_totale = 1.0
    for c in ordinati:
        if len(selezionati) < 3 and quota_totale < 2.60:
            selezionati.append(c)
            quota_totale *= c['quota']

    quota_totale = round(quota_totale, 2)
    if quota_totale < 2.00:
        print(f"Alpha: Quota totale troppo bassa ({quota_totale}), scartata.")
        return

    partite_pulite = [{k: v for k, v in c.items() if k not in ['score', 'giorni_attesa']} for c in selezionati]
    stake = 12.0

    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8], 'modello': 'alpha', 'data_creazione': data_oggi_str,
        'importo': stake, 'quota_totale': quota_totale, 'ritorno_potenziale': round(stake * quota_totale, 2),
        'stato_schedina': 'in attesa', 'telegram_inviato': True,
        'payload_criptato': cripta_dati_sensibili(partite_pulite), 'partite': crea_partite_offuscate_per_sito(partite_pulite)
    })
    salva_database_principale(db_principale)

    msg = f"<b>🚀 MODELLO ALPHA | MULTIPLA PROTETTA</b>\n\n📊 <b>Moltiplicatore Totale</b>: {quota_totale}\n💰 <b>Stake</b>: {stake}€\n\n"
    for c in partite_pulite:
        msg += f"⚽ <b>{c['data']} | {html.escape(c['squadra_casa'])} - {html.escape(c['squadra_trasferta'])}</b>\n🛡️ <b>Scelta</b>: {html.escape(c['pronostico'])} (@{c['quota']})\n\n"
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Avviso invio Telegram Alpha: {e}")

if __name__ == "__main__":
    esegui_alpha()
