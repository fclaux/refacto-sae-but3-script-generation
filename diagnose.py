def diagnose_feasibility(d):
    jours = d['jours']
    cpd = d['creneaux_par_jour']
    slots = d['slots']  # list of (day, offset)
    fenetre_midi = set(d['fenetre_midi'])
    nb_slots = d['nb_slots']
    salles = list(d['salles'].items())  # [(name,cap), ...] insertion order kept

    # Per-day available offsets (non-midi)
    usable_offsets = [o for o in range(cpd) if o not in fenetre_midi]
    usable_per_day = len(usable_offsets)
    total_usable_slots = usable_per_day * jours

    problems = {'no_valid_start': [], 'no_room': [], 'group_overbooked': []}

    # 1) check each course for at least one valid start
    for c in d['cours']:
        cid = c['id']
        duration = d['duree_cours'][cid]
        valid_starts = []
        # enumerate slots s by (day, offset)
        for s, (day, offset) in enumerate(slots):
            # must fit in the day (not overflow)
            if offset + duration > cpd:
                continue
            # must not intersect midi window
            intersects_midi = any((offset + i) in fenetre_midi for i in range(duration))
            if intersects_midi:
                continue
            # must not cross into a different day — already ensured by offset + duration <= cpd
            valid_starts.append((s, day, offset))
        if not valid_starts:
            problems['no_valid_start'].append((cid, duration))
        # store number for info
        # print(f"{cid}: {len(valid_starts)} valid starts")

    # 2) check room capacities
    # for each course, check if at least one room has capacity >= group size
    for c in d['cours']:
        cid = c['id']
        group = c['groups'][0]
        taille = d['taille_groupes'].get(group, 0)
        ok = any(cap >= taille for _, cap in salles)
        if not ok:
            problems['no_room'].append((cid, group, taille))

    # 3) crude group-level capacity: total required slots <= total usable slots
    # (necessary but not sufficient check)
    group_required = {}
    for grp, course_ids in d['map_groupe_cours'].items():
        total = 0
        for cid in course_ids:
            total += d['duree_cours'][cid]
        group_required[grp] = total
        if total > total_usable_slots:
            problems['group_overbooked'].append((grp, total, total_usable_slots))

    # Print summary
    print("=== Diagnostic faisabilité (statique) ===")
    print(f"Jours: {jours}, creneaux_par_jour: {cpd}, slots total: {nb_slots}")
    print(f"Slots utilisables par jour (hors midi): {usable_per_day}, total utilisables: {total_usable_slots}")
    print()
    if problems['no_valid_start']:
        print("Cours sans aucun start valide (durée incompatible ou traversée midi):")
        for cid, duration in problems['no_valid_start']:
            print(f" - {cid}: durée {duration} slots")
    else:
        print("OK: tous les cours ont au moins un start valide.")

    if problems['no_room']:
        print("\nCours sans salle suffisante (capacité):")
        for cid, grp, taille in problems['no_room']:
            print(f" - {cid}: groupe {grp} taille {taille}")
    else:
        print("OK: toutes les classes ont au moins une salle de capacité suffisante.")

    if problems['group_overbooked']:
        print("\nGroupes demandant plus de slots utilisables que disponibles (impossible globalement):")
        for grp, need, avail in problems['group_overbooked']:
            print(f" - {grp}: besoin {need} slots, mais seulement {avail} utilisables")
    else:
        print("OK: aucun groupe n'exige plus de slots utilisables que disponibles (check global nécessaire mais non suffisant).")

    print("\nSi tout est OK ci-dessus mais INFEASIBLE persiste, vérifier :")
    print("- contrainte de salles disponibles simultanément (nombre de grandes salles pour BUT3)")
    print("- contraintes de profs (s'il y a des restrictions implicites)")
    print("- intégrité des linking constraints (start -> occupe) : assure-toi qu'elles correspondent exactement aux indices de slots")
    return problems