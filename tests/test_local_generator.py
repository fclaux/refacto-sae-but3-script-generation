import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import tkinter as tk
import sys

# Mock la connexion DB AVANT d'importer local_generator
mock_engine = MagicMock()
with patch('sqlalchemy.create_engine', return_value=mock_engine):
    from local_generator import (
        df_to_courses_list,
        build_config_from_db,
        EDTViewerApp,
    )


class TestDfToCoursesListBasic:
    """Tests pour la fonction df_to_courses_list - conversion de base"""

    def test_df_to_courses_list_basic_conversion(self):
        """Test la conversion basique d'un DataFrame en liste de cours"""
        df = pd.DataFrame([
            {
                'jour': 'Lundi',
                'horaire': '08:00 → 10:00',
                'cours': 'Mathématiques',
                'professeur': 'Prof A',
                'salle': 'A101',
                'type_cours': 'CM',
                'promotion': 'BUT1',
                'semaine': 1,
                'groupe': None,
                'sous_groupe': None,
                'duration': 2.0
            }
        ])

        result = df_to_courses_list(df)

        assert len(result) == 1
        cours = result[0]
        assert cours[0] == 'Lundi'  # jour
        assert cours[1] == '08:00'  # heure_debut
        assert cours[2] == 4  # durée en demi-heures (2h = 4 * 30min)
        assert cours[3] == 'Mathématiques'  # cours
        assert cours[4] == 'Prof A'  # prof
        assert cours[5] == 'A101'  # salle
        assert cours[6] == 'CM'  # type
        assert cours[7] is None  # groupe_spec (cours commun)

    def test_df_to_courses_list_with_promotion_filter(self):
        """Test le filtrage par promotion"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': 1,
             'groupe': None, 'sous_groupe': None},
            {'jour': 'Mardi', 'horaire': '10:00 → 11:00', 'cours': 'Info', 'professeur': 'P2',
             'salle': 'B2', 'type_cours': 'TD', 'promotion': 'BUT2', 'semaine': 1,
             'groupe': None, 'sous_groupe': None}
        ])

        result = df_to_courses_list(df, promotion_filter='BUT1')

        assert len(result) == 1
        assert result[0][3] == 'Math'  # Seul le cours de BUT1

    def test_df_to_courses_list_with_week_filter(self):
        """Test le filtrage par semaine"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': 1,
             'groupe': None, 'sous_groupe': None},
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'Physique', 'professeur': 'P2',
             'salle': 'A2', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': 2,
             'groupe': None, 'sous_groupe': None}
        ])

        result = df_to_courses_list(df, week_filter=1)

        assert len(result) == 1
        assert result[0][3] == 'Math'

    def test_df_to_courses_list_with_group_filter(self):
        """Test le filtrage par groupe"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'TD', 'promotion': 'BUT1', 'semaine': 1,
             'groupe': 'G1', 'sous_groupe': None},
            {'jour': 'Lundi', 'horaire': '10:00 → 11:00', 'cours': 'Info', 'professeur': 'P2',
             'salle': 'B2', 'type_cours': 'TD', 'promotion': 'BUT1', 'semaine': 1,
             'groupe': 'G2', 'sous_groupe': None}
        ])

        result = df_to_courses_list(df, group_filter=['G1'])

        assert len(result) == 1
        assert result[0][3] == 'Math'


class TestDfToCoursesListGroupHandling:
    """Tests pour la gestion des groupes et sous-groupes dans df_to_courses_list"""

    def test_df_to_courses_list_with_sous_groupe(self):
        """Test la conversion avec sous-groupe"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'TP', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'TP', 'promotion': 'BUT1', 'semaine': 1,
             'groupe': 'G1', 'sous_groupe': 'G1A'}
        ])

        result = df_to_courses_list(df)

        assert len(result) == 1
        # groupe_spec doit contenir [0, 'A'] pour G1A
        assert result[0][7] is not None
        assert isinstance(result[0][7], list)
        assert result[0][7][1] == 'A'

    def test_df_to_courses_list_groupe_filter_includes_common_courses(self):
        """Test que les cours communs sont inclus même avec un filtre de groupe"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'CM Commun', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': 1,
             'groupe': None, 'sous_groupe': None},
            {'jour': 'Lundi', 'horaire': '10:00 → 11:00', 'cours': 'TD G1', 'professeur': 'P2',
             'salle': 'B2', 'type_cours': 'TD', 'promotion': 'BUT1', 'semaine': 1,
             'groupe': 'G1', 'sous_groupe': None}
        ])

        result = df_to_courses_list(df, group_filter=['G1'])

        # Les deux cours doivent être présents : le commun et celui de G1
        assert len(result) == 2


class TestDfToCoursesListDurationCalculation:
    """Tests pour le calcul de durée dans df_to_courses_list"""

    def test_df_to_courses_list_duration_calculation(self):
        """Test le calcul de durée en demi-heures depuis l'horaire"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:30', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': 1,
             'groupe': None, 'sous_groupe': None}
        ])

        result = df_to_courses_list(df)

        # 1h30 = 90 minutes = 3 demi-heures
        assert result[0][2] == 3

    def test_df_to_courses_list_duration_fallback(self):
        """Test le fallback de durée en cas d'erreur de parsing"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → ?', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': 1,
             'groupe': None, 'sous_groupe': None}
        ])

        result = df_to_courses_list(df)

        # Fallback = 2 demi-heures
        assert result[0][2] == 2

    def test_df_to_courses_list_handles_missing_data(self):
        """Test la gestion des données manquantes"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': None, 'professeur': None,
             'salle': None, 'type_cours': None, 'promotion': 'BUT1', 'semaine': 1,
             'groupe': None, 'sous_groupe': None}
        ])

        result = df_to_courses_list(df)

        assert result[0][3] == 'Cours sans nom'  # cours par défaut
        assert result[0][4] == ''  # prof vide
        assert result[0][5] == ''  # salle vide
        assert result[0][6] == 'Inconnu'  # type par défaut


class TestBuildConfigFromDb:
    """Tests pour la fonction build_config_from_db"""

    def test_build_config_from_db_basic(self):
        """Test la construction basique d'une config depuis un DataFrame"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 10:00', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': '1',
             'groupe': 'G1', 'sous_groupe': None, 'duration': 4}
        ])

        result = build_config_from_db(df, week_number=1, promotion_filter='BUT1')

        assert 'BUT1' in result
        assert 'groupes' in result['BUT1']
        assert 'cours' in result['BUT1']
        assert len(result['BUT1']['cours']) == 1

    def test_build_config_from_db_empty_dataframe(self):
        """Test avec un DataFrame vide"""
        df = pd.DataFrame()

        result = build_config_from_db(df, week_number=1)

        assert result == {}

    def test_build_config_from_db_no_matching_week(self):
        """Test quand aucun cours ne correspond à la semaine"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 10:00', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': '1',
             'groupe': None, 'sous_groupe': None, 'duration': 4}
        ])

        result = build_config_from_db(df, week_number=999)

        assert result == {}

    def test_build_config_from_db_groups_extraction(self):
        """Test l'extraction correcte des groupes"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'TD1', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'TD', 'promotion': 'BUT1', 'semaine': '1',
             'groupe': 'G1', 'sous_groupe': None, 'duration': 2},
            {'jour': 'Lundi', 'horaire': '09:00 → 10:00', 'cours': 'TP', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'TP', 'promotion': 'BUT1', 'semaine': '1',
             'groupe': 'G1', 'sous_groupe': 'G1A', 'duration': 2}
        ])

        result = build_config_from_db(df, week_number=1, promotion_filter='BUT1')

        # Vérifie que les groupes sont bien extraits
        assert 'BUT1' in result
        groups = result['BUT1']['groupes']
        # Les groupes doivent être triés et inclure G1, G1A, etc.
        assert len(groups) > 0

    def test_build_config_from_db_but1_groups(self):
        """Test que les groupes BUT1 sont correctement définis"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': '1',
             'groupe': None, 'sous_groupe': None, 'duration': 2}
        ])

        result = build_config_from_db(df, week_number=1, promotion_filter='BUT1')

        # Pour BUT1, les groupes doivent être G1, G1A, G1B, G2, G2A, G2B, G3, G3A, G3B
        expected_groups = ['G1', 'G1A', 'G1B', 'G2', 'G2A', 'G2B', 'G3', 'G3A', 'G3B']
        assert result['BUT1']['groupes'] == expected_groups

    def test_build_config_from_db_but2_groups(self):
        """Test que les groupes BUT2 sont correctement définis"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT2', 'semaine': '1',
             'groupe': None, 'sous_groupe': None, 'duration': 2}
        ])

        result = build_config_from_db(df, week_number=1, promotion_filter='BUT2')

        expected_groups = ['G4', 'G4A', 'G4B', 'G5', 'G5A', 'G5B']
        assert result['BUT2']['groupes'] == expected_groups

    def test_build_config_from_db_but3_groups(self):
        """Test que les groupes BUT3 sont correctement définis"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': 'Math', 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT3', 'semaine': '1',
             'groupe': None, 'sous_groupe': None, 'duration': 2}
        ])

        result = build_config_from_db(df, week_number=1, promotion_filter='BUT3')

        expected_groups = ['G7', 'G7A', 'G7B', 'G8', 'G8A']
        assert result['BUT3']['groupes'] == expected_groups


class TestBuildConfigFromDbCourseDetails:
    """Tests pour les détails des cours dans build_config_from_db"""

    def test_build_config_from_db_course_tuple_structure(self):
        """Test la structure du tuple de cours généré"""
        df = pd.DataFrame([
            {'jour': 'Mardi', 'horaire': '10:00 → 11:30', 'cours': 'Algo', 'professeur': 'Prof X',
             'salle': 'B202', 'type_cours': 'TD', 'promotion': 'BUT1', 'semaine': '5',
             'groupe': 'G1', 'sous_groupe': None, 'duration': 3}
        ])

        result = build_config_from_db(df, week_number=5, promotion_filter='BUT1')

        cours = result['BUT1']['cours'][0]
        assert cours[0] == 'Mardi'  # jour
        assert cours[1] == '10:00'  # heure_debut
        assert cours[2] == 6  # durée (3 * 2 = 6 demi-heures)
        assert cours[3] == 'Algo'  # cours
        assert cours[4] == 'Prof X'  # prof
        assert cours[5] == 'B202'  # salle
        assert cours[6] == 'TD'  # type

    def test_build_config_from_db_common_course_has_none_groupe_spec(self):
        """Test qu'un cours commun a groupe_spec = None"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 10:00', 'cours': 'CM Commun', 'professeur': 'P1',
             'salle': 'Amphi', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': '1',
             'groupe': None, 'sous_groupe': None, 'duration': 4}
        ])

        result = build_config_from_db(df, week_number=1, promotion_filter='BUT1')

        cours = result['BUT1']['cours'][0]
        assert cours[7] is None  # groupe_spec

    def test_build_config_from_db_handles_missing_course_title(self):
        """Test la gestion des titres de cours manquants"""
        df = pd.DataFrame([
            {'jour': 'Lundi', 'horaire': '08:00 → 09:00', 'cours': None, 'professeur': 'P1',
             'salle': 'A1', 'type_cours': 'CM', 'promotion': 'BUT1', 'semaine': '1',
             'groupe': None, 'sous_groupe': None, 'duration': 2}
        ])

        result = build_config_from_db(df, week_number=1, promotion_filter='BUT1')

        cours = result['BUT1']['cours'][0]
        assert cours[3] == 'Cours sans titre'  # Le titre par défaut pour pd.isna(cours)


class TestEDTViewerAppCalculerHoraire:
    """Tests pour la fonction calculer_horaire (logique métier)"""

    def test_calculer_horaire_standard(self):
        """Test le calcul d'horaire standard"""
        # Simule la fonction calculer_horaire extraite de la méthode
        from datetime import datetime, timedelta

        def calculer_horaire(row):
            try:
                heure_debut = datetime.strptime(row['start_hour'], '%H:%M:%S')
                duree_heures = float(row['duration'])
                heure_fin = (heure_debut + timedelta(hours=duree_heures))
                return f"{heure_debut.strftime('%H:%M')} → {heure_fin.strftime('%H:%M')}"
            except:
                return f"{row['start_hour'][:5]} → ?"

        row = {'start_hour': '08:00:00', 'duration': 2.0}
        result = calculer_horaire(row)

        assert result == '08:00 → 10:00'

    def test_calculer_horaire_avec_demi_heure(self):
        """Test le calcul avec des demi-heures"""
        from datetime import datetime, timedelta

        def calculer_horaire(row):
            try:
                heure_debut = datetime.strptime(row['start_hour'], '%H:%M:%S')
                duree_heures = float(row['duration'])
                heure_fin = (heure_debut + timedelta(hours=duree_heures))
                return f"{heure_debut.strftime('%H:%M')} → {heure_fin.strftime('%H:%M')}"
            except:
                return f"{row['start_hour'][:5]} → ?"

        row = {'start_hour': '14:00:00', 'duration': 1.5}
        result = calculer_horaire(row)

        assert result == '14:00 → 15:30'

    def test_calculer_horaire_error_handling(self):
        """Test la gestion d'erreur dans calculer_horaire"""
        from datetime import datetime, timedelta

        def calculer_horaire(row):
            try:
                heure_debut = datetime.strptime(row['start_hour'], '%H:%M:%S')
                duree_heures = float(row['duration'])
                heure_fin = (heure_debut + timedelta(hours=duree_heures))
                return f"{heure_debut.strftime('%H:%M')} → {heure_fin.strftime('%H:%M')}"
            except:
                return f"{row['start_hour'][:5]} → ?"

        row = {'start_hour': 'invalid', 'duration': 'bad'}
        result = calculer_horaire(row)

        assert ' → ?' in result


class TestEDTViewerAppMethods:
    """Tests pour les méthodes de EDTViewerApp qui retournent des valeurs"""

    def test_filtrer_with_empty_search(self):
        """Test que filtrer sans terme affiche toutes les données"""
        # Mock complètement Tkinter pour éviter les problèmes d'initialisation Tcl/Tk
        with patch('local_generator.engine'):
            app = object.__new__(EDTViewerApp)
            app.tree = MagicMock()

            # Mock StringVar avec un comportement simple
            mock_search_var = MagicMock()
            mock_search_var.get.return_value = ''
            app.search_var = mock_search_var

            app.data_complet = pd.DataFrame([
                {'cours': 'Math', 'prof': 'P1'},
                {'cours': 'Info', 'prof': 'P2'}
            ])
            app.afficher_dans_tableau = MagicMock()

            app.filtrer()

            # Doit afficher le DataFrame complet
            app.afficher_dans_tableau.assert_called_once()
            call_df = app.afficher_dans_tableau.call_args[0][0]
            assert len(call_df) == 2

    def test_filtrer_with_search_term(self):
        """Test le filtrage avec un terme de recherche"""
        with patch('local_generator.engine'):
            app = object.__new__(EDTViewerApp)
            app.tree = MagicMock()

            # Mock StringVar avec le terme 'math'
            mock_search_var = MagicMock()
            mock_search_var.get.return_value = 'math'
            app.search_var = mock_search_var

            app.data_complet = pd.DataFrame([
                {'cours': 'Mathématiques', 'prof': 'Dupont'},
                {'cours': 'Informatique', 'prof': 'Martin'}
            ])
            app.afficher_dans_tableau = MagicMock()

            app.filtrer()

            # Doit afficher seulement les lignes contenant 'math'
            call_df = app.afficher_dans_tableau.call_args[0][0]
            assert len(call_df) == 1
            assert 'Mathématiques' in call_df['cours'].values

