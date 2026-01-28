import unittest
from unittest.mock import patch, MagicMock
import os


class TestGetDbConfig(unittest.TestCase):
    """Tests pour la fonction get_db_config."""

    @patch.dict(os.environ, {
        'DB_HOST': 'testhost',
        'DB_PORT': '5432',
        'DB_DATABASE': 'testdb',
        'DB_USER': 'testuser',
        'DB_PASSWORD': 'testpass'
    })
    def test_get_db_config_from_env(self):
        """get_db_config récupère les valeurs depuis les variables d'environnement."""
        from db_utils import get_db_config
        
        config = get_db_config()
        
        self.assertEqual(config['host'], 'testhost')
        self.assertEqual(config['port'], 5432)
        self.assertEqual(config['database'], 'testdb')
        self.assertEqual(config['user'], 'testuser')
        self.assertEqual(config['password'], 'testpass')

    @patch.dict(os.environ, {}, clear=True)
    def test_get_db_config_defaults(self):
        """get_db_config utilise les valeurs par défaut si env non défini."""
        import importlib
        import db_utils
        importlib.reload(db_utils)
        
        config = db_utils.get_db_config()
        
        self.assertEqual(config['host'], '127.0.0.1')
        self.assertEqual(config['port'], 3306)
        self.assertEqual(config['database'], 'provisional_calendar')
        self.assertEqual(config['user'], 'root')
        self.assertEqual(config['password'], 'secret')

    def test_get_db_config_returns_dict(self):
        """get_db_config retourne un dictionnaire."""
        from db_utils import get_db_config
        
        config = get_db_config()
        
        self.assertIsInstance(config, dict)

    def test_get_db_config_has_all_required_keys(self):
        """get_db_config retourne toutes les clés requises."""
        from db_utils import get_db_config
        
        config = get_db_config()
        required_keys = ['host', 'port', 'database', 'user', 'password']
        
        for key in required_keys:
            self.assertIn(key, config)

    def test_get_db_config_port_is_integer(self):
        """get_db_config retourne le port en tant qu'entier."""
        from db_utils import get_db_config
        
        config = get_db_config()
        
        self.assertIsInstance(config['port'], int)

    @patch.dict(os.environ, {'DB_PORT': '5433'})
    def test_get_db_config_converts_port_string_to_int(self):
        """get_db_config convertit le port string en int."""
        from db_utils import get_db_config
        
        config = get_db_config()
        
        self.assertEqual(config['port'], 5433)
        self.assertIsInstance(config['port'], int)

    @patch.dict(os.environ, {
        'DB_HOST': 'partial_host'
    })
    def test_get_db_config_partial_env(self):
        """get_db_config gère les variables partiellement définies."""
        from db_utils import get_db_config
        
        config = get_db_config()
        
        self.assertEqual(config['host'], 'partial_host')
        # Les autres doivent avoir leurs valeurs par défaut ou celles du .env


class TestGetConnectionUrl(unittest.TestCase):
    """Tests pour la fonction get_connection_url."""

    def test_get_connection_url_with_config(self):
        """get_connection_url construit l'URL correctement avec une config."""
        from db_utils import get_connection_url
        
        config = {
            'host': 'myhost',
            'port': 3307,
            'database': 'mydb',
            'user': 'myuser',
            'password': 'mypass'
        }
        
        url = get_connection_url(config)
        
        self.assertEqual(url, 'mysql+mysqlconnector://myuser:mypass@myhost:3307/mydb')

    @patch('db_utils.get_db_config')
    def test_get_connection_url_without_config(self, mock_get_config):
        """get_connection_url utilise get_db_config si aucune config fournie."""
        from db_utils import get_connection_url
        
        mock_get_config.return_value = {
            'host': 'defaulthost',
            'port': 3306,
            'database': 'defaultdb',
            'user': 'defaultuser',
            'password': 'defaultpass'
        }
        
        url = get_connection_url()
        
        mock_get_config.assert_called_once()
        self.assertIn('defaulthost', url)
        self.assertIn('defaultdb', url)

    def test_get_connection_url_format(self):
        """get_connection_url retourne une URL au format SQLAlchemy valide."""
        from db_utils import get_connection_url
        
        config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'testdb',
            'user': 'user',
            'password': 'pass'
        }
        
        url = get_connection_url(config)
        
        self.assertTrue(url.startswith('mysql+mysqlconnector://'))
        self.assertIn('@', url)
        self.assertIn(':', url)

    def test_get_connection_url_with_special_characters_in_password(self):
        """get_connection_url gère les mots de passe avec caractères spéciaux."""
        from db_utils import get_connection_url
        
        config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'testdb',
            'user': 'user',
            'password': 'p@ss#word!'
        }
        
        url = get_connection_url(config)
        
        self.assertIn('p@ss#word!', url)

    def test_get_connection_url_returns_string(self):
        """get_connection_url retourne une chaîne de caractères."""
        from db_utils import get_connection_url
        
        config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'db',
            'user': 'u',
            'password': 'p'
        }
        
        url = get_connection_url(config)
        
        self.assertIsInstance(url, str)

    def test_get_connection_url_includes_all_config_values(self):
        """get_connection_url inclut toutes les valeurs de configuration."""
        from db_utils import get_connection_url
        
        config = {
            'host': 'unique_host_123',
            'port': 9999,
            'database': 'unique_db_456',
            'user': 'unique_user_789',
            'password': 'unique_pass_000'
        }
        
        url = get_connection_url(config)
        
        self.assertIn('unique_host_123', url)
        self.assertIn('9999', url)
        self.assertIn('unique_db_456', url)
        self.assertIn('unique_user_789', url)
        self.assertIn('unique_pass_000', url)


class TestCreateDbEngine(unittest.TestCase):
    """Tests pour la fonction create_db_engine."""

    @patch('db_utils.create_engine')
    def test_create_db_engine_with_config(self, mock_create_engine):
        """create_db_engine crée un engine avec la config fournie."""
        from db_utils import create_db_engine
        
        config = {
            'host': 'testhost',
            'port': 3306,
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }
        
        create_db_engine(config)
        
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0][0]
        self.assertIn('testhost', call_args)
        self.assertIn('testdb', call_args)

    @patch('db_utils.create_engine')
    @patch('db_utils.get_db_config')
    def test_create_db_engine_without_config(self, mock_get_config, mock_create_engine):
        """create_db_engine utilise get_db_config si aucune config fournie."""
        from db_utils import create_db_engine
        
        mock_get_config.return_value = {
            'host': 'envhost',
            'port': 3306,
            'database': 'envdb',
            'user': 'envuser',
            'password': 'envpass'
        }
        
        create_db_engine()
        
        mock_get_config.assert_called_once()
        mock_create_engine.assert_called_once()

    @patch('db_utils.create_engine')
    def test_create_db_engine_returns_engine(self, mock_create_engine):
        """create_db_engine retourne l'engine créé."""
        from db_utils import create_db_engine
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        config = {
            'host': 'h', 'port': 3306, 'database': 'd',
            'user': 'u', 'password': 'p'
        }
        
        result = create_db_engine(config)
        
        self.assertIs(result, mock_engine)

    @patch('db_utils.create_engine')
    def test_create_db_engine_passes_correct_url(self, mock_create_engine):
        """create_db_engine passe l'URL correcte à create_engine."""
        from db_utils import create_db_engine
        
        config = {
            'host': 'myhost',
            'port': 3307,
            'database': 'mydb',
            'user': 'myuser',
            'password': 'mypass'
        }
        
        create_db_engine(config)
        
        expected_url = 'mysql+mysqlconnector://myuser:mypass@myhost:3307/mydb'
        mock_create_engine.assert_called_once_with(expected_url)

    @patch('db_utils.create_engine')
    def test_create_db_engine_multiple_calls_create_different_engines(self, mock_create_engine):
        """Chaque appel à create_db_engine crée un nouvel engine."""
        from db_utils import create_db_engine
        
        mock_engine1 = MagicMock()
        mock_engine2 = MagicMock()
        mock_create_engine.side_effect = [mock_engine1, mock_engine2]
        
        config = {
            'host': 'h', 'port': 3306, 'database': 'd',
            'user': 'u', 'password': 'p'
        }
        
        engine1 = create_db_engine(config)
        engine2 = create_db_engine(config)
        
        self.assertEqual(mock_create_engine.call_count, 2)


class TestGetEngine(unittest.TestCase):
    """Tests pour la fonction get_engine (singleton)."""

    def setUp(self):
        """Réinitialise le singleton avant chaque test."""
        from db_utils import reset_engine
        reset_engine()

    def tearDown(self):
        """Nettoie après chaque test."""
        from db_utils import reset_engine
        reset_engine()

    @patch('db_utils.create_db_engine')
    def test_get_engine_creates_singleton(self, mock_create_engine):
        """get_engine crée un engine singleton."""
        from db_utils import get_engine
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        engine1 = get_engine()
        engine2 = get_engine()
        
        self.assertIs(engine1, engine2)
        self.assertEqual(mock_create_engine.call_count, 1)

    @patch('db_utils.create_db_engine')
    def test_get_engine_returns_engine(self, mock_create_engine):
        """get_engine retourne un engine."""
        from db_utils import get_engine
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        engine = get_engine()
        
        self.assertIs(engine, mock_engine)

    @patch('db_utils.create_db_engine')
    def test_get_engine_calls_create_db_engine_once(self, mock_create_engine):
        """get_engine n'appelle create_db_engine qu'une seule fois."""
        from db_utils import get_engine
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        for _ in range(5):
            get_engine()
        
        self.assertEqual(mock_create_engine.call_count, 1)

    @patch('db_utils.create_db_engine')
    def test_get_engine_after_reset_creates_new(self, mock_create_engine):
        """get_engine crée un nouvel engine après reset_engine."""
        from db_utils import get_engine, reset_engine
        
        mock_engine1 = MagicMock()
        mock_engine2 = MagicMock()
        mock_create_engine.side_effect = [mock_engine1, mock_engine2]
        
        engine1 = get_engine()
        reset_engine()
        engine2 = get_engine()
        
        self.assertIs(engine1, mock_engine1)
        self.assertIs(engine2, mock_engine2)
        self.assertEqual(mock_create_engine.call_count, 2)


class TestResetEngine(unittest.TestCase):
    """Tests pour la fonction reset_engine."""

    def setUp(self):
        """Réinitialise avant chaque test."""
        from db_utils import reset_engine
        reset_engine()

    def tearDown(self):
        """Nettoie après chaque test."""
        from db_utils import reset_engine
        reset_engine()

    @patch('db_utils.create_db_engine')
    def test_reset_engine_disposes_and_clears(self, mock_create_engine):
        """reset_engine dispose l'engine et le réinitialise."""
        from db_utils import get_engine, reset_engine
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        get_engine()
        reset_engine()
        
        mock_engine.dispose.assert_called_once()
        
        get_engine()
        self.assertEqual(mock_create_engine.call_count, 2)

    def test_reset_engine_without_engine_does_not_raise(self):
        """reset_engine ne lève pas d'exception si aucun engine n'existe."""
        from db_utils import reset_engine
        
        # Ne doit pas lever d'exception
        reset_engine()
        reset_engine()

    @patch('db_utils.create_db_engine')
    def test_reset_engine_allows_new_engine_creation(self, mock_create_engine):
        """reset_engine permet la création d'un nouvel engine."""
        from db_utils import get_engine, reset_engine
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        engine1 = get_engine()
        reset_engine()
        engine2 = get_engine()
        
        # Vérifie que create_db_engine a été appelé deux fois
        self.assertEqual(mock_create_engine.call_count, 2)

    @patch('db_utils.create_db_engine')
    def test_reset_engine_calls_dispose_on_engine(self, mock_create_engine):
        """reset_engine appelle dispose() sur l'engine existant."""
        from db_utils import get_engine, reset_engine
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        get_engine()
        mock_engine.dispose.assert_not_called()
        
        reset_engine()
        mock_engine.dispose.assert_called_once()


class TestModuleIntegration(unittest.TestCase):
    """Tests d'intégration pour le module db_utils."""

    def setUp(self):
        """Réinitialise le singleton avant chaque test."""
        from db_utils import reset_engine
        reset_engine()

    def tearDown(self):
        """Nettoie après chaque test."""
        from db_utils import reset_engine
        reset_engine()

    @patch('db_utils.create_engine')
    def test_full_workflow(self, mock_create_engine):
        """Test du workflow complet: config -> url -> engine."""
        from db_utils import get_db_config, get_connection_url, create_db_engine
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        # 1. Obtenir la config
        config = get_db_config()
        self.assertIsInstance(config, dict)
        
        # 2. Construire l'URL
        url = get_connection_url(config)
        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith('mysql+mysqlconnector://'))
        
        # 3. Créer l'engine
        engine = create_db_engine(config)
        mock_create_engine.assert_called_once()

    @patch('db_utils.create_engine')
    def test_singleton_pattern_integrity(self, mock_create_engine):
        """Test de l'intégrité du pattern singleton."""
        from db_utils import get_engine, reset_engine
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        # Premier appel crée l'engine
        e1 = get_engine()
        self.assertEqual(mock_create_engine.call_count, 1)
        
        # Appels suivants retournent le même engine
        e2 = get_engine()
        e3 = get_engine()
        self.assertEqual(mock_create_engine.call_count, 1)
        self.assertIs(e1, e2)
        self.assertIs(e2, e3)
        
        # Reset et nouveau cycle
        reset_engine()
        e4 = get_engine()
        self.assertEqual(mock_create_engine.call_count, 2)


if __name__ == '__main__':
    unittest.main()
