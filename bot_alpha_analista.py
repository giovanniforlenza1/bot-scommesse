import requests
import json
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

campionati = [
    'soccer_italy_serie_a', 'soccer_epl', 'soccer_spain_la_liga',
    'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_netherlands_eredivisie', 'soccer_uefa_champs_league', 'soccer_uefa_europa_league'
]

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus",
    "Hellas Verona": "Verona", "Bologna FC": "Bologna", "Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Venezia FC": "Venezia", "Parma Calcio 1913": "Parma",
    "Como 1907": "Como", "Manchester Utd": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham",
    "Newcastle Utd": "Newcastle", "Paris Saint Germain": "PSG",
    "Bayern Munich": "Bayern Monaco", "Bayer Leverkusen": "Bayer Leverkusen"
}

def traduci_squadra(nome):
    nome_pulito = nome.strip()
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
    limite_temporale = oggi + timedelta(days=3)
    
    db_principale = carica_database_principale()
    # Controlla se c'è già una schedina Alpha attiva creata oggi
    for s in db_principale['schedine']:
        if s.get('modello') == 'alpha' and s.get('data_creazione') == oggi.strftime("%d/%m/%Y"):
            print("Alpha già generata oggi.")
            return

    candidati_alpha = []

    for camp in campionati:
        # Scansiona sia 1X2 (h2h) sia Over/Under (totals) per trovare giocate "Scudo"
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
                for m in book.get('markets', []):
                    if m['key'] == 'h2h':
                        for out in m['outcomes']:
                            if out['name'] == casa_orig:
                                opzioni_match.setdefault(f"Vittoria {casa_ita}", []).append(out['price'])
                            elif out['name'] == trasf_orig:
                                opzioni_match.setdefault(f"Vittoria {trasf_ita}", []).append(out['price'])
                    elif m['key'] == 'totals':
                        for out in m['outcomes']:
                            if out.get('name') == 'Over' and out.get('point') in [1.5, 2.5]:
                                label = f"Over {out['point']} Gol"
                                opzioni_match.setdefault(label, []).append(out['price'])

            # Valuta l'opzione più sicura nel range 1.25 - 1.58 per questo match
            miglior_pick = None
            miglior_confidenza = 0.0
            quota_scelta = 0.0

            for pick, lista_quote in opzioni_match.items():
                if len(lista_quote) < 2: continue
                q_media = round(sum(lista_quote) / len(lista_quote), 2)
                q_max = max(lista_quote)
                
                if 1.25 <= q_media <= 1.58:
                    # Bonus confidenza del +4% ai mercati Over (meno soggetti alla trappola del pareggio)
                    bonus_scudo = 0.04 if "Over" in pick else 0.0
                    confidenza = (1.0 / q_media) + bonus_scudo
                    if confidenza > miglior_confidenza:
                        miglior_confidenza = confidenza
                        miglior_pick = pick
                        quota_scelta = q_max

            if miglior_pick:
                candidati_alpha.append({
                    'id_partita': p['id'],
                    'data': data_ita.strftime("%d/%m %H:%M"),
                    'squadra_casa': casa_ita,
                    'squadra_trasferta': trasf_ita,
                    'pronostico': miglior_pick,
                    'quota': round(quota_scelta, 2),
                    'confidenza': miglior_confidenza,
                    'lega': camp,
                    'stato': 'in attesa',
                    'risultato_reale': ''
                })

    if len(candidati_alpha) < 3: return

    # Ordina dando priorità a Serie A e alla massima confidenza matematica
    ordinati = sorted(candidati_alpha, key=lambda x: (0 if x['lega'] == 'soccer_italy_serie_a' else 1, -x['confidenza']))

    selezionati = []
    quota_totale = 1.0
    for c in ordinati:
        if len(selezionati) < 5 and quota_totale < 5.00:
            selezionati.append({k: v for k, v in c.items() if k != 'confidenza'})
            quota_totale *= c['quota']

    quota_totale = round(quota_totale, 2)
    if quota_totale < 4.80: return # Sicurezza: pubblica solo se raggiunge la soglia target ~5.00

    stake = 10.0
    db_principale['schedine'].append({
        'id': str(uuid.uuid4())[:8],
        'modello': 'alpha',
        'data_creazione': oggi.strftime("%d/%m/%Y"),
        'importo': stake,
        'quota_totale': quota_totale,
        'ritorno_potenziale': round(stake * quota_totale, 2),
        'stato_schedina': 'in attesa',
        'partite': selezionati
    })

    msg = "**🚀 MODELLO ALPHA | QUOTA 5+**\n\n"
    msg += f"📊 **Moltiplicatore Totale**: {quota_totale}\n"
    msg += f"💰 **Stake**: {stake}€ (Vincita pot.: {round(stake * quota_totale, 2)}€)\n\n"
    for c in selezionati:
        msg += f"⚽ **{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}**\n"
        msg += f"🛡️ **Scelta**: {c['pronostico']} (@{c['quota']})\n\n"
    msg += "**#SmartBetting #ModelloAlpha #Multiple**"

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    salva_database_principale(db_principale)

if __name__ == "__main__":
    esegui_alpha()
