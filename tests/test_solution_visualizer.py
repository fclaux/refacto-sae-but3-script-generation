from unittest.mock import Mock, patch, MagicMock
import pytest

from solution_visualizer import SolutionVisualizer
from group_classifier import GroupClassifier
from course_converter import CourseConverter
from course_data_models import CourseScheduleInfo


def test_group_to_indices_but_and_simple_and_suffix():
    """Test les formats valides de groupes"""
    classifier = GroupClassifier()

    assert classifier.group_to_indices("BUT1") is None
    assert classifier.group_to_indices("G1") == [0]
    assert classifier.group_to_indices("G3") == [2]
    assert classifier.group_to_indices("G1A") == [0, "A"]
    assert classifier.group_to_indices("G2B") == [1, "B"]


def test_group_to_indices_invalid_format():
    """Test que les formats invalides retournent None"""
    classifier = GroupClassifier()

    assert classifier.group_to_indices("XYZ") is None
    assert classifier.group_to_indices("UNKNOWN") is None


def test_get_year_level():
    """Test la classification par année"""
    classifier = GroupClassifier()

    assert classifier.get_year_level("G1") == "B1"
    assert classifier.get_year_level("G2") == "B1"
    assert classifier.get_year_level("G4") == "B2"
    assert classifier.get_year_level("G5") == "B2"
    assert classifier.get_year_level("UNKNOWN") == "B3"


def test_convert_courses_to_room_lists():
    """Test la conversion des cours vers les listes B1/B2/B3"""
    classifier = GroupClassifier()
    converter = CourseConverter(classifier)
    room_list = ["R1", "R2", "R3"]

    courses = [
        CourseScheduleInfo(
            name="CM_Math_G1_s1",
            day=0,
            start_hour="08:00",
            duration=1,
            teacher="T1",
            room=1
        ),
        CourseScheduleInfo(
            name="TP_Algo_G5_s2",
            day=1,
            start_hour="10:00",
            duration=2,
            teacher="T2",
            room=2
        ),
    ]

    B1, B2, B3 = converter.convert_to_room_lists(courses, room_list)

    # Vérifie B1 (G1 -> B1)
    assert len(B1) == 1
    b1 = B1[0]
    assert b1[0] == "Lundi"  # day_name
    assert b1[1] == "08:00"  # start_hour
    assert b1[2] == 1  # duration
    assert b1[3] == "Math"  # matière
    assert b1[4] == "T1"  # teacher
    assert b1[5] == "R1"  # room
    assert b1[6] == "CM"  # type
    assert b1[7] == [0]  # indices

    # Vérifie B2 (G5 -> B2)
    assert len(B2) == 1
    b2 = B2[0]
    assert b2[0] == "Mardi"
    assert b2[1] == "10:00"
    assert b2[2] == 2
    assert b2[3] == "Algo"
    assert b2[4] == "T2"
    assert b2[5] == "R2"
    assert b2[6] == "TP"
    assert b2[7] == [1]

    # B3 doit être vide
    assert len(B3) == 0


def test_convert_courses_mapping_days():
    """Test le mapping des jours"""
    classifier = GroupClassifier()
    converter = CourseConverter(classifier)
    room_list = ["R1"]

    courses = [
        CourseScheduleInfo(name="CM_A_G1_s1", day=0, start_hour="08:00", duration=1, teacher="T", room=1),
        CourseScheduleInfo(name="CM_B_G1_s2", day=2, start_hour="08:00", duration=1, teacher="T", room=1),
        CourseScheduleInfo(name="CM_C_G1_s3", day=4, start_hour="08:00", duration=1, teacher="T", room=1),
    ]

    B1, _, _ = converter.convert_to_room_lists(courses, room_list)

    assert B1[0][0] == "Lundi"
    assert B1[1][0] == "Mercredi"
    assert B1[2][0] == "Vendredi"


# ==============================================================================
# TESTS POUR SolutionVisualizer
# ==============================================================================
def test_solution_visualizer_initialization():
    """Test l'initialisation du SolutionVisualizer"""
    solution = {
        'solver': Mock(),
        'vars': {
            'start': {},
            'y_salle': {},
            'z_prof': {}
        }
    }
    data = {
        'cours': [],
        'salles': {},
        'profs': [],
        'jours': 5,
        'creneaux_par_jour': 10,
        'duree_cours': {},
        'nb_slots': 50  # 5 jours * 10 créneaux
    }

    visualizer = SolutionVisualizer(solution, data)

    assert visualizer.data == data
    assert visualizer._assignments == []
    # Le planning doit avoir nb_slots entrées avec des listes vides
    assert len(visualizer._planning) == 50
    assert all(visualizer._planning[i] == [] for i in range(50))


def test_get_course_schedule_info():
    """Test la récupération des infos de cours"""
    solution = {
        'solver': Mock(),
        'vars': {
            'start': {},
            'y_salle': {},
            'z_prof': {}
        }
    }
    data = {
        'cours': [],
        'salles': {},
        'profs': [],
        'jours': 5,
        'creneaux_par_jour': 10,
        'duree_cours': {},
        'nb_slots': 50
    }

    visualizer = SolutionVisualizer(solution, data)

    # Au début, la liste doit être vide
    infos = visualizer.get_course_schedule_info()
    assert infos == []


def test_display_calls_console_and_graphical():
    """Test que display appelle bien les deux méthodes d'affichage"""
    solution = {
        'solver': Mock(),
        'vars': {
            'start': {},
            'y_salle': {},
            'z_prof': {}
        }
    }
    data = {
        'cours': [],
        'salles': {},
        'profs': [],
        'jours': 1,
        'creneaux_par_jour': 4,
        'duree_cours': {},
        'fenetre_midi': [],
        'nb_slots': 4
    }

    visualizer = SolutionVisualizer(solution, data)

    # Mock des méthodes internes
    visualizer._print_schedule_to_console = Mock()
    visualizer._generate_graphical_schedule = Mock()

    data_provider = Mock()

    visualizer.display(data_provider, "S222")

    # Vérifie que les deux méthodes ont été appelées
    visualizer._print_schedule_to_console.assert_called_once()
    visualizer._generate_graphical_schedule.assert_called_once_with(data_provider, "S222")


def test_generate_graphical_schedule_handles_exception(caplog):
    """Test la gestion des exceptions lors de la génération graphique"""
    import logging

    solution = {
        'solver': Mock(),
        'vars': {
            'start': {},
            'y_salle': {},
            'z_prof': {}
        }
    }
    data = {
        'cours': [],
        'salles': {},
        'profs': [],
        'jours': 1,
        'creneaux_par_jour': 4,
        'duree_cours': {},
        'fenetre_midi': [],
        'nb_slots': 4
    }

    visualizer = SolutionVisualizer(solution, data)

    data_provider = Mock()
    data_provider.get_list_room.side_effect = Exception("DB Error")

    with caplog.at_level(logging.ERROR):
        visualizer._generate_graphical_schedule(data_provider, week_id=1)

    # Vérifie qu'un message d'erreur a été loggé
    assert any("ERREUR lors de la génération graphique" in record.message for record in caplog.records)


def test_generate_graphical_schedule_success():
    """Test la génération graphique réussie"""
    solution = {
        'solver': Mock(),
        'vars': {
            'start': {},
            'y_salle': {},
            'z_prof': {}
        }
    }
    data = {
        'cours': [],
        'salles': {},
        'profs': [],
        'jours': 1,
        'creneaux_par_jour': 4,
        'duree_cours': {},
        'fenetre_midi': [],
        'nb_slots': 4
    }

    visualizer = SolutionVisualizer(solution, data)

    # Mock du data_provider
    data_provider = Mock()
    data_provider.get_list_room.return_value = ["R1", "R2", "R3"]
    data_provider.convert_courses_dict_to_list_insert = Mock()

    # Mock du générateur graphique
    visualizer._graphical_generator.generate_schedules = Mock()

    visualizer._generate_graphical_schedule(data_provider, "S222")

    # Vérifie les appels
    data_provider.get_list_room.assert_called_once()
    data_provider.convert_courses_dict_to_list_insert.assert_called_once()
    visualizer._graphical_generator.generate_schedules.assert_called_once()
