#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour ajouter des contraintes globales de temps
Par exemple: pause déjeuner obligatoire 12h-13h30
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from constraint_manager import ConstraintManager, ConstraintPriority
import mysql.connector

def add_no_course_slot(manager: ConstraintManager, start_time: str, end_time: str, reason: str, week_id=None, force_permanent=False):
    """
    Ajoute une contrainte de créneau sans cours pour tous les groupes
    """
    conn = manager._get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Récupérer tous les groupes actifs
        cursor.execute("SELECT id, name FROM `groups` ORDER BY name")
        groups = cursor.fetchall()
        
        if not groups:
            print("Aucun groupe trouvé dans la base")
            return
        
        # Si force_permanent est demandé, on ignore week_id fourni
        if force_permanent:
            actual_week_id = None
            week_label = "PERMANENTE"
        elif week_id is not None:
            actual_week_id = week_id
            week_label = f"semaine {week_id}"
        else:
            actual_week_id = manager.default_week_id
            week_label = f"semaine {actual_week_id}" if actual_week_id else "PERMANENTE"
        
        print(f"\nAjout de créneau bloqué ({start_time}-{end_time}) pour {len(groups)} groupes...")
        print(f"   Raison: {reason}")
        
        added_count = 0
        
        # Pour chaque jour de la semaine
        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
        
        for group in groups:
            group_id = group['id']
            group_name = group['name']
            
            for day in days:
                try:
                    constraint_id = manager.add_group_unavailability(
                        group_id=group_id,
                        day=day,
                        start_time=start_time,
                        end_time=end_time,
                        reason=reason,
                        priority=ConstraintPriority.HARD,
                        week_id=actual_week_id
                    )
                    added_count += 1
                except Exception as e:
                    print(f"Erreur pour {group_name} {day}: {e}")
        
        print(f"\n{added_count} contraintes ajoutées ({week_label})")
        print(f"   Groupes concernés: {', '.join([g['name'] for g in groups])}")
        
    finally:
        cursor.close()
        conn.close()


def main():
    """Menu interactif pour ajouter des contraintes globales de temps"""
    manager = ConstraintManager()
    
    print("\n" + "="*80)
    print("  CONTRAINTES GLOBALES DE TEMPS")
    print("="*80)
    
    print("\nOptions disponibles:")
    print("  1. Ajouter un créneau bloqué personnalisé")
    print("  0. Quitter")
    
    choice = input("\nVotre choix: ").strip()
    
    if choice == "1":
        print("\nCRÉNEAU BLOQUÉ PERSONNALISÉ")
        start_time = input("Heure de début (HH:MM): ").strip()
        end_time = input("Heure de fin (HH:MM): ").strip()
        reason = input("Raison: ").strip()
        
        permanent = input("Contrainte permanente ? (o/n) [o]: ").strip().lower()
        force_permanent = permanent != 'n'
        
        if not force_permanent:
            week_id_str = input("ID de la semaine (laisser vide pour permanent): ").strip()
            week_id = int(week_id_str) if week_id_str else None
        else:
            week_id = None
        
        confirm = input(f"\nAjouter créneau bloqué {start_time}-{end_time} pour TOUS les groupes ? (o/n): ").strip().lower()
        if confirm == 'o':
            add_no_course_slot(manager, start_time, end_time, reason, week_id=week_id, force_permanent=force_permanent)
        else:
            print("Annulé")
    
    elif choice == "0":
        print("Au revoir!")
        return
    
    else:
        print("Choix invalide")


if __name__ == "__main__":
    main()
