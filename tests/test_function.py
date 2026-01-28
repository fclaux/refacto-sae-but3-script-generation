"""
Tests pour le module function.
Refactorisé pour éliminer la duplication de code.
"""
import unittest
import pandas as pd
from function import (
    get_end_time, get_start_time, convert_daystring_to_int, convert_days_int_to_string,
    _time_to_slot, recup_cours, recup_id_slot_from_str_to_int,
    recuperation_indisponibilites, recuperation_disponibilites_profs,
    get_availabilityProf_From_Unavailable, recuperation_indisponibilites_rooms,
    recuperation_indisponibilites_group, recuperation_indisponibilites_slot,
)


def make_indispo_df(id_col, id_val, day, start, end):
    """Factory pour créer un DataFrame d'indisponibilités."""
    return pd.DataFrame({id_col: [id_val], 'day_of_week': [day], 'start_time': [start], 'end_time': [end]})


class TestGetTime(unittest.TestCase):
    """Tests pour get_end_time et get_start_time."""

    TEST_CASES_END = [
        ('2026-01-27 14:30:00', '14:30:00'),
        ('09:00:00', '09:00:00'),
        (pd.NA, ''),
        (None, ''),
    ]
    TEST_CASES_START = [
        ('2026-01-27 08:00:00', '08:00:00'),
        ('13:30:00', '13:30:00'),
        (pd.NA, ''),
        (None, ''),
    ]

    def test_get_end_time(self):
        for input_val, expected in self.TEST_CASES_END:
            with self.subTest(input=input_val):
                self.assertEqual(get_end_time({'end_time': input_val}), expected)

    def test_get_start_time(self):
        for input_val, expected in self.TEST_CASES_START:
            with self.subTest(input=input_val):
                self.assertEqual(get_start_time({'start_time': input_val}), expected)


class TestDayConversions(unittest.TestCase):
    """Tests pour convert_daystring_to_int et convert_days_int_to_string."""

    DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

    def test_convert_daystring_to_int(self):
        for i, day in enumerate(self.DAYS):
            with self.subTest(day=day):
                self.assertEqual(convert_daystring_to_int(day), i)

    def test_convert_days_int_to_string(self):
        for i, day in enumerate(self.DAYS):
            with self.subTest(i=i):
                self.assertEqual(convert_days_int_to_string(i), day)


class TestTimeToSlot(unittest.TestCase):
    """Tests pour _time_to_slot."""

    TEST_CASES = [
        ('08:00:00', 0),
        ('08:30:00', 1),
        ('09:00:00', 2),
        ('12:00:00', 8),
        ('13:30:00', 11),
        ('18:00:00', 20),
        (pd.NA, 0),
    ]

    def test_time_to_slot(self):
        for time_str, expected in self.TEST_CASES:
            with self.subTest(time=time_str):
                self.assertEqual(_time_to_slot(time_str), expected)


class TestRecupCours(unittest.TestCase):
    """Tests pour recup_cours."""

    TEST_CASES = [
        ("CM_R1.01 Initiation au développement_BUT1_s7000000", ('CM', 'R1.01 Initiation au développement')),
        ("TD_Mathématiques_BUT2_s123", ('TD', 'Mathématiques')),
        ("TP_Programmation_G1_s456", ('TP', 'Programmation')),
    ]

    def test_recup_cours(self):
        for input_str, expected in self.TEST_CASES:
            with self.subTest(input=input_str):
                self.assertEqual(recup_cours(input_str), expected)


class TestRecupIdSlotFromStrToInt(unittest.TestCase):
    """Tests pour recup_id_slot_from_str_to_int."""

    TEST_CASES = [
        ("développement_BUT1_s7000000", 7000000),
        ("cours_groupe_s123", 123),
        ("test_s0", 0),
    ]

    def test_recup_id_slot(self):
        for input_str, expected in self.TEST_CASES:
            with self.subTest(input=input_str):
                self.assertEqual(recup_id_slot_from_str_to_int(input_str), expected)


class TestRecuperationIndisponibilites(unittest.TestCase):
    """Tests pour recuperation_indisponibilites (profs)."""

    def test_single_indisponibilite(self):
        df = make_indispo_df('teacher_id', 1, 'Lundi', '08:00:00', '10:00:00')
        result = recuperation_indisponibilites(df, {})
        self.assertIn(1, result)
        self.assertEqual(result[1]['Lundi'], [(0, 4)])

    def test_multiple_teachers(self):
        df = pd.DataFrame({
            'teacher_id': [1, 2],
            'day_of_week': ['Lundi', 'Mardi'],
            'start_time': ['08:00:00', '14:00:00'],
            'end_time': ['09:00:00', '16:00:00']
        })
        result = recuperation_indisponibilites(df, {})
        self.assertEqual(result[1]['Lundi'], [(0, 2)])
        self.assertEqual(result[2]['Mardi'], [(12, 16)])

    def test_empty_times(self):
        df = make_indispo_df('teacher_id', 1, 'Lundi', None, None)
        result = recuperation_indisponibilites(df, {})
        self.assertEqual(result[1]['Lundi'], [('', '')])

    def test_existing_dict(self):
        df = make_indispo_df('teacher_id', 1, 'Mardi', '10:00:00', '11:00:00')
        existing = {1: {'Lundi': [(0, 2)]}}
        result = recuperation_indisponibilites(df, existing)
        self.assertIn('Lundi', result[1])
        self.assertIn('Mardi', result[1])


class TestRecuperationIndisponibilitesRooms(unittest.TestCase):
    """Tests pour recuperation_indisponibilites_rooms."""

    def test_single_room(self):
        df = make_indispo_df('room_id', 10, 'Mercredi', '13:00:00', '15:00:00')
        result = recuperation_indisponibilites_rooms(df, {})
        self.assertIn(10, result)
        self.assertEqual(result[10]['Mercredi'], [(10, 14)])

    def test_multiple_rooms(self):
        df = pd.DataFrame({
            'room_id': [10, 20],
            'day_of_week': ['Lundi', 'Vendredi'],
            'start_time': ['08:00:00', '16:00:00'],
            'end_time': ['09:00:00', '18:00:00']
        })
        result = recuperation_indisponibilites_rooms(df, {})
        self.assertIn(10, result)
        self.assertIn(20, result)


class TestRecuperationIndisponibilitesGroup(unittest.TestCase):
    """Tests pour recuperation_indisponibilites_group."""

    def test_single_group(self):
        df = make_indispo_df('group_id', 5, 'Jeudi', '14:00:00', '16:00:00')
        result = recuperation_indisponibilites_group(df, {})
        self.assertIn(5, result)
        self.assertEqual(result[5]['Jeudi'], [(12, 16)])


class TestRecuperationIndisponibilitesSlot(unittest.TestCase):
    """Tests pour recuperation_indisponibilites_slot."""

    def test_single_slot(self):
        df = make_indispo_df('slot_id', 100, 'Lundi', '08:00:00', '10:00:00')
        result = recuperation_indisponibilites_slot(df, {})
        self.assertIn(100, result)
        self.assertIn(0, result[100])  # 0 = Lundi
        self.assertEqual(result[100][0], [(0, 4)])


class TestGetAvailabilityProfFromUnavailable(unittest.TestCase):
    """Tests pour get_availabilityProf_From_Unavailable."""

    def test_empty_dataframe(self):
        df = pd.DataFrame({'teacher_id': [], 'day_of_week': [], 'start_time': [], 'end_time': []})
        result = get_availabilityProf_From_Unavailable(df, 20)
        self.assertEqual(result, {})

    def test_with_indisponibilite(self):
        df = make_indispo_df('teacher_id', 1, 'Lundi', '08:00:00', '10:00:00')
        result = get_availabilityProf_From_Unavailable(df, 20)
        self.assertIn(1, result)
        # Prof dispo les autres jours
        for day in [1, 2, 3, 4]:  # Mardi à Vendredi
            self.assertIn(day, result[1])


class TestRecuperationDisponibilitesProfs(unittest.TestCase):
    """Tests pour recuperation_disponibilites_profs."""

    def test_jour_sans_indisponibilite(self):
        indispo = {1: {'Lundi': [(0, 4)]}}
        result = recuperation_disponibilites_profs(20, {}, indispo)
        self.assertIn(1, result)
        self.assertEqual(result[1][1], [(0, 20)])  # Mardi dispo tout le jour

    def test_tous_les_jours_disponibles(self):
        indispo = {1: {}}
        result = recuperation_disponibilites_profs(20, {}, indispo)
        for day in range(5):
            self.assertEqual(result[1][day], [(0, 20)])


if __name__ == '__main__':
    unittest.main()
