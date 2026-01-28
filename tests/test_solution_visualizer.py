import builtins
from unittest.mock import Mock, patch
import pytest

from solution_visualizer import (
    groupe_to_indices,
    convert_courses_dict_to_list_room_name,
    SolutionVisualizer,
)


def test_groupe_to_indices_but_and_simple_and_suffix():
    """Test les formats valides de groupes"""
    assert groupe_to_indices("BUT1") is None
    assert groupe_to_indices("G1") == [0]
    assert groupe_to_indices("G3") == [2]
    assert groupe_to_indices("G1A") == [0, "A"]
    assert groupe_to_indices("G2B") == [1, "B"]


def test_groupe_to_indices_invalid_format():
    """Test que les formats invalides lèvent une ValueError (bug existant à documenter)"""
    with pytest.raises(ValueError, match="invalid literal for int"):
        groupe_to_indices("XYZ")

    with pytest.raises(ValueError, match="invalid literal for int"):
        groupe_to_indices("UNKNOWN")


def test_convert_courses_dict_to_list_room_name_mapping_and_defaults():
    """Test le mapping complet des cours vers B1/B2/B3 avec vérification de tous les champs"""
    list_room = ["R1", "R2", "R3"]
    courses = [
        {
            "name": "CM_Math_G1_s1",
            "day": 0,
            "start_hour": "08:00",
            "duration": 1,
            "teacher": "T1",
            "room": 1,
        },
        {
            "name": "TP_Algo_G5_s2",
            "day": 1,
            "start_hour": "10:00",
            "duration": 2,
            "teacher": "T2",
            "room": 2,
        },
    ]

    B1, B2, B3 = convert_courses_dict_to_list_room_name(courses, list_room)

    # Vérifie B1 (G1 -> B1)
    assert len(B1) == 1
    b1 = B1[0]
    assert b1[0] == "Lundi"  # day_name
    assert b1[1] == "08:00"  # start_hour
    assert b1[2] == 1  # duration
    assert b1[3] == "Math"  # matière (split '_')[1]
    assert b1[4] == "T1"  # teacher
    assert b1[5] == "R1"  # room (list_room[0])
    assert b1[6] == "CM"  # type (split '_')[0]
    assert b1[7] == [0]  # groupe_to_indices("G1")

    # Vérifie B2 (G5 -> B2)
    assert len(B2) == 1
    b2 = B2[0]
    assert b2[0] == "Mardi"  # mapping jour
    assert b2[1] == "10:00"
    assert b2[2] == 2
    assert b2[3] == "Algo"
    assert b2[4] == "T2"
    assert b2[5] == "R2"  # list_room[1]
    assert b2[6] == "TP"
    assert b2[7] == [1]  # G5 -> (5-1)%3 = 1

    # B3 doit être vide
    assert len(B3) == 0


def test_convert_courses_dict_mapping_days():
    """Test spécifique du mapping jour (int -> string)"""
    list_room = ["R1"]
    courses = [
        {"name": "CM_A_G1_s1", "day": 0, "start_hour": "08:00", "duration": 1, "teacher": "T", "room": 1},
        {"name": "CM_B_G1_s2", "day": 2, "start_hour": "08:00", "duration": 1, "teacher": "T", "room": 1},
        {"name": "CM_C_G1_s3", "day": 4, "start_hour": "08:00", "duration": 1, "teacher": "T", "room": 1},
    ]

    B1, _, _ = convert_courses_dict_to_list_room_name(courses, list_room)

    assert B1[0][0] == "Lundi"
    assert B1[1][0] == "Mercredi"
    assert B1[2][0] == "Vendredi"


def test_print_schedule_populates_temp_and_duration():
    """Test que _print_schedule_to_console remplit correctement temp avec duration"""
    sv = object.__new__(SolutionVisualizer)

    sv.temp = []
    sv.data = {
        "jours": 1,
        "creneaux_par_jour": 4,
        "fenetre_midi": [],
    }

    # Simule un cours "C1" qui dure 2 créneaux
    sv.planning = {
        0: [("C1", "R1", "T1")],
        1: [("C1", "R1", "T1")],
        2: [],
        3: [],
    }
    sv.actual_starts = {"C1": 0}

    # Capture les prints pour ne pas polluer la sortie
    with patch('builtins.print'):
        sv._print_schedule_to_console()

    # Vérifie que temp contient bien le cours avec duration 2
    assert len(sv.temp) == 1
    cours = sv.temp[0]
    assert cours["name"] == "C1"
    assert cours["start_hour"] == "08:00"
    assert cours["duration"] == 2
    assert cours["room"] == "R1"
    assert cours["teacher"] == "T1"
    assert cours["day"] == 0


def test_print_schedule_slot_to_time_conversion():
    """Test la conversion des slots en heures (08:00, 08:30, etc.)"""
    sv = object.__new__(SolutionVisualizer)

    sv.temp = []
    sv.data = {"jours": 1, "creneaux_par_jour": 3, "fenetre_midi": []}

    # Cours à différents créneaux
    sv.planning = {
        0: [("C1", "R1", "T1")],  # 08:00
        1: [("C2", "R2", "T2")],  # 08:30
        2: [("C3", "R3", "T3")],  # 09:00
    }
    sv.actual_starts = {"C1": 0, "C2": 1, "C3": 2}

    with patch('builtins.print'):
        sv._print_schedule_to_console()

    assert sv.temp[0]["start_hour"] == "08:00"
    assert sv.temp[1]["start_hour"] == "08:30"
    assert sv.temp[2]["start_hour"] == "09:00"


def test_generate_graphical_schedule_calls_providers_and_generates(monkeypatch):
    """Test que _generate_graphical_schedule appelle les bonnes méthodes avec les bons paramètres"""
    sv = object.__new__(SolutionVisualizer)
    sv.temp = [
        {
            "day": 0,
            "start_hour": "08:00",
            "duration": 1,
            "name": "CM_Math_G1_s1",
            "teacher": "T1",
            "room": 1,
            "course_type": None,
            "course_group": None,
        }
    ]

    # Mock DataProviderInsert
    data_provider = Mock()
    data_provider.get_list_room.return_value = ["R1", "R2", "R3"]
    data_provider.convert_courses_dict_to_list_insert = Mock()

    # Mock fonctions de génération graphique
    mock_gen = Mock()
    monkeypatch.setattr("solution_visualizer.sg.generate_schedule", mock_gen)
    mock_show = Mock()
    monkeypatch.setattr("solution_visualizer.sg.plt.show", mock_show)

    # Capture les prints
    with patch('builtins.print'):
        sv._generate_graphical_schedule(data_provider, week_id=7)

    # Vérifie que get_list_room a été appelé
    data_provider.get_list_room.assert_called_once()

    # Vérifie que convert_courses_dict_to_list_insert a été appelé avec temp
    data_provider.convert_courses_dict_to_list_insert.assert_called_once_with(sv.temp)

    # Vérifie que generate_schedule a été appelé 3 fois (A1, A2, A3)
    assert mock_gen.call_count == 3

    # Vérifie les paramètres du premier appel (A1)
    first_call = mock_gen.call_args_list[0]
    assert first_call[0][0] == "A1"
    assert first_call[0][1] == 7

    # Vérifie les paramètres du deuxième appel (A2)
    second_call = mock_gen.call_args_list[1]
    assert second_call[0][0] == "A2"
    assert second_call[0][1] == 7

    # Vérifie les paramètres du troisième appel (A3)
    third_call = mock_gen.call_args_list[2]
    assert third_call[0][0] == "A3"
    assert third_call[0][1] == 7

    # Vérifie que plt.show a été appelé
    mock_show.assert_called_once()


def test_generate_graphical_schedule_handles_exception(monkeypatch):
    """Test que _generate_graphical_schedule gère les exceptions correctement"""
    sv = object.__new__(SolutionVisualizer)
    sv.temp = []

    data_provider = Mock()
    data_provider.get_list_room.side_effect = Exception("DB Error")

    # Capture les prints
    with patch('builtins.print') as mock_print:
        sv._generate_graphical_schedule(data_provider, week_id=1)

        # Vérifie qu'un message d'erreur a été affiché
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("ERROR during graphical generation" in str(call) for call in calls)
