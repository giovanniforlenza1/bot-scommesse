import json
import os
import requests
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def carica_database_principale():
    if os.path.exists('database.json'):
        with open('database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'capitale_iniziale': 200.0, 'schedine': []}

def salva_database_principale(db):
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def lancia_allerta_quota5():
    if not os.path.exists('database_alpha.json'):
        print("Cecchino Alpha: database_alpha.json non trovato.")
        return
        
    with open('database_alpha.json', 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    schedine = db.get("schedine", [])
    if not schedine:
        print("Cecchino Alpha: nessuna schedina presente nel file.")
        return
        
    db_principale = carica_database_principale()
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi_str = datetime.now(fuso_italia).strftime("%d/%m/%Y")
    
    budget_base = 10.0
    schedine_inviate = 0
    
    for ticket in schedine:
        # Blocco assoluto: rifiuta moltiplicatori inferiori a 5.00
        if ticket.get('quota_totale', 0) < 5.00:
            continue
            
        partite_per_db = []
        for p in ticket['partite']:
            partite_per_db.append({
                'squadra_casa': p['squadra_casa'],
                'squadra_trasferta': p['squadra_trasferta'],
                'pronostico': p['pronostico'],
                'quota': p['quota'],
                'stato': 'in attesa',
                'risultato_reale': ''
            })
            
        db_principale['schedine'].append({
            'id': str(uuid.uuid4())[:8],
            'modello': 'alpha',
            'data_creazione': oggi_str,
            'importo': budget_base,
            'quota_totale': ticket['quota_totale'],
            'ritorno_potenziale': round(budget_base * ticket['quota_totale'], 2),
            'stato_schedina': 'in attesa',
            'partite': partite_per_db
        })
        
        nome_lega_formattato = ticket.get('lega', 'MIX').replace("soccer_", "").replace("_", " ").upper()
        
        msg = f"**SBR | {nome_lega_formattato}**\n\n"
        msg += "**Multipla ad alto rendimento (Quota 5+).**\n\n"
        msg += f"📊 **Quota totale**: @{ticket['quota_totale']}\n"
        msg += f"💼 **Stake**: {budget_base}€\n\n"
        
        for p in ticket['partite']:
            msg += f"⚽ **{p['data']} | {p['match']}**\n"
            msg += f"🎯 **Giocata**: {p['pronostico']} (@{p['quota']})\n\n"
            
        msg += "**#TradingSportivo #ValueBetting #ScommesseSportive #Quota5**"
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        schedine_inviate += 1
        
    if schedine_inviate > 0:
        salva_database_principale(db_principale)
        print(f"Cecchino Alpha: inviate {schedine_inviate} schedine con successo.")
    else:
        print("Cecchino Alpha: nessuna multipla ha superato il filtro matematico (Quota < 5.00).")

if __name__ == "__main__":
    lancia_allerta_quota5()
