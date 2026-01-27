#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'intégration des contraintes avec OR-Tools CP-SAT Solver
Permet d'ajouter les contraintes métier à l'algorithme de génération d'emploi du temps
"""

from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ortools.sat.python import cp_model

try:
    from ortools.sat.python import cp_model
except ImportError:
    print("OR-Tools non installé. Installez-le avec: pip install ortools")
    cp_model = None

from constraint_validator import ConstraintValidator


class ConstraintIntegration:
    """Intègre les contraintes métier dans le modèle OR-Tools"""
    
    def __init__(self, model, week_id: Optional[int] = None):
        """
        Initialise l'intégration des contraintes
        """
        self.model = model
        self.validator = ConstraintValidator(week_id=week_id)
        self.week_id = week_id
    
    def add_teacher_unavailability_constraints(self, course_vars: Dict, teacher_mapping: Dict[int, int],slot_mapping: Dict[int, Tuple[str, str]]):
        """
        Ajoute les contraintes d'indisponibilité des enseignants au modèle
        """
        count = 0
        
        for teacher_id_db, teacher_idx in teacher_mapping.items():
            blocked_slots = self.validator.get_blocked_slots_for_teacher(teacher_id_db)
            
            for day, time_ranges in blocked_slots.items():
                # Trouver les slots correspondant à ce jour et ces heures
                blocked_slot_indices = self._find_blocked_slots(day, time_ranges, slot_mapping)
                
                # Ajouter une contrainte pour chaque slot bloqué
                for slot_idx in blocked_slot_indices:
                    # Interdire tous les cours assignés à cet enseignant sur ce slot
                    for key, var in course_vars.items():
                        course_id, assigned_teacher_idx, room_idx, assigned_slot = key
                        if assigned_teacher_idx == teacher_idx and assigned_slot == slot_idx:
                            # Forcer cette variable à 0 (cours non assigné)
                            self.model.Add(var == 0)
                            count += 1
        
        return count
    
    def add_room_unavailability_constraints(self, course_vars: Dict, room_mapping: Dict[int, int], slot_mapping: Dict[int, Tuple[str, str]]):
        """
        Ajoute les contraintes d'indisponibilité des salles au modèle
        """
        count = 0
        
        for room_id_db, room_idx in room_mapping.items():
            blocked_slots = self.validator.get_blocked_slots_for_room(room_id_db)
            
            for day, time_ranges in blocked_slots.items():
                blocked_slot_indices = self._find_blocked_slots(day, time_ranges, slot_mapping)
                
                for slot_idx in blocked_slot_indices:
                    for key, var in course_vars.items():
                        course_id, teacher_idx, assigned_room_idx, assigned_slot = key
                        if assigned_room_idx == room_idx and assigned_slot == slot_idx:
                            self.model.Add(var == 0)
                            count += 1
        
        return count
    
    def add_group_unavailability_constraints(self, course_vars: Dict, group_mapping: Dict[int, int], course_groups: Dict[int, List[int]], slot_mapping: Dict[int, Tuple[str, str]]):
        """
        Ajoute les contraintes d'indisponibilité des groupes au modèle
        """
        count = 0
        
        for group_id_db, group_idx in group_mapping.items():
            blocked_slots = self.validator.get_blocked_slots_for_group(group_id_db)
            
            for day, time_ranges in blocked_slots.items():
                blocked_slot_indices = self._find_blocked_slots(day, time_ranges, slot_mapping)
                
                for slot_idx in blocked_slot_indices:
                    # Trouver tous les cours concernant ce groupe
                    for key, var in course_vars.items():
                        course_id, teacher_idx, room_idx, assigned_slot = key
                        
                        # Vérifier si ce cours concerne le groupe bloqué
                        if course_id in course_groups:
                            if group_id_db in course_groups[course_id]:
                                if assigned_slot == slot_idx:
                                    self.model.Add(var == 0)
                                    count += 1
        
        return count
    
    def _find_blocked_slots(self, day: str, time_ranges: List[Tuple[str, str]], slot_mapping: Dict[int, Tuple[str, str]]):
        """
        Trouve les indices de slots bloqués correspondant à un jour et des plages horaires
        """
        blocked = set()
        
        for slot_idx, (slot_day, slot_time) in slot_mapping.items():
            if slot_day == day:
                # Vérifier si ce slot tombe dans une des plages bloquées
                for start_time, end_time in time_ranges:
                    if self._is_time_in_range(slot_time, start_time, end_time):
                        blocked.add(slot_idx)
                        break
        
        return blocked
    
    def _is_time_in_range(self, time_str: str, start_str: str, end_str: str):
        """
        Vérifie si une heure est dans une plage horaire
        """
        # Normaliser les formats (enlever les secondes si présentes)
        time_str = time_str.split(':')[:2]
        start_str = start_str.split(':')[:2]
        end_str = end_str.split(':')[:2]
        
        time_minutes = int(time_str[0]) * 60 + int(time_str[1])
        start_minutes = int(start_str[0]) * 60 + int(start_str[1])
        end_minutes = int(end_str[0]) * 60 + int(end_str[1])
        
        return start_minutes <= time_minutes < end_minutes
    
    def add_all_constraints(self, course_vars: Dict, teacher_mapping: Dict[int, int], room_mapping: Dict[int, int], group_mapping: Dict[int, int], course_groups: Dict[int, List[int]], slot_mapping: Dict[int, Tuple[str, str]]):
        """
        Ajoute toutes les contraintes au modèle
        """
        stats = {}
        
        # Contraintes enseignants
        print("Contraintes enseignants...", end=" ")
        stats['teachers'] = self.add_teacher_unavailability_constraints(
            course_vars, teacher_mapping, slot_mapping
        )
        print(f"{stats['teachers']} contraintes ajoutées")
        
        # Contraintes salles
        print("Contraintes salles...", end=" ")
        stats['rooms'] = self.add_room_unavailability_constraints(
            course_vars, room_mapping, slot_mapping
        )
        print(f"{stats['rooms']} contraintes ajoutées")
        
        # Contraintes groupes
        print("Contraintes groupes...", end=" ")
        stats['groups'] = self.add_group_unavailability_constraints(
            course_vars, group_mapping, course_groups, slot_mapping
        )
        print(f"{stats['groups']} contraintes ajoutées")
        
        stats['total'] = stats['teachers'] + stats['rooms'] + stats['groups']
        print(f"\nTotal: {stats['total']} contraintes métier ajoutées au modèle\n")
        
        return stats


def integrate_constraints_to_model(model, course_vars: Dict, teacher_mapping: Dict[int, int], room_mapping: Dict[int, int], group_mapping: Dict[int, int], course_groups: Dict[int, List[int]], slot_mapping: Dict[int, Tuple[str, str]], week_id: Optional[int] = None):
    """
    Fonction utilitaire pour intégrer facilement les contraintes dans un modèle OR-Tools
    """
    integration = ConstraintIntegration(model, week_id)
    return integration.add_all_constraints(
        course_vars,
        teacher_mapping,
        room_mapping,
        group_mapping,
        course_groups,
        slot_mapping
    )


if __name__ == "__main__":
    print("=== MODULE D'INTÉGRATION DES CONTRAINTES ===\n")
    
    # Test avec un validateur
    validator = ConstraintValidator(week_id=1)
    summary = validator.get_summary()
    print(f"\nContraintes disponibles pour la semaine {summary['week_id']}:")
    print(f"   - {summary['teacher_constraints']} contraintes enseignants")
    print(f"   - {summary['room_constraints']} contraintes salles")
    print(f"   - {summary['group_constraints']} contraintes groupes")
    print(f"   - Total: {summary['total_constraints']} contraintes")
