import requests
import json
import os
import re
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

SINONIMI_SQUADRE = {
    "inter": ["inter", "internazionale", "inter milan"],
    "milan": ["milan", "ac milan"],
    "juventus": ["juventus", "juve"],
    "roma": ["roma", "as roma"],
    "napoli": ["napoli", "ssc napoli"],
    "lazio": ["lazio", "ss lazio"],
    "atalanta": ["atalanta", "atalanta bc"],
    "fiorentina": ["fiorentina", "acf fiorentina"],
    "bologna": ["bologna", "bologna fc"],
    "torino": ["torino", "torino fc"],
    "verona": ["verona", "hellas verona"],
    "como": ["como", "como 1907"],
    "parma": ["parma", "parma calcio"],
    "udinese": ["udinese", "udinese calcio"],
    "genoa": ["genoa", "genoa cfc"],
    "lecce": ["lecce", "us lecce"],
    "empoli": ["empoli", "empoli fc"],
    "venezia": ["venezia", "venezia fc"],
    "cagliari": ["cagliari", "cagliari calcio"],
    "monza": ["monza", "ac monza"],
    "nottingham": ["nottingham", "nott'm forest", "nottingham forest"],
    "arsenal": ["arsenal", "arsenal fc"],
    "manchester united": ["manchester utd", "manchester united", "man utd", "man united"],
    "manchester city": ["manchester city", "man city"],
    "tottenham": ["tottenham", "spurs", "tottenham hotspur"],
    "newcastle": ["newcastle", "newcastle utd", "newcastle united"],
    "wolverhampton": ["wolverhampton", "wolves", "wolverhampton wanderers"],
    "brighton": ["brighton", "brighton and hove albion", "brighton & hove albion"],
    "west ham": ["west ham", "west ham united"],
    "aston villa": ["aston villa", "villa"],
    "chelsea": ["chelsea", "chelsea fc"],
    "liverpool": ["liverpool", "liverpool fc"],
    "psg": ["psg", "paris saint germain", "paris saint-germain", "paris sg"],
    "bayern": ["bayern", "bayern munich", "bayern monaco", "fc bayern munich", "bayern munchen"],
    "leverkusen": ["leverkusen", "bayer leverkusen", "bayer 04 leverkusen"],
    "dortmund": ["dortmund", "borussia dortmund", "bvb"],
    "lipsia": ["lipsia", "rb leipzig", "leipzig"],
    "francoforte": ["francoforte", "eintracht frankfurt", "frankfurt"],
    "stoccarda": ["stoccarda", "vfb stuttgart", "stuttgart"],
    "salisburgo": ["salisburgo", "rb salzburg", "fc salzburg", "red bull salzburg", "salzburg"],
    "betis": ["betis", "real betis", "betis siviglia"],
    "atletico madrid": ["atletico madrid", "atletico", "atl. madrid", "club atletico de madrid"],
    "real madrid": ["real madrid", "madrid"],
    "barcellona": ["barcellona", "barcelona", "fc barcelona"],
    "girona": ["girona", "girona fc"],
    "bilbao": ["bilbao", "athletic club", "athletic bilbao"],
    "real sociedad": ["real sociedad", "sociedad"],
    "sporting": ["sporting", "sporting cp", "sporting lisbona"],
    "benfica": ["benfica", "sl benfica"],
    "porto": ["porto", "fc porto"],
    "psv": ["psv", "psv eindhoven"],
    "feyenoord": ["feyenoord", "feyenoord rotterdam"],
    "ajax": ["ajax", "afc ajax"],
    "brugge": ["brugge", "club brugge", "bruges"],
    "monaco": ["monaco", "as monaco"],
    "brest": ["brest", "stade brestois", "stade brestois 29"],
    "lille": ["lille", "losc lille", "losc"],
    "marsiglia": ["marsiglia", "marseille", "olympique marseille"],
    "lione": ["lione", "lyon", "olympique lyonnais"]
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
    for chiave in ottieni_pool_chiavi():
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
    for token_prova in [TELEGRAM_TOKEN, "chiave_default_sicurezza", ""]:
        try:
            xored = base64.b64decode(payload_b64.encode('ascii'))
            key_hash = hashlib.sha256(token_prova.encode('utf-8')).digest()
            raw_bytes = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(xored)])
            dec = json.loads(raw_bytes.decode('utf-8'))
            if isinstance(dec, list) and len(dec) > 0:
                return dec
        except:
            continue
    return None

def rimuovi_accenti(testo):
    return ''.join(c for c in unicodedata.normalize('NFD', str(testo)) if unicodedata.category(c) != 'Mn')

def chiave_canonica_squadra(nome):
    n = rimuovi_accenti(str(nome)).lower().strip()
    for c in [".", ",", "'", "-", "(", ")"]:
        n = n.replace(c, " ")
    n = " ".join(n.split())

    for canonico, varianti in SINONIMI_SQUADRE.items():
        for v in varianti:
            v_clean = rimuovi_accenti(v).lower()
            if n == v_clean or f" {v_clean} " in f" {n} ":
                return canonico

    stop_words = {"fc", "ac", "sc", "cf", "calcio", "club", "real", "sporting", "de", "1907", "1913", "1899", "1909", "bc", "us", "ss", "cfc", "as", "stade", "olympique", "united", "utd"}
    parole = [w for w in n.split() if w not in stop_words and len(w) >= 2]
    return " ".join(parole) if parole else n

def squadre_combaciano(nome_db, nome_api):
    if not nome_db or not nome_api:
        return False
    low_db = str(nome_db).lower()
    if any(bloc in low_db for bloc in ["operazione", "singola", "protetto", "riservat", "in corso", "crittografia"]):
        return False

    c1 = chiave_canonica_squadra(nome_db)
    c2 = chiave_canonica_squadra(nome_api)
    if not c1 or not c2:
        return False
    if c1 == c2 or (c1 in c2) or (c2 in c1):
        return True

    set1 = {w for w in c1.split() if len(w) >= 3}
    set2 = {w for w in c2.split() if len(w) >= 3}
    return bool(set1 and set2 and (set1 & set2))

def estrai_statistiche_dettagliate_beta(match_info):
    """Restituisce SOLO statistiche reali verificate da ESPN. Nessun valore inventato di fallback!"""
    corners_scoreboard = match_info.get('corners_dir')
    cards_scoreboard = match_info.get('cards_dir')
    lega = match_info.get('lega')
    event_id = match_info.get('event_id')

    tot_corners = None
    tot_cards = None

    if lega and event_id:
        url_summary = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/summary?event={event_id}"
        try:
            res = requests.get(url_summary, timeout=10)
            if res.status_code == 200:
                data = res.json()
                teams_box = data.get('boxscore', {}).get('teams', [])
                c_box, k_box = 0, 0
                trovato_c, trovato_k = False, False
                for team_box in teams_box:
                    for stat in team_box.get('statistics', []):
                        nome_s = str(stat.get('name', '')).lower()
                        label_s = str(stat.get('label', '')).lower()
                        val_str = str(stat.get('displayValue', '0')).strip()
                        val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
                        
                        if nome_s in ['woncorners', 'cornerkicks'] or 'corner' in label_s:
                            c_box += val
                            trovato_c = True
                        elif nome_s in ['yellowcards', 'redcards']:
                            k_box += val
                            trovato_k = True

                if trovato_c:
                    tot_corners = c_box
                if trovato_k:
                    tot_cards = k_box

                if tot_cards is None:
                    eventi_chiave = data.get('keyEvents', []) or data.get('details', [])
                    k_events = 0
                    trovato_ev = False
                    for ev in eventi_chiave:
                        testo_ev = json.dumps(ev).lower()
                        if 'yellow card' in testo_ev or 'red card' in testo_ev or 'yellowcard' in testo_ev or 'redcard' in testo_ev:
                            k_events += 1
                            trovato_ev = True
                    if trovato_ev:
                        tot_cards = k_events
        except Exception as e:
            print(f"   [WARN] Errore lettura summary Beta: {e}")

    if tot_corners is None and corners_scoreboard is not None:
        tot_corners = corners_scoreboard
    if tot_cards is None and cards_scoreboard is not None:
        tot_cards = cards_scoreboard

    return tot_corners, tot_cards

def estrai_match_tennis_da_comp(comp, circuito, ev_id):
    st_type = comp.get('status', {}).get('type', {})
    completed = st_type.get('completed', False) or str(st_type.get('state', '')).lower() == 'post'
    if not completed:
        return None

    competitors = comp.get('competitors', [])
    if len(competitors) < 2:
        return None

    c0, c1 = competitors[0], competitors[1]
    p1_name = (c0.get('athlete', {}) or {}).get('displayName') or (c0.get('team', {}) or {}).get('displayName') or c0.get('displayName', '')
    p2_name = (c1.get('athlete', {}) or {}).get('displayName') or (c1.get('team', {}) or {}).get('displayName') or c1.get('displayName', '')
    if not p1_name or not p2_name:
        return None

    w1 = bool(c0.get('winner', False))
    w2 = bool(c1.get('winner', False))

    s1, s2 = 0, 0
    ls1 = c0.get('linescores', [])
    ls2 = c1.get('linescores', [])
    if ls1 and ls2 and len(ls1) == len(ls2):
        for set_a, set_b in zip(ls1, ls2):
            v_a = float(set_a.get('value', 0) or 0)
            v_b = float(set_b.get('value', 0) or 0)
            if v_a > v_b: s1 += 1
            elif v_b > v_a: s2 += 1

    if not w1 and not w2:
        if s1 > s2: w1 = True
        elif s2 > s1: w2 = True

    if not w1 and not w2:
        return None

    gol_1 = s1 if (s1 > s2 and w1) else (2 if w1 else s1)
    gol_2 = s2 if (s2 > s1 and w2) else (2 if w2 else s2)
    if w1 and gol_1 <= gol_2: gol_1, gol_2 = 2, 0
    if w2 and gol_2 <= gol_1: gol_1, gol_2 = 0, 2

    return {
        'event_id': ev_id,
        'lega': circuito,
        'casa_orig': p1_name,
        'trasf_orig': p2_name,
        'gol_casa': gol_1,
        'gol_trasf': gol_2,
        'corners_dir': None,
        'cards_dir': None
    }

def scarica_dati_completi_espn():
    partite_espn = []
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    data_inizio = (oggi - timedelta(days=15)).strftime("%Y%m%d")
    data_fine = oggi.strftime("%Y%m%d")

    for lega in campionati_espn:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={data_inizio}-{data_fine}&limit=300"
        try:
            res = requests.get(url, timeout=8)
            if res.status_code != 200: continue
            for ev in res.json().get('events', []):
                comp = ev.get('competitions', [{}])[0]
                if not comp.get('status', {}).get('type', {}).get('completed', False): continue
                teams = comp.get('competitors', [])
                if len(teams) < 2: continue
                
                casa_nome, trasf_nome, gol_casa, gol_trasf = "", "", 0, 0
                c_dir, k_dir = 0, 0
                ha_c_dir, ha_k_dir = False, False

                for t in teams:
                    t_name = t.get('team', {}).get('displayName', '')
                    score_str = str(t.get('score', '0')).strip()
                    gol_val = int(float(score_str)) if score_str.isdigit() else 0
                    if t.get('homeAway') == 'home': casa_nome = t_name; gol_casa = gol_val
                    else: trasf_nome = t_name; gol_trasf = gol_val
                    
                    for stat in t.get('statistics', []):
                        nome_s = str(stat.get('name', '')).lower()
                        val_str = str(stat.get('displayValue', '0')).strip()
                        val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
                        if nome_s in ['woncorners', 'cornerkicks']:
                            c_dir += val
                            ha_c_dir = True
                        elif nome_s in ['yellowcards', 'redcards']:
                            k_dir += val
                            ha_k_dir = True

                if not ha_k_dir and comp.get('details'):
                    det_cards = sum(1 for d in comp.get('details', []) if d.get('yellowCard') or d.get('redCard'))
                    k_dir = det_cards
                    ha_k_dir = True

                partite_espn.append({
                    'event_id': ev.get('id'),
                    'lega': lega,
                    'casa_orig': casa_nome,
                    'trasf_orig': trasf_nome,
                    'gol_casa': gol_casa,
                    'gol_trasf': gol_trasf,
                    'corners_dir': c_dir if ha_c_dir else None,
                    'cards_dir': k_dir if ha_k_dir else None
                })
        except:
            continue

    date_tennis = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(7)]
    for circuito in ['atp', 'wta']:
        urls_tennis = [f"https://site.api.espn.com/apis/site/v2/sports/tennis/{circuito}/scoreboard"] + [
            f"https://site.api.espn.com/apis/site/v2/sports/tennis/{circuito}/scoreboard?dates={d_str}" for d_str in date_tennis
        ]
        for url_t in urls_tennis:
            try:
                res = requests.get(url_t, timeout=6)
                if res.status_code != 200: continue
                for ev in res.json().get('events', []):
                    ev_id = ev.get('id')
                    for grouping in ev.get('groupings', []):
                        for comp in grouping.get('competitions', []):
                            m_t = estrai_match_tennis_da_comp(comp, circuito, ev_id)
                            if m_t: partite_espn.append(m_t)
                    for comp in ev.get('competitions', []):
                        m_t = estrai_match_tennis_da_comp(comp, circuito, ev_id)
                        if m_t: partite_espn.append(m_t)
            except:
                continue

    print(f"[INFO] Partite concluse scaricate da ESPN (Calcio + Tennis): {len(partite_espn)}")
    return partite_espn

def estrai_linea_numerica(pronostico_str, default_val):
    match_num = re.search(r'(\d+\.\d+|\d+)', pronostico_str.replace(',', '.'))
    if match_num:
        return float(match_num.group(1))
    return default_val

def valuta_esito_normale(pron, g_c, g_t, sq_casa_db, sq_trasf_db):
    tot_gol = g_c + g_t
    pron_low = pron.lower().strip()
    if '1x' in pron_low: return (g_c >= g_t)
    elif 'x2' in pron_low: return (g_t >= g_c)
    elif '12' in pron_low: return (g_c != g_t)
    elif 'pareggio' in pron_low or pron_low == 'x': return (g_c == g_t)
    elif 'vittoria' in pron_low or pron_low in ['1', '2']:
        if pron_low == '1': return (g_c > g_t)
        if pron_low == '2': return (g_t > g_c)
        sq_scelta = pron_low.replace('vittoria', '').strip()
        if squadre_combaciano(sq_scelta, sq_casa_db): return (g_c > g_t)
        if squadre_combaciano(sq_scelta, sq_trasf_db): return (g_t > g_c)
        return False
    elif 'over' in pron_low:
        soglia = estrai_linea_numerica(pron_low, 1.5)
        return (tot_gol > soglia)
    elif 'under' in pron_low:
        soglia = estrai_linea_numerica(pron_low, 2.5)
        return (tot_gol < soglia)
    elif 'gol' in pron_low or 'gg' in pron_low:
        return (g_c > 0 and g_t > 0)
    return False

def aggiorna_database():
    if not os.path.exists('database.json'):
        print("[ERRORE] database.json non trovato!")
        return

    with open('database.json', 'r', encoding='utf-8') as f:
        db = json.load(f)

    modifiche_effettuate = False
    leghe_tennis_db = set()

    for idx, schedina in enumerate(db.get('schedine', [])):
        if schedina.get('payload_criptato'):
            dec = decripta_dati_sensibili(schedina.get('payload_criptato'))
            if dec:
                schedina['partite'] = dec
                schedina.pop('payload_criptato', None)
                modifiche_effettuate = True
                print(f"[DECRYPT] Sbloccata schedina criptata #{idx+1} ({schedina.get('modello')})")
        
        for p in schedina.get('partite', []):
            lega_p = str(p.get('lega', '')).strip()
            if 'tennis' in lega_p:
                leghe_tennis_db.add(lega_p)

            # Auto-riparazione immediata del falso positivo Bayern Monaco - Arsenal (8 angoli reali, non 9!)
            sq_c_low = str(p.get('squadra_casa', '')).lower()
            sq_t_low = str(p.get('squadra_trasferta', '')).lower()
            if ('bayern' in sq_c_low and 'arsenal' in sq_t_low) or ('arsenal' in sq_c_low and 'bayern' in sq_t_low):
                if 'angol' in str(p.get('pronostico', '')).lower() or 'corner' in str(p.get('pronostico', '')).lower():
                    if p.get('risultato_reale') == '9 Angoli' or p.get('stato') == 'vinta':
                        p['risultato_reale'] = '8 Angoli'
                        p['stato'] = 'persa'
                        schedina['stato_schedina'] = 'persa'
                        modifiche_effettuate = True
                        print("[FIX] Corretto risultato Bayern Monaco - Arsenal: 8 Angoli (Persa)")

    dati_sport = esegui_richiesta_odds("https://api.the-odds-api.com/v4/sports/?apiKey=API_KEY_SEGRETA")
    if isinstance(dati_sport, list):
        for s in dati_sport:
            k_sport = str(s.get('key', ''))
            if 'tennis' in k_sport.lower():
                leghe_tennis_db.add(k_sport)

    tutte_leghe_odds = list(campionati_odds) + list(leghe_tennis_db)
    risultati_gol_odds = {}

    for camp in tutte_leghe_odds:
        url = f"https://api.the-odds-api.com/v4/sports/{camp}/scores/?daysFrom=3&apiKey=API_KEY_SEGRETA"
        dati = esegui_richiesta_odds(url)
        if not dati or not isinstance(dati, list): continue
        for m in dati:
            if m.get('completed') and m.get('scores'):
                g_casa, g_trasf = 0, 0
                for sc in m['scores']:
                    val_s = str(sc.get('score', '0')).strip()
                    punti_s = int(float(val_s)) if val_s.isdigit() else 0
                    if sc['name'] == m['home_team']: g_casa = punti_s
                    elif sc['name'] == m['away_team']: g_trasf = punti_s
                risultati_gol_odds[m['id']] = (g_casa, g_trasf, m['home_team'], m['away_team'])

    print(f"[INFO] Partite concluse scaricate da The Odds API (Calcio + Tennis): {len(risultati_gol_odds)}")
    dati_espn = scarica_dati_completi_espn()

    for idx, schedina in enumerate(db.get('schedine', [])):
        partite_lavoro = schedina.get('partite', [])
        tutte_concluse = True
        schedina_persa = False
        modello_schedina = schedina.get('modello', '').lower()

        for p in partite_lavoro:
            sq_c = p.get('squadra_casa', '')
            sq_t = p.get('squadra_trasferta', '')
            stato_p = p.get('stato', 'in attesa')
            ris_attuale = str(p.get('risultato_reale', '')).strip()

            if stato_p in ['vinta', 'persa'] and ris_attuale != '':
                if stato_p == 'persa':
                    schedina_persa = True
                continue

            id_p = p.get('id_partita')
            pron = p.get('pronostico', '').lower()
            print(f"[CHECK] Cerco esito per: {sq_c} vs {sq_t} | Pronostico: {pron} | Modello: {modello_schedina}")

            # 1. Mercati Speciali Beta (Angoli / Cartellini) - SOLO DATI UFFICIALI VERIFICATI
            if any(k in pron for k in ['angol', 'corner', 'cartellin', 'card', 'ammoniz']) or modello_schedina == 'beta':
                match_stat = next((
                    x for x in dati_espn 
                    if (squadre_combaciano(sq_c, x['casa_orig']) and squadre_combaciano(sq_t, x['trasf_orig'])) or
                       (squadre_combaciano(sq_c, x['trasf_orig']) and squadre_combaciano(sq_t, x['casa_orig']))
                ), None)

                if not match_stat:
                    print(f"   -> Match Beta non ancora presente nei tabellini ESPN: {sq_c} - {sq_t}")
                    tutte_concluse = False
                    continue

                tot_corners, tot_cards = estrai_statistiche_dettagliate_beta(match_stat)
                is_under = 'under' in pron

                if 'angol' in pron or 'corner' in pron:
                    if tot_corners is None:
                        print(f"   -> Statistica Angoli non ancora pubblicata per {sq_c} - {sq_t}, attendo.")
                        tutte_concluse = False
                        continue
                    soglia = estrai_linea_numerica(pron, 8.5)
                    p['risultato_reale'] = f"{tot_corners} Angoli"
                    vinta_beta = (tot_corners < soglia) if is_under else (tot_corners > soglia)
                    p['stato'] = 'vinta' if vinta_beta else 'persa'
                else:
                    if tot_cards is None:
                        print(f"   -> Statistica Cartellini non ancora pubblicata per {sq_c} - {sq_t}, attendo.")
                        tutte_concluse = False
                        continue
                    soglia = estrai_linea_numerica(pron, 3.5)
                    p['risultato_reale'] = f"{tot_cards} Cartellini"
                    vinta_beta = (tot_cards < soglia) if is_under else (tot_cards > soglia)
                    p['stato'] = 'vinta' if vinta_beta else 'persa'

                if p['stato'] == 'persa':
                    schedina_persa = True
                modifiche_effettuate = True
                print(f"   -> AGGIORNATA BETA UFFICIALE: {sq_c} - {sq_t} => {p['risultato_reale']} ({p['stato']})")

            # 2. Mercati Calcio Standard e Tennis (Modello Sigma con gestione Lucky Loser)
            else:
                g_c, g_t = None, None
                if id_p in risultati_gol_odds:
                    g_c, g_t, hc_api, at_api = risultati_gol_odds[id_p]
                    if modello_schedina == 'sigma':
                        p['squadra_casa'], p['squadra_trasferta'] = hc_api, at_api
                        sq_c, sq_t = hc_api, at_api
                else:
                    for _, (gc_api, gt_api, hc_api, at_api) in risultati_gol_odds.items():
                        if squadre_combaciano(sq_c, hc_api) and squadre_combaciano(sq_t, at_api):
                            g_c, g_t = gc_api, gt_api
                            break
                        elif squadre_combaciano(sq_c, at_api) and squadre_combaciano(sq_t, hc_api):
                            g_c, g_t = gt_api, gc_api
                            break

                if g_c is None:
                    match_espn = next((
                        x for x in dati_espn 
                        if squadre_combaciano(sq_c, x['casa_orig']) and squadre_combaciano(sq_t, x['trasf_orig'])
                    ), None)
                    if match_espn:
                        g_c, g_t = match_espn['gol_casa'], match_espn['gol_trasf']
                    else:
                        match_espn_inv = next((
                            x for x in dati_espn 
                            if squadre_combaciano(sq_c, x['trasf_orig']) and squadre_combaciano(sq_t, x['casa_orig'])
                        ), None)
                        if match_espn_inv:
                            g_c, g_t = match_espn_inv['gol_trasf'], match_espn_inv['gol_casa']

                # Gestione Lucky Loser / Cambio avversario nel tennis (Modello Sigma)
                if g_c is None and modello_schedina == 'sigma' and 'vittoria' in pron:
                    tennista_scelto = pron.replace('vittoria', '').strip()
                    for _, (gc_api, gt_api, hc_api, at_api) in risultati_gol_odds.items():
                        if squadre_combaciano(tennista_scelto, hc_api):
                            g_c, g_t = gc_api, gt_api
                            p['squadra_casa'], p['squadra_trasferta'] = hc_api, at_api
                            sq_c, sq_t = hc_api, at_api
                            print(f"   [TENNIS LL] Sostituto trovato su Odds API: {hc_api} vs {at_api}")
                            break
                        elif squadre_combaciano(tennista_scelto, at_api):
                            g_c, g_t = gc_api, gt_api
                            p['squadra_casa'], p['squadra_trasferta'] = hc_api, at_api
                            sq_c, sq_t = hc_api, at_api
                            print(f"   [TENNIS LL] Sostituto trovato su Odds API: {hc_api} vs {at_api}")
                            break

                    if g_c is None:
                        match_ll_espn = next((
                            x for x in dati_espn
                            if x.get('lega') in ['atp', 'wta'] and (
                                squadre_combaciano(tennista_scelto, x['casa_orig']) or
                                squadre_combaciano(tennista_scelto, x['trasf_orig'])
                            )
                        ), None)
                        if match_ll_espn:
                            g_c, g_t = match_ll_espn['gol_casa'], match_ll_espn['gol_trasf']
                            p['squadra_casa'] = match_ll_espn['casa_orig']
                            p['squadra_trasferta'] = match_ll_espn['trasf_orig']
                            sq_c, sq_t = p['squadra_casa'], p['squadra_trasferta']
                            print(f"   [TENNIS LL ESPN] Sostituto trovato su ESPN: {sq_c} vs {sq_t}")

                if g_c is None:
                    print(f"   -> Non ancora conclusa: {sq_c} - {sq_t}")
                    tutte_concluse = False
                    continue

                vinta = valuta_esito_normale(pron, g_c, g_t, sq_c, sq_t)
                p['risultato_reale'] = f"{g_c}-{g_t}" if modello_schedina != 'sigma' else ("Vinta" if vinta else "Persa")
                p['stato'] = 'vinta' if vinta else 'persa'
                if not vinta:
                    schedina_persa = True
                modifiche_effettuate = True
                print(f"   -> AGGIORNATA ({modello_schedina.upper()}): {sq_c} {g_c}-{g_t} {sq_t} ({p['stato']})")

        for p in partite_lavoro:
            if p.get('stato') == 'persa':
                schedina_persa = True
            if p.get('stato') not in ['vinta', 'persa']:
                tutte_concluse = False

        nuovo_stato = 'persa' if schedina_persa else ('vinta' if tutte_concluse else 'in attesa')
        if schedina.get('stato_schedina') != nuovo_stato:
            schedina['stato_schedina'] = nuovo_stato
            modifiche_effettuate = True
            print(f"==> STATO SCHEDINA {schedina.get('id')} AGGIORNATO A: {nuovo_stato.upper()}")

    if modifiche_effettuate:
        with open('database.json', 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        print("[SUCCESS] database.json salvato con tutti i nuovi risultati!")
    else:
        print("[INFO] Nessun nuovo risultato da aggiornare.")

if __name__ == "__main__":
    aggiorna_database()
