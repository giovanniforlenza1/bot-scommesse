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

def lancia_allerta_raddoppio():
    if not os.path.exists('database_alpha.json'):
        return
        
    with open('database_alpha.json', 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    schedine = db.get("schedine", [])
    if not schedine:
        return
        
    top_schedina = schedine[0] 
    
    # blocco di sicurezza totale: rifiuta e ignora le quote inferiori a 1.80
    if top_schedina['quota_totale'] < 1.80:
        return
        
    budget_base = 10.0
    
    db_principale = carica_database_principale()
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi_str = datetime.now(fuso_italia).strftime("%d/%m/%Y")
    
    partite_per_db = []
    for p in top_schedina['partite']:
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
        'quota_totale': top_schedina['quota_totale'],
        'ritorno_potenziale': round(budget_base * top_schedina['quota_totale'], 2),
        'stato_schedina': 'in attesa',
        'partite': partite_per_db
    })
    
    msg = "**MODELLO ALPHA**\n\n"
    msg += "**multipla raddoppio.**\n\n"
    msg += f"📊 **quota totale**: @{top_schedina['quota_totale']}\n"
    msg += f"💼 **stake**: {budget_base}€\n\n"
    
    for p in top_schedina['partite']:
        msg += f"⚽ **{p['data']} | {p['match']}**\n"
        msg += f"🎯 **giocata**: {p['pronostico']} (@{p['quota']})\n\n"
        
    msg += "**#Raddoppio #BettingQuantitativo #TradingSportivo**"
    
    salva_database_principale(db_principale)
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    lancia_allerta_raddoppio()
