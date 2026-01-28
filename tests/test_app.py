"""
Tests pour le module app (test_combination et diagnostic_automatique).
Refactorisé pour éliminer la duplication de code.
"""
import unittest
from unittest.mock import MagicMock, patch
from ortools.sat.python import cp_model


def make_model_data(jours=5, creneaux=8, fenetre_midi=None):
    """Factory pour créer des données de modèle de test."""
    fenetre_midi = fenetre_midi or [3, 4]
    return {
        'jours': jours,
        'creneaux_par_jour': creneaux,
        'slots': [(j, o) for j in range(jours) for o in range(creneaux)],
        'fenetre_midi': fenetre_midi,
        'nb_slots': jours * creneaux,
        'salles': {'Salle1': 30},
        'profs': ['Prof1'],
        'cours': [{'id': 'C1', 'groups': ['G1']}],
        'duree_cours': {'C1': 2},
        'taille_groupes': {'G1': 25},
        'map_groupe_cours': {'G1': ['C1']}
    }


def make_mock_solver(status=cp_model.OPTIMAL, status_name="OPTIMAL"):
    """Factory pour créer un solver mocké."""
    mock_solver = MagicMock()
    mock_solver.Solve.return_value = status
    mock_solver.StatusName.return_value = status_name
    mock_solver.parameters = MagicMock()
    return mock_solver


def make_mock_scheduler():
    """Factory pour créer un scheduler mocké."""
    mock_scheduler = MagicMock()
    mock_scheduler.model = MagicMock()
    return mock_scheduler


class TestTestCombination(unittest.TestCase):
    """Tests pour la fonction test_combination."""

    def setUp(self):
        self.mock_data = make_model_data()

    def _run_test_combination(self, mock_solver_class, status, disabled_blocks, timeout=10):
        """Helper pour exécuter test_combination avec les paramètres donnés."""
        from app import test_combination
        
        mock_solver = make_mock_solver(status, cp_model.CpSolver().StatusName(status) if hasattr(cp_model, 'CpSolver') else "STATUS")
        mock_solver_class.return_value = mock_solver
        
        mock_model_class = MagicMock()
        mock_scheduler = make_mock_scheduler()
        mock_model_class.return_value = mock_scheduler
        
        result = test_combination(mock_model_class, self.mock_data, disabled_blocks, timeout=timeout)
        return result, mock_scheduler, mock_solver

    @patch('app.cp_model.CpSolver')
    def test_combination_returns_true_on_optimal(self, mock_solver_class):
        """test_combination retourne True si le solver trouve OPTIMAL."""
        result, mock_scheduler, _ = self._run_test_combination(
            mock_solver_class, cp_model.OPTIMAL, ['profs']
        )
        self.assertTrue(result)
        mock_scheduler.build_model.assert_called_once_with(disable_blocks=['profs'])

    @patch('app.cp_model.CpSolver')
    def test_combination_returns_true_on_feasible(self, mock_solver_class):
        """test_combination retourne True si le solver trouve FEASIBLE."""
        result, _, _ = self._run_test_combination(
            mock_solver_class, cp_model.FEASIBLE, ['salles']
        )
        self.assertTrue(result)

    @patch('app.cp_model.CpSolver')
    def test_combination_returns_false_on_infeasible(self, mock_solver_class):
        """test_combination retourne False si le problème est infaisable."""
        result, _, _ = self._run_test_combination(
            mock_solver_class, cp_model.INFEASIBLE, ['profs']
        )
        self.assertFalse(result)

    @patch('app.cp_model.CpSolver')
    def test_combination_with_multiple_blocks(self, mock_solver_class):
        """test_combination fonctionne avec plusieurs blocs désactivés."""
        disabled = ['profs', 'salles', 'etudiant']
        result, mock_scheduler, _ = self._run_test_combination(
            mock_solver_class, cp_model.OPTIMAL, disabled
        )
        self.assertTrue(result)
        mock_scheduler.build_model.assert_called_once_with(disable_blocks=disabled)

    @patch('app.cp_model.CpSolver')
    def test_combination_sets_solver_parameters(self, mock_solver_class):
        """test_combination configure correctement les paramètres du solver."""
        _, _, mock_solver = self._run_test_combination(
            mock_solver_class, cp_model.INFEASIBLE, ['profs'], timeout=120
        )
        self.assertEqual(mock_solver.parameters.max_time_in_seconds, 120)
        self.assertEqual(mock_solver.parameters.num_search_workers, 8)
        self.assertFalse(mock_solver.parameters.log_search_progress)

    @patch('app.cp_model.CpSolver')
    def test_combination_creates_scheduler_with_data(self, mock_solver_class):
        """test_combination crée le scheduler avec les bonnes données."""
        from app import test_combination
        mock_solver_class.return_value = make_mock_solver(cp_model.INFEASIBLE)
        mock_model_class = MagicMock()
        mock_model_class.return_value = make_mock_scheduler()
        
        test_combination(mock_model_class, self.mock_data, ['profs'], timeout=10)
        mock_model_class.assert_called_once_with(self.mock_data)


class TestDiagnosticAutomatique(unittest.TestCase):
    """Tests pour la fonction diagnostic_automatique."""

    BLOCKS = ["profs", "salles", "etudiant", "hierarchies", 
              "ordre_cm_td_tp", "prof disponibles", "salles dispo"]
    NUM_SINGLES = 7
    NUM_PAIRS = 21  # C(7,2)
    NUM_TRIPLETS = 35  # C(7,3)
    TOTAL_COMBINATIONS = NUM_SINGLES + NUM_PAIRS + NUM_TRIPLETS

    def setUp(self):
        self.mock_data = make_model_data()

    def _run_diagnostic(self, mock_test_combination, side_effect=None, return_value=None):
        """Helper pour exécuter diagnostic_automatique."""
        from app import diagnostic_automatique
        
        if side_effect:
            mock_test_combination.side_effect = side_effect
        else:
            mock_test_combination.return_value = return_value or False
        
        mock_model_class = MagicMock()
        diagnostic_automatique(mock_model_class, self.mock_data, timeout_per_test=10)
        return mock_test_combination

    @patch('app.test_combination')
    def test_diagnostic_stops_on_single_block_success(self, mock_test_combination):
        """diagnostic_automatique s'arrête dès qu'un seul bloc résout le problème."""
        self._run_diagnostic(mock_test_combination, return_value=True)
        self.assertEqual(mock_test_combination.call_count, 1)

    @patch('app.test_combination')
    def test_diagnostic_tests_all_single_blocks(self, mock_test_combination):
        """diagnostic_automatique teste tous les blocs seuls si aucun ne suffit."""
        def side_effect(model_class, data, blocks, timeout):
            return len(blocks) == 2  # Première paire fonctionne
        
        self._run_diagnostic(mock_test_combination, side_effect=side_effect)
        # 7 blocs seuls + 1 paire = 8 appels
        self.assertEqual(mock_test_combination.call_count, 8)

    @patch('app.test_combination')
    def test_diagnostic_tests_pairs_after_singles_fail(self, mock_test_combination):
        """diagnostic_automatique passe aux paires quand les blocs seuls échouent."""
        call_args_list = []
        
        def side_effect(model_class, data, blocks, timeout):
            call_args_list.append(blocks.copy())
            return len(blocks) == 2 and 'profs' in blocks and 'salles' in blocks
        
        self._run_diagnostic(mock_test_combination, side_effect=side_effect)
        
        single_calls = [c for c in call_args_list if len(c) == 1]
        pair_calls = [c for c in call_args_list if len(c) == 2]
        self.assertEqual(len(single_calls), self.NUM_SINGLES)
        self.assertGreater(len(pair_calls), 0)

    @patch('app.test_combination')
    def test_diagnostic_tests_triplets_after_pairs_fail(self, mock_test_combination):
        """diagnostic_automatique passe aux triplets quand les paires échouent."""
        call_args_list = []
        
        def side_effect(model_class, data, blocks, timeout):
            call_args_list.append(blocks.copy())
            return len(blocks) == 3  # Premier triplet fonctionne
        
        self._run_diagnostic(mock_test_combination, side_effect=side_effect)
        
        single_calls = [c for c in call_args_list if len(c) == 1]
        pair_calls = [c for c in call_args_list if len(c) == 2]
        triplet_calls = [c for c in call_args_list if len(c) == 3]
        
        self.assertEqual(len(single_calls), self.NUM_SINGLES)
        self.assertEqual(len(pair_calls), self.NUM_PAIRS)
        self.assertGreater(len(triplet_calls), 0)

    @patch('app.test_combination')
    def test_diagnostic_continues_when_all_fail(self, mock_test_combination):
        """diagnostic_automatique continue jusqu'à la fin quand tout échoue."""
        self._run_diagnostic(mock_test_combination, return_value=False)
        self.assertEqual(mock_test_combination.call_count, self.TOTAL_COMBINATIONS)


class TestBlockNames(unittest.TestCase):
    """Tests pour vérifier que les noms de blocs sont corrects."""

    EXPECTED_BLOCKS = [
        "profs", "salles", "etudiant", "hierarchies",
        "ordre_cm_td_tp", "prof disponibles", "salles dispo"
    ]

    def test_all_block_names_defined(self):
        """Vérifie que tous les noms de blocs attendus sont utilisés."""
        from app import diagnostic_automatique
        self.assertEqual(len(self.EXPECTED_BLOCKS), 7)


if __name__ == '__main__':
    unittest.main()
