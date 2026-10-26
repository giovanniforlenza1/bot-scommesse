def scarica_dati_completi_espn():
    partite_espn = []
    fuso_italia = ZoneInfo("Europe/Rome")
    oggi = datetime.now(fuso_italia)
    # Scansione giornaliera precisa degli ultimi 10 giorni (evita il limite di troncamento di ESPN!)
    date_calcio = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(10)]

    for lega in campionati_espn:
        for d_str in date_calcio:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard?dates={d_str}"
            try:
                res = requests.get(url, timeout=5)
                if res.status_code != 200: continue
                for ev in res.json().get('events', []):
                    comp = ev.get('competitions', [{}])[0]
                    st_type = comp.get('status', {}).get('type', {})
                    completed = st_type.get('completed', False) or str(st_type.get('state', '')).lower() == 'post'
                    if not completed: continue
                    teams = comp.get('competitors', [])
                    if len(teams) < 2: continue
                    
                    casa_nome, trasf_nome, gol_casa, gol_trasf = "", "", 0, 0
                    c_dir, k_dir = 0, 0
                    ha_c_dir, ha_k_dir = False, False

                    for t in teams:
                        t_name = t.get('team', {}).get('displayName', '')
                        score_str = str(t.get('score', '0')).strip()
                        gol_val = int(float(score_str)) if score_str.isdigit() else 0
                        if t.get('homeAway') == 'home': casa_nome = t_name; gol_casa = gol_val
                        else: trasf_nome = t_name; gol_trasf = gol_val
                        
                        for stat in t.get('statistics', []):
                            nome_s = str(stat.get('name', '')).lower()
                            val_str = str(stat.get('displayValue', '0')).strip()
                            val = int(float(val_str)) if val_str.replace('.', '', 1).isdigit() else 0
                            if nome_s in ['woncorners', 'cornerkicks', 'corners']:
                                c_dir += val
                                ha_c_dir = True
                            elif nome_s in ['yellowcards', 'redcards']:
                                k_dir += val
                                ha_k_dir = True

                    if not ha_k_dir and comp.get('details') is not None and len(comp.get('details', [])) > 0:
                        det_cards = sum(1 for d in comp.get('details', []) if d.get('yellowCard') or d.get('redCard'))
                        k_dir = det_cards
                        ha_k_dir = True

                    partite_espn.append({
                        'event_id': ev.get('id'),
                        'lega': lega,
                        'casa_orig': casa_nome,
                        'trasf_orig': trasf_nome,
                        'gol_casa': gol_casa,
                        'gol_trasf': gol_trasf,
                        'corners_dir': c_dir if ha_c_dir else None,
                        'cards_dir': k_dir if ha_k_dir else None
                    })
            except:
                continue

    date_tennis = [(oggi - timedelta(days=i)).strftime("%Y%m%d") for i in range(8)]
    for circuito in ['atp', 'wta']:
        urls_tennis = [f"https://site.api.espn.com/apis/site/v2/sports/tennis/{circuito}/scoreboard"] + [
            f"https://site.api.espn.com/apis/site/v2/sports/tennis/{circuito}/scoreboard?dates={d_str}" for d_str in date_tennis
        ]
        for url_t in urls_tennis:
            try:
                res = requests.get(url_t, timeout=6)
                if res.status_code != 200: continue
                for ev in res.json().get('events', []):
                    ev_id = ev.get('id')
                    for grouping in ev.get('groupings', []):
                        for comp in grouping.get('competitions', []):
                            m_t = estrai_match_tennis_da_comp(comp, circuito, ev_id)
                            if m_t: partite_espn.append(m_t)
                    for comp in ev.get('competitions', []):
                        m_t = estrai_match_tennis_da_comp(comp, circuito, ev_id)
                        if m_t: partite_espn.append(m_t)
            except:
                continue

    print(f"[INFO] Partite concluse scaricate da ESPN (Calcio + Tennis): {len(partite_espn)}")
    return partite_espn
