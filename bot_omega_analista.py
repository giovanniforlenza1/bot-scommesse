import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

campionati = [
    'soccer_uefa_nations_league',
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
    "Athletic Club": "Athletic Bilbao", "Wolverhampton Wanderers": "Wolverhampton",
    "Italy": "Italia", "France": "Francia", "Germany": "Germania", "Spain": "Spagna",
    "England": "Inghilterra", "Netherlands": "Olanda", "Belgium": "Belgio", "Portugal": "Portogallo",
    "Croatia": "Croazia", "Switzerland": "Svizzera", "Poland": "Polonia", "Denmark": "Danimarca",
    "Sweden": "Svezia", "Norway": "Norvegia", "Austria": "Austria", "Scotland": "Scozia",
    "Wales": "Galles", "Hungary": "Ungheria", "Turkey": "Turchia", "Albania": "Albania",
    "Serbia": "Serbia", "Greece": "Grecia", "Czech Republic": "Repubblica Ceca", "Ukraine": "Ucraina",
    "Republic of Ireland": "Irlanda", "Ireland": "Irlanda", "Northern Ireland": "Irlanda del Nord",
    "Finland": "Finlandia", "Iceland": "Islanda", "Bosnia and Herzegovina": "Bosnia",
    "Bosnia & Herzegovina": "Bosnia", "Romania": "Romania", "Slovakia": "Slovacchia", "Slovenia": "Slovenia"
}

def ottieni_pool_chiavi():
    nomi_secrets = [
        "CHIAVE_D", "CHIAVE_E", "CHIAVE_A", "CHIAVE_B", "CHIAVE_C", 
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
            if res.status_code == 200:
                return res.json()
        except:
            pass
    return None

def traduci_squadra(nome):
    nome_pulito = str(nome).strip()
    if nome_pulito in TRADUZIONI_SQUADRE:
        return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "")

def esegui_analista():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    inizio_finestra = oggi + timedelta(minutes=30)
    limite_temporale = oggi + timedelta(days=3)

    risultati_analisi = []
    storico_squadre = {}

    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        partite = esegui_richiesta_api(url_template)
        if not partite:
            continue

        for p in partite:
            data_ita = datetime.strptime(p['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita < inizio_finestra or data_ita > limite_temporale:
                continue

            casa_orig, trasf_orig = p['home_team'], p['away_team']
            casa_ita, trasf_ita = traduci_squadra(casa_orig), traduci_squadra(trasf_orig)

            q1_list, qx_list, q2_list = [], [], []
            for book in p.get('bookmakers', []):
                if 'exchange' in book.get('title', '').lower():
                    continue
                for m in book.get('markets', []):
                    if m['key'] == 'h2h':
                        for out in m['outcomes']:
                            if out['name'] == casa_orig: q1_list.append(out['price'])
                            elif out['name'] == trasf_orig: q2_list.append(out['price'])
                            elif out['name'].lower() == 'draw': qx_list.append(out['price'])

            if not q1_list or not qx_list or not q2_list:
                continue

            q1_med = sum(q1_list) / len(q1_list)
            qx_med = sum(qx_list) / len(qx_list)
            q2_med = sum(q2_list) / len(q2_list)

            inv_sum = (1.0 / q1_med) + (1.0 / qx_med) + (1.0 / q2_med)
            prob_1 = (1.0 / q1_med) / inv_sum
            prob_2 = (1.0 / q2_med) / inv_sum

            if prob_1 >= prob_2 and prob_1 >= 0.51:
                consiglio = f"Vittoria {casa_ita}"
                prob_scelta = prob_1
                quota_equa = round(1.0 / prob_1, 2)
            elif prob_2 > prob_1 and prob_2 >= 0.51:
                consiglio = f"Vittoria {trasf_ita}"
                prob_scelta = prob_2
                quota_equa = round(1.0 / prob_2, 2)
            else:
                continue

            storico_squadre[casa_ita] = {"prob_stimata": round(prob_1 * 100, 1), "ultimo_match": data_ita.strftime("%d/%m %H:%M")}
            storico_squadre[trasf_ita] = {"prob_stimata": round(prob_2 * 100, 1), "ultimo_match": data_ita.strftime("%d/%m %H:%M")}

            risultati_analisi.append({
                "id_partita": p['id'],
                "data": data_ita.strftime("%d/%m %H:%M"),
                "match": f"{casa_ita} - {trasf_ita}",
                "consiglio_algoritmo": consiglio,
                "probabilita_reale": round(prob_scelta * 100, 1),
                "quota_equa": quota_equa,
                "lega": camp
            })

    with open('database_analisi.json', 'w', encoding='utf-8') as f:
        json.dump({"ultimo_aggiornamento": oggi.strftime("%d/%m/%Y %H:%M"), "analisi": risultati_analisi}, f, indent=4, ensure_ascii=False)

    with open('database_squadre.json', 'w', encoding='utf-8') as fs:
        json.dump({"ultimo_aggiornamento": oggi.strftime("%d/%m/%Y %H:%M"), "squadre": storico_squadre}, fs, indent=4, ensure_ascii=False)

    print(f"Omega Analista completato: {len(risultati_analisi)} match imminenti salvati.")

if __name__ == "__main__":
    esegui_analista()
