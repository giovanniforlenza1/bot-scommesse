import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

campionati_odds = [
    'soccer_italy_serie_a', 'soccer_italy_serie_b', 'soccer_epl', 'soccer_efl_champ',
    'soccer_spain_la_liga', 'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'soccer_uefa_nations_league'
]

# Mappatura gratuita ESPN per leggere Angoli e Cartellini del Modello Beta
campionati_espn = [
    'ita.1', 'ita.2', 'eng.1', 'eng.2', 'esp.1', 'ger.1', 
    'fra.1', 'ned.1', 'por.1', 'uefa.champions', 'uefa.europa'
]

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
    "Inter Milan": "Inter", "Internazionale": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus",
    "Hellas Verona": "Verona", "Bologna FC": "Bologna", "Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Venezia FC": "Venezia", "Parma Calcio 1913": "Parma",
    "Como 1907": "Como", "Manchester Utd": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham", "Tottenham Hotspur": "Tottenham",
    "Newcastle Utd": "Newcastle", "Newcastle United": "Newcastle", "Paris Saint Germain": "PSG",
    "Paris Saint-Germain": "PSG", "Bayern Munich": "Bayern Monaco", "Bayer Leverkusen": "Bayer Leverkusen",
    "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad",
    "Athletic Club": "Athletic Bilbao"
}

def traduci_squadra(nome):
    nome_pulito = nome.strip()
    if nome_pulito in TRADUZIONI_NAZIONALI: return TRADUZIONI_NAZIONALI[nome_pulito]
    if nome_pulito in TRADUZIONI_SQUADRE: return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "").replace(" CF", "")

def normalizza_per_confronto(nome):
    # Rende il nome minuscolo ed essenziale per far combaciare i database
    n = traduci_squadra(nome).lower()
    for parola in ["calcio", "fc", "ac", "sc", "cf", "united", "city", "sporting"]:
        n = n.replace(parola, "")
    return n.strip()

def esegui_richiesta_odds(url_template):
    chiavi = [k.strip() for k in os.environ.get("ODDS_API_KEY", "").split(",") if k.strip()]
    if not chiavi: return None
    for chiave in chiavi:
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200: return res.json()
        except: pass
    return None

def scarica_statistiche_espn():
    """Scarica gratuitamente Corner e Cartellini degli ultimi 3 giorni da ESPN"""
    stats_partite = []
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    date_controllo = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(4)]

    for lega in campionati_espn:
        for data_str in date_controllo:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={data_str}"
            try:
                res = requests.get(url, timeout=8)
                if res.status_code != 200: continue
                data = res.json()
                for ev in data.get('events', []):
                    comp = ev.get('competitions', [{}])[0]
                    status = comp.get('status', {}).get('type', {}).get('completed', False)
                    if not status: continue

                    teams = comp.get('competitors', [])
                    if len(teams) < 2: continue

                    casa_nome, trasf_nome = "", ""
                    tot_corners = 0
                    tot_cards = 0

                    for t in teams:
                        t_name = t.get('team', {}).get('displayName', '')
                        if t.get('homeAway') == 'home': casa_nome = t_name
                        else: trasf_nome = t_name

                        for s in t.get('statistics', []):
                            s_name = s.get('name', '')
                            val = float(s.get('displayValue', '0') or 0)
                            if s_name == 'wonCorners':
                                tot_corners += int(val)
                            elif s_name in ['yellowCards', 'redCards']:
                                tot_cards += int(val)

                    stats_partite.append({
                        'casa_norm': normalizza_per_confronto(casa_nome),
                        'trasf_norm': normalizza_per_confronto(trasf_nome),
                        'corners': tot_corners,
                        'cards': tot_cards
                    })
            except:
                continue
    return stats_partite

def aggiorna_database():
    if not os.path.exists('database.json'): return
    with open('database.json', 'r', encoding='utf-8') as f:
        db = json.load(f)

    # 1. Raccoglie i risultati normali (Gol 1X2 / Over) da The Odds API
    risultati_gol = {}
    for camp in campionati_odds:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/scores/?daysFrom=3&apiKey=API_KEY_SEGRETA"
        dati = esegui_richiesta_odds(url)
        if not dati: continue
        for m in dati:
            if m.get('completed') and m.get('scores'):
                g_casa, g_trasf = 0, 0
                for s in m['scores']:
                    if s['name'] == m['home_team']: g_casa = int(s['score'])
                    elif s['name'] == m['away_team']: g_trasf = int(s['score'])
                risultati_gol[m['id']] = (g_casa, g_trasf, traduci_squadra(m['home_team']), traduci_squadra(m['away_team']))

    # 2. Raccoglie Angoli e Cartellini da ESPN se ci sono schedine Beta in attesa
    ha_beta_in_attesa = any(s.get('modello') == 'beta' and s.get('stato_schedina') == 'in attesa' for s in db.get('schedine', []))
    stats_espn = scarica_statistiche_espn() if ha_beta_in_attesa else []

    modifiche_effettuate = False

    for schedina in db.get('schedine', []):
        if schedina.get('stato_schedina') != 'in attesa':
            continue

        tutte_concluse = True
        schedina_persa = False

        for p in schedina.get('partite', []):
            if p.get('stato') != 'in attesa':
                if p.get('stato') == 'persa': schedina_persa = True
                continue

            pron = p.get('pronostico', '').lower()

            # --- VERIFICA MODELLO BETA (ANGOLI E CARTELLINI) ---
            if 'angol' in pron or 'corner' in pron or 'cartellin' in pron:
                c_norm = normalizza_per_confronto(p['squadra_casa'])
                t_norm = normalizza_per_confronto(p['squadra_trasferta'])
                
                match_stat = next((x for x in stats_espn if (c_norm in x['casa_norm'] or x['casa_norm'] in c_norm) and (t_norm in x['trasf_norm'] or x['trasf_norm'] in t_norm)), None)
                
                if not match_stat:
                    tutte_concluse = False
                    continue

                if 'angol' in pron or 'corner' in pron:
                    totale = match_stat['corners']
                    soglia = 9.5 if '9.5' in pron else 8.5
                    p['risultato_reale'] = f"{totale} Angoli"
                    p['stato'] = 'vinta' if totale > soglia else 'persa'
                elif 'cartellin' in pron:
                    totale = match_stat['cards']
                    soglia = 4.5 if '4.5' in pron else 3.5
                    p['risultato_reale'] = f"{totale} Cartellini"
                    p['stato'] = 'vinta' if totale > soglia else 'persa'

                if p['stato'] == 'persa': schedina_persa = True
                modifiche_effettuate = True

            # --- VERIFICA MODELLO OMEGA E ALPHA (1X2 E OVER GOL) ---
            else:
                id_p = p.get('id_partita')
                if id_p not in risultati_gol:
                    tutte_concluse = False
                    continue

                g_c, g_t, nome_c, nome_t = risultati_gol[id_p]
                p['risultato_reale'] = f"{g_c}-{g_t}"
                tot_gol = g_c + g_t

                vinta = False
                if 'pareggio' in pron:
                    vinta = (g_c == g_t)
                elif 'vittoria' in pron:
                    sq_scelta = pron.replace('vittoria', '').strip()
                    if sq_scelta in p['squadra_casa'].lower() and g_c > g_t: vinta = True
                    elif sq_scelta in p['squadra_trasferta'].lower() and g_t > g_c: vinta = True
                elif 'over 1.5' in pron:
                    vinta = (tot_gol >= 2)
                elif 'over 2.5' in pron:
                    vinta = (tot_gol >= 3)

                p['stato'] = 'vinta' if vinta else 'persa'
                if not vinta: schedina_persa = True
                modifiche_effettuate = True

        # Aggiorna lo stato generale dell'intera schedina
        if schedina_persa:
            schedina['stato_schedina'] = 'persa'
            modifiche_effettuate = True
        elif tutte_concluse:
            schedina['stato_schedina'] = 'vinta'
            modifiche_effettuate = True

    if modifiche_effettuate:
        with open('database.json', 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        print("Database risultati aggiornato con successo (incluso Modello Beta)!")
    else:
        print("Nessun nuovo risultato da aggiornare.")

if __name__ == "__main__":
    aggiorna_database()
