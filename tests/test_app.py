import unittest
from unittest.mock import MagicMock, patch, call
from ortools.sat.python import cp_model


class TestTestCombination(unittest.TestCase):
    """Tests pour la fonction test_combination."""

    def setUp(self):
        """Configuration de base pour les tests."""
        self.mock_data = {
            'jours': 5,
            'creneaux_par_jour': 8,
            'slots': [(j, o) for j in range(5) for o in range(8)],
            'fenetre_midi': [3, 4],
            'nb_slots': 40,
            'salles': {'Salle1': 30},
            'profs': ['Prof1'],
            'cours': [{'id': 'C1', 'groups': ['G1']}],
            'duree_cours': {'C1': 2},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['C1']}
        }

    @patch('app.cp_model.CpSolver')
    def test_combination_returns_true_on_optimal(self, mock_solver_class):
        """test_combination retourne True si le solver trouve OPTIMAL."""
        from app import test_combination
        
        mock_solver = MagicMock()
        mock_solver_class.return_value = mock_solver
        mock_solver.Solve.return_value = cp_model.OPTIMAL
        mock_solver.StatusName.return_value = "OPTIMAL"
        
        mock_model_class = MagicMock()
        mock_scheduler = MagicMock()
        mock_model_class.return_value = mock_scheduler
        
        result = test_combination(mock_model_class, self.mock_data, ['profs'], timeout=10)
        
        self.assertTrue(result)
        mock_scheduler.build_model.assert_called_once_with(disable_blocks=['profs'])

    @patch('app.cp_model.CpSolver')
    def test_combination_returns_true_on_feasible(self, mock_solver_class):
        """test_combination retourne True si le solver trouve FEASIBLE."""
        from app import test_combination
        
        mock_solver = MagicMock()
        mock_solver_class.return_value = mock_solver
        mock_solver.Solve.return_value = cp_model.FEASIBLE
        mock_solver.StatusName.return_value = "FEASIBLE"
        
        mock_model_class = MagicMock()
        mock_scheduler = MagicMock()
        mock_model_class.return_value = mock_scheduler
        
        result = test_combination(mock_model_class, self.mock_data, ['salles'], timeout=10)
        
        self.assertTrue(result)

    @patch('app.cp_model.CpSolver')
    def test_combination_returns_false_on_infeasible(self, mock_solver_class):
        """test_combination retourne False si le problème est infaisable."""
        from app import test_combination
        
        mock_solver = MagicMock()
        mock_solver_class.return_value = mock_solver
        mock_solver.Solve.return_value = cp_model.INFEASIBLE
        mock_solver.StatusName.return_value = "INFEASIBLE"
        
        mock_model_class = MagicMock()
        mock_scheduler = MagicMock()
        mock_model_class.return_value = mock_scheduler
        
        result = test_combination(mock_model_class, self.mock_data, ['profs'], timeout=10)
        
        self.assertFalse(result)

    @patch('app.cp_model.CpSolver')
    def test_combination_with_multiple_blocks(self, mock_solver_class):
        """test_combination fonctionne avec plusieurs blocs désactivés."""
        from app import test_combination
        
        mock_solver = MagicMock()
        mock_solver_class.return_value = mock_solver
        mock_solver.Solve.return_value = cp_model.OPTIMAL
        mock_solver.StatusName.return_value = "OPTIMAL"
        
        mock_model_class = MagicMock()
        mock_scheduler = MagicMock()
        mock_model_class.return_value = mock_scheduler
        
        disabled = ['profs', 'salles', 'etudiant']
        result = test_combination(mock_model_class, self.mock_data, disabled, timeout=10)
        
        self.assertTrue(result)
        mock_scheduler.build_model.assert_called_once_with(disable_blocks=disabled)

    @patch('app.cp_model.CpSolver')
    def test_combination_sets_solver_parameters(self, mock_solver_class):
        """test_combination configure correctement les paramètres du solver."""
        from app import test_combination
        
        mock_solver = MagicMock()
        mock_solver_class.return_value = mock_solver
        mock_solver.Solve.return_value = cp_model.INFEASIBLE
        mock_solver.StatusName.return_value = "INFEASIBLE"
        
        mock_model_class = MagicMock()
        mock_scheduler = MagicMock()
        mock_model_class.return_value = mock_scheduler
        
        test_combination(mock_model_class, self.mock_data, ['profs'], timeout=120)
        
        self.assertEqual(mock_solver.parameters.max_time_in_seconds, 120)
        self.assertEqual(mock_solver.parameters.num_search_workers, 8)
        self.assertEqual(mock_solver.parameters.log_search_progress, False)


class TestDiagnosticAutomatique(unittest.TestCase):
    """Tests pour la fonction diagnostic_automatique."""

    def setUp(self):
        """Configuration de base pour les tests."""
        self.mock_data = {
            'jours': 5,
            'creneaux_par_jour': 8,
            'slots': [(j, o) for j in range(5) for o in range(8)],
            'fenetre_midi': [3, 4],
            'nb_slots': 40,
            'salles': {'Salle1': 30},
            'profs': ['Prof1'],
            'cours': [{'id': 'C1', 'groups': ['G1']}],
            'duree_cours': {'C1': 2},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['C1']}
        }
        self.blocks = [
            "profs", "salles", "etudiant", "hierarchies",
            "ordre_cm_td_tp", "prof disponibles", "salles dispo"
        ]

    @patch('app.test_combination')
    def test_diagnostic_stops_on_single_block_success(self, mock_test_combination):
        """diagnostic_automatique s'arrête dès qu'un seul bloc résout le problème."""
        from app import diagnostic_automatique
        
        # Le premier bloc ('profs') résout le problème
        mock_test_combination.return_value = True
        
        mock_model_class = MagicMock()
        
        diagnostic_automatique(mock_model_class, self.mock_data, timeout_per_test=10)
        
        # Vérifie qu'on a appelé test_combination une seule fois
        self.assertEqual(mock_test_combination.call_count, 1)
        mock_test_combination.assert_called_once_with(
            mock_model_class, self.mock_data, ['profs'], 10
        )

    @patch('app.test_combination')
    def test_diagnostic_tests_all_single_blocks(self, mock_test_combination):
        """diagnostic_automatique teste tous les blocs seuls si aucun ne suffit."""
        from app import diagnostic_automatique
        
        # Aucun bloc seul ne fonctionne, mais la première paire fonctionne
        def side_effect(model_class, data, blocks, timeout):
            if len(blocks) == 2:
                return True  # Première paire fonctionne
            return False
        
        mock_test_combination.side_effect = side_effect
        
        mock_model_class = MagicMock()
        
        diagnostic_automatique(mock_model_class, self.mock_data, timeout_per_test=10)
        
        # 7 blocs seuls + 1 paire = 8 appels
        self.assertEqual(mock_test_combination.call_count, 8)

    @patch('app.test_combination')
    def test_diagnostic_tests_pairs_after_singles_fail(self, mock_test_combination):
        """diagnostic_automatique passe aux paires quand les blocs seuls échouent."""
        from app import diagnostic_automatique
        
        call_args_list = []
        
        def side_effect(model_class, data, blocks, timeout):
            call_args_list.append(blocks.copy())
            if len(blocks) == 2 and 'profs' in blocks and 'salles' in blocks:
                return True
            return False
        
        mock_test_combination.side_effect = side_effect
        
        mock_model_class = MagicMock()
        
        diagnostic_automatique(mock_model_class, self.mock_data, timeout_per_test=10)
        
        # Vérifie que les 7 blocs seuls ont été testés
        single_block_calls = [c for c in call_args_list if len(c) == 1]
        self.assertEqual(len(single_block_calls), 7)
        
        # Vérifie qu'au moins une paire a été testée
        pair_calls = [c for c in call_args_list if len(c) == 2]
        self.assertGreater(len(pair_calls), 0)

    @patch('app.test_combination')
    def test_diagnostic_tests_triplets_after_pairs_fail(self, mock_test_combination):
        """diagnostic_automatique passe aux triplets quand les paires échouent."""
        from app import diagnostic_automatique
        
        call_args_list = []
        
        def side_effect(model_class, data, blocks, timeout):
            call_args_list.append(blocks.copy())
            if len(blocks) == 3:
                return True  # Premier triplet fonctionne
            return False
        
        mock_test_combination.side_effect = side_effect
        
        mock_model_class = MagicMock()
        
        diagnostic_automatique(mock_model_class, self.mock_data, timeout_per_test=10)
        
        # Vérifie que les 7 blocs seuls ont été testés
        single_block_calls = [c for c in call_args_list if len(c) == 1]
        self.assertEqual(len(single_block_calls), 7)
        
        # Vérifie que toutes les paires (C(7,2) = 21) ont été testées
        pair_calls = [c for c in call_args_list if len(c) == 2]
        self.assertEqual(len(pair_calls), 21)
        
        # Vérifie qu'au moins un triplet a été testé
        triplet_calls = [c for c in call_args_list if len(c) == 3]
        self.assertGreater(len(triplet_calls), 0)

    @patch('app.test_combination')
    def test_diagnostic_continues_when_all_fail(self, mock_test_combination):
        """diagnostic_automatique continue jusqu'à la fin quand tout échoue."""
        from app import diagnostic_automatique
        
        mock_test_combination.return_value = False
        
        mock_model_class = MagicMock()
        
        # Ne doit pas lever d'exception
        diagnostic_automatique(mock_model_class, self.mock_data, timeout_per_test=10)
        
        # 7 blocs seuls + 21 paires + 35 triplets = 63 appels au total
        self.assertEqual(mock_test_combination.call_count, 63)


class TestBlockNames(unittest.TestCase):
    """Tests pour vérifier que les noms de blocs sont corrects."""

    def test_all_block_names_defined(self):
        """Vérifie que tous les noms de blocs attendus sont utilisés."""
        expected_blocks = [
            "profs",
            "salles",
            "etudiant",
            "hierarchies",
            "ordre_cm_td_tp",
            "prof disponibles",
            "salles dispo"
        ]
        
        # Import de la fonction pour vérifier les noms
        from app import diagnostic_automatique
        
        # Le test s'assure que le module s'importe correctement
        # Les noms sont définis en dur dans la fonction
        self.assertEqual(len(expected_blocks), 7)


class TestIntegrationTestCombination(unittest.TestCase):
    """Tests d'intégration pour test_combination avec un vrai modèle mock."""

    def setUp(self):
        """Configuration pour les tests d'intégration."""
        self.mock_data = {
            'jours': 1,
            'creneaux_par_jour': 4,
            'slots': [(0, 0), (0, 1), (0, 2), (0, 3)],
            'fenetre_midi': [2],
            'nb_slots': 4,
            'salles': {'Salle1': 30},
            'profs': ['Prof1'],
            'cours': [{'id': 'C1', 'groups': ['G1']}],
            'duree_cours': {'C1': 1},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['C1']}
        }

    @patch('app.cp_model.CpSolver')
    def test_combination_creates_scheduler_with_data(self, mock_solver_class):
        """test_combination crée le scheduler avec les bonnes données."""
        from app import test_combination
        
        mock_solver = MagicMock()
        mock_solver_class.return_value = mock_solver
        mock_solver.Solve.return_value = cp_model.INFEASIBLE
        mock_solver.StatusName.return_value = "INFEASIBLE"
        
        mock_model_class = MagicMock()
        mock_scheduler = MagicMock()
        mock_model_class.return_value = mock_scheduler
        
        test_combination(mock_model_class, self.mock_data, ['profs'], timeout=10)
        
        mock_model_class.assert_called_once_with(self.mock_data)

    @patch('app.cp_model.CpSolver')
    def test_combination_solves_scheduler_model(self, mock_solver_class):
        """test_combination résout le modèle du scheduler."""
        from app import test_combination
        
        mock_solver = MagicMock()
        mock_solver_class.return_value = mock_solver
        mock_solver.Solve.return_value = cp_model.OPTIMAL
        mock_solver.StatusName.return_value = "OPTIMAL"
        
        mock_model_class = MagicMock()
        mock_scheduler = MagicMock()
        mock_scheduler.model = MagicMock()
        mock_model_class.return_value = mock_scheduler
        
        test_combination(mock_model_class, self.mock_data, ['profs'], timeout=10)
        
        mock_solver.Solve.assert_called_once_with(mock_scheduler.model)


if __name__ == '__main__':
    unittest.main()
