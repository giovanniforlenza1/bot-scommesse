import json
import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def lancia_allerta_esotica():
    if not os.path.exists('database_beta.json'):
        print("Nessun database Beta trovato.")
        return
        
    with open('database_beta.json', 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    segnali = db.get("segnali", [])
    if not segnali:
        print("Nessun segnale esotico di valore trovato oggi.")
        return
        
    # Prendiamo solo i 3 segnali più forti in assoluto
    top_segnali = segnali[:3]
    
    msg = f"⚠️ **SEGNALI BETA: MERCATI ESOTICI (SINGOLE)** ⚠️\n\n"
    msg += "Il modello matematico ha individuato fortissime anomalie statistiche sui mercati secondari. Verifica le quote sul tuo bookmaker di fiducia (Snai, Bet365, Eurobet) e piazza la giocata SOLO se l'offerta supera la nostra quota di ingresso minima.\n\n"
    
    for s in top_segnali:
        msg += f"⚽ **{s['data']} | {s['match']}**\n"
        msg += f"🎯 **Mercato**: {s['mercato']}\n"
        msg += f"🔥 **Pronostico**: {s['pronostico']}\n"
        msg += f"📊 Probabilità matematica: {s['probabilita']}%\n"
        msg += f"💰 **QUOTA MINIMA DA GIOCARE**: @{s['quota_ingresso_minima']}\n\n"
        
    msg += "La disciplina fa la differenza. Se il bookmaker offre di meno, scarta la giocata.\n\n"
    msg += "**#Angoli #Cartellini #SingoleDiValore #ValueBetting**"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    print("Allerta Beta inviata su Telegram con successo.")

if __name__ == "__main__":
    lancia_allerta_esotica()
