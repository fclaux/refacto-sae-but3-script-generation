"""
Parser pour extraire les affectations de cours depuis une solution OR-Tools.
Respecte le principe Single Responsibility (SOLID).
"""
from typing import Dict, Any, List, Optional
from course_data_models import CourseAssignment


class SolutionParser:
    """Extrait les informations d'affectation depuis une solution du solver."""

    def __init__(self, solution: Dict[str, Any], data: Dict[str, Any]):
        self.solver = solution['solver']
        self._vars = solution['vars']
        self.data = data

    def parse_assignments(self) -> List[CourseAssignment]:
        """
        Parse toutes les affectations de cours depuis la solution.

        Returns:
            Liste des affectations de cours valides
        """
        assignments = []

        for course in self.data['cours']:
            course_id = course['id']

            start_slot = self._find_start_slot(course_id)
            room_idx = self._find_room_index(course_id)
            teacher_idx = self._find_teacher_index(course_id)

            if self._is_valid_assignment(start_slot, room_idx, teacher_idx):
                assignment = self._create_assignment(course_id, start_slot, room_idx, teacher_idx)
                assignments.append(assignment)

        return assignments

    def _find_start_slot(self, course_id: int) -> Optional[int]:
        """Trouve le créneau de début pour un cours."""
        for slot_key, var in self._vars['start'].items():
            if var is not None and var.Name().startswith(f"start_{course_id}"):
                if self.solver.Value(var):
                    return slot_key[1] if isinstance(slot_key, tuple) else None
        return None

    def _find_room_index(self, course_id: int) -> Optional[int]:
        """Trouve l'index de la salle affectée à un cours."""
        for room_key, var in self._vars['y_salle'].items():
            if var.Name().startswith(f"y_salle_{course_id}"):
                if self.solver.Value(var):
                    return room_key[1] if isinstance(room_key, tuple) else None
        return None

    def _find_teacher_index(self, course_id: int) -> Optional[int]:
        """Trouve l'index du professeur affecté à un cours."""
        for teacher_key, var in self._vars['z_prof'].items():
            if var.Name().startswith(f"z_prof_{course_id}"):
                if self.solver.Value(var):
                    return teacher_key[1] if isinstance(teacher_key, tuple) else None
        return None

    def _is_valid_assignment(self, start_slot: Optional[int],
                            room_idx: Optional[int],
                            teacher_idx: Optional[int]) -> bool:
        """Vérifie si une affectation est valide."""
        return all(x is not None for x in [start_slot, room_idx, teacher_idx])

    def _create_assignment(self, course_id: int, start_slot: int,
                          room_idx: int, teacher_idx: int) -> CourseAssignment:
        """Crée un objet CourseAssignment à partir des indices."""
        room_name = list(self.data['salles'].keys())[room_idx]
        teacher_name = self.data['profs'][teacher_idx]
        duration = self.data['duree_cours'][course_id]

        return CourseAssignment(
            course_id=course_id,
            start_slot=start_slot,
            room_id=room_idx,
            teacher_id=teacher_idx,
            room_name=room_name,
            teacher_name=teacher_name,
            duration=duration
        )

