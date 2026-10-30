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
    'ita.1', 'ita.2', 'eng.1', 'eng.2', 'esp.1', 'esp.2',
    'ger.1', 'ger.2', 'fra.1', 'fra.2', 'ned.1', 'por.1',
    'ita.coppa_italia', 'eng.fa', 'eng.league_cup', 'esp.copa_del_rey', 'ger.dfb_pokal', 'fra.coupe_de_france'
]

SINONIMI_SQUADRE = {
    "inter": ["inter", "internazionale", "inter milan", "fc internazionale"],
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
    "parma": ["parma", "parma calcio", "parma calcio 1913"],
    "udinese": ["udinese", "udinese calcio"],
    "genoa": ["genoa", "genoa cfc"],
    "lecce": ["lecce", "us lecce"],
    "empoli": ["empoli", "empoli fc"],
    "venezia": ["venezia", "venezia fc"],
    "cagliari": ["cagliari", "cagliari calcio"],
    "monza": ["monza", "ac monza"],
    "nottingham": ["nottingham", "nott'm forest", "nottingham forest", "nottm forest"],
    "arsenal": ["arsenal", "arsenal fc"],
    "manchester united": ["manchester utd", "manchester united", "man utd", "man united"],
    "manchester city": ["manchester city", "man city"],
    "tottenham": ["tottenham", "spurs", "tottenham hotspur"],
    "newcastle": ["newcastle", "newcastle utd", "newcastle united"],
    "wolverhampton": ["wolverhampton", "wolves", "wolverhampton wanderers"],
    "brighton": ["brighton", "brighton and hove albion", "brighton & hove albion", "brighton hove albion"],
    "west ham": ["west ham", "west ham united", "west ham utd"],
    "aston villa": ["aston villa", "villa"],
    "chelsea": ["chelsea", "chelsea fc"],
    "liverpool": ["liverpool", "liverpool fc"],
    "psg": ["psg", "paris saint germain", "paris saint-germain", "paris sg"],
    "bayern": ["bayern", "bayern munich", "bayern monaco", "fc bayern munich", "bayern munchen", "fc bayern munchen"],
    "leverkusen": ["leverkusen", "bayer leverkusen", "bayer 04 leverkusen"],
    "dortmund": ["dortmund", "borussia dortmund", "bvb"],
    "lipsia": ["lipsia", "rb leipzig", "leipzig", "rasenballsport leipzig"],
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
    for c in [".", ",", "'", "-", "(", ")", "&", "/"]:
        n = n.replace(c, " ")
    n = " ".join(n.split())

    for canonico, varianti in SINONIMI_SQUADRE.items():
        for v in varianti:
            v_clean = rimuovi_accenti(v).lower()
            for c in [".", ",", "'", "-"]:
                v_clean = v_clean.replace(c, " ")
            v_clean = " ".join(v_clean.split())
            if n == v_clean or f" {v_clean} " in f" {n} ":
                return canonico

    stop_words = {"fc", "ac", "sc", "cf", "calcio", "club", "real", "sporting", "de", "1907", "1913", "1899", "1909", "04", "05", "bc", "us", "ss", "cfc", "as", "stade", "olympique", "united", "utd", "afc", "rcd", "rc", "ud", "cd", "vfb", "vfl", "tsg", "fsv", "sv"}
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

def estrai_cognome_tennista(nome_completo):
    pulito = rimuovi_accenti(str(nome_completo)).lower()
    pulito = re.sub(r'\(.*?\)', ' ', pulito)
    for c in [".", ",", "-", "'"]:
        pulito = pulito.replace(c, " ")
    parti = [p for p in pulito.split() if len(p) >= 1]
    if not parti:
        return "", ""
    if len(parti) == 1:
        return parti[0], ""
    if len(parti[-1]) == 1 and len(parti[0]) > 1:
        return parti[0], parti[-1]
    return parti[-1], parti[0][0]

def tennisti_combaciano(nome_a, nome_b):
    if not nome_a or not nome_b:
        return False
    na_norm = " ".join(rimuovi_accenti(str(nome_a)).lower().split())
    nb_norm = " ".join(rimuovi_accenti(str(nome_b)).lower().split())
    if na_norm == nb_norm:
        return True

    cog_a, ini_a = estrai_cognome_tennista(nome_a)
    cog_b, ini_b = estrai_cognome_tennista(nome_b)
    if not cog_a or not cog_b or len(cog_a) < 2 or len(cog_b) < 2:
        return False
    if cog_a != cog_b:
        return False
    if ini_a and ini_b and ini_a != ini_b:
        return False
    return True

def fallback_thesportsdb_beta(sq_casa, sq_trasf):
    try:
        q = f"{chiave_canonica_squadra(sq_casa)}_vs_{chiave_canonica_squadra(sq_trasf)}".replace(" ", "_")
        url = f"https://www.thesportsdb.com/api/v1/json/3/searchevents.php?e={q}"
        res = requests.get(url, timeout=8)
        if res.status_code != 200:
            return None, None
        events = res.json().get('event') or []
        for ev in events[:3]:
            id_ev = ev.get('idEvent')
            if not id_ev or ev.get('intHomeScore') is None:
                continue
            r_stat = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/lookupeventstats.php?id={id_ev}", timeout=8)
            if r_stat.status_code == 200:
                stats = r_stat.json().get('eventstats') or []
                c_tot, k_tot = None, 0
                ha_k = False
                for st in stats:
                    nome_st = str(st.get('strStat', '')).lower()
                    vh = int(st.get('intHome') or 0)
                    va = int(st.get('intAway') or 0)
                    if 'corner' in nome_st:
                        c_tot = vh + va
                    elif 'yellow' in nome_st or 'red' in nome_st:
                        k_tot += (vh + va)
                        ha_k = True
                return c_tot, (k_tot if ha_k else None)
    except:
        pass
    return None, None

def estrai_statistiche_dettagliate_beta(match_info, sq_c_db="", sq_t_db=""):
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
                ha_statistiche_complete = False

                for team_box in teams_box:
                    stats_list = team_box.get('statistics', [])
                    if len(stats_list) >= 3:
                        ha_statistiche_complete = True
                    for stat in stats_list:
                        nome_s = str(stat.get('name', '')).lower()
                        label_s = str(stat.get('label', '')).lower()
                        abbr_s = str(stat.get('abbreviation', '')).lower()
                        val_str = str(stat.get('displayValue', '0')).strip()
                        val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0

                        if nome_s in ['woncorners', 'cornerkicks', 'corners'] or 'corner' in label_s or 'angolo' in label_s:
                            c_box += val
                            trovato_c = True
                        elif nome_s in ['yellowcards', 'redcards'] or label_s in ['yellow cards', 'red cards'] or abbr_s in ['yc', 'rc']:
                            k_box += val
                            trovato_k = True

                if trovato_c:
                    tot_corners = c_box
                if trovato_k:
                    tot_cards = k_box

                header_comps = data.get('header', {}).get('competitions', [])
                if header_comps:
                    h_comp = header_comps[0]
                    if tot_corners is None or tot_cards is None:
                        c_hdr, k_hdr = 0, 0
                        tr_ch, tr_kh = False, False
                        for comp_t in h_comp.get('competitors', []):
                            for stat in comp_t.get('statistics', []):
                                nome_s = str(stat.get('name', '')).lower()
                                val_str = str(stat.get('displayValue', '0')).strip()
                                val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
                                if 'corner' in nome_s:
                                    c_hdr += val
                                    tr_ch = True
                                elif 'yellow' in nome_s or 'red' in nome_s:
                                    k_hdr += val
                                    tr_kh = True
                        if tot_corners is None and tr_ch:
                            tot_corners = c_hdr
                        if tot_cards is None and tr_kh:
                            tot_cards = k_hdr

                    if tot_cards is None and h_comp.get('details') is not None:
                        k_det = 0
                        for d in h_comp.get('details', []):
                            tipo_d = str(d.get('type', {}).get('text', '')).lower()
                            if d.get('yellowCard') or d.get('redCard') or 'yellow' in tipo_d or 'red card' in tipo_d:
                                k_det += 1
                        if k_det > 0 or ha_statistiche_complete:
                            tot_cards = k_det

                if tot_cards is None:
                    eventi_chiave = data.get('keyEvents') or data.get('details')
                    if isinstance(eventi_chiave, list) and (len(eventi_chiave) > 0 or ha_statistiche_complete):
                        k_events = 0
                        for ev in eventi_chiave:
                            tipo_txt = str(ev.get('type', {}).get('text', '')).lower()
                            if ev.get('yellowCard') or ev.get('redCard') or 'yellow card' in tipo_txt or 'red card' in tipo_txt or 'second yellow' in tipo_txt:
                                k_events += 1
                        tot_cards = k_events
        except Exception as e:
            print(f"   [WARN] Errore lettura summary Beta: {e}")

    if tot_corners is None and corners_scoreboard is not None:
        tot_corners = corners_scoreboard
    if tot_cards is None and cards_scoreboard is not None:
        tot_cards = cards_scoreboard

    if (tot_corners is None or tot_cards is None) and sq_c_db and sq_t_db:
        c_tsdb, k_tsdb = fallback_thesportsdb_beta(sq_c_db, sq_t_db)
        if tot_corners is None and c_tsdb is not None:
            tot_corners = c_tsdb
        if tot_cards is None and k_tsdb is not None:
            tot_cards = k_tsdb

    return tot_corners, tot_cards

def estrai_match_tennis_da_comp(comp, circuito, ev_id):
    st_type = comp.get('status', {}).get('type', {})
    desc_stato = str(st_type.get('description', '')).lower()
    detail_stato = str(st_type.get('detail', '')).lower()
    completed = st_type.get('completed', False) or str(st_type.get('state', '')).lower() == 'post'
    
    if 'walkover' in desc_stato or 'canceled' in desc_stato or 'cancelled' in desc_stato:
        return None
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
    g1_tot, g2_tot = 0, 0
    ls1 = c0.get('linescores', [])
    ls2 = c1.get('linescores', [])
    if ls1 and ls2 and len(ls1) == len(ls2):
        for set_a, set_b in zip(ls1, ls2):
            v_a = float(set_a.get('value', 0) or 0)
            v_b = float(set_b.get('value', 0) or 0)
            g1_tot += v_a
            g2_tot += v_b
            if v_a >= 6 and v_a > v_b: s1 += 1
            elif v_b >= 6 and v_b > v_a: s2 += 1

    is_ritiro = ('ret' in desc_stato or 'ret' in detail_stato)
    if not w1 and not w2:
        if s1 > s2 and not is_ritiro: w1 = True
        elif s2 > s1 and not is_ritiro: w2 = True
        elif is_ritiro:
            if g1_tot > g2_tot: w1 = True
            elif g2_tot > g1_tot: w2 = True

    if not w1 and not w2:
        return None

    return {
        'event_id': ev_id,
        'lega': circuito,
        'casa_orig': p1_name,
        'trasf_orig': p2_name,
        'gol_casa': 2 if w1 else 0,
        'gol_trasf': 2 if w2 else 0,
        'ritiro': is_ritiro,
        'corners_dir': None,
        'cards_dir': None
    }

def scarica_dati_completi_espn():
    partite_espn = []
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    date_calcio = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(12)]

    for lega in campionati_espn:
        for d_str in date_calcio:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={d_str}"
            try:
                res = requests.get(url, timeout=5)
                if res.status_code != 200: continue
                for ev in res.json().get('events', []):
                    comp = ev.get('competitions', [{}])[0]
                    st_type = comp.get('status', {}).get('type', {})
                    completed = st_type.get('completed', False) or str(st_type.get('state', '')).lower() == 'post'
                    if not completed: continue
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
                            if nome_s in ['woncorners', 'cornerkicks', 'corners']:
                                c_dir += val
                                ha_c_dir = True
                            elif nome_s in ['yellowcards', 'redcards']:
                                k_dir += val
                                ha_k_dir = True

                    if not ha_k_dir and comp.get('details') is not None and len(comp.get('details', [])) > 0:
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

    date_tennis = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(8)]
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

def valuta_esito_normale(pron, g_c, g_t, sq_casa_db, sq_trasf_db, is_tennis=False):
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
        if is_tennis:
            if tennisti_combaciano(sq_scelta, sq_casa_db): return (g_c > g_t)
            if tennisti_combaciano(sq_scelta, sq_trasf_db): return (g_t > g_c)
            return False
        else:
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

def ripara_errori_storici_noti(db):
    riparato = False
    for schedina in db.get('schedine', []):
        for p in schedina.get('partite', []):
            sq_c_low = str(p.get('squadra_casa', '')).lower()
            sq_t_low = str(p.get('squadra_trasferta', '')).lower()
            pron_low = str(p.get('pronostico', '')).lower()

            if 'vacherot' in pron_low and ('royer' in sq_t_low or 'tabur' in sq_c_low or p.get('stato') == 'persa'):
                if schedina.get('data_creazione') == '26/10/2026' or '26/10' in str(p.get('data', '')):
                    p['squadra_casa'] = 'Valentin Vacherot'
                    p['squadra_trasferta'] = 'Mariano Navone'
                    p['risultato_reale'] = 'Vinta'
                    p['stato'] = 'vinta'
                    schedina['stato_schedina'] = 'vinta'
                    riparato = True

            if 'rybakina' in pron_low and 'kudermetova' in sq_t_low and p.get('stato') == 'persa':
                p['risultato_reale'] = 'Vinta (Rit.)'
                p['stato'] = 'vinta'
                schedina['stato_schedina'] = 'vinta'
                riparato = True

            if ('bayern' in sq_c_low and 'arsenal' in sq_t_low) or ('arsenal' in sq_c_low and 'bayern' in sq_t_low):
                if 'angol' in pron_low or 'corner' in pron_low:
                    if p.get('risultato_reale') == '9 Angoli' or p.get('stato') == 'vinta':
                        p['risultato_reale'] = '8 Angoli'
                        p['stato'] = 'persa'
                        schedina['stato_schedina'] = 'persa'
                        riparato = True
    return riparato

def aggiorna_database():
    if not os.path.exists('database.json'):
        print("[ERRORE] database.json non trovato!")
        return

    with open('database.json', 'r', encoding='utf-8') as f:
        db = json.load(f)

    modifiche_effettuate = ripara_errori_storici_noti(db)

    for idx, schedina in enumerate(db.get('schedine', [])):
        if schedina.get('payload_criptato'):
            dec = decripta_dati_sensibili(schedina.get('payload_criptato'))
            if dec:
                schedina['partite'] = dec
                schedina.pop('payload_criptato', None)
                modifiche_effettuate = True

    risultati_gol_odds = {}
    for camp in campionati_odds:
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
            is_tennis = (modello_schedina == 'sigma' or 'tennis' in str(p.get('lega', '')).lower())

            # 1. Mercati Speciali Beta (Angoli / Cartellini)
            if not is_tennis and (any(k in pron for k in ['angol', 'corner', 'cartellin', 'card', 'ammoniz']) or modello_schedina == 'beta'):
                match_stat = next((
                    x for x in dati_espn 
                    if x.get('lega') not in ['atp', 'wta'] and (
                        (squadre_combaciano(sq_c, x['casa_orig']) and squadre_combaciano(sq_t, x['trasf_orig'])) or
                        (squadre_combaciano(sq_c, x['trasf_orig']) and squadre_combaciano(sq_t, x['casa_orig']))
                    )
                ), None)

                conclusa_altrove = (id_p in risultati_gol_odds)
                if not match_stat and not conclusa_altrove:
                    tutte_concluse = False
                    continue

                if match_stat:
                    tot_corners, tot_cards = estrai_statistiche_dettagliate_beta(match_stat, sq_c, sq_t)
                else:
                    tot_corners, tot_cards = fallback_thesportsdb_beta(sq_c, sq_t)

                is_under = 'under' in pron

                if 'angol' in pron or 'corner' in pron:
                    if tot_corners is None:
                        tutte_concluse = False
                        continue
                    soglia = estrai_linea_numerica(pron, 8.5)
                    p['risultato_reale'] = f"{tot_corners} Angoli"
                    vinta_beta = (tot_corners < soglia) if is_under else (tot_corners > soglia)
                    p['stato'] = 'vinta' if vinta_beta else 'persa'
                else:
                    if tot_cards is None:
                        tutte_concluse = False
                        continue
                    soglia = estrai_linea_numerica(pron, 3.5)
                    p['risultato_reale'] = f"{tot_cards} Cartellini"
                    vinta_beta = (tot_cards < soglia) if is_under else (tot_cards > soglia)
                    p['stato'] = 'vinta' if vinta_beta else 'persa'

                if p['stato'] == 'persa':
                    schedina_persa = True
                modifiche_effettuate = True

            # 2. TENNIS (Modello Sigma)
            elif is_tennis:
                match_tennis = next((
                    x for x in dati_espn
                    if x.get('lega') in ['atp', 'wta'] and (
                        (tennisti_combaciano(sq_c, x['casa_orig']) and tennisti_combaciano(sq_t, x['trasf_orig'])) or
                        (tennisti_combaciano(sq_c, x['trasf_orig']) and tennisti_combaciano(sq_t, x['casa_orig']))
                    )
                ), None)

                g_c, g_t = None, None
                if match_tennis:
                    if tennisti_combaciano(sq_c, match_tennis['casa_orig']):
                        g_c, g_t = match_tennis['gol_casa'], match_tennis['gol_trasf']
                    else:
                        g_c, g_t = match_tennis['gol_trasf'], match_tennis['gol_casa']

                if g_c is None and 'vittoria' in pron:
                    tennista_scelto = pron.replace('vittoria', '').strip()
                    candidati_ll = [
                        x for x in dati_espn
                        if x.get('lega') in ['atp', 'wta'] and (
                            tennisti_combaciano(tennista_scelto, x['casa_orig']) or
                            tennisti_combaciano(tennista_scelto, x['trasf_orig'])
                        )
                    ]
                    if len(candidati_ll) == 1:
                        m_ll = candidati_ll[0]
                        g_c, g_t = m_ll['gol_casa'], m_ll['gol_trasf']
                        p['squadra_casa'] = m_ll['casa_orig']
                        p['squadra_trasferta'] = m_ll['trasf_orig']
                        sq_c, sq_t = p['squadra_casa'], p['squadra_trasferta']

                if g_c is None:
                    tutte_concluse = False
                    continue

                vinta = valuta_esito_normale(pron, g_c, g_t, sq_c, sq_t, is_tennis=True)
                p['risultato_reale'] = "Vinta" if vinta else "Persa"
                p['stato'] = 'vinta' if vinta else 'persa'
                if not vinta:
                    schedina_persa = True
                modifiche_effettuate = True

            # 3. Mercati Calcio Standard (Omega / Alpha)
            else:
                g_c, g_t = None, None
                if id_p in risultati_gol_odds:
                    g_c, g_t, _, _ = risultati_gol_odds[id_p]
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
                        if x.get('lega') not in ['atp', 'wta'] and squadre_combaciano(sq_c, x['casa_orig']) and squadre_combaciano(sq_t, x['trasf_orig'])
                    ), None)
                    if match_espn:
                        g_c, g_t = match_espn['gol_casa'], match_espn['gol_trasf']
                    else:
                        match_espn_inv = next((
                            x for x in dati_espn 
                            if x.get('lega') not in ['atp', 'wta'] and squadre_combaciano(sq_c, x['trasf_orig']) and squadre_combaciano(sq_t, x['casa_orig'])
                        ), None)
                        if match_espn_inv:
                            g_c, g_t = match_espn_inv['gol_trasf'], match_espn_inv['gol_casa']

                if g_c is None:
                    tutte_concluse = False
                    continue

                vinta = valuta_esito_normale(pron, g_c, g_t, sq_c, sq_t, is_tennis=False)
                p['risultato_reale'] = f"{g_c}-{g_t}"
                p['stato'] = 'vinta' if vinta else 'persa'
                if not vinta:
                    schedina_persa = True
                modifiche_effettuate = True

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
        print("[SUCCESS] database.json salvato e aggiornato con successo!")
    else:
        print("[INFO] Nessuna modifica.")

if __name__ == "__main__":
    aggiorna_database()
