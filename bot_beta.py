import requests
import json
import os
import uuid
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")

LEGHE_TARGET = [5, 34, 135, 39, 140, 78, 61, 2, 3]

TRADUZIONI_NAZIONALI = {
    "Italy": "Italia", "France": "Francia", "Germany": "Germania", 
    "Spain": "Spagna", "England": "Inghilterra", "Netherlands": "Olanda", 
    "Belgium": "Belgio", "Portugal": "Portogallo", "Croatia": "Croazia", 
    "Switzerland": "Svizzera", "Poland": "Polonia", "Denmark": "Danimarca",
    "Sweden": "Svezia", "Norway": "Norvegia", "Austria": "Austria",
    "Scotland": "Scozia", "Wales": "Galles", "Hungary": "Ungheria",
    "Turkey": "Turchia", "Albania": "Albania", "Serbia": "Serbia"
}

def traduci_squadra(nome_inglese):
    return TRADUZIONI_NAZIONALI.get(nome_inglese.strip(), nome_inglese.strip())

def carica_database():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f: 
            return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database(db):
    with open('database.json', 'w', encoding='utf-8') as f: 
        json.dump(db, f, indent=4, ensure_ascii=False)

def estrai_valore_stat(stats_array, tipo_stat):
    for s in stats_array:
        if s.get('type') == tipo_stat and s.get('value') is not None:
            if isinstance(s['value'], str) and '%' in s['value']:
                return float(s['value'].replace('%', ''))
            return float(s['value'])
    return 0.0

def analizza_trend_squadra(team_id, headers):
    """
    Scarica le ultime 3 partite giocate e calcola la media esatta di corner e cartellini.
    Limitato a 3 per non esaurire il piano gratuito di API-Football.
    """
    stats_medie = {'corner': 0.0, 'cartellini': 0.0}
    try:
        res_fix = requests.get(f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=3", headers=headers, timeout=10)
        fixtures = res_fix.json().get('response', [])
        
        tot_corner, tot_cartellini, match_validi = 0, 0, 0
        time.sleep(0.3) 
        
        for f in fixtures:
            fix_id = f['fixture']['id']
            res_stats = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fix_id}&team={team_id}", headers=headers, timeout=10)
            data_stats = res_stats.json().get('response', [])
            time.sleep(0.3)
            
            if not data_stats:
                continue
                
            stats = data_stats[0].get('statistics', [])
            corner = estrai_valore_stat(stats, 'Corner Kicks')
            gialli = estrai_valore_stat(stats, 'Yellow Cards')
            rossi = estrai_valore_stat(stats, 'Red Cards')
            
            tot_corner += corner
            tot_cartellini += (gialli + (rossi * 2)) # Un rosso pesa il doppio
            match_validi += 1
            
        if match_validi > 0:
            stats_medie['corner'] = round(tot_corner / match_validi, 2)
            stats_medie['cartellini'] = round(tot_cartellini / match_validi, 2)
            
    except Exception as e:
        pass
        
    return stats_medie

def genera_modello_predittivo():
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia).date()
    headers = {'x-apisports-key': API_FOOTBALL_KEY}
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Avvio Modello Beta Predittivo: Scansione trend...")
    
    # 1. Recupero le partite dei prossimi 2 giorni
    partite_candidabili = []
    for giorni_avanti in range(2):
        data_target = (oggi + timedelta(days=giorni_avanti)).strftime("%Y-%m-%d")
        url = f"https://v3.football.api-sports.io/fixtures?date={data_target}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                for match in res.json().get('response', []):
                    if match['league']['id'] in LEGHE_TARGET:
                        partite_candidabili.append(match)
        except:
            continue
            
    # 2. Limitiamo l'analisi a massimo 5 match per proteggere le chiamate API
    partite_candidabili = partite_candidabili[:5]
    print(f"Trovati {len(partite_candidabili)} match di cartello. Inizio analisi referti storici...")
    
    selezioni_giocabili = []
    
    for match in partite_candidabili:
        fix_data = match['fixture']
        match_date = datetime.strptime(fix_data['date'], "%Y-%m-%dT%H:%M:%S%z").astimezone(fuso_italia)
        
        home_id = match['teams']['home']['id']
        away_id = match['teams']['away']['id']
        home_name = traduci_squadra(match['teams']['home']['name'])
        away_name = traduci_squadra(match['teams']['away']['name'])
        
        print(f"Analisi in corso: {home_name} - {away_name}...")
        trend_home = analizza_trend_squadra(home_id, headers)
        trend_away = analizza_trend_squadra(away_id, headers)
        
        corner_totali_attesi = trend_home['corner'] + trend_away['corner']
        cartellini_totali_attesi = trend_home['cartellini'] + trend_away['cartellini']
        
        # LOGICA PREDITTIVA
        # Se le squadre superano i 10.5 corner di media combinata, andiamo sull'Over 8.5
        if corner_totali_attesi >= 10.5:
            selezioni_giocabili.append({
                'id_partita': fix_data['id'],
                'data': match_date.strftime("%d/%m %H:%M"),
                'squadra_casa': home_name,
                'squadra_trasferta': away_name,
                'pronostico': "Over 8.5 Calci d'Angolo",
                'quota_minima_consigliata': 1.45,
                'info_trend': f"Trend combinato: {round(corner_totali_attesi, 1)} corner a partita",
                'score': corner_totali_attesi
            })
        # Altrimenti, se sono squadre fallose/nervose (media cartellini combinata > 5.5)
        elif cartellini_totali_attesi >= 5.5:
            selezioni_giocabili.append({
                'id_partita': fix_data['id'],
                'data': match_date.strftime("%d/%m %H:%M"),
                'squadra_casa': home_name,
                'squadra_trasferta': away_name,
                'pronostico': "Over 3.5 Cartellini Totali",
                'quota_minima_consigliata': 1.50,
                'info_trend': f"Trend nervosismo: {round(cartellini_totali_attesi, 1)} cartellini a partita",
                'score': cartellini_totali_attesi
            })

    if not selezioni_giocabili:
        msg_err = f"⚠️ **SBR ALERT - MODELLO BETA**\n\nL'analisi dei trend storici su Corner e Cartellini non ha evidenziato anomalie statistiche sfruttabili oggi. Conserviamo la cassa."
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg_err, "parse_mode": "Markdown"})
        return
        
    # Ordiniamo per score (i trend più aggressivi) e prendiamo le top 3
    finalisti = sorted(selezioni_giocabili, key=lambda x: x['score'], reverse=True)[:3]
    
    # Costruiamo il messaggio SEO Social
    msg = f"📊 **MODELLO BETA: TREND SPECIAL BETS**\n\n"
    msg += "Il nostro motore ha analizzato i referti arbitrali delle ultime gare, calcolando l'aggressività e le tendenze di gioco per prevedere i mercati secondari.\n\n"
    msg += "⚠️ *Non essendoci quote stabili pre-match, gioca questa selezione solo se il tuo bookmaker offre una quota pari o superiore a quella indicata.*\n\n"
    
    quota_combinata = 1.0
    for c in finalisti:
        msg += f"⚽ **{c['data']} | {c['squadra_casa']} - {c['squadra_trasferta']}**\n"
        msg += f"🎯 **Giocata:** {c['pronostico']}\n"
        msg += f"📈 **Dato Reale:** {c['info_trend']}\n"
        msg += f"💰 **Gioca solo se a quota > {c['quota_minima_consigliata']}**\n\n"
        quota_combinata *= c['quota_minima_consigliata']
        
    msg += f"💡 **Moltiplicatore potenziale minimo:** @{round(quota_combinata, 2)}\n\n"
    msg += "**#SBR #PronosticiCalcio #CornerBetting #StatisticheCalcio #SportTrading**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    print("Modello Beta eseguito. Messaggio Telegram inviato con i trend statistici.")

if __name__ == "__main__":
    genera_modello_predittivo()
