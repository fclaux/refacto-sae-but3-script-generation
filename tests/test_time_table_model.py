"""
Tests pour le module time_table_model.
Refactorisé pour éliminer la duplication de code.
"""
import unittest
from unittest.mock import MagicMock, patch
from ortools.sat.python import cp_model
from time_table_model import TimetableModel


def make_base_data(jours=1, creneaux=4, fenetre_midi=None, salles=None, profs=None):
    """Factory pour créer des données de base pour TimetableModel."""
    fenetre_midi = fenetre_midi if fenetre_midi is not None else []
    salles = salles or {'Salle1': 50}
    profs = profs or ['Prof1']
    return {
        'jours': jours,
        'creneaux_par_jour': creneaux,
        'slots': [(j, o) for j in range(jours) for o in range(creneaux)],
        'fenetre_midi': fenetre_midi,
        'nb_slots': jours * creneaux,
        'salles': salles,
        'profs': profs,
        'cours': [],
        'duree_cours': {},
        'taille_groupes': {},
        'map_groupe_cours': {}
    }


def add_course(data, cid, groups, duration=1, group_size=25, allowed_profs=None):
    """Helper pour ajouter un cours aux données."""
    course = {'id': cid, 'groups': groups}
    if allowed_profs is not None:
        course['allowed_prof_indices'] = allowed_profs
    data['cours'].append(course)
    data['duree_cours'][cid] = duration
    for g in groups:
        data['taille_groupes'][g] = group_size
        data['map_groupe_cours'].setdefault(g, []).append(cid)
    return data


def make_complete_data():
    """Factory pour des données complètes nécessaires à build_model."""
    data = make_base_data()
    add_course(data, 'CM_Test_G1_s1', ['G1'], duration=1, group_size=25)
    data.update({
        'capacites': [50],
        'map_cours_groupes': {'CM_Test_G1_s1': ['G1']},
        'disponibilites_profs': {},
        'disponibilites_salles': {},
        'disponibilites_groupes': {},
        'obligations_slots': {},
        'prof_to_teacher_id': {}
    })
    return data


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
        self.data = make_base_data(fenetre_midi=[2])
        add_course(self.data, 'C1', ['G1'])

    def _create_model_with_vars(self, data=None):
        """Helper pour créer un modèle avec variables."""
        model = TimetableModel(data or self.data)
        model._create_decision_variables()
        return model

    def test_creates_all_variable_types(self):
        model = self._create_model_with_vars()
        for var_type in ['start', 'occupe', 'y_salle', 'z_prof']:
            self.assertIn(var_type, model._vars)

    def test_creates_start_variables(self):
        model = self._create_model_with_vars()
        self.assertIn(('C1', 0), model._vars['start'])

    def test_creates_occupe_variables(self):
        model = self._create_model_with_vars()
        for t in range(self.data['nb_slots']):
            self.assertIn(('C1', t), model._vars['occupe'])

    def test_start_none_when_overlaps_midi(self):
        """Un cours qui chevauche midi ne doit pas avoir de start valide."""
        self.data['duree_cours'] = {'C1': 2}
        model = self._create_model_with_vars()
        self.assertIsNone(model._vars['start'][('C1', 1)])

    def test_start_none_when_exceeds_day(self):
        """Un cours qui dépasse la journée ne doit pas avoir de start valide."""
        self.data['duree_cours'] = {'C1': 2}
        model = self._create_model_with_vars()
        self.assertIsNone(model._vars['start'][('C1', 3)])


class TestContrainteOrdre(unittest.TestCase):
    """Tests pour contrainte_ordre_cm_td_tp."""

    def setUp(self):
        self.data = make_base_data(creneaux=8, fenetre_midi=[3, 4])
        for cid in ['CM_Maths_G1_s1', 'TD_Maths_G1_s2', 'TP_Maths_G1_s3']:
            add_course(self.data, cid, ['G1'])

    def _get_ordres(self):
        model = TimetableModel(self.data)
        model.contrainte_ordre_cm_td_tp(self.data)
        return model._ordres_a_forcer

    def test_detecte_relations_ordre(self):
        """Vérifie que les relations CM→TD, CM→TP, TD→TP sont détectées."""
        self.assertGreaterEqual(len(self._get_ordres()), 3)

    def test_cm_avant_td(self):
        ordres = self._get_ordres()
        self.assertTrue(any('CM_Maths' in a and 'TD_Maths' in b for a, b in ordres))

    def test_cm_avant_tp(self):
        ordres = self._get_ordres()
        self.assertTrue(any('CM_Maths' in a and 'TP_Maths' in b for a, b in ordres))

    def test_td_avant_tp(self):
        ordres = self._get_ordres()
        self.assertTrue(any('TD_Maths' in a and 'TP_Maths' in b for a, b in ordres))


class TestContrainteHierarchique(unittest.TestCase):
    """Tests pour contrainte_hierarchique."""

    def test_hierarchie_g1a_g1(self):
        data = make_base_data()
        add_course(data, 'C1', ['G1'], group_size=50)
        add_course(data, 'C2', ['G1A'], group_size=25)
        
        model = TimetableModel(data)
        model._create_decision_variables()
        model.contrainte_hierarchique(data)  # Ne doit pas lever d'exception


class TestContrainteEtudiant(unittest.TestCase):
    """Tests pour contrainte_etudiant."""

    def test_meme_groupe_pas_en_meme_temps(self):
        data = make_base_data()
        add_course(data, 'C1', ['G1'])
        add_course(data, 'C2', ['G1'])
        
        model = TimetableModel(data)
        model._create_decision_variables()
        model.contrainte_etudiant(data)  # Ne doit pas lever d'exception


class TestPenaliserFinTardive(unittest.TestCase):
    """Tests pour penaliser_fin_tardive."""

    def setUp(self):
        self.data = make_base_data(creneaux=24, fenetre_midi=[6, 7, 8])
        add_course(self.data, 'C1', ['G1'], duration=2)

    def test_cree_penalites_fin_tardive(self):
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.penaliser_fin_tardive(self.data, cout_penalite=500, limite_offset_fin=20)
        
        self.assertTrue(hasattr(model, 'penalites_fin_tardive'))
        self.assertIsInstance(model.penalites_fin_tardive, list)

    def test_penalite_pour_cours_tardif(self):
        model = TimetableModel(self.data)
        model._create_decision_variables()
        model.penaliser_fin_tardive(self.data, cout_penalite=500, limite_offset_fin=10)
        self.assertGreater(len(model.penalites_fin_tardive), 0)


class TestSolve(unittest.TestCase):
    """Tests pour la méthode solve."""

    def setUp(self):
        self.data = make_complete_data()

    def test_solve_returns_dict(self):
        model = TimetableModel(self.data)
        model.build_model()
        result = model.solve(max_time_seconds=10)
        
        self.assertIsInstance(result, dict)
        for key in ['status', 'solver', 'vars']:
            self.assertIn(key, result)

    def test_solve_simple_feasible(self):
        model = TimetableModel(self.data)
        model.build_model()
        result = model.solve(max_time_seconds=10)
        self.assertIn(result['status'], [cp_model.OPTIMAL, cp_model.FEASIBLE])


class TestDefineObjectiveFunction(unittest.TestCase):
    """Tests pour _define_objective_function."""

    def test_cree_penalites_capacite(self):
        data = make_base_data(salles={'Salle1': 20, 'Salle2': 50})
        data['capacites'] = [20, 50]
        add_course(data, 'C1', ['G1'], group_size=30)  # Trop grand pour Salle1
        
        model = TimetableModel(data)
        model._create_decision_variables()
        model.penalites_fin_tardive = []
        model._define_objective_function()
        
        self.assertIn('penalites_capacite', model._vars)
        self.assertGreater(len(model._vars['penalites_capacite']), 0)


class TestAddLinkingConstraints(unittest.TestCase):
    """Tests pour _add_linking_constraints."""

    def test_linking_constraints_added(self):
        data = make_base_data(profs=['Prof1', 'Prof2'])
        add_course(data, 'C1', ['G1'], allowed_profs=[0])
        
        model = TimetableModel(data)
        model._create_decision_variables()
        model._add_linking_constraints()  # Ne doit pas lever d'exception


class TestContrainteDisponibilites(unittest.TestCase):
    """Tests pour les contraintes de disponibilités."""

    def _make_model_with_vars(self, data):
        model = TimetableModel(data)
        model._create_decision_variables()
        return model

    def test_contrainte_dispo_prof(self):
        data = make_base_data()
        add_course(data, 'C1', ['G1'], allowed_profs=[0])
        data['disponibilites_profs'] = {1: {0: [(0, 2)]}}
        data['prof_to_teacher_id'] = {'Prof1': 1}
        
        model = self._make_model_with_vars(data)
        model.contrainte_disponibilites_professeurs(data)

    def test_contrainte_dispo_groupe(self):
        data = make_base_data()
        add_course(data, 'C1', ['G1'])
        data['map_cours_groupes'] = {'C1': ['G1']}
        data['disponibilites_groupes'] = {'G1': {0: [(0, 2)]}}
        
        model = self._make_model_with_vars(data)
        model.contrainte_disponibilites_groupes(data)

    def test_contrainte_dispo_salle(self):
        data = make_base_data()
        add_course(data, 'C1', ['G1'])
        data['disponibilites_salles'] = {'Salle1': {0: [(0, 2)]}}
        
        model = self._make_model_with_vars(data)
        model.contrainte_disponibilites_salles_generalisee(data)

    def test_salle_sans_disponibilite(self):
        data = make_base_data()
        add_course(data, 'C1', ['G1'])
        data['disponibilites_salles'] = {}
        
        model = self._make_model_with_vars(data)
        model.contrainte_disponibilites_salles_generalisee(data)


class TestAppliquerOrdreCmTdTp(unittest.TestCase):
    """Tests pour appliquer_ordre_cm_td_tp."""

    def test_applique_ordre_sans_exception(self):
        data = make_base_data(creneaux=8)
        add_course(data, 'CM_Maths_G1_s1', ['G1'])
        add_course(data, 'TD_Maths_G1_s2', ['G1'])
        
        model = TimetableModel(data)
        model._create_decision_variables()
        model.contrainte_ordre_cm_td_tp(data)
        model.appliquer_ordre_cm_td_tp()

    def test_sans_ordres_a_forcer(self):
        data = make_base_data()
        model = TimetableModel(data)
        model._ordres_a_forcer = []
        model.appliquer_ordre_cm_td_tp()  # Ne doit pas lever d'exception


if __name__ == '__main__':
    unittest.main()
