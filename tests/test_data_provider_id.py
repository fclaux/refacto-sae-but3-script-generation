# Fichier: tests/test_data_provider_id.py

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from data_provider_id import DataProviderID


@pytest.fixture
def db_config():
    return {
        'user': 'test_user',
        'password': 'test_pass',
        'host': 'localhost',
        'port': 3306,
        'database': 'test_db'
    }


@pytest.fixture
def data_provider(db_config):
    with patch('db_utils.create_engine'):
        return DataProviderID(db_config)


class TestDataProviderIDInit:
    def test_init_creates_engine_with_correct_url(self, db_config):
        with patch('db_utils.create_engine') as mock_engine:
            DataProviderID(db_config)
            expected_url = "mysql+mysqlconnector://test_user:test_pass@localhost:3306/test_db"
            mock_engine.assert_called_once_with(expected_url)


class TestTimeToSlot:
    def test_time_to_slot_8h00(self, data_provider):
        assert data_provider._time_to_slot("08:00:00") == 0

    def test_time_to_slot_8h30(self, data_provider):
        assert data_provider._time_to_slot("08:30:00") == 1

    def test_time_to_slot_13h30(self, data_provider):
        assert data_provider._time_to_slot("13:30:00") == 11

    def test_time_to_slot_18h00(self, data_provider):
        assert data_provider._time_to_slot("18:00:00") == 20

    def test_time_to_slot_nan(self, data_provider):
        assert data_provider._time_to_slot(pd.NA) == 0


class TestConvertDaystringToInt:
    def test_convert_lundi(self, data_provider):
        assert data_provider.convert_daystring_to_int("Lundi") == 0

    def test_convert_mardi(self, data_provider):
        assert data_provider.convert_daystring_to_int("Mardi") == 1

    def test_convert_mercredi(self, data_provider):
        assert data_provider.convert_daystring_to_int("Mercredi") == 2

    def test_convert_jeudi(self, data_provider):
        assert data_provider.convert_daystring_to_int("Jeudi") == 3

    def test_convert_vendredi(self, data_provider):
        assert data_provider.convert_daystring_to_int("Vendredi") == 4


class TestGetStartTime:
    def test_get_start_time_valid(self, data_provider):
        row = {'start_time': '08:00:00'}
        assert data_provider.get_start_time(row) == '08:00:00'

    def test_get_start_time_nan(self, data_provider):
        row = {'start_time': pd.NA}
        assert data_provider.get_start_time(row) == ""


class TestGetEndTime:
    def test_get_end_time_valid(self, data_provider):
        row = {'end_time': '10:00:00'}
        assert data_provider.get_end_time(row) == '10:00:00'

    def test_get_end_time_nan(self, data_provider):
        row = {'end_time': pd.NA}
        assert data_provider.get_end_time(row) == ""


class TestGetListRoom:
    def test_get_list_room(self, data_provider):
        df_mock = pd.DataFrame({'name': ['Salle1', 'Salle2', 'Salle3']})
        with patch.object(pd, 'read_sql', return_value=df_mock):
            result = data_provider.get_list_room()
            assert result == ['Salle1', 'Salle2', 'Salle3']

    def test_get_list_room_empty(self, data_provider):
        df_mock = pd.DataFrame({'name': []})
        with patch.object(pd, 'read_sql', return_value=df_mock):
            result = data_provider.get_list_room()
            assert result == []


class TestBuildCourseStructures:
    def test_build_course_structures_cm(self, data_provider):
        df = pd.DataFrame({
            'duration': [1.5],
            'type_id': [1],
            'teaching_title': ['Math'],
            'promotion_name': ['BUT1'],
            'group_name': [None],
            'subgroup_name': [None],
            'promo_size': [100],
            'group_size': [None],
            'subgroup_size': [None]
        }, index=[1])

        profs_par_slot = {1: ['Prof A']}
        profs = ['Prof A', 'Prof B']

        cours, duree, taille, map_groupe = data_provider._build_course_structures(df, profs_par_slot, profs)

        assert len(cours) == 1
        assert 'CM_Math_BUT1_s1' in cours[0]['id']
        assert 'BUT1' in cours[0]['groups']
        assert duree['CM_Math_BUT1_s1'] == 3

    def test_build_course_structures_td(self, data_provider):
        df = pd.DataFrame({
            'duration': [1.0],
            'type_id': [2],
            'teaching_title': ['Info'],
            'promotion_name': ['BUT1'],
            'group_name': ['G1'],
            'subgroup_name': [None],
            'promo_size': [100],
            'group_size': [30],
            'subgroup_size': [None]
        }, index=[2])

        profs_par_slot = {2: ['Prof B']}
        profs = ['Prof A', 'Prof B']

        cours, duree, taille, map_groupe = data_provider._build_course_structures(df, profs_par_slot, profs)

        assert len(cours) == 1
        assert 'TD_Info_G1_s2' in cours[0]['id']
        assert cours[0]['groups'] == ['G1']

    def test_build_course_structures_tp(self, data_provider):
        df = pd.DataFrame({
            'duration': [2.0],
            'type_id': [3],
            'teaching_title': ['TP Algo'],
            'promotion_name': ['BUT1'],
            'group_name': ['G1'],
            'subgroup_name': ['A'],
            'promo_size': [100],
            'group_size': [30],
            'subgroup_size': [15]
        }, index=[3])

        profs_par_slot = {3: ['Prof A']}
        profs = ['Prof A']

        cours, duree, taille, map_groupe = data_provider._build_course_structures(df, profs_par_slot, profs)

        assert len(cours) == 1
        assert 'TP_TP Algo_G1A_s3' in cours[0]['id']
        assert cours[0]['groups'] == ['G1A']
        assert duree['TP_TP Algo_G1A_s3'] == 4

    def test_build_course_structures_no_prof_assigned(self, data_provider):
        df = pd.DataFrame({
            'duration': [1.0],
            'type_id': [2],
            'teaching_title': ['Test'],
            'promotion_name': ['BUT1'],
            'group_name': ['G1'],
            'subgroup_name': [None],
            'promo_size': [100],
            'group_size': [30],
            'subgroup_size': [None]
        }, index=[5])

        profs_par_slot = {}
        profs = ['Prof A']

        cours, duree, taille, map_groupe = data_provider._build_course_structures(df, profs_par_slot, profs)

        assert len(cours) == 1
        assert 'None_0' in profs


class TestConvertCoursesDictToListInsert:
    def test_convert_courses_dict(self, data_provider):
        courses = [
            {'name': 'CM_Math_BUT1_s1', 'day': 0, 'start_hour': '08:00', 'room': 'A101'}
        ]

        with patch.object(data_provider, 'insert_data_with_pandas'):
            with patch('data_provider_id.convert_days_int_to_string', return_value='Lundi'):
                result = data_provider.convert_courses_dict_to_list_insert(courses)

                assert len(result) == 1
                assert result[0][0] == '08:00'
                assert result[0][2] == 'A101'
                assert result[0][3] == 'Lundi'

class TestLoadAndPrepareData:
    def test_load_and_prepare_data_structure(self, data_provider):
        # Mock de toutes les requêtes SQL
        df_salles = pd.DataFrame({'name': ['A101', 'B202'], 'seat_capacity': [30, 50]})
        df_profs = pd.DataFrame({
            'teacher_id': [1, 2],
            'prof_name': ['Prof A', 'Prof B']
        })
        df_planning = pd.DataFrame({
            'duration': [1.5],
            'type_id': [1],
            'teaching_title': ['Math'],
            'promotion_name': ['BUT1'],
            'group_name': [None],
            'subgroup_name': [None],
            'promo_size': [100],
            'group_size': [None],
            'subgroup_size': [None],
            'promotion_id': [1]
        }, index=[1])
        df_prof_slot = pd.DataFrame({'slot_id': [1], 'prof_name': ['Prof A']})
        df_dispos = pd.DataFrame(columns=['teacher_id', 'day_of_week', 'start_time', 'end_time', 'priority', 'week_id'])

        with patch.object(pd, 'read_sql', side_effect=[
                              df_salles,
                              df_profs,
                              df_planning,
                              df_dispos,
                              df_dispos,
                              df_dispos,
                              df_dispos,
                              df_prof_slot
                          ]):
            with patch('data_provider_id.get_availabilityProf_From_Unavailable', return_value={}):
                with patch('data_provider_id.get_availabilityRoom_From_Unavailable', return_value={}):
                    with patch('data_provider_id.get_availabilityGroup_From_Unavailable', return_value={}):
                        with patch('data_provider_id.get_availabilitySlot_From_Unavailable', return_value={}):
                            result = data_provider.load_and_prepare_data(week_id=1)

        assert 'jours' in result
        assert result['jours'] == 5
        assert 'creneaux_par_jour' in result
        assert result['creneaux_par_jour'] == 23
        assert 'cours' in result
        assert 'salles' in result
        assert 'profs' in result
        assert 'disponibilites_profs' in result
        assert result['salles'] == {'A101': 30, 'B202': 50}
        assert result['profs'] == ['Prof A', 'Prof B']


class TestGetAvailabilityProfFromUnavailable:
    def test_get_availability_prof_basic(self, data_provider):
        df_dispos = pd.DataFrame({
            'teacher_id': [1, 1, 2],
            'day_of_week': ['Lundi', 'Mardi', 'Lundi'],
            'start_time': ['08:00:00', '10:00:00', '14:00:00'],
            'end_time': ['10:00:00', '12:00:00', '16:00:00']
        })

        result = data_provider.get_availabilityProf_From_Unavailable(df_dispos)

        assert result is None  # La méthode ne retourne rien

    def test_get_availability_prof_with_na_times(self, data_provider):
        df_dispos = pd.DataFrame({
            'teacher_id': [1],
            'day_of_week': ['Lundi'],
            'start_time': [pd.NA],
            'end_time': [pd.NA]
        })

        result = data_provider.get_availabilityProf_From_Unavailable(df_dispos)

        assert result is None


class TestConvertCoursesDictToListInsertComplete:
    def test_convert_courses_dict_complete(self, data_provider):
        courses = [
            {'name': 'CM_Math_BUT1_s42', 'day': 0, 'start_hour': '08:00', 'room': 'A101'},
            {'name': 'TD_Info_G1_s15', 'day': 2, 'start_hour': '10:00', 'room': 'B202'}
        ]

        mock_insert = Mock()
        data_provider.insert_data_with_pandas = mock_insert

        with patch('data_provider_id.convert_days_int_to_string', side_effect=['Lundi', 'Mercredi']):
            result = data_provider.convert_courses_dict_to_list_insert(courses)

        assert len(result) == 2
        assert result[0] == ('08:00', '42', 'A101', 'Lundi')
        assert result[1] == ('10:00', '15', 'B202', 'Mercredi')

        # Vérifie que insert_data_with_pandas a été appelé
        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][1] == 'edt_slot'
        df_inserted = call_args[0][0]
        assert len(df_inserted) == 2
        assert list(df_inserted.columns) == ['start_hour', 'slot_id', 'room_id', 'day_of_week']

    def test_convert_courses_dict_slot_id_extraction(self, data_provider):
        courses = [
            {'name': 'TP_Algo_G1A_s123', 'day': 1, 'start_hour': '14:00', 'room': 'C303'}
        ]

        with patch.object(data_provider, 'insert_data_with_pandas'):
            with patch('data_provider_id.convert_days_int_to_string', return_value='Mardi'):
                result = data_provider.convert_courses_dict_to_list_insert(courses)

        assert result[0][1] == '123'

    def test_convert_courses_empty_list(self, data_provider):
        courses = []

        with patch.object(data_provider, 'insert_data_with_pandas') as mock_insert:
            result = data_provider.convert_courses_dict_to_list_insert(courses)

        assert result == []
        mock_insert.assert_called_once()


class TestInsertDataWithPandas:
    def test_insert_data_with_pandas_success(self, data_provider):
        df_test = pd.DataFrame({
            'start_hour': ['08:00'],
            'slot_id': [1],
            'room_id': ['A101'],
            'day_of_week': ['Lundi']
        })

        with patch.object(df_test, 'to_sql', return_value=1) as mock_to_sql:
            data_provider.insert_data_with_pandas(df_test, 'edt_slot')

            mock_to_sql.assert_called_once_with(
                name='edt_slot',
                con=data_provider.engine,
                if_exists='append',
                index=False
            )

    def test_insert_data_with_pandas_error(self, data_provider, capsys):
        df_test = pd.DataFrame({'col': [1]})

        with patch.object(df_test, 'to_sql', side_effect=Exception("DB Error")):
            data_provider.insert_data_with_pandas(df_test, 'test_table')

            captured = capsys.readouterr()
            assert "Erreur lors de l'insertion" in captured.out
