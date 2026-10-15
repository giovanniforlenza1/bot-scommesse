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

siti_ammessi = ['Bet365', 'Snai', 'Sisal', 'Eurobet', 'PlanetWin365', 'GoldBet', 'Betfair', 'William Hill', 'Unibet', 'Marathonbet', '888sport']

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
    "Athletic Club": "Athletic Bilbao"
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
    
    # Rimuove eventuali schedine Alpha di oggi rimaste "fantasma" (senza invio Telegram) per forzare l'invio pulito
    db_principale['schedine'] = [
        s for s in db_principale['schedine'] 
        if not (s.get('modello') == 'alpha' and s.get('data_creazione') == data_oggi_str and not s.get('telegram_inviato'))
    ]

    for s in db_principale['schedine']:
        if s.get('modello') == 'alpha' and s.get('data_creazione') == data_oggi_str and s.get('telegram_inviato'):
            print("Alpha: Schedina già generata e confermata su Telegram oggi.")
            return

    candidati_alpha = []

    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu&markets=h2h,totals"
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
                is_ammesso = any(sb.lower() in titolo_book.lower() for sb in siti_ammessi)
                
                for m in book.get('markets', []):
                    if m['key'] == 'h2h':
                        for out in m['outcomes']:
                            if out['name'] == casa_orig:
                                opzioni_match.setdefault(f"Vittoria {casa_ita}", []).append((out['price'], is_ammesso))
                            elif out['name'] == trasf_orig:
                                opzioni_match.setdefault(f"Vittoria {trasf_ita}", []).append((out['price'], is_ammesso))
                    elif m['key'] == 'totals':
                        for out in m['outcomes']:
                            if out.get('name') == 'Over' and out.get('point') in [1.5, 2.5]:
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
                
                if 1.25 <= q_media <= 1.72 and 1.25 <= q_giocabile <= 1.78:
                    edge_quota = q_giocabile / q_media
                    bonus_over = 0.05 if "Over" in pick else 0.0
                    score = (1.0 / q_media) * edge_quota + bonus_over
                    
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

    print(f"Alpha: Trovati {len(candidati_alpha)} candidati validi nei prossimi 4 giorni.")
    if len(candidati_alpha) < 3:
        print("Alpha Stop: Meno di 3 candidati disponibili in lavagna.")
        return

    ordinati = sorted(candidati_alpha, key=lambda x: (0 if x['lega'] == 'soccer_italy_serie_a' else 1, -x['score']))

    selezionati = []
    quota_totale = 1.0
    
    for c in ordinati:
        if len(selezionati) < 5 and quota_totale < 5.00:
            selezionati.append(c)
            quota_totale *= c['quota']

    if quota_totale < 4.60 and len(ordinati) > len(selezionati):
        restanti_alti = sorted(ordinati[len(selezionati):], key=lambda x: -x['quota'])
        for extra in restanti_alti:
            if len(selezionati) < 6 and quota_totale < 4.80:
                selezionati.append(extra)
                quota_totale *= extra['quota']

    quota_totale = round(quota_totale, 2)
    print(f"Alpha: Schedina calcolata con {len(selezionati)} eventi -> Quota Totale: {quota_totale}")

    if quota_totale < 4.50:
        print(f"Alpha Stop: Quota totale ({quota_totale}) insufficiente per il target Alpha.")
        return

    partite_pulite = [{k: v for k, v in c.items() if k != 'score'} for c in selezionati]
    stake = 10.0

    # Formattazione HTML blindata (non salta mai per apostrofi o caratteri speciali)
    msg = "<b>🚀 MODELLO ALPHA | QUOTA 5+</b>\n\n"
    msg += f"📊 <b>Moltiplicatore Totale</b>: {quota_totale}\n"
    msg += f"💰 <b>Stake</b>: {stake}€ (Vincita pot.: {round(stake * quota_totale, 2)}€)\n\n"
    for c in partite_pulite:
        msg += f"⚽ <b>{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}</b>\n"
        msg += f"🛡️ <b>Scelta</b>: {c['pronostico']} (@{c['quota']})\n\n"
    msg += "<b>#SmartBetting #ModelloAlpha #Multiple</b>"

    res = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    )
    print(f"Alpha Telegram Status: {res.status_code} - Risposta: {res.text}")

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
    else:
        print("ERRORE TELEGRAM: Messaggio non consegnato. Controlla CHAT_ID o i permessi del bot.")

if __name__ == "__main__":
    esegui_alpha()
