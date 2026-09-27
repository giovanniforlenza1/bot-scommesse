import requests
from datetime import datetime, timedelta

# INSERISCI I TUOI DATI TRA LE VIRGOLETTE
TELEGRAM_TOKEN = "8981487141:AAFvKmVGm62wnENn-6uJZPedv0WMbp8ewr0"
CHAT_ID = "-1004229932372" 
ODDS_API_KEY = "8c17009a702111adb9f70dff1242a7c7"

def scarica_partite():
    # scarichiamo le quote principali (1x2) e i totali (over/under)
    url = f"https://api.the-odds-api.com/v4/sports/soccer_italy_serie_a/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals"
    risposta = requests.get(url)
    return risposta.json()

def analizza_e_invia():
    partite = scarica_partite()
    oggi = datetime.now().date()
    domani = oggi + timedelta(days=1)
    
    partite_utili = []
    data_prima_partita = None

    # analizziamo solo le partite dei prossimi 3 giorni per evitare accavallamenti
    for partita in partite:
        data_stringa = partita['commence_time'][:10]
        data_partita = datetime.strptime(data_stringa, "%Y-%m-%d").date()
        
        if oggi <= data_partita <= oggi + timedelta(days=3):
            partite_utili.append(partita)
            if data_prima_partita is None or data_partita < data_prima_partita:
                data_prima_partita = data_partita

    if not partite_utili:
        print("nessuna partita in programma a breve.")
        return

    # gestiamo la logica del messaggio: teaser il giorno prima, pronostici il giorno stesso
    messaggio = ""
    
    if data_prima_partita == domani:
        messaggio = "⏳ **PREPARATEVI PER LA NUOVA GIORNATA**\n\n"
        messaggio += "I nostri algoritmi stanno elaborando i dati. Domani alla stessa ora usciranno i pronostici ufficiali e le migliori quote studiate dal modello matematico.\n\n"
        messaggio += "#SerieA #Pronostici #ScommesseSportive #Betting"
        
    elif data_prima_partita == oggi:
        messaggio = "🔥 **LE GIOCATE UFFICIALI DEL MODELLO**\n\n"
        partite_trovate = 0
        
        for partita in partite_utili:
            squadra_casa = partita['home_team']
            squadra_trasferta = partita['away_team']
            
            if partita.get('bookmakers'):
                mercati = partita['bookmakers'][0]['markets']
                quota_1 = 0
                quota_over = 0
                
                # estraiamo i mercati multipli: vittoria e over 2.5
                for mercato in mercati:
                    if mercato['key'] == 'h2h':
                        quota_1 = next((q['price'] for q in mercato['outcomes'] if q['name'] == squadra_casa), 0)
                    if mercato['key'] == 'totals':
                        quota_over = next((q['price'] for q in mercato['outcomes'] if q['name'] == 'Over' and q.get('point') == 2.5), 0)
                
                # filtro di sicurezza: troviamo la giocata migliore tra vittoria e over
                giocata_scelta = ""
                quota_scelta = 0
                
                if 1.50 <= quota_1 <= 1.90:
                    giocata_scelta = f"vittoria {squadra_casa}"
                    quota_scelta = quota_1
                elif 1.50 <= quota_over <= 1.85:
                    giocata_scelta = "over 2.5 gol"
                    quota_scelta = quota_over
                    
                if giocata_scelta:
                    messaggio += f"⚽ **{squadra_casa} vs {squadra_trasferta}**\n"
                    messaggio += f"🎯 Giocata suggerita: **{giocata_scelta}**\n"
                    messaggio += f"📈 Quota di valore: **{quota_scelta}**\n\n"
                    partite_trovate += 1
                    
        if partite_trovate > 0:
            messaggio += "#SerieA #Pronostici #ScommesseSportive #Betting"
        else:
            messaggio = "nessuna quota ha superato i nostri filtri di sicurezza oggi."

    if messaggio:
        url_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url_telegram, json={"chat_id": CHAT_ID, "text": messaggio, "parse_mode": "Markdown"})
        print("messaggio elaborato e inviato!")

# esecuzione
analizza_e_invia()
