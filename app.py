"""
Module principal de génération d'emploi du temps.
Gère le diagnostic d'infaisabilité et l'optimisation.
"""
import os
import sys

# --- DÉBUT DU BLOC DE CORRECTION DE CHEMIN ---
# Ce bloc s'exécute UNIQUEMENT lorsque l'application est "gelée" (PyInstaller)
if getattr(sys, 'frozen', False):
    bundle_dir = os.path.dirname(sys.executable)

    # Chemins basés sur la structure PyInstaller (dist/test/_internal/...)
    ortools_dll_path_1 = os.path.join(bundle_dir, '_internal', 'ortools', '.libs')
    ortools_dll_path_2 = os.path.join(bundle_dir, '_internal', 'ortools')

    # Ajout des chemins existants à la variable d'environnement PATH
    paths_to_add = [p for p in [ortools_dll_path_1, ortools_dll_path_2] if os.path.exists(p)]

    for path_to_add in paths_to_add:
        # Ajoute le nouveau chemin au début du PATH pour la recherche de DLLs
        os.environ['PATH'] = path_to_add + os.pathsep + os.environ['PATH']
        print(f"INFO: PATH ajusté pour OR-Tools: {path_to_add}")
# Assurez-vous que ces modules sont accessibles et fonctionnels
import argparse
import itertools
import time
from pathlib import Path

from ortools.sat.python import cp_model

import diagnose
from data_provider_id import DataProviderID
from solution_visualizer import SolutionVisualizer
from time_table_model import TimetableModel
from logger_config import get_logger

# Configuration du logger pour ce module
logger = get_logger(__name__)

# Ajout du chemin OR-Tools si nécessaire
ortools_path = Path(r"C:\Users\rouff\AppData\Local\Programs\Python\Python313\Lib\site-packages\ortools")
if ortools_path.exists():
    path_to_add = str(ortools_path.parent)
    if path_to_add not in sys.path:
        sys.path.insert(0, path_to_add)
        logger.info(f"PATH ajusté pour OR-Tools: {path_to_add}")


def test_combination(model_class, data, disabled_blocks, timeout=60):
    """Teste si en désactivant une liste de blocs, le problème devient faisable"""
    logger.info("="*70)
    if len(disabled_blocks) == 1:
        logger.info(f"TEST UNIQUE → Désactivation : {disabled_blocks[0]}")
    else:
        logger.info(f"TEST COMBINAISON → Désactivation : {' + '.join(disabled_blocks)}")

    start = time.perf_counter()
    scheduler = model_class(data)
    scheduler.build_model(disable_blocks=disabled_blocks)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = False

    status = solver.Solve(scheduler.model)

    elapsed = time.perf_counter() - start

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        logger.info(f"SOLUTION TROUVÉE en {elapsed:.2f}s !")
        logger.info(f"LES CONTRAINTES BLOQUANTES SONT DANS : {', '.join(disabled_blocks)}")
        return True
    else:
        logger.warning(f"Infaisable ({solver.StatusName(status)}) après {elapsed:.2f}s")
        return False


def diagnostic_automatique(model_class, data, timeout_per_test=60):
    blocks = [
        "profs",
        "salles",
        "etudiant",
        "hierarchies",
        "ordre_cm_td_tp",
        "prof disponibles",
        "salles dispo"
    ]

    logger.info("🔍 DIAGNOSTIC AUTOMATIQUE DE L'INFAISABILITÉ")
    logger.info("="*70)

    # === ÉTAPE 1 : Test un par un ===
    logger.info("\n1. Test des blocs un par un...")
    for block in blocks:
        if test_combination(model_class, data, [block], timeout_per_test):
            logger.info(f"\n✅ UN SEUL BLOC SUFFIT → '{block}' est la source du problème.")
            return

    logger.info("\n⚠️ Aucun bloc seul ne résout le problème.")

    # === ÉTAPE 2 : Test des paires ===
    logger.info("\n2. Test des combinaisons de 2 blocs...")
    for combo in itertools.combinations(blocks, 2):
        if test_combination(model_class, data, list(combo), timeout_per_test):
            logger.info(f"\n✅ COMBINAISON GAGNANTE → Il fallait désactiver : {combo[0]} + {combo[1]}")
            return

    logger.info("\n⚠️ Aucune paire ne suffit.")

    # === ÉTAPE 3 : Test des triplets ===
    logger.info("\n3. Test des combinaisons de 3 blocs...")
    for combo in itertools.combinations(blocks, 3):
        if test_combination(model_class, data, list(combo), timeout_per_test):
            logger.info(f"\n✅ COMBINAISON GAGNANTE → Il fallait désactiver : {', '.join(combo)}")
            return

    logger.warning("\n❌ Même en désactivant 3 blocs, toujours infaisable.")
    logger.warning("Possibles causes restantes :")
    logger.warning("   • Données incohérentes (ex: cours sans prof possible, salle trop petite obligatoire)")
    logger.warning("   • Problème dans les variables de décision ou les contraintes de base")
    logger.warning("   • Besoin de désactiver plus de 3 blocs (rare) ou assouplir les contraintes souples")
    logger.info("\n💡 Prochaine étape recommandée : utiliser le module 'diagnose.py' avec explain_infeasibility()")


# ==============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    start_time = time.perf_counter()

    parser = argparse.ArgumentParser(description="Exemple d'entrée en ligne de commande")
    parser.add_argument("--id_semaine", type=int, required=True, help="Un entier en entrée correspondant à la semaine à générer")
    argvs = parser.parse_args()

    print("Vous avez fourni :", argvs.id_semaine)
    logger.info(f"Vous avez fourni : {argvs.id_semaine}")

    # Utilise la configuration depuis .env via db_utils
    DataProviderInsert = DataProviderID()
    model_data = DataProviderInsert.load_and_prepare_data(argvs.id_semaine)
    scheduler = TimetableModel(model_data)
    scheduler.build_model()

    # Exemple d'appel:
    probs = diagnose.diagnose_feasibility(model_data)
    solution = scheduler.solve(max_time_seconds=300)
    #print("solution",solution)

    if solution and solution['vars']:
        visualizer = SolutionVisualizer(solution, model_data)
        visualizer.display(DataProviderInsert,argvs.id_semaine)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        logger.info(f"Programme exécuté en : {execution_time: .5f} secondes")
    else:
        logger.warning("\nÉchec de la résolution. Le modèle reste infaisable même avec des contraintes assouplies.")
        logger.warning(
            "Causes possibles : Surcharge totale des ressources (pas assez de salles/profs pour le nombre de cours) ou une autre contrainte dure est trop restrictive (ex: pause midi).")
        #diagnostic_automatique(TimetableModelId, model_data, timeout_per_test=90)

        total_time = time.perf_counter() - start_time
        logger.info(f"\nDiagnostic terminé en {total_time:.1f} secondes.")
