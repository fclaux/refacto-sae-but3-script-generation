import unittest
import pandas as pd
from function import (
    get_end_time,
    get_start_time,
    convert_daystring_to_int,
    convert_days_int_to_string,
    _time_to_slot,
    recup_cours,
    recup_id_slot_from_str_to_int,
    recuperation_indisponibilites,
    recuperation_disponibilites_profs,
    get_availabilityProf_From_Unavailable,
    recuperation_indisponibilites_rooms,
    recuperation_indisponibilites_group,
    recuperation_indisponibilites_slot,
)


class TestGetEndTime(unittest.TestCase):
    """Tests pour get_end_time."""

    def test_valid_time(self):
        row = {'end_time': '2026-01-27 14:30:00'}
        self.assertEqual(get_end_time(row), '14:30:00')

    def test_time_only(self):
        row = {'end_time': '09:00:00'}
        self.assertEqual(get_end_time(row), '09:00:00')

    def test_na_value(self):
        row = {'end_time': pd.NA}
        self.assertEqual(get_end_time(row), '')

    def test_none_value(self):
        row = {'end_time': None}
        self.assertEqual(get_end_time(row), '')


class TestGetStartTime(unittest.TestCase):
    """Tests pour get_start_time."""

    def test_valid_time(self):
        row = {'start_time': '2026-01-27 08:00:00'}
        self.assertEqual(get_start_time(row), '08:00:00')

    def test_time_only(self):
        row = {'start_time': '13:30:00'}
        self.assertEqual(get_start_time(row), '13:30:00')

    def test_na_value(self):
        row = {'start_time': pd.NA}
        self.assertEqual(get_start_time(row), '')

    def test_none_value(self):
        row = {'start_time': None}
        self.assertEqual(get_start_time(row), '')


class TestConvertDaystringToInt(unittest.TestCase):
    """Tests pour convert_daystring_to_int."""

    def test_lundi(self):
        self.assertEqual(convert_daystring_to_int('Lundi'), 0)

    def test_mardi(self):
        self.assertEqual(convert_daystring_to_int('Mardi'), 1)

    def test_mercredi(self):
        self.assertEqual(convert_daystring_to_int('Mercredi'), 2)

    def test_jeudi(self):
        self.assertEqual(convert_daystring_to_int('Jeudi'), 3)

    def test_vendredi(self):
        self.assertEqual(convert_daystring_to_int('Vendredi'), 4)


class TestConvertDaysIntToString(unittest.TestCase):
    """Tests pour convert_days_int_to_string."""

    def test_0_is_lundi(self):
        self.assertEqual(convert_days_int_to_string(0), 'Lundi')

    def test_1_is_mardi(self):
        self.assertEqual(convert_days_int_to_string(1), 'Mardi')

    def test_2_is_mercredi(self):
        self.assertEqual(convert_days_int_to_string(2), 'Mercredi')

    def test_3_is_jeudi(self):
        self.assertEqual(convert_days_int_to_string(3), 'Jeudi')

    def test_4_is_vendredi(self):
        self.assertEqual(convert_days_int_to_string(4), 'Vendredi')


class TestTimeToSlot(unittest.TestCase):
    """Tests pour _time_to_slot."""

    def test_8h00(self):
        self.assertEqual(_time_to_slot('08:00:00'), 0)

    def test_8h30(self):
        self.assertEqual(_time_to_slot('08:30:00'), 1)

    def test_9h00(self):
        self.assertEqual(_time_to_slot('09:00:00'), 2)

    def test_12h00(self):
        self.assertEqual(_time_to_slot('12:00:00'), 8)

    def test_13h30(self):
        self.assertEqual(_time_to_slot('13:30:00'), 11)

    def test_18h00(self):
        self.assertEqual(_time_to_slot('18:00:00'), 20)

    def test_na_value(self):
        self.assertEqual(_time_to_slot(pd.NA), 0)


class TestRecupCours(unittest.TestCase):
    """Tests pour recup_cours."""

    def test_cm_cours(self):
        result = recup_cours("CM_R1.01 Initiation au développement_BUT1_s7000000")
        self.assertEqual(result, ('CM', 'R1.01 Initiation au développement'))

    def test_td_cours(self):
        result = recup_cours("TD_Mathématiques_BUT2_s123")
        self.assertEqual(result, ('TD', 'Mathématiques'))

    def test_tp_cours(self):
        result = recup_cours("TP_Programmation_G1_s456")
        self.assertEqual(result, ('TP', 'Programmation'))


class TestRecupIdSlotFromStrToInt(unittest.TestCase):
    """Tests pour recup_id_slot_from_str_to_int."""

    def test_slot_7000000(self):
        result = recup_id_slot_from_str_to_int("développement_BUT1_s7000000")
        self.assertEqual(result, 7000000)

    def test_slot_123(self):
        result = recup_id_slot_from_str_to_int("cours_groupe_s123")
        self.assertEqual(result, 123)

    def test_slot_0(self):
        result = recup_id_slot_from_str_to_int("test_s0")
        self.assertEqual(result, 0)


class TestRecuperationIndisponibilites(unittest.TestCase):
    """Tests pour recuperation_indisponibilites (profs)."""

    def test_single_indisponibilite(self):
        df = pd.DataFrame({
            'teacher_id': [1],
            'day_of_week': ['Lundi'],
            'start_time': ['08:00:00'],
            'end_time': ['10:00:00']
        })
        result = recuperation_indisponibilites(df, {})
        self.assertIn(1, result)
        self.assertIn('Lundi', result[1])
        self.assertEqual(result[1]['Lundi'], [(0, 4)])

    def test_multiple_teachers(self):
        df = pd.DataFrame({
            'teacher_id': [1, 2],
            'day_of_week': ['Lundi', 'Mardi'],
            'start_time': ['08:00:00', '14:00:00'],
            'end_time': ['09:00:00', '16:00:00']
        })
        result = recuperation_indisponibilites(df, {})
        self.assertIn(1, result)
        self.assertIn(2, result)
        self.assertEqual(result[1]['Lundi'], [(0, 2)])
        self.assertEqual(result[2]['Mardi'], [(12, 16)])

    def test_empty_times(self):
        df = pd.DataFrame({
            'teacher_id': [1],
            'day_of_week': ['Lundi'],
            'start_time': [None],
            'end_time': [None]
        })
        result = recuperation_indisponibilites(df, {})
        self.assertEqual(result[1]['Lundi'], [('', '')])

    def test_existing_dict(self):
        df = pd.DataFrame({
            'teacher_id': [1],
            'day_of_week': ['Mardi'],
            'start_time': ['10:00:00'],
            'end_time': ['11:00:00']
        })
        existing = {1: {'Lundi': [(0, 2)]}}
        result = recuperation_indisponibilites(df, existing)
        self.assertIn('Lundi', result[1])
        self.assertIn('Mardi', result[1])


class TestRecuperationIndisponibilitesRooms(unittest.TestCase):
    """Tests pour recuperation_indisponibilites_rooms."""

    def test_single_room_indisponibilite(self):
        df = pd.DataFrame({
            'room_id': [10],
            'day_of_week': ['Mercredi'],
            'start_time': ['13:00:00'],
            'end_time': ['15:00:00']
        })
        result = recuperation_indisponibilites_rooms(df, {})
        self.assertIn(10, result)
        self.assertIn('Mercredi', result[10])
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

    def test_single_group_indisponibilite(self):
        df = pd.DataFrame({
            'group_id': [5],
            'day_of_week': ['Jeudi'],
            'start_time': ['14:00:00'],
            'end_time': ['16:00:00']
        })
        result = recuperation_indisponibilites_group(df, {})
        self.assertIn(5, result)
        self.assertIn('Jeudi', result[5])
        self.assertEqual(result[5]['Jeudi'], [(12, 16)])


class TestRecuperationIndisponibilitesSlot(unittest.TestCase):
    """Tests pour recuperation_indisponibilites_slot."""

    def test_single_slot_indisponibilite(self):
        df = pd.DataFrame({
            'slot_id': [100],
            'day_of_week': ['Lundi'],
            'start_time': ['08:00:00'],
            'end_time': ['10:00:00']
        })
        result = recuperation_indisponibilites_slot(df, {})
        self.assertIn(100, result)
        self.assertIn(0, result[100])  # 0 = Lundi
        self.assertEqual(result[100][0], [(0, 4)])


class TestGetAvailabilityProfFromUnavailable(unittest.TestCase):
    """Tests pour get_availabilityProf_From_Unavailable."""

    def test_empty_dataframe(self):
        df = pd.DataFrame({
            'teacher_id': [],
            'day_of_week': [],
            'start_time': [],
            'end_time': []
        })
        result = get_availabilityProf_From_Unavailable(df, 20)
        self.assertEqual(result, {})

    def test_with_indisponibilite(self):
        df = pd.DataFrame({
            'teacher_id': [1],
            'day_of_week': ['Lundi'],
            'start_time': ['08:00:00'],
            'end_time': ['10:00:00']
        })
        result = get_availabilityProf_From_Unavailable(df, 20)
        self.assertIn(1, result)
        # Le prof doit avoir des disponibilités pour les autres jours
        self.assertIn(1, result[1])  # Mardi
        self.assertIn(2, result[1])  # Mercredi
        self.assertIn(3, result[1])  # Jeudi
        self.assertIn(4, result[1])  # Vendredi


class TestRecuperationDisponibilitesProfs(unittest.TestCase):
    """Tests pour recuperation_disponibilites_profs."""

    def test_jour_sans_indisponibilite(self):
        indispo = {1: {'Lundi': [(0, 4)]}}
        result = recuperation_disponibilites_profs(20, {}, indispo)
        # Le prof doit être dispo les autres jours (Mardi à Vendredi)
        self.assertIn(1, result)
        self.assertIn(1, result[1])  # Mardi
        self.assertEqual(result[1][1], [(0, 20)])

    def test_tous_les_jours_disponibles(self):
        indispo = {1: {}}  # Aucune indisponibilité
        result = recuperation_disponibilites_profs(20, {}, indispo)
        self.assertIn(1, result)
        # Doit avoir (0, 20) pour chaque jour
        for day in range(5):
            self.assertIn(day, result[1])
            self.assertEqual(result[1][day], [(0, 20)])


if __name__ == '__main__':
    unittest.main()
