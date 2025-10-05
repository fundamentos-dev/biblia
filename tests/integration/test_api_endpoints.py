import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app


class TestBibliaAPI:
    """Testes de integração para endpoints da API bíblica."""
    
    @classmethod
    def setup_class(cls):
        """Setup da classe de testes."""
        cls.client = TestClient(app)
    
    @patch('app.routers.biblia.capturar_referencia_versiculos')
    def test_busca_versiculo_sucesso(self, mock_parser):
        """Testa busca bem-sucedida de versículo."""
        # Setup mock
        mock_ref = Mock()
        mock_ref.versao_abrev = "ARA"
        mock_ref.livro_abrev = "Jo"
        mock_ref.capitulo = 3
        mock_ref.versiculo = 16
        mock_ref.capturar_texto_no_banco_de_dados.return_value = "Porque Deus amou o mundo..."
        
        mock_parser.return_value = [mock_ref]
        
        response = self.client.get("/api/v1/biblia/verse?q=João 3:16")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["livro_abrev"] == "Jo"
        assert data[0]["texto"] == "Porque Deus amou o mundo..."
    
    @patch('app.routers.biblia.capturar_referencia_versiculos')
    def test_busca_formato_invalido(self, mock_parser):
        """Testa resposta para formato de busca inválido."""
        mock_parser.side_effect = ValueError("Formato inválido")
        
        response = self.client.get("/api/v1/biblia/verse?q=formato inválido")
        
        assert response.status_code == 400
        assert "Formato inválido" in response.json()["detail"]
    
    def test_busca_sem_parametro_query(self):
        """Testa resposta quando parâmetro obrigatório não é fornecido."""
        response = self.client.get("/api/v1/biblia/verse")
        
        assert response.status_code == 422  # Unprocessable Entity
    
    @patch('app.routers.biblia.Session')
    def test_listar_livros_sucesso(self, mock_session):
        """Testa listagem bem-sucedida de livros."""
        # Setup mock
        mock_livro = Mock()
        mock_livro.id = 1
        mock_livro.nome = "João" 
        mock_livro.abrev = "Jo"
        mock_livro.posicao = 43
        
        mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = [mock_livro]
        
        response = self.client.get("/api/v1/biblia/books")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["nome"] == "João"
    
    @patch('app.routers.biblia.Session')
    def test_contar_capitulos_sucesso(self, mock_session):
        """Testa contagem bem-sucedida de capítulos."""
        mock_session.return_value.__enter__.return_value.exec.return_value.all.return_value = [Mock(), Mock(), Mock()]
        
        response = self.client.get("/api/v1/biblia/book/1/chapters")
        
        assert response.status_code == 200
        assert response.json() == 3
    
    @patch('app.routers.biblia.Session')
    def test_contar_versiculos_sucesso(self, mock_session):
        """Testa contagem bem-sucedida de versículos."""
        mock_resultado = Mock()
        mock_resultado.total_versiculos = 31
        
        mock_session.return_value.__enter__.return_value.exec.return_value.first.return_value = mock_resultado
        
        response = self.client.get("/api/v1/biblia/book/1/chapter/1/verses")
        
        assert response.status_code == 200
        assert response.json() == 31
    
    @patch('app.routers.biblia.Session')
    def test_contar_versiculos_capitulo_inexistente(self, mock_session):
        """Testa contagem para capítulo inexistente."""
        mock_session.return_value.__enter__.return_value.exec.return_value.first.return_value = None
        
        response = self.client.get("/api/v1/biblia/book/999/chapter/999/verses")
        
        assert response.status_code == 200
        assert response.json() == 0


class TestGeralAPI:
    """Testes de integração para endpoints gerais."""
    
    @classmethod
    def setup_class(cls):
        """Setup da classe de testes."""
        cls.client = TestClient(app)
    
    def test_hello_endpoint(self):
        """Testa endpoint básico de hello."""
        response = self.client.get("/api/v1/hello")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Sistema Bíblia Self-Hosted" in data["info"]
    
    @patch('app.routers.geral.Session')
    def test_health_check_sucesso(self, mock_session):
        """Testa health check com banco funcionando."""
        mock_session.return_value.__enter__.return_value.exec.return_value = None
        
        response = self.client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
    
    @patch('app.routers.geral.Session')
    def test_health_check_falha_banco(self, mock_session):
        """Testa health check com falha no banco."""
        mock_session.return_value.__enter__.side_effect = Exception("Connection failed")
        
        response = self.client.get("/api/v1/health")
        
        assert response.status_code == 503
        assert "indisponível" in response.json()["detail"]
    
    @patch('app.routers.geral.Session')
    def test_alembic_version_sucesso(self, mock_session):
        """Testa obtenção da versão do Alembic."""
        mock_session.return_value.__enter__.return_value.exec.return_value.first.return_value = ["abc123"]
        
        response = self.client.get("/api/v1/alembic_version")
        
        assert response.status_code == 200
        data = response.json()
        assert data["schema_version"] == "abc123"
        assert data["migration_tool"] == "alembic"
    
    def test_redirecionamento_raiz(self):
        """Testa redirecionamento da página raiz."""
        response = self.client.get("/", follow_redirects=False)
        
        assert response.status_code == 307  # Temporary Redirect
        assert response.headers["location"] == "/docs"
    
    def test_api_info(self):
        """Testa endpoint de informações da API."""
        response = self.client.get("/api")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Bíblia Self-Hosted API"
        assert data["version"] == "0.2.0"