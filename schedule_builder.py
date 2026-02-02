"""
Constructeur d'emploi du temps à partir des affectations.
Respecte le principe Single Responsibility (SOLID).
"""
from typing import Dict, List
from course_data_models import CourseAssignment, CourseScheduleInfo
from interfaces import ITimeFormatter


class ScheduleBuilder:
    """Construit une structure d'emploi du temps à partir des affectations."""

    def __init__(self, data: Dict, time_formatter: ITimeFormatter):
        self.data = data
        self.time_formatter = time_formatter

    def build_planning(self, assignments: List[CourseAssignment]) -> Dict[int, List[tuple]]:
        """
        Construit un planning en associant chaque créneau aux cours.

        Returns:
            Dictionnaire {slot: [(course_id, room, teacher), ...]}
        """
        planning = {s: [] for s in range(self.data['nb_slots'])}

        for assignment in assignments:
            for offset in range(assignment.duration):
                slot = assignment.start_slot + offset
                planning[slot].append((
                    assignment.course_id,
                    assignment.room_name,
                    assignment.teacher_name
                ))

        return planning

    def build_course_schedule_info(self, assignments: List[CourseAssignment]) -> List[CourseScheduleInfo]:
        """
        Construit une liste de CourseScheduleInfo pour chaque cours.

        Returns:
            Liste d'objets CourseScheduleInfo
        """
        course_infos = []

        for assignment in assignments:
            day = assignment.start_slot // self.data['creneaux_par_jour']
            time_in_day = assignment.start_slot % self.data['creneaux_par_jour']
            time_str = self.time_formatter.slot_to_time(time_in_day)
            start_hour = time_str.split('-')[0]

            course_info = CourseScheduleInfo(
                day=day,
                start_hour=start_hour,
                duration=assignment.duration,
                name=str(assignment.course_id),
                teacher=assignment.teacher_name,
                room=assignment.room_name
            )
            course_infos.append(course_info)

        return course_infos

