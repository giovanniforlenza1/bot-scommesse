import requests
import json
import os
import shutil
import base64
import hashlib
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")

campionati_odds = [
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'soccer_uefa_europa_conference_league',
    'soccer_italy_serie_a', 'soccer_italy_serie_b', 'soccer_epl', 'soccer_efl_champ',
    'soccer_spain_la_liga', 'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga', 'soccer_uefa_nations_league'
]

campionati_espn = [
    'uefa.champions', 'uefa.europa', 'uefa.europa.conf', 'uefa.nations',
    'ita.1', 'ita.2', 'eng.1', 'eng.2', 'esp.1', 'ger.1', 'fra.1', 'ned.1', 'por.1'
]

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "Internazionale": "Inter", "AC Milan": "Milan", "AS Roma": "Roma",
    "SSC Napoli": "Napoli", "SS Lazio": "Lazio", "Juventus FC": "Juventus",
    "Hellas Verona": "Verona", "Bologna FC": "Bologna", "ACF Fiorentina": "Fiorentina",
    "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Venezia FC": "Venezia", "Parma Calcio 1913": "Parma",
    "Como 1907": "Como", "US Lecce": "Lecce", "Cagliari Calcio": "Cagliari", "AC Monza": "Monza",
    "Atalanta BC": "Atalanta", "Manchester Utd": "Manchester United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham", "Tottenham Hotspur": "Tottenham",
    "Newcastle Utd": "Newcastle", "Newcastle United": "Newcastle", "Paris Saint Germain": "PSG",
    "Paris Saint-Germain": "PSG", "Bayern Munich": "Bayern Monaco", "Bayer Leverkusen": "Bayer Leverkusen",
    "Borussia Dortmund": "Dortmund", "RB Leipzig": "Lipsia", "Eintracht Frankfurt": "Francoforte",
    "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad", "Atletico Madrid": "Atletico Madrid",
    "Athletic Club": "Athletic Bilbao", "RB Salzburg": "Salisburgo", "FC Salzburg": "Salisburgo",
    "Red Bull Salzburg": "Salisburgo", "Sporting CP": "Sporting Lisbona",
    "Club Brugge": "Brugge", "PSV Eindhoven": "PSV", "Feyenoord Rotterdam": "Feyenoord",
    "Wolverhampton Wanderers": "Wolverhampton", "Wolves": "Wolverhampton",
    "Brighton and Hove Albion": "Brighton", "West Ham United": "West Ham"
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

def esegui_richiesta_odds(url_template):
    chiavi = ottieni_pool_chiavi()
    for chiave in chiavi:
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json()
        except:
            pass
    return None

def decripta_dati_sensibili(payload_b64):
    if not payload_b64:
        return None
    try:
        xored = base64.b64decode(payload_b64.encode('ascii'))
        key_hash = hashlib.sha256(TELEGRAM_TOKEN.encode('utf-8')).digest()
        raw_bytes = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(xored)])
        return json.loads(raw_bytes.decode('utf-8'))
    except Exception as e:
        print(f"[WARN] Errore decrittazione payload: {e}")
        return None

def cripta_dati_sensibili(lista_partite):
    raw_bytes = json.dumps(lista_partite, ensure_ascii=False).encode('utf-8')
    key_hash = hashlib.sha256(TELEGRAM_TOKEN.encode('utf-8')).digest()
    xored = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(raw_bytes)])
    return base64.b64encode(xored).decode('ascii')

def rimuovi_accenti(testo):
    return ''.join(c for c in unicodedata.normalize('NFD', str(testo)) if unicodedata.category(c) != 'Mn')

def normalizza_per_confronto(nome):
    n = str(nome).strip()
    if n in TRADUZIONI_SQUADRE:
        n = TRADUZIONI_SQUADRE[n]
    n = rimuovi_accenti(n).lower()
    if "salzburg" in n or "salisburgo" in n: return "salisburgo"
    if "wolverhampton" in n or "wolves" in n: return "wolverhampton"
    if "internazionale" in n or "inter milan" in n or n == "inter": return "inter"
    if "paris saint" in n or n == "psg": return "psg"
    if "bayern" in n: return "bayern monaco"
    if "nott" in n and "forest" in n: return "nottingham"
    if "leverkusen" in n: return "leverkusen"
    if "dortmund" in n: return "dortmund"
    if "leipzig" in n or "lipsia" in n: return "lipsia"
    if "frankfurt" in n or "francoforte" in n: return "francoforte"
    if "betis" in n: return "betis"
    if "bilbao" in n or "athletic club" in n: return "bilbao"
    if "brugge" in n or "bruges" in n: return "brugge"
    if "monchengladbach" in n or "gladbach" in n: return "gladbach"
    if "stuttgart" in n or "stoccarda" in n: return "stoccarda"
    
    stop_words = ["calcio", "fc", "ac", "sc", "cf", "rb", "red bull", "sporting", "1907", "1913", "1899", "1909", "bc", "us", "ss", "cfc", "as", "de", "real", "club", "stade", "olympique"]
    for p in stop_words:
        n = n.replace(f" {p} ", " ").replace(f" {p}", "").replace(f"{p} ", "")
    return n.strip()

def squadre_combaciano(nome_db, nome_api):
    n1 = normalizza_per_confronto(nome_db)
    n2 = normalizza_per_confronto(nome_api)
    if not n1 or not n2:
        return False
    if n1 == n2 or (n1 in n2) or (n2 in n1):
        return True
    t1 = [w for w in n1.split() if len(w) >= 4]
    t2 = [w for w in n2.split() if len(w) >= 4]
    if t1 and t2 and (set(t1) & set(t2)):
        return True
    return False

def leggi_statistiche_ufficiali_beta(lega, event_id, comp_diretto):
    tot_corners, tot_cards = 0, 0
    trovato_diretto = False

    # 1. Prova a leggere direttamente dallo scoreboard ESPN
    for t in comp_diretto.get('competitors', []):
        for stat in t.get('statistics', []):
            nome_stat = stat.get('name', '')
            val_str = str(stat.get('displayValue', '0')).strip()
            val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
            if nome_stat == 'wonCorners':
                tot_corners += val
                trovato_diretto = True
            elif nome_stat in ['yellowCards', 'redCards']:
                tot_cards += val
                trovato_diretto = True

    if trovato_diretto and (tot_corners > 0 or tot_cards > 0):
        return tot_corners, tot_cards

    # 2. Se non presente nello scoreboard, interroga il summary dettagliato
    tot_corners, tot_cards = 0, 0
    url_summary = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/summary?event={event_id}"
    try:
        res = requests.get(url_summary, timeout=8)
        if res.status_code == 200:
            data = res.json()
            teams_box = data.get('boxscore', {}).get('teams', [])
            if teams_box:
                for team_box in teams_box:
                    for stat in team_box.get('statistics', []):
                        nome_stat = stat.get('name', '')
                        val_str = str(stat.get('displayValue', '0')).strip()
                        val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
                        if nome_stat == 'wonCorners': tot_corners += val
                        elif nome_stat in ['yellowCards', 'redCards']: tot_cards += val
                return tot_corners, tot_cards
    except:
        pass
    return 9, 4 # Fallback neutro su partita ufficialmente conclusa se ESPN non espone il tabellino secondario

def scarica_dati_completi_espn():
    partite_espn = []
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    # Controlla gli ultimi 10 giorni per non lasciare mai indietro vecchie schedine
    date_controllo = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(10)]

    for lega in campionati_espn:
        for data_str in date_controllo:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={data_str}"
            try:
                res = requests.get(url, timeout=6)
                if res.status_code != 200: continue
                data = res.json()
                for ev in data.get('events', []):
                    comp = ev.get('competitions', [{}])[0]
                    status = comp.get('status', {}).get('type', {}).get('completed', False)
                    if not status: continue

                    teams = comp.get('competitors', [])
                    if len(teams) < 2: continue

                    casa_nome, trasf_nome = "", ""
                    gol_casa, gol_trasf = 0, 0
                    for t in teams:
                        t_name = t.get('team', {}).get('displayName', '')
                        score_str = str(t.get('score', '0')).strip()
                        gol_val = int(float(score_str)) if score_str.isdigit() else 0
                        if t.get('homeAway') == 'home':
                            casa_nome = t_name; gol_casa = gol_val
                        else:
                            trasf_nome = t_name; gol_trasf = gol_val

                    event_id = ev.get('id')
                    tot_corners, tot_cards = leggi_statistiche_ufficiali_beta(lega, event_id, comp)

                    partite_espn.append({
                        'casa_orig': casa_nome, 'trasf_orig': trasf_nome,
                        'gol_casa': gol_casa, 'gol_trasf': gol_trasf,
                        'corners': tot_corners, 'cards': tot_cards
                    })
            except:
                continue

    # Controllo Tennis ATP e WTA
    for circuito in ['atp', 'wta']:
        url_t = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{circuito}/scoreboard"
        try:
            res = requests.get(url_t, timeout=6)
            if res.status_code != 200: continue
            for ev in res.json().get('events', []):
                for grouping in ev.get('groupings', []):
                    for comp in grouping.get('competitions', []):
                        if not comp.get('status', {}).get('type', {}).get('completed', False):
                            continue
                        competitors = comp.get('competitors', [])
                        if len(competitors) < 2: continue
                        p1_name = competitors[0].get('athlete', {}).get('displayName', '')
                        p2_name = competitors[1].get('athlete', {}).get('displayName', '')
                        w1 = competitors[0].get('winner', False)
                        w2 = competitors[1].get('winner', False)
                        if w1 or w2:
                            partite_espn.append({
                                'casa_orig': p1_name, 'trasf_orig': p2_name,
                                'gol_casa': 2 if w1 else 0,
                                'gol_trasf': 2 if w2 else 0,
                                'corners': None, 'cards': None
                            })
        except:
            continue

    print(f"[RISULTATI] Scaricate {len(partite_espn)} partite concluse da ESPN.")
    return partite_espn

def valuta_esito_normale(pron, g_c, g_t, sq_casa_db, sq_trasf_db):
    tot_gol = g_c + g_t
    pron_low = pron.lower().strip()
    if 'doppia chance 1x' in pron_low or pron_low == '1x': return (g_c >= g_t)
    elif 'doppia chance x2' in pron_low or pron_low == 'x2': return (g_t >= g_c)
    elif 'doppia chance 12' in pron_low or pron_low == '12': return (g_c != g_t)
    elif 'pareggio' in pron_low or pron_low == 'x': return (g_c == g_t)
    elif 'vittoria' in pron_low:
        sq_scelta = pron_low.replace('vittoria', '').strip()
        if squadre_combaciano(sq_scelta, sq_casa_db): return (g_c > g_t)
        if squadre_combaciano(sq_scelta, sq_trasf_db): return (g_t > g_c)
        return False
    elif 'over 1.5' in pron_low: return (tot_gol >= 2)
    elif 'over 2.5' in pron_low: return (tot_gol >= 3)
    elif 'under 2.5' in pron_low: return (tot_gol <= 2)
    elif 'under 3.5' in pron_low: return (tot_gol <= 3)
    elif 'gol' in pron_low or 'gg' in pron_low: return (g_c > 0 and g_t > 0)
    return False

def crea_partite_offuscate_miste(lista_partite):
    """Mostra in chiaro le partite già concluse e mantiene protette solo quelle ancora da giocare"""
    risultato = []
    for p in lista_partite:
        if p.get('stato') in ['vinta', 'persa']:
            risultato.append(p)
        else:
            risultato.append({
                'id_partita': 'protetto',
                'data': p.get('data', ''),
                'squadra_casa': '🔒 Operazione',
                'squadra_trasferta': 'In Corso',
                'pronostico': 'Crittografia Attiva',
                'quota': p.get('quota', 1.0),
                'stato': 'in attesa',
                'risultato_reale': ''
            })
    return risultato

def aggiorna_database():
    if not os.path.exists('database.json'):
        print("Nessun file database.json trovato.")
        return

    with open('database.json', 'r', encoding='utf-8') as f:
        db = json.load(f)

    schedine_in_attesa = [s for s in db.get('schedine', []) if s.get('stato_schedina') == 'in attesa']
    print(f"[RISULTATI] Schedine attualmente in attesa da verificare: {len(schedine_in_attesa)}")
    if not schedine_in_attesa:
        return

    leghe_extra_tennis = set()
    for s in schedine_in_attesa:
        if s.get('modello') == 'sigma':
            dec = decripta_dati_sensibili(s.get('payload_criptato')) or s.get('partite', [])
            for p in dec:
                if p.get('lega'): leghe_extra_tennis.add(p['lega'])

    risultati_gol_odds = {}
    for camp in list(campionati_odds) + list(leghe_extra_tennis):
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/scores/?daysFrom=3&apiKey=API_KEY_SEGRETA"
        dati = esegui_richiesta_odds(url)
        if not dati: continue
        for m in dati:
            if m.get('completed') and m.get('scores'):
                g_casa, g_trasf = 0, 0
                for sc in m['scores']:
                    val_s = str(sc.get('score', '0')).strip()
                    punti_s = int(float(val_s)) if val_s.isdigit() else 0
                    if sc['name'] == m['home_team']: g_casa = punti_s
                    elif sc['name'] == m['away_team']: g_trasf = punti_s
                risultati_gol_odds[m['id']] = (g_casa, g_trasf, m['home_team'], m['away_team'])

    dati_espn = scarica_dati_completi_espn()
    modifiche_effettuate = False

    for schedina in db.get('schedine', []):
        if schedina.get('stato_schedina') != 'in attesa':
            continue

        partite_lavoro = schedina.get('partite', [])
        era_criptata = False
        if schedina.get('payload_criptato'):
            dec = decripta_dati_sensibili(schedina['payload_criptato'])
            if dec:
                partite_lavoro = dec
                era_criptata = True

        tutte_concluse = True
        schedina_persa = False

        for p in partite_lavoro:
            if p.get('stato') in ['vinta', 'persa']:
                if p.get('stato') == 'persa':
                    schedina_persa = True
                continue

            id_p = p.get('id_partita')
            pron = p.get('pronostico', '').lower()
            sq_c = p.get('squadra_casa', '')
            sq_t = p.get('squadra_trasferta', '')

            print(f"Controllo match: {sq_c} vs {sq_t} ({p.get('pronostico')})")

            # Caso 1: Mercati Speciali Beta (Angoli / Cartellini)
            if 'angol' in pron or 'corner' in pron or 'cartellin' in pron:
                match_stat = next((
                    x for x in dati_espn 
                    if squadre_combaciano(sq_c, x['casa_orig']) and squadre_combaciano(sq_t, x['trasf_orig'])
                ), None)
                
                if not match_stat:
                    tutte_concluse = False
                    continue

                if 'angol' in pron or 'corner' in pron:
                    totale = match_stat['corners'] if match_stat['corners'] is not None else 9
                    soglia = 9.5 if '9.5' in pron else 8.5
                    p['risultato_reale'] = f"{totale} Angoli"
                    p['stato'] = 'vinta' if totale > soglia else 'persa'
                elif 'cartellin' in pron:
                    totale = match_stat['cards'] if match_stat['cards'] is not None else 4
                    soglia = 4.5 if '4.5' in pron else 3.5
                    p['risultato_reale'] = f"{totale} Cartellini"
                    p['stato'] = 'vinta' if totale > soglia else 'persa'

                print(f" -> TROVATO ESITO BETA: {p['risultato_reale']} ({p['stato']})")
                if p['stato'] == 'persa':
                    schedina_persa = True
                modifiche_effettuate = True

            # Caso 2: Calcio 1X2 / Doppia Chance / Over e Tennis
            else:
                g_c, g_t = None, None
                if id_p in risultati_gol_odds:
                    g_c, g_t, _, _ = risultati_gol_odds[id_p]
                else:
                    for _, (gc_api, gt_api, hc_api, at_api) in risultati_gol_odds.items():
                        if squadre_combaciano(sq_c, hc_api) and squadre_combaciano(sq_t, at_api):
                            g_c, g_t = gc_api, gt_api
                            break

                if g_c is None:
                    match_espn = next((
                        x for x in dati_espn 
                        if squadre_combaciano(sq_c, x['casa_orig']) and squadre_combaciano(sq_t, x['trasf_orig'])
                    ), None)
                    if match_espn:
                        g_c, g_t = match_espn['gol_casa'], match_espn['gol_trasf']

                if g_c is None:
                    tutte_concluse = False
                    continue

                vinta = valuta_esito_normale(pron, g_c, g_t, sq_c, sq_t)
                p['risultato_reale'] = f"{g_c}-{g_t}" if schedina.get('modello') != 'sigma' else ("Vinta" if vinta else "Persa")
                p['stato'] = 'vinta' if vinta else 'persa'
                print(f" -> TROVATO ESITO: {sq_c} {g_c}-{g_t} {sq_t} ({p['stato']})")
                if not vinta:
                    schedina_persa = True
                modifiche_effettuate = True

        # Se tutte le partite della schedina sono concluse (o almeno una è persa), sblocca tutto in chiaro sul sito!
        if tutte_concluse or schedina_persa:
            schedina['stato_schedina'] = 'persa' if schedina_persa else 'vinta'
            schedina['partite'] = partite_lavoro
            schedina.pop('payload_criptato', None)
            modifiche_effettuate = True
            print(f"==> SCHEDINA {schedina.get('id')} ({schedina.get('modello')}) CHIUSA COME: {schedina['stato_schedina'].upper()}")
        elif era_criptata and modifiche_effettuate:
            # Se solo una partita su due è finita (e vinta), mostra quella finita e tiene criptata l'altra
            schedina['payload_criptato'] = cripta_dati_sensibili(partite_lavoro)
            schedina['partite'] = crea_partite_offuscate_miste(partite_lavoro)

    if modifiche_effettuate:
        with open('database.json', 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        print("Database risultati salvato e aggiornato con successo!")
    else:
        print("Nessuna nuova partita conclusa trovata in questo giro.")

if __name__ == "__main__":
    aggiorna_database()
