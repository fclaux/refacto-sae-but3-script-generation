import unittest
from diagnose import diagnose_feasibility


class TestDiagnoseFeasibility(unittest.TestCase):
    """Tests unitaires pour diagnose_feasibility."""

    def setUp(self):
        """Configuration de base pour les tests."""
        self.base_data = {
            'jours': 5,
            'creneaux_par_jour': 8,
            'slots': [(j, o) for j in range(5) for o in range(8)],
            'fenetre_midi': [3, 4],  # créneaux midi
            'nb_slots': 40,
            'salles': {'Salle1': 30, 'Salle2': 50},
            'cours': [],
            'duree_cours': {},
            'taille_groupes': {},
            'map_groupe_cours': {}
        }

    def test_empty_courses(self):
        """Test avec aucun cours - aucun problème détecté."""
        d = self.base_data.copy()
        
        result = diagnose_feasibility(d)
        
        self.assertEqual(result['no_valid_start'], [])
        self.assertEqual(result['no_room'], [])
        self.assertEqual(result['group_overbooked'], [])

    def test_valid_course(self):
        """Test avec un cours valide."""
        d = self.base_data.copy()
        d['cours'] = [{'id': 'C1', 'groups': ['G1']}]
        d['duree_cours'] = {'C1': 2}
        d['taille_groupes'] = {'G1': 25}
        d['map_groupe_cours'] = {'G1': ['C1']}
        
        result = diagnose_feasibility(d)
        
        self.assertEqual(result['no_valid_start'], [])
        self.assertEqual(result['no_room'], [])
        self.assertEqual(result['group_overbooked'], [])

    def test_no_valid_start_duration_too_long(self):
        """Test cours avec durée trop longue pour tenir dans la journée."""
        d = self.base_data.copy()
        d['creneaux_par_jour'] = 4
        d['slots'] = [(j, o) for j in range(5) for o in range(4)]
        d['fenetre_midi'] = [2]  # 1 créneau midi
        d['nb_slots'] = 20
        d['cours'] = [{'id': 'C1', 'groups': ['G1']}]
        d['duree_cours'] = {'C1': 5}  # durée > créneaux par jour
        d['taille_groupes'] = {'G1': 25}
        d['map_groupe_cours'] = {'G1': ['C1']}
        
        result = diagnose_feasibility(d)
        
        self.assertEqual(len(result['no_valid_start']), 1)
        self.assertEqual(result['no_valid_start'][0], ('C1', 5))

    def test_no_valid_start_intersects_midi(self):
        """Test cours qui chevauche obligatoirement la fenêtre midi."""
        d = self.base_data.copy()
        d['creneaux_par_jour'] = 4
        d['slots'] = [(j, o) for j in range(5) for o in range(4)]
        d['fenetre_midi'] = [1, 2]  # milieu bloqué
        d['nb_slots'] = 20
        d['cours'] = [{'id': 'C1', 'groups': ['G1']}]
        d['duree_cours'] = {'C1': 4}  # durée = toute la journée, doit croiser midi
        d['taille_groupes'] = {'G1': 25}
        d['map_groupe_cours'] = {'G1': ['C1']}
        
        result = diagnose_feasibility(d)
        
        self.assertEqual(len(result['no_valid_start']), 1)
        self.assertEqual(result['no_valid_start'][0], ('C1', 4))

    def test_no_room_capacity(self):
        """Test cours avec groupe trop grand pour toutes les salles."""
        d = self.base_data.copy()
        d['salles'] = {'Salle1': 20, 'Salle2': 30}  # max 30 places
        d['cours'] = [{'id': 'C1', 'groups': ['G1']}]
        d['duree_cours'] = {'C1': 2}
        d['taille_groupes'] = {'G1': 50}  # groupe de 50, aucune salle suffisante
        d['map_groupe_cours'] = {'G1': ['C1']}
        
        result = diagnose_feasibility(d)
        
        self.assertEqual(result['no_valid_start'], [])
        self.assertEqual(len(result['no_room']), 1)
        self.assertEqual(result['no_room'][0], ('C1', 'G1', 50))

    def test_room_capacity_ok(self):
        """Test cours avec groupe qui peut tenir dans une salle."""
        d = self.base_data.copy()
        d['salles'] = {'Salle1': 20, 'Salle2': 60}  # Salle2 assez grande
        d['cours'] = [{'id': 'C1', 'groups': ['G1']}]
        d['duree_cours'] = {'C1': 2}
        d['taille_groupes'] = {'G1': 50}
        d['map_groupe_cours'] = {'G1': ['C1']}
        
        result = diagnose_feasibility(d)
        
        self.assertEqual(result['no_room'], [])

    def test_group_overbooked(self):
        """Test groupe avec plus de cours que de créneaux disponibles."""
        d = self.base_data.copy()
        d['jours'] = 1
        d['creneaux_par_jour'] = 6
        d['slots'] = [(0, o) for o in range(6)]
        d['fenetre_midi'] = [2, 3]  # 2 créneaux midi, reste 4 utilisables
        d['nb_slots'] = 6
        d['salles'] = {'Salle1': 100}
        d['cours'] = [
            {'id': 'C1', 'groups': ['G1']},
            {'id': 'C2', 'groups': ['G1']},
            {'id': 'C3', 'groups': ['G1']}
        ]
        d['duree_cours'] = {'C1': 2, 'C2': 2, 'C3': 2}  # total = 6 slots nécessaires
        d['taille_groupes'] = {'G1': 25}
        d['map_groupe_cours'] = {'G1': ['C1', 'C2', 'C3']}  # besoin 6 slots, 4 dispo
        
        result = diagnose_feasibility(d)
        
        self.assertEqual(len(result['group_overbooked']), 1)
        self.assertEqual(result['group_overbooked'][0], ('G1', 6, 4))

    def test_group_not_overbooked(self):
        """Test groupe avec assez de créneaux disponibles."""
        d = self.base_data.copy()
        d['jours'] = 2
        d['creneaux_par_jour'] = 6
        d['slots'] = [(j, o) for j in range(2) for o in range(6)]
        d['fenetre_midi'] = [2, 3]  # 2 créneaux midi par jour, reste 4*2=8 utilisables
        d['nb_slots'] = 12
        d['salles'] = {'Salle1': 100}
        d['cours'] = [
            {'id': 'C1', 'groups': ['G1']},
            {'id': 'C2', 'groups': ['G1']},
            {'id': 'C3', 'groups': ['G1']}
        ]
        d['duree_cours'] = {'C1': 2, 'C2': 2, 'C3': 2}  # total = 6 slots nécessaires
        d['taille_groupes'] = {'G1': 25}
        d['map_groupe_cours'] = {'G1': ['C1', 'C2', 'C3']}  # besoin 6 slots, 8 dispo
        
        result = diagnose_feasibility(d)
        
        self.assertEqual(result['group_overbooked'], [])

    def test_multiple_problems(self):
        """Test avec plusieurs problèmes simultanés."""
        d = self.base_data.copy()
        d['jours'] = 1
        d['creneaux_par_jour'] = 4
        d['slots'] = [(0, o) for o in range(4)]
        d['fenetre_midi'] = [1, 2]
        d['nb_slots'] = 4
        d['salles'] = {'Salle1': 10}  # petite salle
        d['cours'] = [
            {'id': 'C1', 'groups': ['G1']},  # durée trop longue
            {'id': 'C2', 'groups': ['G2']}   # groupe trop grand
        ]
        d['duree_cours'] = {'C1': 4, 'C2': 1}
        d['taille_groupes'] = {'G1': 5, 'G2': 50}
        d['map_groupe_cours'] = {'G1': ['C1'], 'G2': ['C2']}
        
        result = diagnose_feasibility(d)
        
        # C1 ne peut pas commencer (durée 4, traverse midi)
        self.assertEqual(len(result['no_valid_start']), 1)
        self.assertIn(('C1', 4), result['no_valid_start'])
        
        # C2 n'a pas de salle assez grande
        self.assertEqual(len(result['no_room']), 1)
        self.assertIn(('C2', 'G2', 50), result['no_room'])

    def test_returns_dict_with_correct_keys(self):
        """Test que la fonction retourne un dict avec les bonnes clés."""
        d = self.base_data.copy()
        
        result = diagnose_feasibility(d)
        
        self.assertIsInstance(result, dict)
        self.assertIn('no_valid_start', result)
        self.assertIn('no_room', result)
        self.assertIn('group_overbooked', result)


if __name__ == '__main__':
    unittest.main()
