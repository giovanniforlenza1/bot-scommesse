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
    budget_simulato = 10.0
    
    db_principale = carica_database_principale()
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi_str = datetime.now(fuso_italia).strftime("%d/%m/%Y")
    
    msg = f"🛡️ **SEGNALI ALPHA: DUTCHING SINTETICO (BASSO RISCHIO)** 🛡️\n\n"
    msg += "il modello ha individuato le favorite più solide del mercato. per battere il margine dei bookmaker, divideremo matematicamente la puntata per assicurarci il rimborso totale in caso di pareggio.\n\n"
    
    for s in top_segnali:
        importo_vittoria = round((s['split_cassa_vittoria'] / 100) * budget_simulato, 2)
        importo_pareggio = round((s['split_cassa_pareggio'] / 100) * budget_simulato, 2)
        
        # Estrapoliamo i nomi per la dashboard
        squadre = s['match'].split(" - ")
        casa = squadre[0] if len(squadre) > 1 else s['match']
        trasferta = squadre[1] if len(squadre) > 1 else ""
        
        # Salvataggio nel database della dashboard
        db_principale['schedine'].append({
            'id': str(uuid.uuid4())[:8],
            'modello': 'alpha',
            'data_creazione': oggi_str,
            'importo': budget_simulato,
            'quota_totale': s['quota_protetta'],
            'ritorno_potenziale': round(budget_simulato * s['quota_protetta'], 2),
            'stato_schedina': 'in attesa',
            'partite': [{
                'squadra_casa': casa,
                'squadra_trasferta': trasferta,
                'pronostico': s['pronostico'],
                'quota': s['quota_protetta'],
                'stato': 'in attesa',
                'risultato_reale': ''
            }]
        })
        
        msg += f"⚽ **{s['data']} | {s['match']}**\n"
        msg += f"🎯 **Giocata di Copertura**: {s['pronostico']}\n"
        msg += f"📊 Probabilità matematica: {s['probabilita_vittoria']}%\n"
        msg += f"🔥 **QUOTA SINTETICA**: @{s['quota_protetta']}\n\n"
        msg += f"💼 **COME PIAZZARE {budget_simulato}€**:\n"
        msg += f"👉 Puntare **{importo_vittoria}€** sulla vittoria di: {s['favorita']}\n"
        msg += f"👉 Puntare **{importo_pareggio}€** sul Pareggio (X)\n\n"
        
    msg += "rispettare rigorosamente questa divisione del budget. l'unico rischio residuo è la vittoria della sfavorita.\n\n"
    msg += "**#CoperturaMatematica #BettingProfessionale #DNB #Dutching #TradingSportivo**"
    
    salva_database_principale(db_principale)
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    print("allerta Alpha inviata e salvata sulla dashboard con successo.")

if __name__ == "__main__":
    lancia_allerta_dutching()
