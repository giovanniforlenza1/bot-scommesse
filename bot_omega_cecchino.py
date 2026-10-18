import requests
import json
import os
import uuid
import html
import base64
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "chiave_default_sicurezza")
OMEGA_CHAT_ID = os.environ.get("OMEGA_CHAT_ID") or os.environ.get("CHAT_ID")

campionati = [
    'soccer_italy_serie_a', 'soccer_italy_serie_b', 'soccer_epl', 'soccer_efl_champ',
    'soccer_spain_la_liga', 'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league', 'soccer_uefa_nations_league'
]

MAPPA_BOOKMAKER_ITALIA = {
    "unibet": "Unibet / Eurobet", "leovegas": "LeoVegas / Eurobet", "casumo": "Eurobet",
    "bwin": "Sisal / Bwin", "betsson": "Sisal / Betsson", "nordicbet": "Sisal / GoldBet",
    "williamhill": "William Hill", "888sport": "888sport", "betway": "Betway",
    "marathonbet": "Snai / Bet365", "pinnacle": "Bet365 / Snai", "coolbet": "GoldBet / PlanetWin365",
    "suprabets": "PlanetWin365", "everygame": "Snai", "betonlineag": "Bet365",
    "coral": "Eurobet", "ladbrokes": "Sisal", "paddypower": "Betfair Sport", "skybet": "SkyBet / Sisal"
}

TRADUZIONI_NAZIONALI = {
    "Italy": "Italia", "France": "Francia", "Germany": "Germania", "Spain": "Spagna",
    "England": "Inghilterra", "Netherlands": "Olanda", "Belgium": "Belgio", "Portugal": "Portogallo",
    "Croatia": "Croazia", "Switzerland": "Svizzera", "Poland": "Polonia", "Denmark": "Danimarca",
    "Sweden": "Svezia", "Norway": "Norvegia", "Austria": "Austria", "Scotland": "Scozia",
    "Wales": "Galles", "Hungary": "Ungheria", "Turkey": "Turchia", "Albania": "Albania",
    "Serbia": "Serbia", "Kosovo": "Kosovo", "North Macedonia": "Macedonia del Nord"
}

TRADUZIONI_SQUADRE = {
    "Inter Milan": "Inter", "AC Milan": "Milan", "AS Roma": "Roma", "SSC Napoli": "Napoli",
    "SS Lazio": "Lazio", "Juventus FC": "Juventus", "Hellas Verona": "Verona", "Bologna FC": "Bologna",
    "Fiorentina": "Fiorentina", "Torino FC": "Torino", "Genoa CFC": "Genoa", "Empoli FC": "Empoli",
    "Udinese Calcio": "Udinese", "Venezia FC": "Venezia", "Parma Calcio 1913": "Parma", "Como 1907": "Como",
    "Manchester Utd": "Manchester United", "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham",
    "Newcastle Utd": "Newcastle", "Paris Saint Germain": "PSG", "Bayern Munich": "Bayern Monaco",
    "Bayer Leverkusen": "Bayer Leverkusen", "Real Betis": "Betis Siviglia", "Real Sociedad": "Real Sociedad",
    "Athletic Club": "Athletic Bilbao", "Wolverhampton Wanderers": "Wolverhampton"
}

def cripta_dati_sensibili(lista_partite):
    """SICUREZZA ANTI-F12: Cripta i dettagli delle partite in corso usando TELEGRAM_TOKEN come chiave segreta"""
    raw_bytes = json.dumps(lista_partite, ensure_ascii=False).encode('utf-8')
    key_hash = hashlib.sha256(TELEGRAM_TOKEN.encode('utf-8')).digest()
    xored = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(raw_bytes)])
    return base64.b64encode(xored).decode('ascii')

def crea_partite_offuscate_per_sito(lista_partite):
    """Mostra nel JSON pubblico solo segnaposto finché la partita non è terminata"""
    return [{
        'id_partita': 'protetto',
        'data': p.get('data', ''),
        'squadra_casa': '🔒 Operazione',
        'squadra_trasferta': 'Riservata VIP',
        'pronostico': 'Crittografia Attiva',
        'quota': p.get('quota', 1.0),
        'stato': 'in attesa',
        'risultato_reale': ''
    } for p in lista_partite]

def traduci_squadra(nome):
    nome_pulito = str(nome).strip()
    if nome_pulito in TRADUZIONI_NAZIONALI: return TRADUZIONI_NAZIONALI[nome_pulito]
    if nome_pulito in TRADUZIONI_SQUADRE: return TRADUZIONI_SQUADRE[nome_pulito]
    return nome_pulito.replace(" FC", "").replace(" AC", "").replace(" Calcio", "")

def formatta_nome_bookmaker(key_book, title_book):
    k = key_book.lower()
    for chiave, nome_ita in MAPPA_BOOKMAKER_ITALIA.items():
        if chiave in k or chiave in title_book.lower(): return nome_ita
    return title_book

 crediti_alert_inviato = False

def esegui_richiesta_api(url_template):
    global crediti_alert_inviato
    chiavi = [k.strip() for k in os.environ.get("ODDS_API_KEY", "").split(",") if k.strip()]
    if not chiavi: return None
    for idx, chiave in enumerate(chiavi):
        url = url_template.replace("API_KEY_SEGRETA", chiave)
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                # Punto 15: Alert Salvavita se l'ultima chiave API ha meno di 40 crediti rimasti
                rem = int(res.headers.get('x-requests-remaining', 500))
                if idx == len(chiavi) - 1 and rem < 40 and not crediti_alert_inviato:
                    crediti_alert_inviato = True
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={
                        "chat_id": OMEGA_CHAT_ID,
                        "text": f"⚠️ <b>AVVISO SISTEMA SBR</b>: Crediti API in esaurimento ({rem} rimasti sull'ultima chiave).",
                        "parse_mode": "HTML"
                    })
                return res.json()
        except: pass
    return None

def carica_database_analisi():
    if os.path.exists('database_analisi.json'):
        with open('database_analisi.json', 'r', encoding='utf-8') as f: return json.load(f)
    return None

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f: 
        json.dump(db, f, indent=4, ensure_ascii=False)

def calcola_cassa_e_circuit_breaker(db, modello_nome):
    """Punto 8: Circuit Breaker automatico in caso di drawdown settimanale >15% o 2 perse consecutive"""
    cassa = 200.0
    picco_massimo = 200.0
    ultime_due = []
    for s in db.get('schedine', []):
        if s.get('modello') == modello_nome and s.get('stato_schedina') in ['vinta', 'persa']:
            imp = float(s.get('importo', 10.0))
            rit = float(s.get('ritorno_potenziale', 0.0))
            if s['stato_schedina'] == 'vinta':
                cassa += (rit - imp)
                ultime_due.append('W')
            else:
                cassa -= imp
                ultime_due.append('L')
            if cassa > picco_massimo: picco_massimo = cassa
            
    drawdown = (picco_massimo - cassa) / picco_massimo if picco_massimo > 0 else 0.0
    freno = 1.0
    if drawdown >= 0.15: freno = 0.55 # Circuit Breaker attivo
    elif len(ultime_due) >= 2 and ultime_due[-2:] == ['L', 'L']: freno = 0.80
    return max(120.0, cassa), freno

def invia_messaggio_protezione():
    msg = (
        "<b>⚠️ AVVISO DAL SISTEMA: PROTEZIONE CASSA (CROLLO QUOTE)</b>\n\n"
        "L'Analista quantitativo aveva individuato partite con un potenziale vantaggio statistico. "
        "Tuttavia, al momento della verifica finale, i bookmaker hanno corretto i mercati abbassando le quote sotto la nostra soglia minima di valore.\n\n"
        "Il Modello Omega blocca le operazioni per proteggere il capitale."
    )
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": OMEGA_CHAT_ID, "text": msg, "parse_mode": "HTML"})

def esegui_cecchino():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    data_oggi_str = oggi.strftime("%d/%m/%Y")
    limite_temporale = oggi + timedelta(days=4)
    
    db_analisi = carica_database_analisi()
    if not db_analisi or not db_analisi.get('analisi'): return
    
    db_principale = carica_database_principale()
    
    for s in db_principale['schedine']:
        if s.get('modello') == 'omega' and s.get('data_creazione') == data_oggi_str:
            print("Omega Cecchino: Operazione già generata oggi.")
            return
    
    candidati_valore = []
    
    for camp in campionati:
        url_template = f"https://api.the-odds-api.com/v4/sports/{camp}/odds/?apiKey=API_KEY_SEGRETA&regions=eu,uk&markets=h2h"
        partite_live = esegui_richiesta_api(url_template)
        if not partite_live: continue
            
        for p_live in partite_live:
            data_ita = datetime.strptime(p_live['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(fuso_italia)
            if data_ita > limite_temporale or data_ita < oggi: continue

            nome_casa_ita = traduci_squadra(p_live['home_team'])
            nome_trasf_ita = traduci_squadra(p_live['away_team'])
            match_intero = f"{nome_casa_ita} - {nome_trasf_ita}"
            
            analisi_match = next((
                a for a in db_analisi['analisi'] 
                if a.get('id_partita') == p_live['id'] or a.get('match') == match_intero
            ), None)
            if not analisi_match: continue
            
            pronostico_richiesto = analisi_match['consiglio_algoritmo']
            quota_minima = analisi_match['quota_valore_minima']
            quota_equa = analisi_match.get('quota_equa', quota_minima)
            quota_apertura = analisi_match.get('quota_apertura_rif', quota_equa)
            prob_reale = analisi_match.get('probabilita_reale', 55.0) / 100.0
            
            tetto_massimo_reale = min(1.95, round(quota_equa * 1.18, 2))
            
            miglior_quota = 0.0
            quota_pinnacle_live = None
            book_vincente = ""
            
            for book in p_live.get('bookmakers', []):
                titolo_book = book.get('title', '')
                key_book = book.get('key', '').lower()
                if 'exchange' in titolo_book.lower() or 'betfair' in key_book or 'matchbook' in key_book or 'smarkets' in key_book:
                    continue
                
                for mercato in book.get('markets', []):
                    if mercato.get('key') != 'h2h': continue
                    for out in mercato.get('outcomes', []):
                        q_attuale = out.get('price', 0)
                        if q_attuale > tetto_massimo_reale: continue
                            
                        nome_esito_originale = out.get('name', '')
                        squadra_vincente_ita = pronostico_richiesto.lower().replace("vittoria ", "").strip()
                        nome_esito_ita = traduci_squadra(nome_esito_originale).lower()
                        
                        if squadra_vincente_ita == nome_esito_ita:
                            if 'pinnacle' in key_book: quota_pinnacle_live = q_attuale
                            if q_attuale > miglior_quota:
                                miglior_quota = q_attuale
                                book_vincente = formatta_nome_bookmaker(key_book, titolo_book)
                            
            if quota_minima <= miglior_quota <= tetto_massimo_reale:
                # Punto 10: Rilevamento Steam Move (crollo quota su Pinnacle > 5% ma bookmaker italiano in ritardo)
                steam_bonus = 0.05 if (quota_pinnacle_live and quota_pinnacle_live < quota_apertura * 0.95 and miglior_quota >= quota_apertura) else 0.0
                
                ev_reale = (prob_reale * miglior_quota) - 1.0 + steam_bonus
                indice_qualita = (ev_reale * 0.65) + (prob_reale * 0.35)
                
                candidati_valore.append({
                    'id_partita': p_live['id'],
                    'data': data_ita.strftime("%d/%m %H:%M"),
                    'squadra_casa': nome_casa_ita,
                    'squadra_trasferta': nome_trasf_ita,
                    'pronostico': pronostico_richiesto,
                    'quota': round(miglior_quota, 2),
                    'bookmaker': book_vincente,
                    'score': round(indice_qualita, 4),
                    'ev': round(ev_reale, 3),
                    'lega': camp,
                    'stato': 'in attesa',
                    'risultato_reale': ''
                })
                
    if not candidati_valore: 
        invia_messaggio_protezione()
        return
    
    ordinati = sorted(candidati_valore, key=lambda x: (0 if 'italy' in x['lega'] else 1, -x['score']))
    
    if ordinati[0]['quota'] >= 1.48:
        finalisti = [ordinati[0]]
        tipo_giocata = "Colpo Mirato in Singola ad Alta Probabilità."
        fattore_varianza_kelly = 1.0
    elif len(ordinati) >= 2:
        finalisti = [ordinati[0], ordinati[1]]
        tipo_giocata = "Doppia Quantitativa a Bassa Varianza."
        # Punto 9: Riduzione Kelly sulle doppie per compensare la varianza combinata
        fattore_varianza_kelly = 0.85
    else:
        finalisti = [ordinati[0]]
        tipo_giocata = "Colpo Mirato in Singola."
        fattore_varianza_kelly = 1.0
    
    q_temp = 1.0
    for f in finalisti: q_temp *= f['quota']
    quota_totale = round(q_temp, 2)
    
    if quota_totale < 1.38: 
        invia_messaggio_protezione()
        return
        
    cassa_omega, freno_rischio = calcola_cassa_e_circuit_breaker(db_principale, 'omega')
    ev_medio = sum(c['ev'] for c in finalisti) / len(finalisti)
    
    percentuale_cassa = min(0.10, max(0.06, 0.06 + (ev_medio * 0.45))) * freno_rischio * fattore_varianza_kelly
    stake_consigliato = round(cassa_omega * percentuale_cassa, 1)
    
    partite_reali = [{k: v for k, v in c.items() if k not in ['score', 'ev']} for c in finalisti]
    
    # Punto 7: Salva in locale gli ID usati da Omega oggi per evitare correlazione con Alpha
    with open('omega_oggi.json', 'w', encoding='utf-8') as fo:
        json.dump([c['id_partita'] for c in partite_reali], fo)

    # Sanitizzazione HTML contro Injection su Telegram
    msg = "<b>MODELLO OMEGA</b>\n\n"
    msg += f"<b>{html.escape(tipo_giocata)}</b>\n\n"
    msg += f"📊 <b>Quota totale</b>: {quota_totale}\n"
    msg += f"💰 <b>Stake Kelly</b>: {stake_consigliato}€\n\n"
    
    for c in partite_reali:
        c_casa = html.escape(c['squadra_casa'])
        c_trasf = html.escape(c['squadra_trasferta'])
        c_pron = html.escape(c['pronostico'].lower())
        c_book = html.escape(c['bookmaker'])
        msg += f"⚽ <b>{c['data']} | {c_casa} - {c_trasf}</b>\n"
        msg += f"🎯 <b>Giocata</b>: {c_pron} (@{c['quota']})\n"
        msg += f"🏦 <b>Bookmaker</b>: {c_book}\n\n"
        
    msg += "<b>#TradingSportivo #ValueBetting #ScommesseSportive</b>"
    
    res = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": OMEGA_CHAT_ID, "text": msg, "parse_mode": "HTML"})
    
    if res.status_code == 200:
        # SICUREZZA ZERO-KNOWLEDGE: Cripta i dettagli nel database finché non finisce la partita!
        db_principale['schedine'].append({
            'id': str(uuid.uuid4())[:8],
            'modello': 'omega',
            'data_creazione': data_oggi_str,
            'importo': stake_consigliato,
            'quota_totale': quota_totale,
            'ritorno_potenziale': round(stake_consigliato * quota_totale, 2),
            'stato_schedina': 'in attesa',
            'payload_criptato': cripta_dati_sensibili(partite_reali),
            'partite': crea_partite_offuscate_per_sito(partite_reali)
        })
        salva_database_principale(db_principale)

if __name__ == "__main__":
    esegui_cecchino()
