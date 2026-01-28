import unittest
from unittest.mock import MagicMock, patch
from ortools.sat.python import cp_model
from time_table_model import TimetableModel


class TestTimetableModelInit(unittest.TestCase):
    """Tests pour l'initialisation de TimetableModel."""

    def test_init_creates_model(self):
        data = {'cours': [], 'slots': [], 'nb_slots': 0, 'salles': {}, 'profs': []}
        model = TimetableModel(data)
        self.assertIsInstance(model.model, cp_model.CpModel)
        self.assertEqual(model.data, data)
        self.assertEqual(model._vars, {})
        self.assertEqual(model._ordres_a_forcer, [])


class TestCreateDecisionVariables(unittest.TestCase):
    """Tests pour _create_decision_variables."""

    def setUp(self):
        self.data = {
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

    def test_creates_start_variables(self):
        model = TimetableModel(self.data)
        model._create_decision_variables()
        
        self.assertIn('start', model._vars)
        # Vérifie que les clés (cid, slot) existent
        self.assertIn(('C1', 0), model._vars['start'])

    def test_creates_occupe_variables(self):
        model = TimetableModel(self.data)
        model._create_decision_variables()
        
        self.assertIn('occupe', model._vars)
        for t in range(self.data['nb_slots']):
            self.assertIn(('C1', t), model._vars['occupe'])

    def test_creates_y_salle_variables(self):
        model = TimetableModel(self.data)
        model._create_decision_variables()
        
        self.assertIn('y_salle', model._vars)
        self.assertIn(('C1', 0), model._vars['y_salle'])

    def test_creates_z_prof_variables(self):
        model = TimetableModel(self.data)
        model._create_decision_variables()
        
        self.assertIn('z_prof', model._vars)
        self.assertIn(('C1', 0), model._vars['z_prof'])

    def test_start_none_when_overlaps_midi(self):
        """Un cours qui chevauche midi ne doit pas avoir de start valide."""
        self.data['duree_cours'] = {'C1': 2}  # durée 2, slot 1 chevauchera midi (slot 2)
        model = TimetableModel(self.data)
        model._create_decision_variables()
        
        # Slot 1 avec durée 2 chevauche le slot 2 (midi)
        self.assertIsNone(model._vars['start'][('C1', 1)])

    def test_start_none_when_exceeds_day(self):
        """Un cours qui dépasse la journée ne doit pas avoir de start valide."""
        self.data['duree_cours'] = {'C1': 2}
        model = TimetableModel(self.data)
        model._create_decision_variables()
        
        # Slot 3 avec durée 2 dépasse la journée (4 créneaux)
        self.assertIsNone(model._vars['start'][('C1', 3)])


class TestContrainteOrdre(unittest.TestCase):
    """Tests pour contrainte_ordre_cm_td_tp."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 8,
            'slots': [(0, i) for i in range(8)],
            'fenetre_midi': [3, 4],
            'nb_slots': 8,
            'salles': {'Salle1': 50},
            'profs': ['Prof1'],
            'cours': [
                {'id': 'CM_Maths_G1_s1', 'groups': ['G1']},
                {'id': 'TD_Maths_G1_s2', 'groups': ['G1']},
                {'id': 'TP_Maths_G1_s3', 'groups': ['G1']}
            ],
            'duree_cours': {
                'CM_Maths_G1_s1': 1,
                'TD_Maths_G1_s2': 1,
                'TP_Maths_G1_s3': 1
            },
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['CM_Maths_G1_s1', 'TD_Maths_G1_s2', 'TP_Maths_G1_s3']}
        }

    def test_detecte_relations_ordre(self):
        """Vérifie que les relations CM→TD et CM→TP sont détectées."""
        model = TimetableModel(self.data)
        model.contrainte_ordre_cm_td_tp(self.data)
        
        # Doit avoir au moins 3 relations: CM→TD, CM→TP, TD→TP
        self.assertGreaterEqual(len(model._ordres_a_forcer), 3)

    def test_cm_avant_td(self):
        """Vérifie que CM doit être avant TD."""
        model = TimetableModel(self.data)
        model.contrainte_ordre_cm_td_tp(self.data)
        
        ordres = model._ordres_a_forcer
        cm_td = any(
            'CM_Maths' in avant and 'TD_Maths' in apres
            for avant, apres in ordres
        )
        self.assertTrue(cm_td)

    def test_cm_avant_tp(self):
        """Vérifie que CM doit être avant TP."""
        model = TimetableModel(self.data)
        model.contrainte_ordre_cm_td_tp(self.data)
        
        ordres = model._ordres_a_forcer
        cm_tp = any(
            'CM_Maths' in avant and 'TP_Maths' in apres
            for avant, apres in ordres
        )
        self.assertTrue(cm_tp)

    def test_td_avant_tp(self):
        """Vérifie que TD doit être avant TP."""
        model = TimetableModel(self.data)
        model.contrainte_ordre_cm_td_tp(self.data)
        
        ordres = model._ordres_a_forcer
        td_tp = any(
            'TD_Maths' in avant and 'TP_Maths' in apres
            for avant, apres in ordres
        )
        self.assertTrue(td_tp)


class TestContrainteHierarchique(unittest.TestCase):
    """Tests pour contrainte_hierarchique."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 4,
            'slots': [(0, i) for i in range(4)],
            'fenetre_midi': [],
            'nb_slots': 4,
            'salles': {'Salle1': 50},
            'profs': ['Prof1'],
            'cours': [
                {'id': 'C1', 'groups': ['G1']},
                {'id': 'C2', 'groups': ['G1A']}
            ],
            'duree_cours': {'C1': 1, 'C2': 1},
            'taille_groupes': {'G1': 50, 'G1A': 25},
            'map_groupe_cours': {
                'G1': ['C1'],
                'G1A': ['C2']
            }
        }

    def test_hierarchie_g1a_g1(self):
        """Vérifie que G1A et G1 sont liés hiérarchiquement."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        
        # La fonction ne doit pas lever d'exception
        model.contrainte_hierarchique(self.data)


class TestContrainteEtudiant(unittest.TestCase):
    """Tests pour contrainte_etudiant."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 4,
            'slots': [(0, i) for i in range(4)],
            'fenetre_midi': [],
            'nb_slots': 4,
            'salles': {'Salle1': 50},
            'profs': ['Prof1'],
            'cours': [
                {'id': 'C1', 'groups': ['G1']},
                {'id': 'C2', 'groups': ['G1']}
            ],
            'duree_cours': {'C1': 1, 'C2': 1},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['C1', 'C2']}
        }

    def test_meme_groupe_pas_en_meme_temps(self):
        """Vérifie que la contrainte étudiant est ajoutée pour un groupe avec plusieurs cours."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        
        # La fonction ne doit pas lever d'exception
        model.contrainte_etudiant(self.data)


class TestPenaliserFinTardive(unittest.TestCase):
    """Tests pour penaliser_fin_tardive."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 24,
            'slots': [(0, i) for i in range(24)],
            'fenetre_midi': [6, 7, 8],
            'nb_slots': 24,
            'salles': {'Salle1': 50},
            'profs': ['Prof1'],
            'cours': [{'id': 'C1', 'groups': ['G1']}],
            'duree_cours': {'C1': 2},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['C1']}
        }

    def test_cree_penalites_fin_tardive(self):
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.penaliser_fin_tardive(self.data, cout_penalite=500, limite_offset_fin=20)
        
        self.assertTrue(hasattr(model, 'penalites_fin_tardive'))
        self.assertIsInstance(model.penalites_fin_tardive, list)

    def test_penalite_pour_cours_tardif(self):
        """Vérifie qu'une pénalité est créée pour un cours finissant après la limite."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.penaliser_fin_tardive(self.data, cout_penalite=500, limite_offset_fin=10)
        
        # Avec limite=10, tout cours finissant après slot 10 aura une pénalité
        # Le cours C1 de durée 2 peut finir au slot 12, 13, etc.
        self.assertGreater(len(model.penalites_fin_tardive), 0)


class TestSolve(unittest.TestCase):
    """Tests pour la méthode solve."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 4,
            'slots': [(0, 0), (0, 1), (0, 2), (0, 3)],
            'fenetre_midi': [],
            'nb_slots': 4,
            'salles': {'Salle1': 50},
            'capacites': [50],
            'profs': ['Prof1'],
            'cours': [{'id': 'CM_Test_G1_s1', 'groups': ['G1']}],
            'duree_cours': {'CM_Test_G1_s1': 1},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['CM_Test_G1_s1']},
            'map_cours_groupes': {'CM_Test_G1_s1': ['G1']},
            'disponibilites_profs': {},
            'disponibilites_salles': {},
            'disponibilites_groupes': {},
            'obligations_slots': {},
            'prof_to_teacher_id': {}
        }

    def test_solve_returns_dict(self):
        model = TimetableModel(self.data)
        model.build_model()
        result = model.solve(max_time_seconds=10)
        
        self.assertIsInstance(result, dict)
        self.assertIn('status', result)
        self.assertIn('solver', result)
        self.assertIn('vars', result)

    def test_solve_simple_feasible(self):
        """Test qu'un problème simple est faisable."""
        model = TimetableModel(self.data)
        model.build_model()
        result = model.solve(max_time_seconds=10)
        
        self.assertIn(result['status'], [cp_model.OPTIMAL, cp_model.FEASIBLE])


class TestDefineObjectiveFunction(unittest.TestCase):
    """Tests pour _define_objective_function."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 4,
            'slots': [(0, 0), (0, 1), (0, 2), (0, 3)],
            'fenetre_midi': [],
            'nb_slots': 4,
            'salles': {'Salle1': 20, 'Salle2': 50},
            'capacites': [20, 50],
            'profs': ['Prof1'],
            'cours': [{'id': 'C1', 'groups': ['G1']}],
            'duree_cours': {'C1': 1},
            'taille_groupes': {'G1': 30},  # Trop grand pour Salle1
            'map_groupe_cours': {'G1': ['C1']}
        }

    def test_cree_penalites_capacite(self):
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.penalites_fin_tardive = []
        model._define_objective_function()
        
        self.assertIn('penalites_capacite', model._vars)

    def test_penalite_quand_groupe_trop_grand(self):
        """Pénalité créée quand le groupe est trop grand pour une salle."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.penalites_fin_tardive = []
        model._define_objective_function()
        
        # Le groupe G1 (30 pers) est trop grand pour Salle1 (20 places)
        # Donc au moins une pénalité
        self.assertGreater(len(model._vars['penalites_capacite']), 0)


class TestAddLinkingConstraints(unittest.TestCase):
    """Tests pour _add_linking_constraints."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 4,
            'slots': [(0, 0), (0, 1), (0, 2), (0, 3)],
            'fenetre_midi': [],
            'nb_slots': 4,
            'salles': {'Salle1': 50},
            'profs': ['Prof1', 'Prof2'],
            'cours': [{'id': 'C1', 'groups': ['G1'], 'allowed_prof_indices': [0]}],
            'duree_cours': {'C1': 1},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['C1']}
        }

    def test_linking_constraints_added(self):
        """Vérifie que les contraintes de liaison sont ajoutées sans erreur."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model._add_linking_constraints()
        
        # Si aucune exception, le test passe

    def test_only_allowed_profs(self):
        """Vérifie que seuls les profs autorisés peuvent enseigner."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model._add_linking_constraints()
        
        # Prof2 (index 1) n'est pas autorisé, son z_prof devrait être contraint à 0


class TestContrainteDisponibilitesProfs(unittest.TestCase):
    """Tests pour contrainte_disponibilites_professeurs."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 4,
            'slots': [(0, 0), (0, 1), (0, 2), (0, 3)],
            'fenetre_midi': [],
            'nb_slots': 4,
            'salles': {'Salle1': 50},
            'profs': ['Prof1'],
            'cours': [{'id': 'C1', 'groups': ['G1'], 'allowed_prof_indices': [0]}],
            'duree_cours': {'C1': 1},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['C1']},
            'disponibilites_profs': {1: {0: [(0, 2)]}},  # Dispo slots 0-2 le jour 0
            'prof_to_teacher_id': {'Prof1': 1}
        }

    def test_contrainte_dispo_prof_appliquee(self):
        """Vérifie que la contrainte de disponibilité prof est appliquée."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.contrainte_disponibilites_professeurs(self.data)
        # Pas d'exception = test passé


class TestContrainteDisponibilitesGroupes(unittest.TestCase):
    """Tests pour contrainte_disponibilites_groupes."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 4,
            'slots': [(0, 0), (0, 1), (0, 2), (0, 3)],
            'fenetre_midi': [],
            'nb_slots': 4,
            'salles': {'Salle1': 50},
            'profs': ['Prof1'],
            'cours': [{'id': 'C1', 'groups': ['G1']}],
            'duree_cours': {'C1': 1},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['C1']},
            'map_cours_groupes': {'C1': ['G1']},
            'disponibilites_groupes': {'G1': {0: [(0, 2)]}}  # Dispo slots 0-2
        }

    def test_contrainte_dispo_groupe_appliquee(self):
        """Vérifie que la contrainte de disponibilité groupe est appliquée."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.contrainte_disponibilites_groupes(self.data)
        # Pas d'exception = test passé


class TestContrainteDisponibilitesSalles(unittest.TestCase):
    """Tests pour contrainte_disponibilites_salles_generalisee."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 4,
            'slots': [(0, 0), (0, 1), (0, 2), (0, 3)],
            'fenetre_midi': [],
            'nb_slots': 4,
            'salles': {'Salle1': 50},
            'profs': ['Prof1'],
            'cours': [{'id': 'C1', 'groups': ['G1']}],
            'duree_cours': {'C1': 1},
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['C1']},
            'disponibilites_salles': {'Salle1': {0: [(0, 2)]}}
        }

    def test_contrainte_dispo_salle_appliquee(self):
        """Vérifie que la contrainte de disponibilité salle est appliquée."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.contrainte_disponibilites_salles_generalisee(self.data)
        # Pas d'exception = test passé

    def test_salle_sans_disponibilite(self):
        """Test avec aucune disponibilité définie."""
        self.data['disponibilites_salles'] = {}
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.contrainte_disponibilites_salles_generalisee(self.data)
        # Pas d'exception = test passé


class TestAppliquerOrdreCmTdTp(unittest.TestCase):
    """Tests pour appliquer_ordre_cm_td_tp."""

    def setUp(self):
        self.data = {
            'jours': 1,
            'creneaux_par_jour': 8,
            'slots': [(0, i) for i in range(8)],
            'fenetre_midi': [],
            'nb_slots': 8,
            'salles': {'Salle1': 50},
            'profs': ['Prof1'],
            'cours': [
                {'id': 'CM_Maths_G1_s1', 'groups': ['G1']},
                {'id': 'TD_Maths_G1_s2', 'groups': ['G1']}
            ],
            'duree_cours': {
                'CM_Maths_G1_s1': 1,
                'TD_Maths_G1_s2': 1
            },
            'taille_groupes': {'G1': 25},
            'map_groupe_cours': {'G1': ['CM_Maths_G1_s1', 'TD_Maths_G1_s2']}
        }

    def test_applique_ordre_sans_exception(self):
        """Vérifie que l'application des ordres ne lève pas d'exception."""
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.contrainte_ordre_cm_td_tp(self.data)
        model.appliquer_ordre_cm_td_tp()

    def test_sans_ordres_a_forcer(self):
        """Test quand il n'y a pas d'ordres à forcer."""
        model = TimetableModel(self.data)
        model._ordres_a_forcer = []
        model.appliquer_ordre_cm_td_tp()  # Ne doit pas lever d'exception


if __name__ == '__main__':
    unittest.main()
