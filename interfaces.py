"""
Interfaces (abstractions) pour l'application d'emploi du temps.
Respecte le Dependency Inversion Principle (SOLID).

Les modules de haut niveau dépendent de ces abstractions,
pas des implémentations concrètes.

Utilise Protocol (PEP 544) pour le structural subtyping (duck typing),
ce qui est plus pythonique et moins intrusif que ABC.
"""
from typing import Protocol, List, Dict, Any, Tuple, Optional
from course_data_models import CourseAssignment, CourseScheduleInfo


# ==============================================================================
# INTERFACES POUR LE FORMATAGE ET LA CONVERSION
# ==============================================================================

class ITimeFormatter(Protocol):
    """Interface pour le formatage des créneaux horaires."""

    def slot_to_time(self, slot: int) -> str:
        """Convertit un créneau en format horaire (HH:MM-HH:MM)."""
        ...

    def get_day_name(self, day_index: int) -> str:
        """Retourne le nom du jour à partir de son index."""
        ...


class IGroupClassifier(Protocol):
    """Interface pour la classification des groupes d'étudiants."""

    def get_year_level(self, group: str) -> str:
        """Retourne le niveau d'année pour un groupe (B1, B2, B3)."""
        ...

    def group_to_indices(self, group: str) -> Optional[List]:
        """Convertit un groupe en indices pour l'affichage."""
        ...


# ==============================================================================
# INTERFACES POUR LE PARSING ET LA CONSTRUCTION
# ==============================================================================

class ISolutionParser(Protocol):
    """Interface pour parser les solutions OR-Tools."""

    def parse_assignments(self) -> List[CourseAssignment]:
        """Parse toutes les affectations de cours depuis la solution."""
        ...


class IScheduleBuilder(Protocol):
    """Interface pour construire un emploi du temps."""

    def build_planning(self, assignments: List[CourseAssignment]) -> Dict[int, List[tuple]]:
        """Construit un planning en associant chaque créneau aux cours."""
        ...

    def build_course_schedule_info(self, assignments: List[CourseAssignment]) -> List[CourseScheduleInfo]:
        """Construit une liste de CourseScheduleInfo pour chaque cours."""
        ...


# ==============================================================================
# INTERFACES POUR L'AFFICHAGE
# ==============================================================================

class IConsolePrinter(Protocol):
    """Interface pour l'affichage console."""

    def print_schedule(self, planning: Dict[int, List[tuple]], actual_starts: Dict[int, int]) -> None:
        """Affiche l'emploi du temps jour par jour dans la console."""
        ...


class ICourseConverter(Protocol):
    """Interface pour la conversion de cours."""

    def convert_to_room_lists(
        self,
        courses: List[CourseScheduleInfo],
        room_list: List[str]
    ) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        """Convertit une liste de cours en 3 listes par année (B1, B2, B3)."""
        ...


class IGraphicalScheduleGenerator(Protocol):
    """Interface pour la génération graphique."""

    def generate_schedules(self, year_configs: List[Any], week_id: str) -> None:
        """Génère les emplois du temps graphiques pour toutes les années."""
        ...


class IYearConfigBuilder(Protocol):
    """Interface pour construire les configurations d'années."""

    def build_configs(
        self,
        b1_courses: List[tuple],
        b2_courses: List[tuple],
        b3_courses: List[tuple]
    ) -> List[Any]:
        """Construit les configurations pour chaque année."""
        ...
