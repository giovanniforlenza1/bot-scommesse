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
        url = f"https://api.the-odds-api.com/v4/sports/{campionato}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals,btts"
        risposta = requests.get(url)
        if risposta.status_code == 200:
            tutte_le_partite.extend(risposta.json())
            
    return tutte_le_partite

def analizza_e_invia():
    partite = scarica_partite()
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia).date()
    domani = oggi + timedelta(days=1)
    fine_turno = oggi + timedelta(days=3)
    
    partite_turno = []
    data_prima_partita = None

    for partita in partite:
        data_partita_utc = datetime.strptime(partita['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
        data_partita_ita = data_partita_utc.astimezone(fuso_italia)
        
        # raccoglie tutte le partite da oggi ai prossimi 3 giorni
        if oggi <= data_partita_ita.date() <= fine_turno:
            partite_turno.append({'dati': partita, 'data_ita': data_partita_ita})
            if data_prima_partita is None or data_partita_ita.date() < data_prima_partita:
                data_prima_partita = data_partita_ita.date()

    messaggio = ""
    siti_italiani = ['Bet365', 'Snai', 'Sisal', 'Eurobet', 'PlanetWin365', 'GoldBet', 'Lottomatica', 'Betfair', 'William Hill']
    
    if data_prima_partita == domani:
        messaggio = "⏳ **IL MODELLO STA CALCOLANDO IL PROSSIMO TURNO**\n\n"
        messaggio += "**i nostri algoritmi stanno elaborando l'intero palinsesto dei prossimi giorni.** **Domani alla stessa ora uscirà la selezione delle giocate con il miglior rapporto rischio/rendimento.**\n\n"
        messaggio += "**#PronosticiCalcio #QuoteValore #ValueBetting #MatchLab**"
        
    elif data_prima_partita == oggi and partite_turno:
        giocate_selezionate = []
        
        for item in partite_turno:
            partita = item['dati']
            data_match = item['data_ita']
            # formatta la data per far capire in che giorno si gioca all'interno del turno
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
                            elif mercato['key'] == 'btts':
                                quota = next((q['price'] for q in mercato['outcomes'] if q['name'] == 'Yes'), 0)
                                if 1.45 <= quota <= 1.95 and quota > quota_massima:
                                    quota_massima = quota
                                    miglior_giocata = "gol (entrambe segnano)"
                        
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
            # ordina tutte le giocate del turno per quota migliore e prende solo la top 4
            giocate_selezionate.sort(key=lambda x: x['valore_numerico'], reverse=True)
            top_selezioni = giocate_selezionate[:4]
            
            messaggio = "🔥 **LE GIOCATE UFFICIALI DELL'INTERO TURNO**\n\n"
            for giocata in top_selezioni:
                messaggio += f"{giocata['testo_partita']}\n{giocata['testo_analisi']}\n{giocata['testo_quota']}\n{giocata['testo_rischio']}\n\n"
            messaggio += "**#PronosticiCalcio #QuoteValore #ValueBetting #MatchLab**"
        else:
            messaggio = "**nessuna quota del turno ha superato il filtro matematico di sicurezza**"
    else:
        print("nessuna partita utile in programma a breve.")
        return

    if messaggio:
        url_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url_telegram, json={"chat_id": CHAT_ID, "text": messaggio, "parse_mode": "Markdown"})
        print("messaggio del turno completo inviato con successo!")

analizza_e_invia()
