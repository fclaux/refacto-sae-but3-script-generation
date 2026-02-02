"""
Modèles de données pour les cours.
Respecte le principe Single Responsibility (SOLID).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class CourseAssignment:
    """Représente l'affectation d'un cours avec ses ressources."""
    course_id: int
    start_slot: int
    room_id: int
    teacher_id: int
    room_name: str
    teacher_name: str
    duration: int


@dataclass
class CourseScheduleInfo:
    """Information formatée pour l'affichage d'un cours dans l'emploi du temps."""
    day: int
    start_hour: str
    duration: int
    name: str
    teacher: str
    room: str
    course_type: Optional[str] = None
    course_group: Optional[str] = None

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour compatibilité."""
        return {
            "day": self.day,
            "start_hour": self.start_hour,
            "duration": self.duration,
            "name": self.name,
            "teacher": self.teacher,
            "room": self.room,
            "course_type": self.course_type,
            "course_group": self.course_group
        }

