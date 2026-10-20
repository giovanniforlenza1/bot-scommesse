import requests
import json
import os
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
    "bayern": ["bayern", "bayern munich", "bayern monaco", "fc bayern munich"],
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
    parole = [w for w in n.split() if w not in stop_words and len(w) > 2]
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

    set1 = {w for w in c1.split() if len(w) >= 4}
    set2 = {w for w in c2.split() if len(w) >= 4}
    return bool(set1 and set2 and (set1 & set2))

def leggi_statistiche_ufficiali_beta(lega, event_id, comp_diretto):
    tot_corners, tot_cards = 0, 0
    trovato = False
    for t in comp_diretto.get('competitors', []):
        for stat in t.get('statistics', []):
            nome_stat = stat.get('name', '')
            val_str = str(stat.get('displayValue', '0')).strip()
            val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
            if nome_stat == 'wonCorners': tot_corners += val; trovato = True
            elif nome_stat in ['yellowCards', 'redCards']: tot_cards += val; trovato = True
    if trovato and (tot_corners > 0 or tot_cards > 0):
        return tot_corners, tot_cards

    url_summary = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/summary?event={event_id}"
    try:
        res = requests.get(url_summary, timeout=6)
        if res.status_code == 200:
            teams_box = res.json().get('boxscore', {}).get('teams', [])
            if teams_box:
                tot_corners, tot_cards = 0, 0
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
    return 9, 4

def scarica_dati_completi_espn():
    partite_espn = []
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    # Controlla gli ultimi 15 giorni usando un singolo range per lega (molto più veloce e completo!)
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
                for t in teams:
                    t_name = t.get('team', {}).get('displayName', '')
                    score_str = str(t.get('score', '0')).strip()
                    gol_val = int(float(score_str)) if score_str.isdigit() else 0
                    if t.get('homeAway') == 'home': casa_nome = t_name; gol_casa = gol_val
                    else: trasf_nome = t_name; gol_trasf = gol_val
                tot_corners, tot_cards = leggi_statistiche_ufficiali_beta(lega, ev.get('id'), comp)
                partite_espn.append({
                    'casa_orig': casa_nome, 'trasf_orig': trasf_nome,
                    'gol_casa': gol_casa, 'gol_trasf': gol_trasf,
                    'corners': tot_corners, 'cards': tot_cards
                })
        except:
            continue

    for circuito in ['atp', 'wta']:
        url_t = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{circuito}/scoreboard?dates={data_inizio}-{data_fine}&limit=300"
        try:
            res = requests.get(url_t, timeout=8)
            if res.status_code != 200: continue
            for ev in res.json().get('events', []):
                for grouping in ev.get('groupings', []):
                    for comp in grouping.get('competitions', []):
                        if not comp.get('status', {}).get('type', {}).get('completed', False): continue
                        competitors = comp.get('competitors', [])
                        if len(competitors) < 2: continue
                        p1_name = competitors[0].get('athlete', {}).get('displayName', '')
                        p2_name = competitors[1].get('athlete', {}).get('displayName', '')
                        w1 = competitors[0].get('winner', False)
                        w2 = competitors[1].get('winner', False)
                        if w1 or w2:
                            partite_espn.append({
                                'casa_orig': p1_name, 'trasf_orig': p2_name,
                                'gol_casa': 2 if w1 else 0, 'gol_trasf': 2 if w2 else 0,
                                'corners': None, 'cards': None
                            })
        except:
            continue

    print(f"[INFO] Partite concluse scaricate da ESPN (ultimi 15 giorni): {len(partite_espn)}")
    return partite_espn

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
    elif 'over 1.5' in pron_low: return (tot_gol >= 2)
    elif 'over 2.5' in pron_low: return (tot_gol >= 3)
    elif 'under 2.5' in pron_low: return (tot_gol <= 2)
    elif 'under 3.5' in pron_low: return (tot_gol <= 3)
    elif 'gol' in pron_low or 'gg' in pron_low: return (g_c > 0 and g_t > 0)
    return False

def aggiorna_database():
    if not os.path.exists('database.json'):
        print("[ERRORE] database.json non trovato!")
        return

    with open('database.json', 'r', encoding='utf-8') as f:
        db = json.load(f)

    # IMPORTANTE: The Odds API supporta al massimo daysFrom=3 (se metti 7 restituisce errore 422!)
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

    print(f"[INFO] Partite concluse scaricate da The Odds API (ultimi 3 giorni): {len(risultati_gol_odds)}")
    dati_espn = scarica_dati_completi_espn()
    modifiche_effettuate = False

    for idx, schedina in enumerate(db.get('schedine', [])):
        # 1. Se la schedina ha ancora payload_criptato, la decripta subito in chiaro!
        if schedina.get('payload_criptato'):
            dec = decripta_dati_sensibili(schedina.get('payload_criptato'))
            if dec:
                schedina['partite'] = dec
                schedina.pop('payload_criptato', None)
                modifiche_effettuate = True
                print(f"[DECRYPT] Sbloccata schedina criptata #{idx+1} ({schedina.get('modello')})")

        partite_lavoro = schedina.get('partite', [])
        tutte_concluse = True
        schedina_persa = False

        # 2. Controlla SEMPRE ogni singola partita che non abbia ancora il risultato_reale
        for p in partite_lavoro:
            sq_c = p.get('squadra_casa', '')
            sq_t = p.get('squadra_trasferta', '')
            stato_p = p.get('stato', 'in attesa')
            ris_attuale = str(p.get('risultato_reale', '')).strip()

            # Se è già vinta/persa E ha già il risultato scritto (es. "1-2"), passa oltre
            if stato_p in ['vinta', 'persa'] and ris_attuale != '':
                if stato_p == 'persa':
                    schedina_persa = True
                continue

            id_p = p.get('id_partita')
            pron = p.get('pronostico', '').lower()
            print(f"[CHECK] Cerco esito per: {sq_c} vs {sq_t} | Pronostico: {pron}")

            if 'angol' in pron or 'corner' in pron or 'cartellin' in pron:
                match_stat = next((
                    x for x in dati_espn 
                    if (squadre_combaciano(sq_c, x['casa_orig']) and squadre_combaciano(sq_t, x['trasf_orig'])) or
                       (squadre_combaciano(sq_c, x['trasf_orig']) and squadre_combaciano(sq_t, x['casa_orig']))
                ), None)
                if not match_stat:
                    print(f"   -> Non ancora conclusa o non trovata su ESPN: {sq_c} - {sq_t}")
                    tutte_concluse = False
                    continue

                if 'angol' in pron or 'corner' in pron:
                    totale = match_stat['corners'] if match_stat['corners'] is not None else 9
                    soglia = 9.5 if '9.5' in pron else 8.5
                    p['risultato_reale'] = f"{totale} Angoli"
                    p['stato'] = 'vinta' if totale > soglia else 'persa'
                else:
                    totale = match_stat['cards'] if match_stat['cards'] is not None else 4
                    soglia = 4.5 if '4.5' in pron else 3.5
                    p['risultato_reale'] = f"{totale} Cartellini"
                    p['stato'] = 'vinta' if totale > soglia else 'persa'

                if p['stato'] == 'persa':
                    schedina_persa = True
                modifiche_effettuate = True
                print(f"   -> AGGIORNATA BETA: {sq_c}-{sq_t} = {p['risultato_reale']} ({p['stato']})")
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

                if g_c is None:
                    print(f"   -> Non ancora conclusa: {sq_c} - {sq_t}")
                    tutte_concluse = False
                    continue

                vinta = valuta_esito_normale(pron, g_c, g_t, sq_c, sq_t)
                p['risultato_reale'] = f"{g_c}-{g_t}" if schedina.get('modello') != 'sigma' else ("Vinta" if vinta else "Persa")
                p['stato'] = 'vinta' if vinta else 'persa'
                if not vinta:
                    schedina_persa = True
                modifiche_effettuate = True
                print(f"   -> AGGIORNATA: {sq_c} {g_c}-{g_t} {sq_t} ({p['stato']})")

        # Ricalcola lo stato generale della schedina
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
