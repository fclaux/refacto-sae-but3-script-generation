#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API de gestion des contraintes - Exemples d'utilisation
Démontre toutes les fonctionnalités du gestionnaire de contraintes
"""

from constraint_manager import ConstraintManager, ConstraintPriority, ConstraintType
import mysql.connector
DEFAULT_YEAR_ID = None
DEFAULT_WEEK_ID = None

def choose_year():
    """Permet de choisir une année (years.id)"""
    conn = mysql.connector.connect(
        host='127.0.0.1',
        port=33066,
        database='edt_app',
        user='edt_user',
        password='userpassword'
    )
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name FROM years ORDER BY name DESC")
        years = cur.fetchall()
        if not years:
            print(" Aucune année trouvée dans la base")
            return None
        print("\nAnnées disponibles:")
        for y in years:
            print(f"  id={y['id']} - {y['name']}")
        try:
            ysel = input("\nEntrez l'id de l'année à utiliser (laisser vide pour la plus récente): ").strip()
            if ysel:
                return int(ysel)
            else:
                return years[0]['id']  # years triées DESC par name
        except Exception:
            return years[0]['id']
    finally:
        cur.close()
        conn.close()

def choose_week(year_id: int | None = None):
    """Permet de choisir une semaine (weeks.id), éventuellement filtrée par année"""
    conn = mysql.connector.connect(
        host='127.0.0.1',
        port=33066,
        database='edt_app',
        user='edt_user',
        password='userpassword'
    )
    cur = conn.cursor(dictionary=True)
    try:
        if year_id:
            cur.execute("SELECT id, week_number, year_id, start_date, end_date FROM weeks WHERE year_id = %s ORDER BY week_number ASC", (year_id,))
        else:
            cur.execute("SELECT id, week_number, year_id, start_date, end_date FROM weeks ORDER BY year_id DESC, week_number ASC")
        weeks = cur.fetchall()
        if not weeks:
            print(" Aucune semaine trouvée dans la base")
            return None
        print("\nSemaines disponibles:")
        for w in weeks:
            print(f"  id={w['id']} - Semaine {w['week_number']} ({w['start_date']} → {w['end_date']}) [year={w['year_id']}]")
        try:
            wsel = input("\nEntrez l'id de la semaine à utiliser (laisser vide pour la plus récente): ").strip()
            if wsel:
                return int(wsel)
            else:
                # si filtré par année, prendre la dernière de la liste (plus grande semaine)
                return weeks[-1]['id']
        except Exception:
            return weeks[-1]['id']
    finally:
        cur.close()
        conn.close()

def get_available_entities():
    """Récupère les entités disponibles (enseignants, salles, groupes)"""
    conn = mysql.connector.connect(
        host='127.0.0.1',
        port=33066,
        database='edt_app',
        user='edt_user',
        password='userpassword'
    )
    cursor = conn.cursor(dictionary=True)
    
    try:
        print("Entités disponibles:\n")
        
        # Enseignants (tous)
        cursor.execute(
            """
            SELECT t.id, u.first_name, u.last_name, u.acronym
            FROM teachers t
            JOIN users u ON t.user_id = u.id
            ORDER BY u.last_name, u.first_name
            """
        )
        teachers = cursor.fetchall()
        print("Enseignants:")
        for t in teachers:
            print(f"   ID {t['id']}: {t['first_name']} {t['last_name']} ({t['acronym']})")

        # Salles (toutes)
        cursor.execute("SELECT id, name, seat_capacity FROM rooms ORDER BY name")
        rooms = cursor.fetchall()
        print("\nSalles:")
        for r in rooms:
            print(f"   ID {r['id']}: {r['name']} ({r['seat_capacity']} places)")

        # Groupes (tous)
        cursor.execute("SELECT id, name FROM `groups` ORDER BY name")
        groups = cursor.fetchall()
        print("\nGroupes:")
        for g in groups:
            print(f"   ID {g['id']}: {g['name']}")
        
        return teachers, rooms, groups
        
    finally:
        cursor.close()
        conn.close()

def display_all_constraints():
    """Affiche toutes les contraintes du système"""
    print("\n" + "="*60)
    print("RÉSUMÉ: Toutes les contraintes actives")
    print("="*60 + "\n")
    
    manager = ConstraintManager()
    # Filtrer l'affichage sur la semaine sélectionnée si définie
    all_constraints = manager.get_all_constraints(week_id=DEFAULT_WEEK_ID)
    
    print("CONTRAINTES ENSEIGNANTS:")
    if all_constraints['teachers']:
        for c in all_constraints['teachers']:
            week_info = "PERMANENTE" if c.get('week_id') is None else f"semaine {c.get('week_id')}"
            print(f"   #{c['id']} ({week_info}): {c['first_name']} {c['last_name']} - "
                  f"{c['day_of_week']} {c['start_time']}-{c['end_time']} "
                  f"[{c['priority']}] - {c['reason']}")
    else:
        print("   Aucune contrainte")
    
    print("\nCONTRAINTES SALLES:")
    if all_constraints['rooms']:
        for c in all_constraints['rooms']:
            week_info = "PERMANENTE" if c.get('week_id') is None else f"semaine {c.get('week_id')}"
            print(f"   #{c['id']} ({week_info}): {c['room_name']} - "
                  f"{c['day_of_week']} {c['start_time']}-{c['end_time']} "
                  f"[{c['priority']}] - {c['reason']}")
    else:
        print("   Aucune contrainte")
    
    print("\nCONTRAINTES GROUPES:")
    if all_constraints['groups']:
        for c in all_constraints['groups']:
            week_info = "PERMANENTE" if c.get('week_id') is None else f"semaine {c.get('week_id')}"
            print(f"   #{c['id']} ({week_info}): {c['group_name']} - "
                  f"{c['day_of_week']} {c['start_time']}-{c['end_time']} "
                  f"[{c['priority']}] - {c['reason']}")
    else:
        print("   Aucune contrainte")
    
    
    print("\nSTATISTIQUES:")
    stats = manager.get_constraint_stats()
    total = 0
    for key, value in stats.items():
        if isinstance(value, dict):
            count = value.get('total_teachers', value.get('total_rooms', 
                             value.get('total_groups', 0)))
            print(f"   - {key.capitalize()}: {count} contrainte(s)")
            total += count if count else 0
    print(f"\n   TOTAL: {total} contraintes actives dans le système")

def display_constraints_for_week(week_id: int):
    """Affiche les contraintes pour une semaine précise"""
    print("\n" + "="*60)
    print(f"RÉSUMÉ: Contraintes actives - Semaine {week_id}")
    print("="*60 + "\n")

    manager = ConstraintManager()
    constraints = manager.get_all_constraints(week_id=week_id)

    def _print_section(title: str, items: list, fmt: callable):
        print(title)
        if items:
            for c in items:
                print("   " + fmt(c))
        else:
            print("   Aucune contrainte")
        print("")

    _print_section("CONTRAINTES ENSEIGNANTS:", constraints['teachers'],
                   lambda c: f"#{c['id']} ({'PERMANENTE' if c.get('week_id') is None else 'semaine ' + str(c.get('week_id'))}): {c['first_name']} {c['last_name']} - {c['day_of_week']} {c['start_time']}-{c['end_time']} [{c['priority']}] - {c['reason']}")
    _print_section("CONTRAINTES SALLES:", constraints['rooms'],
                   lambda c: f"#{c['id']} ({'PERMANENTE' if c.get('week_id') is None else 'semaine ' + str(c.get('week_id'))}): {c['room_name']} - {c['day_of_week']} {c['start_time']}-{c['end_time']} [{c['priority']}] - {c['reason']}")
    _print_section("CONTRAINTES GROUPES:", constraints['groups'],
                   lambda c: f"#{c['id']} ({'PERMANENTE' if c.get('week_id') is None else 'semaine ' + str(c.get('week_id'))}): {c['group_name']} - {c['day_of_week']} {c['start_time']}-{c['end_time']} [{c['priority']}] - {c['reason']}")
    
def display_constraints_by_year(year_id: int):
    """Affiche un récapitulatif des contraintes pour toutes les semaines d'une année"""
    print("\n" + "="*60)
    print(f"RÉCAP: Contraintes par semaine - Année {year_id}")
    print("="*60)

    # Récupérer les semaines de l'année
    conn = mysql.connector.connect(
        host='127.0.0.1', port=33066, database='edt_app', user='edt_user', password='userpassword'
    )
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, week_number, start_date, end_date FROM weeks WHERE year_id = %s ORDER BY week_number", (year_id,))
        weeks = cur.fetchall()
        if not weeks:
            print("\n Aucune semaine pour cette année.")
            return
        manager = ConstraintManager()
        for w in weeks:
            cons = manager.get_all_constraints(week_id=w['id'])
            total = sum(len(cons[k]) for k in cons)
            tcnt = len(cons['teachers'])
            rcnt = len(cons['rooms'])
            gpcnt = len(cons['groups'])
            print(f"\n• Semaine {w['week_number']} (id={w['id']}, {w['start_date']}→{w['end_date']}) :"
                  f" total={total}, enseignants={tcnt}, salles={rcnt}, groupes={gpcnt}")
    finally:
        cur.close()
        conn.close()

def interactive_menu():
    """Menu interactif pour gérer les contraintes"""
    manager = ConstraintManager()
    # Tentative automatique de création de la colonne is_exam si nécessaire.
    # Ceci utilise la logique déjà présente dans ConstraintManager et n'ajoute
    # aucun fichier externe. Les erreurs sont affichées mais n'empêchent pas
    # l'ouverture du menu.
    try:
        manager.ensure_is_exam_column()
    except Exception as e:
        print(f"Avertissement: la migration is_exam a échoué (ignorée): {e}")
    # Sélectionner une année et une semaine et les définir par défaut pour les ajouts
    global DEFAULT_YEAR_ID, DEFAULT_WEEK_ID
    if not DEFAULT_YEAR_ID:
        DEFAULT_YEAR_ID = choose_year()
    if not DEFAULT_WEEK_ID:
        DEFAULT_WEEK_ID = choose_week(DEFAULT_YEAR_ID)
    if DEFAULT_WEEK_ID:
        manager.set_default_week(DEFAULT_WEEK_ID)
    
    while True:
        print("\n" + "="*60)
        print("   GESTIONNAIRE DE CONTRAINTES - MENU")
        print("="*60)
        print(f"\nContexte: Année={DEFAULT_YEAR_ID} | Semaine={DEFAULT_WEEK_ID}")
        print("\n1. Ajouter contrainte enseignant")
        print("2. Ajouter contrainte salle")
        print("3. Ajouter contrainte groupe")
        print("4. Voir toutes les contraintes")
        print("5. Modifier priorité d'une contrainte")
        print("6. Supprimer une contrainte")
        print("7. Vider toutes les tables de contraintes")
        print("8. Changer d'année/semaine")
        print("9. Voir contraintes pour une semaine (sélection)")
        print("10. Voir contraintes par semaine pour l'année courante")
        print("11. Modifier contrainte (local)")
        print("12. Marquer/démarquer un slot comme examen")
        print("\n0. Quitter")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == "0":
            print("\nAu revoir!")
            break
        
        elif choice == "1":
            print("\n AJOUT CONTRAINTE ENSEIGNANT")
            try:
                teacher_id = int(input("ID enseignant: "))
                day = input("Jour (Lundi, Mardi, ...): ")
                start_time = input("Heure début (HH:MM): ")
                end_time = input("Heure fin (HH:MM): ")
                reason = input("Raison: ")
                priority_str = input("Priorité (hard/medium/soft): ").lower()
                is_permanent = input("Contrainte permanente ? (oui/non) [non]: ").strip().lower()
                
                priority_map = {
                    'hard': ConstraintPriority.HARD,
                    'medium': ConstraintPriority.MEDIUM,
                    'soft': ConstraintPriority.SOFT
                }
                priority = priority_map.get(priority_str, ConstraintPriority.MEDIUM)
                
                # Si permanent, utiliser force_permanent=True
                is_perm = is_permanent in ['oui', 'o', 'yes', 'y']
                
                constraint_id = manager.add_teacher_unavailability(
                    teacher_id, day, start_time, end_time, reason, priority, force_permanent=is_perm
                )
                perm_info = " (PERMANENTE)" if is_perm else f" (semaine {DEFAULT_WEEK_ID})"
                print(f"\n Contrainte #{constraint_id} créée avec succès{perm_info}!")
                
            except Exception as e:
                print(f"\n Erreur: {e}")
        
        elif choice == "4":
            display_all_constraints()
        elif choice == "7":
            confirm = input("\nÊtes-vous sûr de vouloir VIDER toutes les tables de contraintes ? (oui/non): ").strip().lower()
            if confirm in ["oui", "o", "yes", "y"]:
                try:
                    manager.clear_all_constraints(hard=True)
                    print("\n Tables vidées")
                except Exception as e:
                    print(f"\n Erreur: {e}")
            else:
                print("\nOpération annulée")
        elif choice == "8":
            # changer d'année/semaine
            new_year = choose_year()
            if new_year:
                DEFAULT_YEAR_ID = new_year
                DEFAULT_WEEK_ID = choose_week(DEFAULT_YEAR_ID)
                if DEFAULT_WEEK_ID:
                    manager.set_default_week(DEFAULT_WEEK_ID)
                print(f"Contexte changé → Année={DEFAULT_YEAR_ID} Semaine={DEFAULT_WEEK_ID}")
        elif choice == "9":
            # afficher contraintes pour une semaine choisie
            w = choose_week(DEFAULT_YEAR_ID)
            if w:
                display_constraints_for_week(w)
        elif choice == "10":
            # récapitulatif par semaine pour l'année courante
            if DEFAULT_YEAR_ID:
                display_constraints_by_year(DEFAULT_YEAR_ID)
            else:
                print("\n Aucune année sélectionnée")
        elif choice == "11":
            # Mise à jour locale d'une contrainte via ConstraintManager
            try:
                print("\nMODIFIER CONTRAINTE (LOCAL)")
                ctype = input("Type (teacher/room/group): ").strip()
                cid = int(input("ID de la contrainte: "))
                print("Entrez les champs à mettre à jour (laisser vide pour ignorer):")
                day = input("Jour (Lundi, Mardi ...): ").strip()
                start_time = input("Heure début (HH:MM): ").strip()
                end_time = input("Heure fin (HH:MM): ").strip()
                reason = input("Raison: ").strip()
                priority = input("Priorité (hard/medium/soft): ").strip().lower()

                updates = {}
                if day:
                    updates['day_of_week'] = day
                if start_time:
                    updates['start_time'] = start_time
                if end_time:
                    updates['end_time'] = end_time
                if reason:
                    updates['reason'] = reason
                if priority:
                    if priority not in ('hard', 'medium', 'soft'):
                        print('Priorité invalide, utiliser hard/medium/soft')
                        continue
                    updates['priority'] = priority

                # Appeler le manager local
                if ctype == 'teacher':
                    ok = manager.update_teacher_constraint(cid, updates)
                elif ctype == 'room':
                    ok = manager.update_constraint('room', cid, updates)
                elif ctype == 'group':
                    ok = manager.update_constraint('group', cid, updates)
                else:
                    print('Type invalide, choisir teacher/room/group')
                    continue

                if ok:
                    print('\n Contrainte mise à jour avec succès')
                else:
                    print('\n Contrainte non trouvée ou aucune modification effectuée')
            except Exception as e:
                print(f"Erreur lors de la mise à jour: {e}")
        elif choice == "12":
            try:
                print("\nMARQUER / DEMARQUER SLOT COMME EXAMEN")
                sid = int(input("ID du slot (slots.id) : "))
                cur_state = input("Marquer comme examen ? (oui/non) [oui]: ").strip().lower()
                mark = True if cur_state in ('', 'oui', 'o', 'yes', 'y') else False
                ok = manager.set_slot_exam(sid, is_exam=mark)
                if ok:
                    print(f"Slot {sid} mis à jour (is_exam={1 if mark else 0})")
                else:
                    print(f"Slot {sid} non trouvé ou aucune modification effectuée")
            except Exception as e:
                print(f"Erreur lors du marquage examen: {e}")
        
        else:
            print("\n Option non implémentée dans ce menu de démo")
        
        input("\nAppuyez sur Entrée pour continuer...")

def main():
    """Fonction principale - Lance le menu interactif"""
    print("\n" + "="*60)
    print("   API GESTIONNAIRE DE CONTRAINTES")
    print("="*60)
    
    # Choisir l'année puis la semaine pour cette session
    global DEFAULT_YEAR_ID, DEFAULT_WEEK_ID
    DEFAULT_YEAR_ID = choose_year()
    DEFAULT_WEEK_ID = choose_week(DEFAULT_YEAR_ID)

    # Afficher les entités disponibles
    get_available_entities()
    
    # Menu interactif
    interactive_menu()

if __name__ == "__main__":
    main()
