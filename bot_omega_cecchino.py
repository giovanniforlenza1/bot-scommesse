import requests
import json
import os
import uuid
import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")
OMEGA_CHAT_ID = os.environ.get("OMEGA_CHAT_ID") or os.environ.get("CHAT_ID")

campionati = [
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'soccer_uefa_europa_conference_league',
    'soccer_italy_serie_a', 'soccer_epl', 'soccer_spain_la_liga', 
    'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga'
]

MAPPA_BOOKMAKER_ITALIA = {
    "unibet": "Unibet / Eurobet", "leovegas": "LeoVegas / Eurobet", "casumo": "Eurobet",
    "bwin": "Sisal / Bwin", "betsson": "Sisal / Betsson", "nordicbet": "Sisal / GoldBet",
    "williamhill": "William Hill", "888sport": "888sport", "betway": "Betway",
    "marathonbet": "Snai / Bet365", "pinnacle": "Bet365 / Snai", "coolbet": "GoldBet / PlanetWin365",
    "suprabets": "PlanetWin365", "everygame": "Snai", "betonlineag": "Bet365",
    "coral": "Eurobet", "ladbrokes": "Sisal", "paddypower": "Betfair Sport", "skybet": "SkyBet / Sisal"
}

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
        "CHIAVE_A", "CHIAVE_B", "CHIAVE_C", "CHIAVE_D", "CHIAVE_E", 
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

def traduci_squadra(nome):
    nome_pulito = str(nome).strip()
    if nome_pulito in TRADUZIONI_SQUADRE: return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "")

def formatta_nome_bookmaker(key_book, title_book):
    k = key_book.lower()
    for chiave, nome_ita in MAPPA_BOOKMAKER_ITALIA.items():
        if chiave in k or chiave in title_book.lower(): return nome_ita
    return title_book

def carica_database_analisi():
    if os.path.exists('database_analisi.json'):
        with open('database_analisi.json', 'r', encoding='utf-8') as f: return json.load(f)
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

def priorita_lega(lega):
    return 0 if ('uefa' in lega or 'italy_serie_a' in lega) else 1

def esegui_cecchino():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    data_oggi_str = oggi.strftime("%d/%m/%Y")
    
    inizio_finestra = oggi + timedelta(minutes=30)
    limite_temporale = oggi + timedelta(days=3)
    
    db_analisi = carica_database_analisi()
    if not db_analisi or not db_analisi.get('analisi'): return
    
    db_principale = carica_database_principale()

    if any(s.get('modello') == 'omega' and s.get('data_creazione') == data_oggi_str for s in db_principale.get('schedine', [])):
        print(f"[OMEGA] Giocata del {data_oggi_str} già presente nel database. Salto.")
        return

    id_gia_giocati, match_gia_giocati = ottieni_partite_gia_giocate(db_principale, 'omega')
    candidati_valore = []
    
    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        partite_live = esegui_richiesta_api(url_template)
        if not partite_live: continue
            
        for p_live in partite_live:
            data_ita = datetime.strptime(p_live['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < inizio_finestra or data_ita > limite_temporale:
                continue

            nome_casa_ita = traduci_squadra(p_live['home_team'])
            nome_trasf_ita = traduci_squadra(p_live['away_team'])
            match_intero = f"{nome_casa_ita} - {nome_trasf_ita}"

            # BLOCCO ANTI-RIPETIZIONE: Salta la partita se è già stata giocata da Omega ieri o nei giorni scorsi!
            if str(p_live['id']) in id_gia_giocati or match_intero.lower() in match_gia_giocati:
                print(f"[OMEGA SKIP] Partita già giocata in precedenza: {match_intero}")
                continue
            
            analisi_match = next((a for a in db_analisi['analisi'] if a.get('id_partita') == p_live['id'] or a.get('match') == match_intero), None)
            if not analisi_match: continue
            
            pronostico_richiesto = analisi_match['consiglio_algoritmo']
            quota_equa = analisi_match.get('quota_equa', 1.50)
            prob_reale = analisi_match.get('probabilita_reale', 55.0) / 100.0
            
            tetto_massimo_reale = min(2.40, round(quota_equa * 1.35, 2))
            miglior_quota = 0.0
            book_vincente = "Bet365 / Snai"
            
            for book in p_live.get('bookmakers', []):
                titolo_book = book.get('title', '')
                key_book = book.get('key', '').lower()
                if 'exchange' in titolo_book.lower() or 'betfair' in key_book or 'matchbook' in key_book: continue
                
                for mercato in book.get('markets', []):
                    if mercato.get('key') != 'h2h': continue
                    for out in mercato.get('outcomes', []):
                        q_attuale = out.get('price', 0)
                        if q_attuale > tetto_massimo_reale: continue
                        if traduci_squadra(out.get('name', '')).lower() == pronostico_richiesto.lower().replace("vittoria ", "").strip():
                            if q_attuale > miglior_quota:
                                miglior_quota = q_attuale
                                book_vincente = formatta_nome_bookmaker(key_book, titolo_book)
                            
            if miglior_quota >= 1.25:
                ev_reale = max(0.01, (prob_reale * miglior_quota) - 1.0)
                giorni_attesa = max(0, (data_ita.date() - oggi.date()).days)
                candidati_valore.append({
                    'id_partita': p_live['id'], 'data': data_ita.strftime("%d/%m %H:%M"),
                    'giorni_attesa': giorni_attesa,
                    'squadra_casa': nome_casa_ita, 'squadra_trasferta': nome_trasf_ita,
                    'pronostico': pronostico_richiesto, 'quota': round(miglior_quota, 2),
                    'bookmaker': book_vincente, 'score': round((ev_reale * 0.5) + (prob_reale * 0.5), 4),
                    'ev': round(ev_reale, 3), 'lega': camp, 'stato': 'in attesa', 'risultato_reale': ''
                })
                
    if not candidati_valore: return
    
    ordinati = sorted(candidati_valore, key=lambda x: (1 if x['giorni_attesa'] > 1 else 0, priorita_lega(x['lega']), -x['score']))
    
    if ordinati[0]['quota'] >= 1.48 or len(ordinati) == 1:
        finalisti = [ordinati[0]]
        tipo_giocata = "Colpo Mirato in Singola ad Alta Probabilità."
    else:
        finalisti = [ordinati[0], ordinati[1]]
        tipo_giocata = "Doppia Quantitativa a Bassa Varianza."
    
    q_tot = 1.0
    for f in finalisti: q_tot *= f['quota']
    quota_totale = round(q_tot, 2)
    stake_consigliato = 15.0
    
    partite_reali = [{k: v for k, v in c.items() if k not in ['score', 'ev', 'giorni_attesa']} for c in finalisti]
    with open('omega_oggi.json', 'w', encoding='utf-8') as fo:
        json.dump([c['id_partita'] for c in partite_reali], fo)

    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'modello': 'omega',
        'data_creazione': data_oggi_str,
        'importo': stake_consigliato,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(stake_consigliato * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'partite': partite_reali
    })
    salva_database_principale(db_principale)
    print(f"OMEGA SALVATO IN DATABASE.JSON: Quota {quota_totale}")

    msg = f"<b>MODELLO OMEGA</b>\n\n<b>{html.escape(tipo_giocata)}</b>\n\n"
    msg += f"📊 <b>Quota totale</b>: {quota_totale}\n💰 <b>Stake Kelly</b>: {stake_consigliato}€\n\n"
    for c in partite_reali:
        msg += f"⚽ <b>{c['data']} | {html.escape(c['squadra_casa'])} - {html.escape(c['squadra_trasferta'])}</b>\n"
        msg += f"🎯 <b>Giocata</b>: {html.escape(c['pronostico'].lower())} (@{c['quota']})\n🏦 <b>Bookmaker</b>: {html.escape(c['bookmaker'])}\n\n"
    msg += "<b>#TradingSportivo #ValueBetting #ScommesseSportive</b>"
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": OMEGA_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Errore Telegram Omega: {e}")

if __name__ == "__main__":
    esegui_cecchino()
