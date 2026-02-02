"""
Classification des groupes d'étudiants.
Respecte le principe Open/Closed (SOLID) - extensible par configuration.
"""
from typing import Optional, List, Final

# Configuration centralisée des groupes
GROUPE_TO_YEAR: Final[dict] = {
    "BUT1": "B1", "G1": "B1", "G2": "B1", "G3": "B1",
    "G1A": "B1", "G1B": "B1", "G2A": "B1", "G2B": "B1", "G3A": "B1", "G3B": "B1",
    "BUT2": "B2", "G4": "B2", "G5": "B2", "G6": "B2",
    "G4A": "B2", "G4B": "B2", "G5A": "B2", "G5B": "B2", "G6A": "B2", "G6B": "B2",
}


class GroupClassifier:
    """Classifie et convertit les groupes d'étudiants."""

    def __init__(self, group_mapping: dict = None):
        """
        Args:
            group_mapping: Mapping personnalisé groupe -> année (optionnel)
        """
        self._group_mapping = group_mapping or GROUPE_TO_YEAR

    def get_year_level(self, group: str) -> str:
        """
        Retourne le niveau d'année pour un groupe donné.

        Args:
            group: Identifiant du groupe (ex: "G1", "G1A", "BUT1")

        Returns:
            Niveau d'année ("B1", "B2", "B3")
        """
        return self._group_mapping.get(group, "B3")

    def group_to_indices(self, group: str) -> Optional[List]:
        """
        Convertit un groupe en indices pour l'affichage.

        Args:
            group: Identifiant du groupe

        Returns:
            Liste d'indices [base] ou [base, suffix] ou None pour BUT
        """
        if group.startswith("BUT"):
            return None

        try:
            base_index = (int(group[1]) - 1) % 3

            if len(group) > 2:
                suffix = group[2:]
                return [base_index, suffix]

            return [base_index]
        except (IndexError, ValueError):
            return None

