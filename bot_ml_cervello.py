import json
import os
import numpy as np
from sklearn.tree import DecisionTreeClassifier

def allena_intelligenza_artificiale():
    if not os.path.exists('database.json'):
        print("database principale non trovato.")
        return

    with open('database.json', 'r', encoding='utf-8') as f:
        db = json.load(f)

    # estraiamo solo le scommesse concluse per l'addestramento
    scommesse_chiuse = [s for s in db.get('schedine', []) if s.get('stato_schedina') in ['vinta', 'persa']]

    if len(scommesse_chiuse) < 3:
        print("dati insufficienti: il machine learning ha bisogno di più schedine chiuse per trarre conclusioni statistiche.")
        return

    X = []
    y = []
    mappa_modelli = {'alpha': 1, 'beta': 2, 'omega': 3}

    # la macchina studia le tue giocate passate
    for s in scommesse_chiuse:
        mod = mappa_modelli.get(s.get('modello', 'omega').lower(), 3)
        quota = s.get('quota_totale', 2.0)
        num_partite = len(s.get('partite', []))
        esito = 1 if s.get('stato_schedina') == 'vinta' else 0

        X.append([mod, quota, num_partite])
        y.append(esito)

    # addestramento dell'albero decisionale per isolare i pattern perdenti
    modello_ml = DecisionTreeClassifier(random_state=42, max_depth=4)
    modello_ml.fit(X, y)

    # regole base di partenza
    nuove_regole = {
        "alpha": {"quota_max_sicura": 3.0}, 
        "beta": {"quota_max_sicura": 3.0}, 
        "omega": {"quota_max_sicura": 3.0}
    }

    # test predittivo: simuliamo quote future per vedere a che livello la macchina prevede una sconfitta certa
    for nome, cod in mappa_modelli.items():
        for q in np.arange(1.5, 5.0, 0.2):
            pred = modello_ml.predict([[cod, q, 2]])
            if pred[0] == 0:
                # la macchina ha capito che oltre questa quota il modello perde sistematicamente
                nuove_regole[nome]["quota_max_sicura"] = round(q - 0.1, 2)
                break

    # salviamo il nuovo cervello
    with open('regole_ml.json', 'w', encoding='utf-8') as f:
        json.dump(nuove_regole, f, indent=4, ensure_ascii=False)

    print("addestramento completato: le nuove direttive di limitazione rischio sono pronte.")

if __name__ == "__main__":
    allena_intelligenza_artificiale()
