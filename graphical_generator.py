"""
Générateur d'emplois du temps graphiques.
Respecte les principes Open/Closed et Dependency Inversion (SOLID).
"""
from typing import List, Dict
from dataclasses import dataclass
from Front import schedule_generator as sg
from logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class YearConfig:
    """Configuration pour une année d'études."""
    year_name: str
    groups: List[str]
    courses: List[tuple]


class GraphicalScheduleGenerator:
    """Génère les emplois du temps graphiques pour toutes les années."""

    def generate_schedules(self, year_configs: List[YearConfig], week_id: str):
        """
        Génère les emplois du temps graphiques pour toutes les années.

        Args:
            year_configs: Liste des configurations par année
            week_id: Identifiant de la semaine
        """
        logger.info("\n5. Génération des emplois du temps graphiques...")

        try:
            for config in year_configs:
                self._generate_single_schedule(config, week_id)

            sg.plt.show()
            logger.info("   -> Graphiques générés avec succès.")
        except ValueError as e:
            logger.error(f"   -> ERREUR de données : {e}")
        except Exception as e:
            logger.error(f"   -> ERREUR lors de la génération graphique : {e}")

    def _generate_single_schedule(self, config: YearConfig, week_id: str):
        """Génère l'emploi du temps pour une année."""
        logger.info(f"   -> Génération de {config.year_name}...")
        sg.generate_schedule(
            config.year_name,
            week_id,
            config.groups,
            config.courses
        )


class YearConfigBuilder:
    """Construit les configurations d'années pour la génération graphique."""

    # Configuration centralisée - respecte Open/Closed
    YEAR_GROUPS: Dict[str, List[str]] = {
        "A1": ["G1", "G2", "G3", "G1A", "G2A", "G3A", "G1B", "G2B", "G3B"],
        "A2": ["G4", "G5", "G4A", "G5A", "G4B", "G5B"],
        "A3": ["G7", "G8", "G7A", "G7B", "G8A"]
    }

    def build_configs(self, b1_courses: List[tuple],
                     b2_courses: List[tuple],
                     b3_courses: List[tuple]) -> List[YearConfig]:
        """
        Construit les configurations pour chaque année.

        Returns:
            Liste des YearConfig prêts pour la génération
        """
        return [
            YearConfig("A1", self.YEAR_GROUPS["A1"], b1_courses),
            YearConfig("A2", self.YEAR_GROUPS["A2"], b2_courses),
            YearConfig("A3", self.YEAR_GROUPS["A3"], b3_courses)
        ]
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

