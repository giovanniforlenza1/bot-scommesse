import json
import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def lancia_allerta_dutching():
    if not os.path.exists('database_alpha.json'):
        print("nessun database Alpha trovato.")
        return
        
    with open('database_alpha.json', 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    segnali = db.get("cassaforte", [])
    if not segnali:
        print("nessuna quota sicura rilevata oggi per la costruzione del dutching.")
        return
        
    top_segnali = segnali[:3]
    budget_simulato = 10.0 # importo fisso base su cui calcolare le percentuali
    
    msg = f"🛡️ **SEGNALI ALPHA: DUTCHING SINTETICO (BASSO RISCHIO)** 🛡️\n\n"
    msg += "il modello ha individuato le favorite più solide del mercato. per battere il margine dei bookmaker, divideremo matematicamente la puntata per assicurarci il rimborso totale in caso di pareggio.\n\n"
    
    for s in top_segnali:
        importo_vittoria = round((s['split_cassa_vittoria'] / 100) * budget_simulato, 2)
        importo_pareggio = round((s['split_cassa_pareggio'] / 100) * budget_simulato, 2)
        
        msg += f"⚽ **{s['data']} | {s['match']}**\n"
        msg += f"🎯 **Giocata di Copertura**: {s['pronostico']}\n"
        msg += f"📊 Probabilità matematica: {s['probabilita_vittoria']}%\n"
        msg += f"🔥 **QUOTA SINTETICA**: @{s['quota_protetta']}\n\n"
        msg += f"💼 **COME PIAZZARE {budget_simulato}€**:\n"
        msg += f"👉 Puntare **{importo_vittoria}€** sulla vittoria di: {s['favorita']}\n"
        msg += f"👉 Puntare **{importo_pareggio}€** sul Pareggio (X)\n\n"
        
    msg += "rispettare rigorosamente questa divisione del budget. in caso di vittoria della favorita otterrai il profitto pieno, in caso di pareggio riavrai esattamente i tuoi 10€ indietro. l'unico rischio residuo è la vittoria della sfavorita.\n\n"
    msg += "**#CoperturaMatematica #BettingProfessionale #DNB #Dutching #TradingSportivo**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    print("allerta Alpha inviata su Telegram con successo.")

if __name__ == "__main__":
    lancia_allerta_dutching()
