from logger_config import get_logger

# Configuration du logger pour ce module
logger = get_logger(__name__)


def diagnose_feasibility(d):
    jours = d['jours']
    cpd = d['creneaux_par_jour']
    slots = d['slots']  # list of (day, offset)
    fenetre_midi = set(d['fenetre_midi'])
    nb_slots = d['nb_slots']
    salles = list(d['salles'].items())  # [(nom, capacité), ...] ordre d'insertion conservé

    # Créneaux disponibles par jour (hors pause midi)
    usable_offsets = [o for o in range(cpd) if o not in fenetre_midi]
    usable_per_day = len(usable_offsets)
    total_usable_slots = usable_per_day * jours

    problems = {'no_valid_start': [], 'no_room': [], 'group_overbooked': []}

    # 1) Vérifier que chaque cours a au moins un créneau de départ valide
    for c in d['cours']:
        cid = c['id']
        duration = d['duree_cours'][cid]
        valid_starts = []
        # Énumérer les créneaux s par (jour, offset)
        for s, (day, offset) in enumerate(slots):
            # Doit tenir dans la journée (pas de débordement)
            if offset + duration > cpd:
                continue
            # Ne doit pas chevaucher la fenêtre midi
            intersects_midi = any((offset + i) in fenetre_midi for i in range(duration))
            if intersects_midi:
                continue
            # Ne doit pas déborder sur un autre jour — déjà assuré par offset + duration <= cpd
            valid_starts.append((s, day, offset))
        if not valid_starts:
            problems['no_valid_start'].append((cid, duration))
        # Stocker le nombre pour info
        # logger.info(f"{cid}: {len(valid_starts)} valid starts")

    # 2) Vérifier les capacités des salles
    # Pour chaque cours, vérifier qu'au moins une salle a une capacité >= taille du groupe
    for c in d['cours']:
        cid = c['id']
        group = c['groups'][0]
        taille = d['taille_groupes'].get(group, 0)
        ok = any(cap >= taille for _, cap in salles)
        if not ok:
            problems['no_room'].append((cid, group, taille))

    # 3) Vérification grossière de capacité par groupe : créneaux requis <= créneaux disponibles
    # (vérification nécessaire mais non suffisante)
    group_required = {}
    for grp, course_ids in d['map_groupe_cours'].items():
        total = 0
        for cid in course_ids:
            total += d['duree_cours'][cid]
        group_required[grp] = total
        if total > total_usable_slots:
            problems['group_overbooked'].append((grp, total, total_usable_slots))

    # Afficher le résumé
    logger.info("=== Diagnostic faisabilité (statique) ===")
    logger.info(f"Jours: {jours}, creneaux_par_jour: {cpd}, slots total: {nb_slots}")
    logger.info(f"Slots utilisables par jour (hors midi): {usable_per_day}, total utilisables: {total_usable_slots}")
    if problems['no_valid_start']:
        logger.info("Cours sans aucun start valide (durée incompatible ou traversée midi):")
        for cid, duration in problems['no_valid_start']:
            logger.info(f" - {cid}: durée {duration} slots")
    else:
        logger.info("OK: tous les cours ont au moins un start valide.")

    if problems['no_room']:
        logger.info("\nCours sans salle suffisante (capacité):")
        for cid, grp, taille in problems['no_room']:
            logger.info(f" - {cid}: groupe {grp} taille {taille}")
    else:
        logger.info("OK: toutes les classes ont au moins une salle de capacité suffisante.")

    if problems['group_overbooked']:
        logger.info("\nGroupes demandant plus de slots utilisables que disponibles (impossible globalement):")
        for grp, need, avail in problems['group_overbooked']:
            logger.info(f" - {grp}: besoin {need} slots, mais seulement {avail} utilisables")
    else:
        logger.info("OK: aucun groupe n'exige plus de slots utilisables que disponibles (check global nécessaire mais non suffisant).")

    logger.info("\nSi tout est OK ci-dessus mais INFEASIBLE persiste, vérifier :")
    logger.info("- contrainte de salles disponibles simultanément (nombre de grandes salles pour BUT3)")
    logger.info("- contraintes de profs (s'il y a des restrictions implicites)")
    logger.info("- intégrité des linking constraints (start -> occupe) : assure-toi qu'elles correspondent exactement aux indices de slots")
    return problems