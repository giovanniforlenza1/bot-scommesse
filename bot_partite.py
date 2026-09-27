import requests
from datetime import datetime, timedelta

# INSERISCI I TUOI DATI TRA LE VIRGOLETTE
TELEGRAM_TOKEN = "8981487141:AAFvKmVGm62wnENn-6uJZPedv0WMbp8ewr0"
CHAT_ID = "-1004229932372" 
ODDS_API_KEY = "8c17009a702111adb9f70dff1242a7c7"

# traduciamo esclusivamente i nomi di tutte le nazioni europee
TRADUZIONI_NAZIONALI = {
    "Italy": "Italia", "France": "Francia", "Germany": "Germania", 
    "Spain": "Spagna", "England": "Inghilterra", "Netherlands": "Olanda", 
    "Belgium": "Belgio", "Portugal": "Portogallo", "Croatia": "Croazia", 
    "Switzerland": "Svizzera", "Poland": "Polonia", "Denmark": "Danimarca", 
    "Sweden": "Svezia", "Norway": "Norvegia", "Austria": "Austria", 
    "Scotland": "Scozia", "Wales": "Galles", "Hungary": "Ungheria", 
    "Turkey": "Turchia", "Albania": "Albania", "Serbia": "Serbia",
    "Finland": "Finlandia", "Belarus": "Bielorussia", "Czech Republic": "Repubblica Ceca",
    "Slovakia": "Slovacchia", "Slovenia": "Slovenia", "Romania": "Romania",
    "Bulgaria": "Bulgaria", "Greece": "Grecia", "Iceland": "Islanda",
    "Republic of Ireland": "Irlanda", "Northern Ireland": "Irlanda del Nord",
    "Bosnia and Herzegovina": "Bosnia ed Erzegovina", "Montenegro": "Montenegro",
    "North Macedonia": "Macedonia del Nord", "Georgia": "Georgia", "Ukraine": "Ucraina",
    "Lithuania": "Lituania", "Latvia": "Lettonia", "Estonia": "Estonia",
    "Cyprus": "Cipro", "Malta": "Malta", "Moldova": "Moldavia", "Andorra": "Andorra",
    "San Marino": "San Marino", "Liechtenstein": "Liechtenstein", "Luxembourg": "Lussemburgo",
    "Armenia": "Armenia", "Azerbaijan": "Azerbaigian", "Kazakhstan": "Kazakistan",
    "Kosovo": "Kosovo", "Israel": "Israele", "Faroe Islands": "Isole Faroe",
    "Gibraltar": "Gibilterra"
}

def traduci_squadra(nome_inglese):
    return TRADUZIONI_NAZIONALI.get(nome_inglese, nome_inglese)

def calcola_rischio(quota):
    if quota <= 1.60:
        return "🟢 basso"
    elif quota <= 1.75:
        return "🟡 medio"
    else:
        return "🟠 alto"

def scarica_partite():
    campionati = [
        'soccer_italy_serie_a', 
        'soccer_uefa_nations_league',
        'soccer_uefa_champs_league',
        'soccer_uefa_europa_league'
    ]
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
        print("nessuna partita utile trovata.")
        return

    messaggio = ""
    siti_italiani = ['Bet365', 'Snai', 'Sisal', 'Eurobet', 'PlanetWin365', 'GoldBet', 'Lottomatica', 'Betfair', 'William Hill']
    
    if data_prima_partita == domani:
        messaggio = "⏳ **IL MODELLO STA CALCOLANDO LE PROSSIME SFIDE**\n\n"
        messaggio += "**i nostri algoritmi stanno analizzando le quote dei prossimi match. Domani alla stessa ora usciranno i pronostici ufficiali con il miglior rapporto rischio/rendimento.**\n\n"
        messaggio += "**#PronosticiCalcio #QuoteValore #BettingTips #ScommesseSportive**"
        
    elif data_prima_partita == oggi:
        messaggio = "🔥 **LE GIOCATE UFFICIALI DEL MATCH LAB**\n\n"
        partite_trovate = 0
        
        for partita in partite_utili:
            squadra_casa_originale = partita['home_team']
            squadra_casa = traduci_squadra(squadra_casa_originale)
            squadra_trasferta = traduci_squadra(partita['away_team'])
            
            if partita.get('bookmakers'):
                bookmaker_valido = None
                
                for bookmaker in partita['bookmakers']:
                    if bookmaker['title'] in siti_italiani:
                        bookmaker_valido = bookmaker
                        break
                        
                if bookmaker_valido:
                    nome_bookmaker = bookmaker_valido['title']
                    mercati = bookmaker_valido['markets']
                    quota_1 = 0
                    quota_over = 0
                    
                    for mercato in mercati:
                        if mercato['key'] == 'h2h':
                            quota_1 = next((q['price'] for q in mercato['outcomes'] if q['name'] == squadra_casa_originale), 0)
                        if mercato['key'] == 'totals':
                            quota_over = next((q['price'] for q in mercato['outcomes'] if q['name'] == 'Over' and q.get('point') == 2.5), 0)
                    
                    giocata_scelta = ""
                    quota_scelta = 0
                    
                    if 1.50 <= quota_1 <= 1.90:
                        giocata_scelta = f"vittoria {squadra_casa}"
                        quota_scelta = quota_1
                    elif 1.50 <= quota_over <= 1.85:
                        giocata_scelta = "over 2.5 gol"
                        quota_scelta = quota_over
                        
                    if giocata_scelta:
                        livello_rischio = calcola_rischio(quota_scelta)
                        messaggio += f"⚽ **{squadra_casa} - {squadra_trasferta}**\n"
                        messaggio += f"🎯 **analisi: {giocata_scelta}**\n"
                        messaggio += f"📈 **quota di valore: {quota_scelta} su {nome_bookmaker}**\n"
                        messaggio += f"📊 **livello di rischio: {livello_rischio}**\n\n"
                        partite_trovate += 1
                        
        if partite_trovate > 0:
            messaggio += "**#PronosticiCalcio #QuoteValore #ValueBetting #ScommesseSportive**"
        else:
            messaggio = "**oggi nessuna quota ha superato il filtro matematico di sicurezza.**"

    if messaggio:
        url_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url_telegram, json={"chat_id": CHAT_ID, "text": messaggio, "parse_mode": "Markdown"})
        print("messaggio inviato con il dizionario aggiornato!")

analizza_e_invia()
