import json
import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

def allena_modello_analitico():
    if not os.path.exists('database_storico.json'):
        print("database storico non trovato. attendere la raccolta dati delle prime partite.")
        return

    with open('database_storico.json', 'r', encoding='utf-8') as f:
        db = json.load(f)

    # estraiamo le partite concluse con i loro dati analitici profondi
    partite_chiuse = [p for p in db.get('match_giocati', []) if p.get('esito_reale') in [0, 1]]

    if len(partite_chiuse) < 10:
        print("dati insufficienti: il random forest richiede almeno 10 match conclusi per imparare i pattern complessi del mercato.")
        return

    X = []
    y = []

    # il modello studia le vere variabili della partita per trovare correlazioni nascoste
    for p in partite_chiuse:
        prob_casa = p.get('prob_casa', 0.33)
        prob_x = p.get('prob_x', 0.33)
        prob_trasferta = p.get('prob_trasferta', 0.33)
        aggio_mercato = p.get('aggio', 1.05)
        quota_offerta = p.get('quota_reale', 2.0)
        
        # assembliamo le caratteristiche matematiche del match
        features = [prob_casa, prob_x, prob_trasferta, aggio_mercato, quota_offerta]
        X.append(features)
        y.append(p.get('esito_reale')) # 1 se la scommessa era corretta, 0 se sbagliata

    # addestramento del random forest classifier per scovare le anomalie
    modello_rf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)
    modello_rf.fit(X, y)

    # salviamo l'intelligenza artificiale addestrata in un file binario pronto all'uso
    joblib.dump(modello_rf, 'cervello_omega.pkl')
    print("addestramento completato: il modello ha imparato a riconoscere le partite ingannevoli incrociando i dati.")

if __name__ == "__main__":
    allena_modello_analitico()
