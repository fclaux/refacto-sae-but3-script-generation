"""
Tests pour le module db_utils.
Refactorisé pour éliminer la duplication de code.
"""
import unittest
from unittest.mock import patch, MagicMock
import os


def make_config(host='localhost', port=3306, database='testdb', user='testuser', password='testpass'):
    """Factory pour créer une configuration de test."""
    return {'host': host, 'port': port, 'database': database, 'user': user, 'password': password}


class DbUtilsTestCase(unittest.TestCase):
    """Classe de base pour les tests db_utils avec setup/teardown du singleton."""
    
    def setUp(self):
        from db_utils import reset_engine
        reset_engine()

    def tearDown(self):
        from db_utils import reset_engine
        reset_engine()


class TestGetDbConfig(unittest.TestCase):
    """Tests pour la fonction get_db_config."""

    ENV_VARS = {
        'DB_HOST': 'testhost', 'DB_PORT': '5432', 'DB_DATABASE': 'testdb',
        'DB_USER': 'testuser', 'DB_PASSWORD': 'testpass'
    }
    EXPECTED_FROM_ENV = {
        'host': 'testhost', 'port': 5432, 'database': 'testdb',
        'user': 'testuser', 'password': 'testpass'
    }
    DEFAULTS = {
        'host': '127.0.0.1', 'port': 3306, 'database': 'provisional_calendar',
        'user': 'default_user', 'password': 'default_pass'
    }
    REQUIRED_KEYS = ['host', 'port', 'database', 'user', 'password']

    @patch.dict(os.environ, ENV_VARS)
    def test_get_db_config_from_env(self):
        """get_db_config récupère les valeurs depuis les variables d'environnement."""
        from db_utils import get_db_config
        config = get_db_config()
        for key, expected in self.EXPECTED_FROM_ENV.items():
            self.assertEqual(config[key], expected)

    @patch.dict(os.environ, {}, clear=True)
    def test_get_db_config_defaults(self):
        """get_db_config utilise les valeurs par défaut si env non défini."""
        from db_utils import get_db_config
        config = get_db_config()
        for key, expected in self.DEFAULTS.items():
            self.assertEqual(config[key], expected)

    def test_get_db_config_returns_dict_with_required_keys(self):
        """get_db_config retourne un dictionnaire avec toutes les clés requises."""
        from db_utils import get_db_config
        config = get_db_config()
        self.assertIsInstance(config, dict)
        for key in self.REQUIRED_KEYS:
            self.assertIn(key, config)

    def test_get_db_config_port_is_integer(self):
        """get_db_config retourne le port en tant qu'entier."""
        from db_utils import get_db_config
        self.assertIsInstance(get_db_config()['port'], int)

    @patch.dict(os.environ, {'DB_PORT': '5433'})
    def test_get_db_config_converts_port_string_to_int(self):
        """get_db_config convertit le port string en int."""
        from db_utils import get_db_config
        config = get_db_config()
        self.assertEqual(config['port'], 5433)
        self.assertIsInstance(config['port'], int)

    @patch.dict(os.environ, {'DB_HOST': 'partial_host'})
    def test_get_db_config_partial_env(self):
        """get_db_config gère les variables partiellement définies."""
        from db_utils import get_db_config
        self.assertEqual(get_db_config()['host'], 'partial_host')


class TestGetConnectionUrl(unittest.TestCase):
    """Tests pour la fonction get_connection_url."""

    def _get_url(self, config):
        from db_utils import get_connection_url
        return get_connection_url(config)

    def test_get_connection_url_with_config(self):
        """get_connection_url construit l'URL correctement avec une config."""
        config = make_config(host='myhost', port=3307, database='mydb', user='myuser', password='mypass')
        url = self._get_url(config)
        self.assertEqual(url, 'mysql+mysqlconnector://myuser:mypass@myhost:3307/mydb')

    @patch('db_utils.get_db_config')
    def test_get_connection_url_without_config(self, mock_get_config):
        """get_connection_url utilise get_db_config si aucune config fournie."""
        mock_get_config.return_value = make_config(host='defaulthost', database='defaultdb')
        from db_utils import get_connection_url
        url = get_connection_url()
        mock_get_config.assert_called_once()
        self.assertIn('defaulthost', url)
        self.assertIn('defaultdb', url)

    def test_get_connection_url_format(self):
        """get_connection_url retourne une URL au format SQLAlchemy valide."""
        url = self._get_url(make_config())
        self.assertTrue(url.startswith('mysql+mysqlconnector://'))
        self.assertIn('@', url)

    def test_get_connection_url_with_special_characters_in_password(self):
        """get_connection_url gère les mots de passe avec caractères spéciaux."""
        url = self._get_url(make_config(password='p@ss#word!'))
        self.assertIn('p@ss#word!', url)

    def test_get_connection_url_returns_string(self):
        """get_connection_url retourne une chaîne de caractères."""
        self.assertIsInstance(self._get_url(make_config()), str)

    def test_get_connection_url_includes_all_config_values(self):
        """get_connection_url inclut toutes les valeurs de configuration."""
        config = make_config(host='h123', port=9999, database='d456', user='u789', password='p000')
        url = self._get_url(config)
        for value in ['h123', '9999', 'd456', 'u789', 'p000']:
            self.assertIn(value, url)


class TestCreateDbEngine(unittest.TestCase):
    """Tests pour la fonction create_db_engine."""

    @patch('db_utils.create_engine')
    def test_create_db_engine_with_config(self, mock_create_engine):
        """create_db_engine crée un engine avec la config fournie."""
        from db_utils import create_db_engine
        config = make_config(host='testhost', database='testdb')
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
        mock_get_config.return_value = make_config()
        create_db_engine()
        mock_get_config.assert_called_once()
        mock_create_engine.assert_called_once()

    @patch('db_utils.create_engine')
    def test_create_db_engine_returns_engine(self, mock_create_engine):
        """create_db_engine retourne l'engine créé."""
        from db_utils import create_db_engine
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        self.assertIs(create_db_engine(make_config()), mock_engine)

    @patch('db_utils.create_engine')
    def test_create_db_engine_passes_correct_url(self, mock_create_engine):
        """create_db_engine passe l'URL correcte à create_engine."""
        from db_utils import create_db_engine
        config = make_config(host='myhost', port=3307, database='mydb', user='myuser', password='mypass')
        create_db_engine(config)
        mock_create_engine.assert_called_once_with('mysql+mysqlconnector://myuser:mypass@myhost:3307/mydb')

    @patch('db_utils.create_engine')
    def test_create_db_engine_multiple_calls(self, mock_create_engine):
        """Chaque appel à create_db_engine crée un nouvel engine."""
        from db_utils import create_db_engine
        mock_create_engine.side_effect = [MagicMock(), MagicMock()]
        create_db_engine(make_config())
        create_db_engine(make_config())
        self.assertEqual(mock_create_engine.call_count, 2)


class TestGetEngine(DbUtilsTestCase):
    """Tests pour la fonction get_engine (singleton)."""

    def _setup_mock_engine(self, mock_create_engine, count=1):
        """Configure le mock pour retourner des engines."""
        engines = [MagicMock() for _ in range(count)]
        mock_create_engine.side_effect = engines if count > 1 else None
        if count == 1:
            mock_create_engine.return_value = engines[0]
        return engines

    @patch('db_utils.create_db_engine')
    def test_get_engine_creates_singleton(self, mock_create_engine):
        """get_engine crée un engine singleton."""
        from db_utils import get_engine
        self._setup_mock_engine(mock_create_engine)
        engine1, engine2 = get_engine(), get_engine()
        self.assertIs(engine1, engine2)
        self.assertEqual(mock_create_engine.call_count, 1)

    @patch('db_utils.create_db_engine')
    def test_get_engine_returns_engine(self, mock_create_engine):
        """get_engine retourne un engine."""
        from db_utils import get_engine
        engines = self._setup_mock_engine(mock_create_engine)
        self.assertIs(get_engine(), engines[0])

    @patch('db_utils.create_db_engine')
    def test_get_engine_calls_create_db_engine_once(self, mock_create_engine):
        """get_engine n'appelle create_db_engine qu'une seule fois."""
        from db_utils import get_engine
        self._setup_mock_engine(mock_create_engine)
        for _ in range(5):
            get_engine()
        self.assertEqual(mock_create_engine.call_count, 1)

    @patch('db_utils.create_db_engine')
    def test_get_engine_after_reset_creates_new(self, mock_create_engine):
        """get_engine crée un nouvel engine après reset_engine."""
        from db_utils import get_engine, reset_engine
        engines = self._setup_mock_engine(mock_create_engine, count=2)
        engine1 = get_engine()
        reset_engine()
        engine2 = get_engine()
        self.assertIs(engine1, engines[0])
        self.assertIs(engine2, engines[1])
        self.assertEqual(mock_create_engine.call_count, 2)


class TestResetEngine(DbUtilsTestCase):
    """Tests pour la fonction reset_engine."""

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
        reset_engine()  # Ne doit pas lever d'exception
        reset_engine()

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


class TestModuleIntegration(DbUtilsTestCase):
    """Tests d'intégration pour le module db_utils."""

    @patch('db_utils.create_engine')
    def test_full_workflow(self, mock_create_engine):
        """Test du workflow complet: config -> url -> engine."""
        from db_utils import get_db_config, get_connection_url, create_db_engine
        mock_create_engine.return_value = MagicMock()
        
        config = get_db_config()
        self.assertIsInstance(config, dict)
        
        url = get_connection_url(config)
        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith('mysql+mysqlconnector://'))
        
        create_db_engine(config)
        mock_create_engine.assert_called_once()

    @patch('db_utils.create_engine')
    def test_singleton_pattern_integrity(self, mock_create_engine):
        """Test de l'intégrité du pattern singleton."""
        from db_utils import get_engine, reset_engine
        mock_create_engine.return_value = MagicMock()
        
        # Premier appel crée l'engine, appels suivants réutilisent
        engines = [get_engine() for _ in range(3)]
        self.assertEqual(mock_create_engine.call_count, 1)
        self.assertTrue(all(e is engines[0] for e in engines))
        
        # Reset et nouveau cycle
        reset_engine()
        get_engine()
        self.assertEqual(mock_create_engine.call_count, 2)


if __name__ == '__main__':
    unittest.main()
