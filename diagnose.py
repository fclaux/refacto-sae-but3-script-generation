from logger_config import get_logger
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Any

# Configuration du logger pour ce module
logger = get_logger(__name__)


@dataclass
class ProblemesFaisabilite:
    """Classe regroupant les différents problèmes de faisabilité détectés."""
    cours_sans_creneau_valide: List[Tuple[str, int]] = field(default_factory=list)
    cours_sans_salle_adequate: List[Tuple[str, str, int]] = field(default_factory=list)
    groupes_surcharges: List[Tuple[str, int, int]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List]:
        """Conversion en dictionnaire pour rétrocompatibilité."""
        return {
            'no_valid_start': self.cours_sans_creneau_valide,
            'no_room': self.cours_sans_salle_adequate,
            'group_overbooked': self.groupes_surcharges
        }


class DiagnosticEmploiDuTemps:
    """Classe pour diagnostiquer la faisabilité d'un emploi du temps."""

    def __init__(self, donnees_planning: Dict[str, Any]):
        """
        Initialise le diagnostic avec les données du planning.
        
        Args:
            donnees_planning: Dictionnaire contenant toutes les données du planning
        """
        self.nombre_jours = donnees_planning['jours']
        self.creneaux_par_jour = donnees_planning['creneaux_par_jour']
        self.liste_creneaux = donnees_planning['slots']  # Liste de (jour, decalage_horaire)
        self.pause_midi = set(donnees_planning['fenetre_midi'])
        self.nombre_total_creneaux = donnees_planning['nb_slots']
        self.salles_avec_capacite = list(donnees_planning['salles'].items())
        self.liste_cours = donnees_planning['cours']
        self.duree_par_cours = donnees_planning['duree_cours']
        self.taille_par_groupe = donnees_planning['taille_groupes']
        self.cours_par_groupe = donnees_planning['map_groupe_cours']

        # Calcul des créneaux utilisables (hors pause midi)
        self.decalages_utilisables = [
            decalage for decalage in range(self.creneaux_par_jour)
            if decalage not in self.pause_midi
        ]
        self.creneaux_utilisables_par_jour = len(self.decalages_utilisables)
        self.total_creneaux_utilisables = self.creneaux_utilisables_par_jour * self.nombre_jours

    def _verifier_creneaux_depart_valides(self, problemes: ProblemesFaisabilite) -> None:
        """Vérifie que chaque cours a au moins un créneau de départ valide."""
        for cours in self.liste_cours:
            id_cours = cours['id']
            duree_cours = self.duree_par_cours[id_cours]
            creneaux_depart_valides = []

            for index_creneau, (jour, decalage_horaire) in enumerate(self.liste_creneaux):
                # Le cours doit tenir dans la journée (pas de débordement)
                if decalage_horaire + duree_cours > self.creneaux_par_jour:
                    continue

                # Le cours ne doit pas chevaucher la pause midi
                chevauche_pause_midi = any(
                    (decalage_horaire + increment) in self.pause_midi
                    for increment in range(duree_cours)
                )
                if chevauche_pause_midi:
                    continue

                creneaux_depart_valides.append((index_creneau, jour, decalage_horaire))

            if not creneaux_depart_valides:
                problemes.cours_sans_creneau_valide.append((id_cours, duree_cours))

    def _verifier_capacite_salles(self, problemes: ProblemesFaisabilite) -> None:
        """Vérifie que chaque cours dispose d'au moins une salle avec capacité suffisante."""
        for cours in self.liste_cours:
            id_cours = cours['id']
            nom_groupe = cours['groups'][0]
            effectif_groupe = self.taille_par_groupe.get(nom_groupe, 0)

            salle_disponible = any(
                capacite_salle >= effectif_groupe
                for _, capacite_salle in self.salles_avec_capacite
            )

            if not salle_disponible:
                problemes.cours_sans_salle_adequate.append((id_cours, nom_groupe, effectif_groupe))

    def _verifier_charge_groupes(self, problemes: ProblemesFaisabilite) -> None:
        """Vérifie que chaque groupe n'a pas plus de cours que de créneaux disponibles."""
        for nom_groupe, liste_id_cours in self.cours_par_groupe.items():
            creneaux_requis = sum(
                self.duree_par_cours[id_cours]
                for id_cours in liste_id_cours
            )

            if creneaux_requis > self.total_creneaux_utilisables:
                problemes.groupes_surcharges.append(
                    (nom_groupe, creneaux_requis, self.total_creneaux_utilisables)
                )

    def _afficher_rapport(self, problemes: ProblemesFaisabilite) -> None:
        """Affiche le rapport de diagnostic dans les logs."""
        logger.info("=== Diagnostic faisabilité (statique) ===")
        logger.info(
            f"Jours: {self.nombre_jours}, "
            f"creneaux_par_jour: {self.creneaux_par_jour}, "
            f"slots total: {self.nombre_total_creneaux}"
        )
        logger.info(
            f"Slots utilisables par jour (hors midi): {self.creneaux_utilisables_par_jour}, "
            f"total utilisables: {self.total_creneaux_utilisables}"
        )

        if problemes.cours_sans_creneau_valide:
            logger.info("Cours sans aucun start valide (durée incompatible ou traversée midi):")
            for id_cours, duree in problemes.cours_sans_creneau_valide:
                logger.info(f" - {id_cours}: durée {duree} slots")
        else:
            logger.info("OK: tous les cours ont au moins un start valide.")

        if problemes.cours_sans_salle_adequate:
            logger.info("\nCours sans salle suffisante (capacité):")
            for id_cours, nom_groupe, effectif in problemes.cours_sans_salle_adequate:
                logger.info(f" - {id_cours}: groupe {nom_groupe} taille {effectif}")
        else:
            logger.info("OK: toutes les classes ont au moins une salle de capacité suffisante.")

        if problemes.groupes_surcharges:
            logger.info("\nGroupes demandant plus de slots utilisables que disponibles (impossible globalement):")
            for nom_groupe, besoin, disponible in problemes.groupes_surcharges:
                logger.info(f" - {nom_groupe}: besoin {besoin} slots, mais seulement {disponible} utilisables")
        else:
            logger.info(
                "OK: aucun groupe n'exige plus de slots utilisables que disponibles "
                "(check global nécessaire mais non suffisant)."
            )

        logger.info("\nSi tout est OK ci-dessus mais INFEASIBLE persiste, vérifier :")
        logger.info("- contrainte de salles disponibles simultanément (nombre de grandes salles pour BUT3)")
        logger.info("- contraintes de profs (s'il y a des restrictions implicites)")
        logger.info(
            "- intégrité des linking constraints (start -> occupe) : "
            "assure-toi qu'elles correspondent exactement aux indices de slots"
        )

    def executer_diagnostic(self) -> Dict[str, List]:
        """
        Exécute le diagnostic complet de faisabilité.
        
        Returns:
            Dictionnaire des problèmes détectés (pour rétrocompatibilité)
        """
        problemes = ProblemesFaisabilite()

        self._verifier_creneaux_depart_valides(problemes)
        self._verifier_capacite_salles(problemes)
        self._verifier_charge_groupes(problemes)
        self._afficher_rapport(problemes)

        return problemes.to_dict()


def diagnose_feasibility(donnees_planning: Dict[str, Any]) -> Dict[str, List]:
    """
    Point d'entrée pour le diagnostic de faisabilité (rétrocompatibilité).
    
    Args:
        donnees_planning: Dictionnaire contenant toutes les données du planning
        
    Returns:
        Dictionnaire des problèmes détectés
    """
    diagnostic = DiagnosticEmploiDuTemps(donnees_planning)
    return diagnostic.executer_diagnostic()