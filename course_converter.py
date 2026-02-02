"""
Convertisseur de cours pour la génération graphique.
Respecte le principe Single Responsibility (SOLID).
"""
from typing import List, Tuple, Dict
from course_data_models import CourseScheduleInfo
from group_classifier import GroupClassifier
from time_formatter import DAYS


class CourseConverter:
    """Convertit les cours en format pour la génération graphique."""

    def __init__(self, group_classifier: GroupClassifier):
        self._group_classifier = group_classifier

    def convert_to_room_lists(self, courses: List[CourseScheduleInfo],
                             room_list: List[str]) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        """
        Convertit une liste de cours en 3 listes par année (B1, B2, B3).

        Args:
            courses: Liste des cours à convertir
            room_list: Liste des noms de salles

        Returns:
            Tuple de 3 listes (B1, B2, B3) contenant les tuples de cours
        """
        b1_courses, b2_courses, b3_courses = [], [], []

        for course in courses:
            tuple_course = self._course_to_tuple(course, room_list)
            year_level = self._extract_year_level(course.name)

            if year_level == "B1":
                b1_courses.append(tuple_course)
            elif year_level == "B2":
                b2_courses.append(tuple_course)
            else:
                b3_courses.append(tuple_course)

        return b1_courses, b2_courses, b3_courses

    def _course_to_tuple(self, course: CourseScheduleInfo, room_list: List[str]) -> tuple:
        """Convertit un CourseScheduleInfo en tuple pour l'affichage."""
        day_name = DAYS[course.day] if course.day < len(DAYS) else f"Jour_{course.day}"

        # Parse le nom du cours: TYPE_NAME_GROUP_...
        parts = course.name.split('_')
        course_type = parts[0] if len(parts) > 0 else ""
        course_name = parts[1] if len(parts) > 1 else course.name
        group = parts[-2] if len(parts) > 2 and '_' in course.name else "UNKNOWN"

        # Récupère le nom de la salle
        room_name = room_list[course.room - 1] if isinstance(course.room, int) and course.room <= len(room_list) else str(course.room)

        return (
            day_name,
            course.start_hour,
            course.duration,
            course_name,
            course.teacher,
            room_name,
            course_type,
            self._group_classifier.group_to_indices(group)
        )

    def _extract_year_level(self, course_name: str) -> str:
        """Extrait le niveau d'année depuis le nom du cours."""
        if '_' not in course_name:
            return "B3"

        parts = course_name.split('_')
        group = parts[-2] if len(parts) > 1 else "UNKNOWN"

        return self._group_classifier.get_year_level(group)

