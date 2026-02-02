"""
Module principal pour visualiser les solutions d'emploi du temps.
Refactorisé selon les principes SOLID.
"""
from typing import Dict, Any, List

from logger_config import get_logger
from time_formatter import TimeFormatter
from course_data_models import CourseScheduleInfo
from solution_parser import SolutionParser
from schedule_builder import ScheduleBuilder
from console_printer import ConsolePrinter
from group_classifier import GroupClassifier
from course_converter import CourseConverter
from graphical_generator import GraphicalScheduleGenerator, YearConfigBuilder

# Configuration du logger pour ce module
logger = get_logger(__name__)


# ==============================================================================
# CLASSE PRINCIPALE: ORCHESTRATION DE L'AFFICHAGE (SolutionVisualizer)
# ==============================================================================
class SolutionVisualizer:
    """
    Orchestre l'affichage des résultats d'une solution d'emploi du temps.

    Respecte les principes SOLID :
    - S: Chaque classe a une responsabilité unique
    - O: Extensible sans modification (configurations centralisées)
    - L: Pas d'héritage problématique
    - I: Interfaces claires et séparées
    - D: Dépendances injectées, pas de couplage fort
    """

    def __init__(self, solution: Dict[str, Any], data: Dict[str, Any]):
        """
        Initialise le visualisateur avec injection de dépendances.

        Args:
            solution: Dictionnaire contenant solver et variables OR-Tools
            data: Données de configuration (cours, salles, profs, etc.)
        """
        self.data = data

        # Injection de dépendances - respecte Dependency Inversion
        self._time_formatter = TimeFormatter()
        self._parser = SolutionParser(solution, data)
        self._schedule_builder = ScheduleBuilder(data, self._time_formatter)
        self._console_printer = ConsolePrinter(data, self._time_formatter)
        self._group_classifier = GroupClassifier()
        self._course_converter = CourseConverter(self._group_classifier)
        self._graphical_generator = GraphicalScheduleGenerator()
        self._year_config_builder = YearConfigBuilder()

        # Parse la solution une seule fois
        self._assignments = self._parser.parse_assignments()
        self._planning = self._schedule_builder.build_planning(self._assignments)
        self._actual_starts = {a.course_id: a.start_slot for a in self._assignments}
        self._course_infos: List[CourseScheduleInfo] = []

    def display(self, data_provider, week_id: str):
        """
        Affiche la solution complète : console + graphiques.

        Args:
            data_provider: Fournisseur de données pour accès base de données
            week_id: Identifiant de la semaine
        """
        logger.info("\n4. Affichage de la solution trouvée :")

        # Affichage console
        self._print_schedule_to_console()

        # Génération graphique
        self._generate_graphical_schedule(data_provider, week_id)

    def _print_schedule_to_console(self):
        """Affiche l'emploi du temps dans la console."""
        self._console_printer.print_schedule(self._planning, self._actual_starts)

        # Construit les infos de cours pour usage ultérieur
        self._course_infos = self._schedule_builder.build_course_schedule_info(self._assignments)

    def _generate_graphical_schedule(self, data_provider, week_id: str):
        """
        Génère les emplois du temps graphiques pour toutes les années.

        Args:
            data_provider: Fournisseur de données
            week_id: Identifiant de la semaine
        """
        try:
            # Récupère la liste des salles
            room_list = data_provider.get_list_room()

            # Convertit les cours en format dictionnaire pour data_provider
            courses_dict_list = [info.to_dict() for info in self._course_infos]
            data_provider.convert_courses_dict_to_list_insert(courses_dict_list)

            # Convertit en listes par année (B1, B2, B3)
            b1, b2, b3 = self._course_converter.convert_to_room_lists(
                self._course_infos,
                room_list
            )

            # Construit les configurations et génère les graphiques
            year_configs = self._year_config_builder.build_configs(b1, b2, b3)
            self._graphical_generator.generate_schedules(year_configs, week_id)

        except Exception as e:
            logger.error(f"   -> ERREUR lors de la génération graphique : {e}")

    def get_course_schedule_info(self) -> List[CourseScheduleInfo]:
        """
        Retourne les informations de cours formatées.

        Returns:
            Liste des CourseScheduleInfo
        """
        if not self._course_infos:
            self._course_infos = self._schedule_builder.build_course_schedule_info(
                self._assignments
            )
        return self._course_infos

