"""
Tests pour le module diagnose.
Refactorisé pour éliminer la duplication de code.
"""
import unittest
from diagnose import diagnose_feasibility


def make_base_data(jours=5, creneaux=8, fenetre_midi=None, salles=None):
    """Factory pour créer des données de base pour les tests."""
    fenetre_midi = fenetre_midi if fenetre_midi is not None else [3, 4]
    salles = salles or {'Salle1': 30, 'Salle2': 50}
    return {
        'jours': jours,
        'creneaux_par_jour': creneaux,
        'slots': [(j, o) for j in range(jours) for o in range(creneaux)],
        'fenetre_midi': fenetre_midi,
        'nb_slots': jours * creneaux,
        'salles': salles,
        'cours': [],
        'duree_cours': {},
        'taille_groupes': {},
        'map_groupe_cours': {}
    }


def add_course(data, cid, group, duration, group_size):
    """Helper pour ajouter un cours aux données."""
    data['cours'].append({'id': cid, 'groups': [group]})
    data['duree_cours'][cid] = duration
    data['taille_groupes'][group] = group_size
    data['map_groupe_cours'].setdefault(group, []).append(cid)
    return data


class TestDiagnoseFeasibility(unittest.TestCase):
    """Tests unitaires pour diagnose_feasibility."""

    RESULT_KEYS = ['no_valid_start', 'no_room', 'group_overbooked']

    def setUp(self):
        self.base_data = make_base_data()

    def _assert_no_problems(self, result):
        """Vérifie qu'aucun problème n'est détecté."""
        for key in self.RESULT_KEYS:
            self.assertEqual(result[key], [])

    def test_empty_courses(self):
        """Test avec aucun cours - aucun problème détecté."""
        result = diagnose_feasibility(self.base_data)
        self._assert_no_problems(result)

    def test_valid_course(self):
        """Test avec un cours valide."""
        data = add_course(self.base_data.copy(), 'C1', 'G1', duration=2, group_size=25)
        result = diagnose_feasibility(data)
        self._assert_no_problems(result)

    def test_no_valid_start_duration_too_long(self):
        """Test cours avec durée trop longue pour tenir dans la journée."""
        data = make_base_data(jours=5, creneaux=4, fenetre_midi=[2])
        add_course(data, 'C1', 'G1', duration=5, group_size=25)  # durée > créneaux
        
        result = diagnose_feasibility(data)
        
        self.assertEqual(len(result['no_valid_start']), 1)
        self.assertEqual(result['no_valid_start'][0], ('C1', 5))

    def test_no_valid_start_intersects_midi(self):
        """Test cours qui chevauche obligatoirement la fenêtre midi."""
        data = make_base_data(jours=5, creneaux=4, fenetre_midi=[1, 2])
        add_course(data, 'C1', 'G1', duration=4, group_size=25)  # toute la journée
        
        result = diagnose_feasibility(data)
        
        self.assertEqual(len(result['no_valid_start']), 1)
        self.assertEqual(result['no_valid_start'][0], ('C1', 4))

    def test_no_room_capacity(self):
        """Test cours avec groupe trop grand pour toutes les salles."""
        data = make_base_data(salles={'Salle1': 20, 'Salle2': 30})  # max 30
        add_course(data, 'C1', 'G1', duration=2, group_size=50)  # groupe de 50
        
        result = diagnose_feasibility(data)
        
        self.assertEqual(result['no_valid_start'], [])
        self.assertEqual(len(result['no_room']), 1)
        self.assertEqual(result['no_room'][0], ('C1', 'G1', 50))

    def test_room_capacity_ok(self):
        """Test cours avec groupe qui peut tenir dans une salle."""
        data = make_base_data(salles={'Salle1': 20, 'Salle2': 60})  # Salle2 OK
        add_course(data, 'C1', 'G1', duration=2, group_size=50)
        
        result = diagnose_feasibility(data)
        self.assertEqual(result['no_room'], [])

    def test_group_overbooked(self):
        """Test groupe avec plus de cours que de créneaux disponibles."""
        data = make_base_data(jours=1, creneaux=6, fenetre_midi=[2, 3], salles={'Salle1': 100})
        # 4 slots utilisables, besoin de 6
        for i, cid in enumerate(['C1', 'C2', 'C3']):
            add_course(data, cid, 'G1', duration=2, group_size=25)
        
        result = diagnose_feasibility(data)
        
        self.assertEqual(len(result['group_overbooked']), 1)
        self.assertEqual(result['group_overbooked'][0], ('G1', 6, 4))

    def test_group_not_overbooked(self):
        """Test groupe avec assez de créneaux disponibles."""
        data = make_base_data(jours=2, creneaux=6, fenetre_midi=[2, 3], salles={'Salle1': 100})
        # 8 slots utilisables, besoin de 6
        for cid in ['C1', 'C2', 'C3']:
            add_course(data, cid, 'G1', duration=2, group_size=25)
        
        result = diagnose_feasibility(data)
        self.assertEqual(result['group_overbooked'], [])

    def test_multiple_problems(self):
        """Test avec plusieurs problèmes simultanés."""
        data = make_base_data(jours=1, creneaux=4, fenetre_midi=[1, 2], salles={'Salle1': 10})
        add_course(data, 'C1', 'G1', duration=4, group_size=5)   # durée trop longue
        add_course(data, 'C2', 'G2', duration=1, group_size=50)  # groupe trop grand
        
        result = diagnose_feasibility(data)
        
        self.assertEqual(len(result['no_valid_start']), 1)
        self.assertIn(('C1', 4), result['no_valid_start'])
        self.assertEqual(len(result['no_room']), 1)
        self.assertIn(('C2', 'G2', 50), result['no_room'])

    def test_returns_dict_with_correct_keys(self):
        """Test que la fonction retourne un dict avec les bonnes clés."""
        result = diagnose_feasibility(self.base_data)
        
        self.assertIsInstance(result, dict)
        for key in self.RESULT_KEYS:
            self.assertIn(key, result)


if __name__ == '__main__':
    unittest.main()
