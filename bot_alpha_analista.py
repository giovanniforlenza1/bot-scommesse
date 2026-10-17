import requests
import json
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

campionati = [
    'soccer_italy_serie_a', 'soccer_italy_serie_b', 'soccer_epl', 'soccer_efl_champ',
    'soccer_spain_la_liga', 'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'soccer_uefa_nations_league'
]

siti_ammessi = ['Bet365', 'Snai', 'Sisal', 'Eurobet', 'PlanetWin365', 'GoldBet', 'William Hill', 'Unibet', 'Marathonbet', '888sport', 'Bwin', 'Betsson']

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

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def esegui_alpha():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    data_oggi_str = oggi.strftime("%d/%m/%Y")
    limite_temporale = oggi + timedelta(days=4)
    
    db_principale = carica_database_principale()
    
    for s in db_principale['schedine']:
        if s.get('modello') == 'alpha' and s.get('data_creazione') == data_oggi_str and s.get('telegram_inviato'):
            print("Alpha: Schedina già generata oggi.")
            return

    candidati_alpha = []

    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h,totals"
        partite = esegui_richiesta_api(url_template)
        if not partite: continue

        for p in partite:
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < oggi or data_ita > limite_temporale: continue

            casa_orig, trasf_orig = p['home_team'], p['away_team']
            casa_ita, trasf_ita = traduci_squadra(casa_orig), traduci_squadra(trasf_orig)

            opzioni_match = {}

            for book in p.get('bookmakers', []):
                titolo_book = book.get('title', '')
                key_b = book.get('key', '').lower()
                if 'exchange' in titolo_book.lower() or 'betfair' in key_b: continue
                is_ammesso = any(sb.lower() in titolo_book.lower() for sb in siti_ammessi)
                
                for m in book.get('markets', []):
                    if m['key'] == 'h2h':
                        q1, qx, q2 = None, None, None
                        for out in m['outcomes']:
                            if out['name'] == casa_orig: q1 = out['price']
                            elif out['name'] == trasf_orig: q2 = out['price']
                            elif out['name'].lower() == 'draw': qx = out['price']
                        
                        # Accetta Vittoria Secca solo se super-favorita in casa (<= 1.48)
                        if q1 and q1 <= 1.48:
                            opzioni_match.setdefault(f"Vittoria {casa_ita}", []).append((q1, is_ammesso))
                        if q2 and q2 <= 1.45:
                            opzioni_match.setdefault(f"Vittoria {trasf_ita}", []).append((q2, is_ammesso))
                        
                        # Doppia Chance Corazzata (copre sempre il pareggio!)
                        if q1 and qx and q2:
                            dc_1x = round(1.0 / ((1.0/q1) + (1.0/qx)) * 0.965, 2)
                            dc_x2 = round(1.0 / ((1.0/q2) + (1.0/qx)) * 0.965, 2)
                            if 1.22 <= dc_1x <= 1.52:
                                opzioni_match.setdefault(f"Doppia Chance 1X ({casa_ita})", []).append((dc_1x, is_ammesso))
                            if 1.22 <= dc_x2 <= 1.52:
                                opzioni_match.setdefault(f"Doppia Chance X2 ({trasf_ita})", []).append((dc_x2, is_ammesso))
                            
                            # Stima matematica Over 1.5 Gol quando le due squadre sono offensive
                            if qx >= 3.55:
                                q_over15 = round(max(1.24, min(1.42, 1.85 / (qx * 0.40))), 2)
                                opzioni_match.setdefault("Over 1.5 Gol", []).append((q_over15, is_ammesso))

                    elif m['key'] == 'totals':
                        for out in m['outcomes']:
                            if out.get('name') == 'Over' and out.get('point') in [1.5, 2.5]:
                                if out['price'] <= 1.62:
                                    label = f"Over {out['point']} Gol"
                                    opzioni_match.setdefault(label, []).append((out['price'], is_ammesso))

            miglior_pick = None
            miglior_score = 0.0
            quota_scelta = 0.0

            for pick, lista_tuple in opzioni_match.items():
                if len(lista_tuple) < 2: continue
                tutte_quote = [q for q, _ in lista_tuple]
                quote_italiane = [q for q, amm in lista_tuple if amm]
                
                q_media = sum(tutte_quote) / len(tutte_quote)
                q_giocabile = max(quote_italiane) if quote_italiane else round(q_media, 2)
                
                if 1.22 <= q_media <= 1.58 and 1.22 <= q_giocabile <= 1.62:
                    edge_quota = min(1.08, q_giocabile / q_media)
                    # Forte priorità a Doppia Chance e Over 1.5 (altissima % di riuscita)
                    bonus_scudo = 0.09 if ("Doppia Chance" in pick or "Over 1.5" in pick) else 0.0
                    score = (1.0 / q_media) * edge_quota + bonus_scudo
                    
                    if score > miglior_score:
                        miglior_score = score
                        miglior_pick = pick
                        quota_scelta = round(q_giocabile, 2)

            if miglior_pick:
                candidati_alpha.append({
                    'id_partita': p['id'],
                    'data': data_ita.strftime("%d/%m %H:%M"),
                    'squadra_casa': casa_ita,
                    'squadra_trasferta': trasf_ita,
                    'pronostico': miglior_pick,
                    'quota': quota_scelta,
                    'score': miglior_score,
                    'lega': camp,
                    'stato': 'in attesa',
                    'risultato_reale': ''
                })

    if len(candidati_alpha) < 2: return

    ordinati = sorted(candidati_alpha, key=lambda x: (0 if x['lega'] == 'soccer_italy_serie_a' else 1, -x['score']))

    # NUOVO TARGET ORO: Massimo 3 partite selezionatissime per una quota tra 2.15 e 3.20!
    selezionati = []
    quota_totale = 1.0
    
    for c in ordinati:
        if len(selezionati) < 3 and quota_totale < 2.45:
            selezionati.append(c)
            quota_totale *= c['quota']

    if quota_totale < 2.05 and len(ordinati) > len(selezionati) and len(selezionati) < 4:
        selezionati.append(ordinati[len(selezionati)])
        quota_totale *= selezionati[-1]['quota']

    quota_totale = round(quota_totale, 2)
    if quota_totale < 1.95: return

    partite_pulite = [{k: v for k, v in c.items() if k != 'score'} for c in selezionati]
    stake = 12.0

    msg = "<b>🚀 MODELLO ALPHA | MULTIPLA PROTETTA</b>\n\n"
    msg += f"📊 <b>Moltiplicatore Totale</b>: {quota_totale}\n"
    msg += f"💰 <b>Stake</b>: {stake}€ (Ritorno pot.: {round(stake * quota_totale, 2)}€)\n\n"
    for c in partite_pulite:
        msg += f"⚽ <b>{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}</b>\n"
        msg += f"🛡️ <b>Scelta Scudo</b>: {c['pronostico']} (@{c['quota']})\n\n"
    msg += "<b>#SmartBetting #ModelloAlpha #RaddoppioPlus</b>"

    res = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    )

    if res.status_code == 200:
        db_principale['schedine'].append({
            'id': str(uuid.uuid4())[:8],
            'modello': 'alpha',
            'data_creazione': data_oggi_str,
            'importo': stake,
            'quota_totale': quota_totale,
            'ritorno_potenziale': round(stake * quota_totale, 2),
            'stato_schedina': 'in attesa',
            'telegram_inviato': True,
            'partite': partite_pulite
        })
        salva_database_principale(db_principale)

if __name__ == "__main__":
    esegui_alpha()
