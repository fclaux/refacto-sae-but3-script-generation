#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de validation des contraintes pour la génération d'emploi du temps
Intègre les contraintes définies dans le système avec l'algorithme de génération
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, time
from constraint_manager import ConstraintManager, ConstraintType, ConstraintPriority


class ConstraintValidator:
    """Validateur de contraintes pour la génération d'emploi du temps"""
    
    # Mapping des jours de la semaine
    DAYS_MAP = {
        "Lundi": 0,
        "Mardi": 1,
        "Mercredi": 2,
        "Jeudi": 3,
        "Vendredi": 4,
        "Samedi": 5,
        "Dimanche": 6
    }
    
    # Horaires standards (créneaux de 30 minutes)
    TIME_SLOTS = [
        "8:00", "8:30", "9:00", "9:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
        "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30"
    ]
    
    def __init__(self, manager=None, week_id: Optional[int] = None):
        """
        Initialise le validateur de contraintes
        
        Args:
            manager: Instance de ConstraintManager (optionnel, créée si non fournie)
            week_id: ID de la semaine pour laquelle valider les contraintes
        """
        self.manager = manager if manager is not None else ConstraintManager()
        self.week_id = week_id
        self._load_constraints()
    
    def _load_constraints(self):
        """Charge toutes les contraintes actives pour la semaine"""
        all_constraints = self.manager.get_all_constraints(week_id=self.week_id)
        
        self.teacher_constraints = all_constraints['teachers']
        self.room_constraints = all_constraints['rooms']
        self.group_constraints = all_constraints['groups']
        
        # Indexer les contraintes par entité pour un accès rapide
        self._index_constraints()
    
    def _index_constraints(self):
        """Crée des index pour accéder rapidement aux contraintes"""
        # Index par teacher_id
        self.teacher_constraints_by_id = {}
        for c in self.teacher_constraints:
            teacher_id = c['teacher_id']
            if teacher_id not in self.teacher_constraints_by_id:
                self.teacher_constraints_by_id[teacher_id] = []
            self.teacher_constraints_by_id[teacher_id].append(c)
        
        # Index par room_id
        self.room_constraints_by_id = {}
        for c in self.room_constraints:
            room_id = c['room_id']
            if room_id not in self.room_constraints_by_id:
                self.room_constraints_by_id[room_id] = []
            self.room_constraints_by_id[room_id].append(c)
        
        # Index par group_id
        self.group_constraints_by_id = {}
        for c in self.group_constraints:
            group_id = c['group_id']
            if group_id not in self.group_constraints_by_id:
                self.group_constraints_by_id[group_id] = []
            self.group_constraints_by_id[group_id].append(c)
    
    def _time_to_slot_index(self, time_str: str):
        """Convertit une heure (HH:MM ou HH:MM:SS) en index de créneau"""
        # Normaliser le format (enlever les secondes si présentes)
        if time_str.count(':') == 2:
            time_str = ':'.join(time_str.split(':')[:2])
        
        try:
            return self.TIME_SLOTS.index(time_str)
        except ValueError:
            # Si l'heure n'est pas dans la liste standard, calculer l'index
            hours, minutes = map(int, time_str.split(':'))
            base_slot = (hours - 8) * 2  # 2 créneaux par heure
            if minutes >= 30:
                base_slot += 1
            return max(0, min(base_slot, len(self.TIME_SLOTS) - 1))
    
    def _slot_index_to_time(self, slot_index: int):
        """Convertit un index de créneau en heure (HH:MM)"""
        if 0 <= slot_index < len(self.TIME_SLOTS):
            return self.TIME_SLOTS[slot_index]
        # Calcul pour les slots en dehors de la plage standard
        hours = 8 + slot_index // 2
        minutes = 30 if slot_index % 2 == 1 else 0
        return f"{hours:02d}:{minutes:02d}"
    
    def _check_time_overlap(self, start1: str, end1: str, start2: str, end2: str):
        """
        Vérifie si deux créneaux horaires se chevauchent
        """
        start1_idx = self._time_to_slot_index(start1)
        end1_idx = self._time_to_slot_index(end1)
        start2_idx = self._time_to_slot_index(start2)
        end2_idx = self._time_to_slot_index(end2)
        
        return not (end1_idx <= start2_idx or end2_idx <= start1_idx)
    
    def validate_teacher_availability(self, teacher_id: int, day: str, start_time: str, end_time: str):
        """
        Vérifie si un enseignant est disponible pour un créneau donné
        """
        if teacher_id not in self.teacher_constraints_by_id:
            return True, None, "OK"
        
        violations = []
        max_priority = None
        
        for constraint in self.teacher_constraints_by_id[teacher_id]:
            if constraint['day_of_week'] == day:
                if self._check_time_overlap(
                    start_time, end_time,
                    str(constraint['start_time']), str(constraint['end_time'])
                ):
                    priority = constraint['priority']
                    reason = constraint['reason'] or "Indisponibilité"
                    violations.append(f"{priority.upper()}: {reason}")
                    
                    if max_priority is None or self._priority_level(priority) > self._priority_level(max_priority):
                        max_priority = priority
        
        if violations:
            teacher_name = f"{constraint['first_name']} {constraint['last_name']}"
            message = f"Enseignant {teacher_name} indisponible: " + "; ".join(violations)
            return False, max_priority, message
        
        return True, None, "OK"
    
    def validate_room_availability(self, room_id: int, day: str, start_time: str, end_time: str):
        """
        Vérifie si une salle est disponible pour un créneau donné
        """
        if room_id not in self.room_constraints_by_id:
            return True, None, "OK"
        
        violations = []
        max_priority = None
        
        for constraint in self.room_constraints_by_id[room_id]:
            if constraint['day_of_week'] == day:
                if self._check_time_overlap(
                    start_time, end_time,
                    str(constraint['start_time']), str(constraint['end_time'])
                ):
                    priority = constraint['priority']
                    reason = constraint['reason'] or "Indisponibilité"
                    violations.append(f"{priority.upper()}: {reason}")
                    
                    if max_priority is None or self._priority_level(priority) > self._priority_level(max_priority):
                        max_priority = priority
        
        if violations:
            room_name = constraint['room_name']
            message = f"Salle {room_name} indisponible: " + "; ".join(violations)
            return False, max_priority, message
        
        return True, None, "OK"
    
    def validate_group_availability(self, group_id: int, day: str, start_time: str, end_time: str):
        """
        Vérifie si un groupe est disponible pour un créneau donné
        """
        if group_id not in self.group_constraints_by_id:
            return True, None, "OK"
        
        violations = []
        max_priority = None
        
        for constraint in self.group_constraints_by_id[group_id]:
            if constraint['day_of_week'] == day:
                if self._check_time_overlap(
                    start_time, end_time,
                    str(constraint['start_time']), str(constraint['end_time'])
                ):
                    priority = constraint['priority']
                    reason = constraint['reason'] or "Indisponibilité"
                    violations.append(f"{priority.upper()}: {reason}")
                    
                    if max_priority is None or self._priority_level(priority) > self._priority_level(max_priority):
                        max_priority = priority
        
        if violations:
            group_name = constraint['group_name']
            message = f"Groupe {group_name} indisponible: " + "; ".join(violations)
            return False, max_priority, message
        
        return True, None, "OK"
    
    def _priority_level(self, priority: str):
        """Convertit une priorité en niveau numérique (plus haut = plus important)"""
        priority_levels = {
            'hard': 3,
            'medium': 2,
            'soft': 1
        }
        return priority_levels.get(priority.lower(), 0)
    
    def validate_course_slot(self, teacher_id: int, room_id: int, group_ids: List[int], day: str, start_time: str, end_time: str):
        """
        Valide un créneau de cours complet (enseignant + salle + groupes)
        """
        violations = []
        has_hard_violation = False
        
        # Vérifier l'enseignant
        is_valid, priority, message = self.validate_teacher_availability(
            teacher_id, day, start_time, end_time
        )
        if not is_valid:
            violations.append({
                'type': 'teacher',
                'priority': priority,
                'message': message
            })
            if priority == 'hard':
                has_hard_violation = True
        
        # Vérifier la salle
        is_valid, priority, message = self.validate_room_availability(
            room_id, day, start_time, end_time
        )
        if not is_valid:
            violations.append({
                'type': 'room',
                'priority': priority,
                'message': message
            })
            if priority == 'hard':
                has_hard_violation = True
        
        # Vérifier les groupes
        for group_id in group_ids:
            is_valid, priority, message = self.validate_group_availability(
                group_id, day, start_time, end_time
            )
            if not is_valid:
                violations.append({
                    'type': 'group',
                    'priority': priority,
                    'message': message,
                    'group_id': group_id
                })
                if priority == 'hard':
                    has_hard_violation = True
        
        return {
            'is_valid': not has_hard_violation,
            'can_proceed': not has_hard_violation,
            'violations': violations,
            'has_soft_violations': any(v['priority'] in ['soft', 'medium'] for v in violations)
        }
    
    def get_blocked_slots_for_teacher(self, teacher_id: int):
        """
        Retourne tous les créneaux bloqués pour un enseignant
        """
        blocked = {}
        
        if teacher_id in self.teacher_constraints_by_id:
            for constraint in self.teacher_constraints_by_id[teacher_id]:
                if constraint['priority'] == 'hard':
                    day = constraint['day_of_week']
                    if day not in blocked:
                        blocked[day] = []
                    blocked[day].append((
                        str(constraint['start_time']),
                        str(constraint['end_time'])
                    ))
        
        return blocked
    
    def get_blocked_slots_for_room(self, room_id: int):
        """
        Retourne tous les créneaux bloqués pour une salle
        """
        blocked = {}
        
        if room_id in self.room_constraints_by_id:
            for constraint in self.room_constraints_by_id[room_id]:
                if constraint['priority'] == 'hard':
                    day = constraint['day_of_week']
                    if day not in blocked:
                        blocked[day] = []
                    blocked[day].append((
                        str(constraint['start_time']),
                        str(constraint['end_time'])
                    ))
        
        return blocked
    
    def get_blocked_slots_for_group(self, group_id: int):
        """
        Retourne tous les créneaux bloqués pour un groupe
        """
        blocked = {}
        
        if group_id in self.group_constraints_by_id:
            for constraint in self.group_constraints_by_id[group_id]:
                if constraint['priority'] == 'hard':
                    day = constraint['day_of_week']
                    if day not in blocked:
                        blocked[day] = []
                    blocked[day].append((
                        str(constraint['start_time']),
                        str(constraint['end_time'])
                    ))
        
        return blocked
    
    def get_summary(self):
        """Retourne un résumé des contraintes chargées"""
        return {
            'week_id': self.week_id,
            'total_constraints': (
                len(self.teacher_constraints) +
                len(self.room_constraints) +
                len(self.group_constraints)
            ),
            'teachers': len(self.teacher_constraints_by_id),
            'rooms': len(self.room_constraints_by_id),
            'groups': len(self.group_constraints_by_id),
            'teacher_constraints': len(self.teacher_constraints),
            'room_constraints': len(self.room_constraints),
            'group_constraints': len(self.group_constraints)
        }


if __name__ == "__main__":
    # Test du validateur
    print("=== TEST DU VALIDATEUR DE CONTRAINTES ===\n")
    
    validator = ConstraintValidator(week_id=1)
    summary = validator.get_summary()
    
    print("Résumé des contraintes:")
    print(f"  - Semaine: {summary['week_id']}")
    print(f"  - Total contraintes: {summary['total_constraints']}")
    print(f"  - Enseignants concernés: {summary['teachers']}")
    print(f"  - Salles concernées: {summary['rooms']}")
    print(f"  - Groupes concernés: {summary['groups']}")
