"""
Affichage console de l'emploi du temps.
Respecte le principe Single Responsibility (SOLID).
"""
from typing import Dict, List
from course_data_models import CourseAssignment
from time_formatter import TimeFormatter
from logger_config import get_logger

logger = get_logger(__name__)


class ConsolePrinter:
    """Affiche l'emploi du temps dans la console."""

    def __init__(self, data: Dict, time_formatter: TimeFormatter):
        self.data = data
        self.time_formatter = time_formatter

    def print_schedule(self, planning: Dict[int, List[tuple]],
                      actual_starts: Dict[int, int]):
        """
        Affiche l'emploi du temps jour par jour dans la console.

        Args:
            planning: Dictionnaire {slot: [(course_id, room, teacher), ...]}
            actual_starts: Dictionnaire {course_id: start_slot}
        """
        for day_idx in range(self.data['jours']):
            logger.info(f"\n=== Day {day_idx + 1} ===")

            for time_in_day in range(self.data['creneaux_par_jour']):
                global_slot = day_idx * self.data['creneaux_par_jour'] + time_in_day
                entries = planning.get(global_slot, [])
                time_str = self.time_formatter.slot_to_time(time_in_day)

                if entries:
                    self._print_slot_with_courses(time_str, global_slot, entries, actual_starts)
                else:
                    self._print_empty_slot(time_str, time_in_day)

            logger.info("-" * 20)

    def _print_slot_with_courses(self, time_str: str, global_slot: int,
                                entries: List[tuple], actual_starts: Dict[int, int]):
        """Affiche un créneau avec des cours."""
        for (course_id, room_str, teacher_str) in entries:
            if actual_starts.get(course_id) == global_slot:
                logger.info(f"  {time_str} : {course_id} (Room: {room_str}, Teacher: {teacher_str}) Début")
            else:
                logger.info(f"  {time_str} : {course_id} (Room: {room_str}, Teacher: {teacher_str})")

    def _print_empty_slot(self, time_str: str, time_in_day: int):
        """Affiche un créneau vide."""
        if not self.data.get('fenetre_midi') or time_in_day not in self.data['fenetre_midi']:
            logger.info(f"  {time_str} : --")

