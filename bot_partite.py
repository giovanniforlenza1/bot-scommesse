import requests
from datetime import datetime, timedelta

# INSERISCI I TUOI DATI TRA LE VIRGOLETTE
TELEGRAM_TOKEN = "8981487141:AAFvKmVGm62wnENn-6uJZPedv0WMbp8ewr0"
CHAT_ID = "-1004229932372" 
ODDS_API_KEY = "8c17009a702111adb9f70dff1242a7c7"

def scarica_partite():
    # Lista delle competizioni da scansionare (Serie A e Nations League)
    campionati = ['soccer_italy_serie_a', 'soccer_uefa_nations_league']
    tutte_le_partite = []
    
    for campionato in campionati:
        url = f"https://api.the-odds-api.com/v4/sports/{campionato}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals"
        risposta = requests.get(url)
        if risposta.status_code == 200:
            tutte_le_partite.extend(risposta.json())
            
    return tutte_le_partite

def analizza_e_invia():
    partite = scarica_partite()
    oggi = datetime.now().date()
    domani = oggi + timedelta(days=1)
    
    partite_utili = []
    data_prima_partita = None

    for partita in partite:
        data_stringa = partita['commence_time'][:10]
        data_partita = datetime.strptime(data_stringa, "%Y-%m-%d").date()
        
        if oggi <= data_partita <= oggi + timedelta(days=3):
            partite_utili.append(partita)
            if data_prima_partita is None or data_partita < data_prima_partita:
                data_prima_partita = data_partita

    if not partite_utili:
        print("Nessuna partita utile trovata.")
        return

    messaggio = ""
    
    if data_prima_partita == domani:
        messaggio = "⏳ **IL MODELLO STA CALCOLANDO LE PROSSIME SFIDE**\n\n"
        messaggio += "I nostri algoritmi stanno analizzando le quote dei prossimi match. Domani alla stessa ora usciranno i pronostici ufficiali con il miglior rapporto rischio/rendimento.\n\n"
        messaggio += "#PronosticiCalcio #ScommesseSportive #SerieA #NationsLeague"
        
    elif data_prima_partita == oggi:
        messaggio = "🔥 **LE GIOCATE UFFICIALI DEL MATCH LAB**\n\n"
        partite_trovate = 0
        
        for partita in partite_utili:
            squadra_casa = partita['home_team']
            squadra_trasferta = partita['away_team']
            
            if partita.get('bookmakers'):
                mercati = partita['bookmakers'][0]['markets']
                quota_1 = 0
                quota_over = 0
                
                for mercato in mercati:
                    if mercato['key'] == 'h2h':
                        quota_1 = next((q['price'] for q in mercato['outcomes'] if q['name'] == squadra_casa), 0)
                    if mercato['key'] == 'totals':
                        quota_over = next((q['price'] for q in mercato['outcomes'] if q['name'] == 'Over' and q.get('point') == 2.5), 0)
                
                giocata_scelta = ""
                quota_scelta = 0
                
                if 1.50 <= quota_1 <= 1.90:
                    giocata_scelta = f"Vittoria {squadra_casa}"
                    quota_scelta = quota_1
                elif 1.50 <= quota_over <= 1.85:
                    giocata_scelta = "Over 2.5 Gol"
                    quota_scelta = quota_over
                    
                if giocata_scelta:
                    messaggio += f"⚽ **{squadra_casa} - {squadra_trasferta}**\n"
                    messaggio += f"🎯 Analisi: **{giocata_scelta}**\n"
                    messaggio += f"📈 Quota di valore: **{quota_scelta}**\n\n"
                    partite_trovate += 1
                    
        if partite_trovate > 0:
            messaggio += "#PronosticiCalcio #ScommesseSportive #SerieA #NationsLeague"
        else:
            messaggio = "Oggi nessuna quota ha superato il filtro matematico di sicurezza del modello."

    if messaggio:
        url_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url_telegram, json={"chat_id": CHAT_ID, "text": messaggio, "parse_mode": "Markdown"})
        print("Messaggio inviato!")

analizza_e_invia()
