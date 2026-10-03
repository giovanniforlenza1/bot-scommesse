import numpy as np

def simula_partita_montecarlo(gol_fatti_casa, gol_subiti_casa, gol_fatti_trasferta, gol_subiti_trasferta, modulo_casa="equilibrato", modulo_trasferta="equilibrato", num_simulazioni=10000):
    # calcolo degli expected goals (xg) base incrociando attacco e difesa
    xg_casa = (gol_fatti_casa + gol_subiti_trasferta) / 2
    xg_trasferta = (gol_fatti_trasferta + gol_subiti_casa) / 2
    
    # applicazione dei modificatori tattici in base ai moduli di gioco
    modificatori = {
        "offensivo": 1.15,     # 4-3-3 o 4-2-3-1: +15% gol fatti, ma scopre la difesa
        "difensivo": 0.85,     # 5-4-1 o 5-3-2: -15% gol fatti, ma copre la difesa
        "equilibrato": 1.00    # 4-4-2 o 3-5-2 standard
    }
    
    # il modulo offensivo di casa aumenta i suoi xg, ma aumenta anche quelli subiti in ripartenza
    xg_casa = xg_casa * modificatori.get(modulo_casa, 1.0)
    xg_trasferta = xg_trasferta * (2.0 - modificatori.get(modulo_casa, 1.0))
    
    xg_trasferta = xg_trasferta * modificatori.get(modulo_trasferta, 1.0)
    xg_casa = xg_casa * (2.0 - modificatori.get(modulo_trasferta, 1.0))
    
    # simulazione di 10.000 partite usando la distribuzione di poisson
    risultati_casa = np.random.poisson(xg_casa, num_simulazioni)
    risultati_trasferta = np.random.poisson(xg_trasferta, num_simulazioni)
    
    vittorie_casa = 0
    pareggi = 0
    vittorie_trasferta = 0
    
    for i in range(num_simulazioni):
        if risultati_casa[i] > risultati_trasferta[i]:
            vittorie_casa += 1
        elif risultati_casa[i] == risultati_trasferta[i]:
            pareggi += 1
        else:
            vittorie_trasferta += 1
            
    # calcolo delle probabilità pure
    prob_1 = vittorie_casa / num_simulazioni
    prob_x = pareggi / num_simulazioni
    prob_2 = vittorie_trasferta / num_simulazioni
    
    # conversione in quote reali (fair odds) senza l'aggio del bookmaker
    quota_reale_1 = round(1 / prob_1, 2) if prob_1 > 0 else 0
    quota_reale_x = round(1 / prob_x, 2) if prob_x > 0 else 0
    quota_reale_2 = round(1 / prob_2, 2) if prob_2 > 0 else 0
    
    print(f"--- RISULTATI SU {num_simulazioni} PARTITE SIMULATE ---")
    print(f"vittoria casa: {prob_1*100:.1f}% (quota reale equa: @{quota_reale_1})")
    print(f"pareggio: {prob_x*100:.1f}% (quota reale equa: @{quota_reale_x})")
    print(f"vittoria trasferta: {prob_2*100:.1f}% (quota reale equa: @{quota_reale_2})")
    
    return {"prob_1": prob_1, "prob_x": prob_x, "prob_2": prob_2}

# test pratico: simuliamo una partita con statistiche medie e una disparità tattica
if __name__ == "__main__":
    print("simulazione: squadra di casa (offensiva) vs squadra in trasferta (difensiva)")
    simula_partita_montecarlo(
        gol_fatti_casa=1.8, gol_subiti_casa=1.1, 
        gol_fatti_trasferta=1.2, gol_subiti_trasferta=0.9, 
        modulo_casa="offensivo", modulo_trasferta="difensivo"
    )
