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

campionati_espn = [
    'ita.1', 'ita.2', 'eng.1', 'eng.2', 'esp.1', 'ger.1', 
    'fra.1', 'ned.1', 'por.1', 'uefa.champions', 'uefa.europa', 'uefa.nations'
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
    "Athletic Club": "Athletic Bilbao", "RB Salzburg": "Salisburgo", "FC Salzburg": "Salisburgo",
    "Red Bull Salzburg": "Salisburgo", "Salzburg": "Salisburgo", "Sporting CP": "Sporting Lisbona",
    "Club Brugge": "Brugge", "PSV Eindhoven": "PSV", "Feyenoord Rotterdam": "Feyenoord"
}

def traduci_squadra(nome):
    nome_pulito = nome.strip()
    if nome_pulito in TRADUZIONI_NAZIONALI: return TRADUZIONI_NAZIONALI[nome_pulito]
    if nome_pulito in TRADUZIONI_SQUADRE: return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "").replace(" CF", "")

def normalizza_per_confronto(nome):
    n = traduci_squadra(nome).lower()
    if "salzburg" in n or "salisburgo" in n:
        return "salisburgo"
    for parola in ["calcio", "fc", "ac", "sc", "cf", "rb", "red bull", "united", "city", "sporting", "1907", "1913"]:
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

def leggi_statistiche_ufficiali(lega, event_id):
    """Legge SOLO la tabella Statistiche di fine partita: Gialli + Rossi e Calci d'Angolo"""
    tot_corners = 0
    tot_cards = 0

    url_summary = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/summary?event={event_id}"
    try:
        res = requests.get(url_summary, timeout=8)
        if res.status_code == 200:
            data = res.json()
            # Scorre le due squadre (Casa e Trasferta) nella tabella Statistiche (boxscore)
            for team_box in data.get('boxscore', {}).get('teams', []):
                gialli = 0
                rossi = 0
                angoli = 0
                for stat in team_box.get('statistics', []):
                    nome_stat = stat.get('name', '')
                    val_str = str(stat.get('displayValue', '0')).strip()
                    val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
                    
                    if nome_stat == 'wonCorners':
                        angoli = val
                    elif nome_stat == 'yellowCards':
                        gialli = val
                    elif nome_stat == 'redCards':
                        rossi = val
                        
                tot_corners += angoli
                tot_cards += (gialli + rossi)
                
            return tot_corners, tot_cards
    except:
        pass
    return None, None

def scarica_statistiche_espn():
    """Raccoglie le statistiche post-partita degli ultimi 5 giorni"""
    stats_partite = []
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    date_controllo = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(5)]

    for lega in campionati_espn:
        for data_str in date_controllo:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={data_str}"
            try:
                res = requests.get(url, timeout=8)
                if res.status_code != 200: continue
                data = res.json()
                for ev in data.get('events', []):
                    comp = ev.get('competitions', [{}])[0]
                    # Verifica che la partita sia terminata (completed = True)
                    status = comp.get('status', {}).get('type', {}).get('completed', False)
                    if not status: continue

                    teams = comp.get('competitors', [])
                    if len(teams) < 2: continue

                    casa_nome, trasf_nome = "", ""
                    for t in teams:
                        t_name = t.get('team', {}).get('displayName', '')
                        if t.get('homeAway') == 'home': casa_nome = t_name
                        else: trasf_nome = t_name

                    event_id = ev.get('id')
                    tot_corners, tot_cards = leggi_statistiche_ufficiali(lega, event_id)
                    if tot_corners is None:
                        continue

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

    # 1. Raccoglie i risultati Gol da The Odds API
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

    # Controlla schedine Beta in attesa o quelle con il conteggio errato da ricalcolare ("0 " o "6 Cartellini")
    valori_da_ricalcolare = ['0 Cartellini', '0 Angoli', '6 Cartellini']
    ha_beta_da_controllare = any(
        s.get('modello') == 'beta' and (
            s.get('stato_schedina') == 'in attesa' or 
            any(p.get('risultato_reale') in valori_da_ricalcolare for p in s.get('partite', []))
        )
        for s in db.get('schedine', [])
    )
    stats_espn = scarica_statistiche_espn() if ha_beta_da_controllare else []

    modifiche_effettuate = False

    for schedina in db.get('schedine', []):
        riaperta_per_fix = any(p.get('risultato_reale') in valori_da_ricalcolare for p in schedina.get('partite', []))
        
        if schedina.get('stato_schedina') != 'in attesa' and not riaperta_per_fix:
            continue

        tutte_concluse = True
        schedina_persa = False

        for p in schedina.get('partite', []):
            if p.get('stato') != 'in attesa' and p.get('risultato_reale') not in valori_da_ricalcolare:
                if p.get('stato') == 'persa': schedina_persa = True
                continue

            pron = p.get('pronostico', '').lower()

            # --- VERIFICA MODELLO BETA (SOMMA GIALLI + ROSSI E ANGOLI DALLE STATISTICHE) ---
            if 'angol' in pron or 'corner' in pron or 'cartellin' in pron:
                c_norm = normalizza_per_confronto(p['squadra_casa'])
                t_norm = normalizza_per_confronto(p['squadra_trasferta'])
                
                match_stat = next((
                    x for x in stats_espn 
                    if (c_norm in x['casa_norm'] or x['casa_norm'] in c_norm) and 
                       (t_norm in x['trasf_norm'] or x['trasf_norm'] in t_norm)
                ), None)
                
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

        if schedina_persa:
            schedina['stato_schedina'] = 'persa'
            modifiche_effettuate = True
        elif tutte_concluse:
            schedina['stato_schedina'] = 'vinta'
            modifiche_effettuate = True

    if modifiche_effettuate:
        with open('database.json', 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        print("Database risultati aggiornato con le sole statistiche ufficiali!")
    else:
        print("Nessun nuovo risultato da aggiornare.")

if __name__ == "__main__":
    aggiorna_database()
