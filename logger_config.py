"""
Module de configuration centralisée pour le logging de l'application.
Remplace les print() pour éviter les failles de sécurité et améliorer la traçabilité.
"""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


# Dossier pour les logs
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configure et retourne un logger avec handlers console et fichier.

    Args:
        name: Nom du logger (généralement __name__ du module)
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)

    # Évite de dupliquer les handlers si le logger existe déjà
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Format détaillé pour les logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler Console (affiche INFO et supérieur)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler Fichier - Log général avec rotation
    file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "application.log",
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler Fichier - Erreurs uniquement
    error_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "errors.log",
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Récupère ou crée un logger pour le module spécifié.

    Usage:
        from logger_config import get_logger
        logger = get_logger(__name__)
        logger.info("Message d'information")
        logger.error("Message d'erreur")

    Args:
        name: Nom du module (utiliser __name__)

    Returns:
        Logger configuré
    """
    return setup_logger(name)


# Logger par défaut pour l'application
app_logger = setup_logger('application')

