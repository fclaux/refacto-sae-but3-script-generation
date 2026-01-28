"""
Module utilitaire pour la gestion des connexions à la base de données.
Centralise la configuration et la création des connexions.
"""
import os
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Charger les variables d'environnement depuis .env
load_dotenv()


def get_db_config() -> Dict[str, Any]:
    """
    Récupère la configuration de la base de données depuis les variables d'environnement.
    
    Returns:
        Dict[str, Any]: Dictionnaire contenant la configuration de la BDD.
    """
    return {
        'host': os.getenv('DB_HOST', '127.0.0.1'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'database': os.getenv('DB_DATABASE', 'provisional_calendar'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'secret'),
    }


def get_connection_url(db_config: Optional[Dict[str, Any]] = None) -> str:
    """
    Construit l'URL de connexion SQLAlchemy à partir de la configuration.
    
    Args:
        db_config: Configuration de la BDD. Si None, utilise les variables d'environnement.
    
    Returns:
        str: URL de connexion au format SQLAlchemy.
    """
    if db_config is None:
        db_config = get_db_config()
    
    return (
        f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )


def create_db_engine(db_config: Optional[Dict[str, Any]] = None) -> Engine:
    """
    Crée et retourne un engine SQLAlchemy.
    
    Args:
        db_config: Configuration de la BDD. Si None, utilise les variables d'environnement.
    
    Returns:
        Engine: Instance SQLAlchemy Engine connectée à la BDD.
    """
    url = get_connection_url(db_config)
    return create_engine(url)


# Singleton pour l'engine global (optionnel, pour réutilisation)
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """
    Retourne un engine singleton. Crée l'engine à la première utilisation.
    
    Returns:
        Engine: Instance SQLAlchemy Engine partagée.
    """
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def reset_engine() -> None:
    """
    Réinitialise l'engine singleton. Utile pour les tests ou le rechargement de config.
    """
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
