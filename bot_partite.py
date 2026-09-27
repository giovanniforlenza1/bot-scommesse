import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# INSERISCI I TUOI DATI TRA LE VIRGOLETTE
TELEGRAM_TOKEN = "8981487141:AAFvKmVGm62wnENn-6uJZPedv0WMbp8ewr0"
CHAT_ID = "-1004229932372" 
ODDS_API_KEY = "8c17009a702111adb9f70dff1242a7c7"

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
        # Rimossa la stringa btts che mandava in blocco l'API
        url = f"https://api.the-odds-api.com/v4/sports/{campionato}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals"
        risposta = requests.get(url)
        if risposta.status_code == 200:
            tutte_le_partite.extend(risposta.json())
            
    return tutte_le_partite

def analizza_e_invia():
    partite = scarica_partite()
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia).date()
    fine_turno = oggi + timedelta(days=3)
    
    partite_turno = []

    for partita in partite:
        data_partita_utc = datetime.strptime(partita['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
        data_partita_ita = data_partita_utc.astimezone(fuso_italia)
        
        # Isola solo i match della finestra di 3 giorni
        if oggi <= data_partita_ita.date() <= fine_turno:
            partite_turno.append({'dati': partita, 'data_ita': data_partita_ita})

    if not partite_turno:
        print("Nessuna partita in programma. Nessun messaggio Telegram inviato.")
        return

    messaggio = ""
    siti_italiani = ['Bet365', 'Snai', 'Sisal', 'Eurobet', 'PlanetWin365', 'GoldBet', 'Lottomatica', 'Betfair', 'William Hill']
    giocate_selezionate = []
    
    for item in partite_turno:
        partita = item['dati']
        data_match = item['data_ita']
        data_formattata = data_match.strftime("%d/%m ore %H:%M")
        
        squadra_casa_originale = partita['home_team']
        squadra_casa = traduci_squadra(squadra_casa_originale)
        squadra_trasferta = traduci_squadra(partita['away_team'])
        
        if partita.get('bookmakers'):
            for bookmaker in partita['bookmakers']:
                if bookmaker['title'] in siti_italiani:
                    nome_bookmaker = bookmaker['title']
                    mercati = bookmaker['markets']
                    
                    miglior_giocata = ""
                    quota_massima = 0
                    
                    for mercato in mercati:
                        if mercato['key'] == 'h2h':
                            quota = next((q['price'] for q in mercato['outcomes'] if q['name'] == squadra_casa_originale), 0)
                            if 1.45 <= quota <= 1.95 and quota > quota_massima:
                                quota_massima = quota
                                miglior_giocata = f"vittoria {squadra_casa}"
                        elif mercato['key'] == 'totals':
                            quota = next((q['price'] for q in mercato['outcomes'] if q['name'] == 'Over' and q.get('point') == 2.5), 0)
                            if 1.45 <= quota <= 1.95 and quota > quota_massima:
                                quota_massima = quota
                                miglior_giocata = "over 2.5 gol"
                    
                    if miglior_giocata:
                        giocate_selezionate.append({
                            'testo_partita': f"⚽ **{data_formattata} | {squadra_casa} - {squadra_trasferta}**",
                            'testo_analisi': f"🎯 **analisi: {miglior_giocata}**",
                            'testo_quota': f"📈 **quota di valore: {quota_massima} su {nome_bookmaker}**",
                            'testo_rischio': f"📊 **livello di rischio: {calcola_rischio(quota_massima)}**",
                            'valore_numerico': quota_massima
                        })
                    break 
                    
    if giocate_selezionate:
        giocate_selezionate.sort(key=lambda x: x['valore_numerico'], reverse=True)
        top_selezioni = giocate_selezionate[:4]
        
        messaggio = "🔥 **LE GIOCATE UFFICIALI DEL MATCH LAB**\n\n"
        for giocata in top_selezioni:
            messaggio += f"{giocata['testo_partita']}\n{giocata['testo_analisi']}\n{giocata['testo_quota']}\n{giocata['testo_rischio']}\n\n"
        messaggio += "**#PronosticiCalcio #QuoteValore #ValueBetting #MatchLab**"

    if messaggio:
        url_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url_telegram, json={"chat_id": CHAT_ID, "text": messaggio, "parse_mode": "Markdown"})
        print("Messaggio inviato con successo!")
    else:
        print("Quote filtrate ma nessuna valida. Nessun avviso inviato.")

analizza_e_invia()
