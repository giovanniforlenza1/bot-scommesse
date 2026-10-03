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

def lancia_allerta_esotica():
    if not os.path.exists('database_beta.json'):
        return
        
    with open('database_beta.json', 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    segnali = db.get("segnali", [])
    if not segnali:
        return
        
    top_segnali = segnali[:3]
    
    db_principale = carica_database_principale()
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi_str = datetime.now(fuso_italia).strftime("%d/%m/%Y")
    budget_base = 10.0
    
    msg = "**MODELLO BETA**\n\n"
    msg += "**singole su mercati esotici.**\n\n"
    
    for s in top_segnali:
        squadre = s['match'].split(" - ")
        casa = squadre[0] if len(squadre) > 1 else s['match']
        trasferta = squadre[1] if len(squadre) > 1 else ""
        
        db_principale['schedine'].append({
            'id': str(uuid.uuid4())[:8],
            'modello': 'beta',
            'data_creazione': oggi_str,
            'importo': budget_base,
            'quota_totale': s['quota_ingresso_minima'],
            'ritorno_potenziale': round(budget_base * s['quota_ingresso_minima'], 2),
            'stato_schedina': 'in attesa',
            'partite': [{
                'squadra_casa': casa,
                'squadra_trasferta': trasferta,
                'pronostico': s['pronostico'],
                'quota': s['quota_ingresso_minima'],
                'stato': 'in attesa',
                'risultato_reale': ''
            }]
        })
        
        msg += f"⚽ **{s['data']} | {s['match']}**\n"
        msg += f"🎯 **mercato**: {s['mercato'].lower()}\n"
        msg += f"🔥 **pronostico**: {s['pronostico'].lower()}\n"
        msg += f"💰 **quota minima**: @{s['quota_ingresso_minima']}\n"
        msg += f"💼 **stake**: {s.get('stake_cassa_perc', 1.0)}% della cassa\n\n"
        
    msg += "**#BettingProfessionale #PronosticiCalcio #ValueBetting #Singole**"
    
    salva_database_principale(db_principale)
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    lancia_allerta_esotica()
