"""
Module pour la conversion et le formatage des créneaux horaires.
Respecte le principe Single Responsibility (SOLID).
"""
from typing import Final

# Constantes de configuration horaire
HOURS_START: Final[int] = 8
SLOT_DURATION_MINUTES: Final[int] = 30
DAYS: Final[list[str]] = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


class TimeFormatter:
    """Convertit les créneaux en format horaire lisible."""

    def __init__(self, start_hour: int = HOURS_START, slot_duration: int = SLOT_DURATION_MINUTES):
        self._start_hour = start_hour
        self._slot_duration = slot_duration

    def slot_to_time(self, slot: int) -> str:
        """
        Convertit un créneau en format horaire.

        Args:
            slot: Index du créneau

        Returns:
            Chaîne au format "HH:MM-HH:MM"
        """
        h = self._start_hour + (slot // 2)
        m = self._slot_duration * (slot % 2)
        h_end = self._start_hour + ((slot + 1) // 2)
        m_end = self._slot_duration * ((slot + 1) % 2)
        return f"{h:02d}:{m:02d}-{h_end:02d}:{m_end:02d}"

    def get_day_name(self, day_index: int) -> str:
        """Retourne le nom du jour à partir de son index."""
        if 0 <= day_index < len(DAYS):
            return DAYS[day_index]
        return f"Jour_{day_index}"

