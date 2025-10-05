import pytest
from unittest.mock import Mock, patch
from app.routers.biblia import ReferenciaBiblica, capturar_referencia_versiculos


class TestReferenciaBiblica:
    """Testes unitários para a classe ReferenciaBiblica."""
    
    def test_init_referencia_basica(self):
        """Testa inicialização básica de uma referência bíblica."""
        ref = ReferenciaBiblica("Jo", 3, 16, "ARA")
        
        assert ref.livro_abrev == "Jo"
        assert ref.capitulo == 3
        assert ref.versiculo == 16
        assert ref.versao_abrev == "ARA"
        assert ref.texto is None
    
    def test_str_representation(self):
        """Testa a representação string da referência."""
        ref = ReferenciaBiblica("Jo", 3, 16, "ARA")
        
        assert str(ref) == "Jo 3:16 ARA"
    
    def test_capturar_texto_sem_versao_raise_error(self):
        """Testa se levanta erro quando versão não é especificada."""
        ref = ReferenciaBiblica("Jo", 3, 16)
        
        with pytest.raises(ValueError, match="Versão da bíblia deve ser especificada"):
            ref.capturar_texto_no_banco_de_dados()
    
    @patch('app.routers.biblia.Session')
    def test_capturar_texto_sucesso(self, mock_session):
        """Testa busca bem-sucedida de texto no banco."""
        # Setup mock
        mock_versiculo = Mock()
        mock_versiculo.texto = "Porque Deus amou o mundo..."
        
        mock_session.return_value.__enter__.return_value.exec.return_value.first.return_value = [mock_versiculo, None, None]
        
        ref = ReferenciaBiblica("Jo", 3, 16, "ARA")
        texto = ref.capturar_texto_no_banco_de_dados()
        
        assert texto == "Porque Deus amou o mundo..."
        assert ref.texto == "Porque Deus amou o mundo..."
    
    @patch('app.routers.biblia.Session')
    def test_capturar_texto_nao_encontrado(self, mock_session):
        """Testa quando versículo não é encontrado no banco."""
        # Mock da sessão retorna None para todas as consultas
        mock_session.return_value.__enter__.return_value.exec.return_value.first.return_value = None
        
        ref = ReferenciaBiblica("Inexistente", 999, 999, "ARA")
        texto = ref.capturar_texto_no_banco_de_dados()
        
        # A função primeiro verifica se a versão existe, por isso essa é a mensagem esperada
        assert texto == "Versão 'ARA' não encontrada no banco"
        assert ref.texto == "Versão 'ARA' não encontrada no banco"


class TestCapturarReferenciaVersiculos:
    """Testes unitários para o parser de referências bíblicas."""
    
    def test_parse_versiculo_unico(self):
        """Testa parse de um único versículo."""
        resultado = capturar_referencia_versiculos("João 3:16")
        
        assert len(resultado) == 1
        assert resultado[0].livro_abrev == "Jo"
        assert resultado[0].capitulo == 3
        assert resultado[0].versiculo == 16
    
    def test_parse_faixa_versiculos(self):
        """Testa parse de faixa de versículos."""
        resultado = capturar_referencia_versiculos("João 3:16-18")
        
        assert len(resultado) == 3
        assert all(ref.livro_abrev == "Jo" for ref in resultado)
        assert all(ref.capitulo == 3 for ref in resultado)
        assert [ref.versiculo for ref in resultado] == [16, 17, 18]
    
    def test_parse_multiplos_versiculos(self):
        """Testa parse de múltiplos versículos separados por vírgula."""
        resultado = capturar_referencia_versiculos("João 3:16,17,20")
        
        assert len(resultado) == 3
        assert all(ref.livro_abrev == "Jo" for ref in resultado)
        assert all(ref.capitulo == 3 for ref in resultado)
        assert [ref.versiculo for ref in resultado] == [16, 17, 20]
    
    def test_parse_multiplos_livros(self):
        """Testa parse de múltiplos livros separados por ponto e vírgula."""
        resultado = capturar_referencia_versiculos("João 3:16; Mateus 5:1")
        
        assert len(resultado) == 2
        assert resultado[0].livro_abrev == "Jo"
        assert resultado[1].livro_abrev == "Mt"
        assert resultado[0].versiculo == 16
        assert resultado[1].versiculo == 1
    
    def test_parse_formato_invalido(self):
        """Testa se levanta erro para formato inválido."""
        with pytest.raises(ValueError, match="Formato de referência bíblica inválido"):
            capturar_referencia_versiculos("formato inválido")
    
    def test_parse_capitulo_invalido(self):
        """Testa se levanta erro para capítulo inválido.""" 
        with pytest.raises(ValueError, match="Formato de referência bíblica inválido"):
            capturar_referencia_versiculos("João abc:16")
    
    def test_parse_versiculo_invalido(self):
        """Testa se levanta erro para versículo inválido."""
        with pytest.raises(ValueError, match="Número de versículo inválido"):
            capturar_referencia_versiculos("João 3:abc")
    
    def test_parse_faixa_invalida(self):
        """Testa se levanta erro para faixa de versículos inválida."""
        with pytest.raises(ValueError, match="Faixa de versículos inválida"):
            capturar_referencia_versiculos("João 3:16-abc")
    
    def test_parse_string_vazia_ignorada(self):
        """Testa se strings vazias são ignoradas."""
        resultado = capturar_referencia_versiculos("João 3:16; ; Mateus 5:1")
        
        assert len(resultado) == 2
        assert resultado[0].livro_abrev == "Jo"
        assert resultado[1].livro_abrev == "Mt"
    
    def test_parse_nomes_com_acentos(self):
        """Testa parse de nomes de livros com acentos."""
        resultado = capturar_referencia_versiculos("João 3:16")
        
        assert len(resultado) == 1
        assert resultado[0].livro_abrev == "Jo"
        assert resultado[0].capitulo == 3
        assert resultado[0].versiculo == 16
    
    def test_parse_nomes_completos(self):
        """Testa parse de nomes completos de livros."""
        resultado = capturar_referencia_versiculos("I Corintios 13:4")
        
        assert len(resultado) == 1
        assert resultado[0].livro_abrev == "1Co"
        assert resultado[0].capitulo == 13
        assert resultado[0].versiculo == 4
    
    def test_parse_nomes_com_acentos_completos(self):
        """Testa parse de nomes completos com acentos."""
        resultado = capturar_referencia_versiculos("I Coríntios 13:4")
        
        assert len(resultado) == 1
        assert resultado[0].livro_abrev == "1Co"
        assert resultado[0].capitulo == 13
        assert resultado[0].versiculo == 4
    
    def test_parse_nomes_diversos_formatos(self):
        """Testa diferentes formatos de nomes de livros."""
        casos = [
            ("Gênesis 1:1", "Gn"),
            ("Genesis 1:1", "Gn"),
            ("Êxodo 3:14", "Ex"),
            ("Exodo 3:14", "Ex"),
            ("II Coríntios 5:17", "2Co"),
            ("Cântico dos Cânticos 2:1", "Ct"),
            ("Cantico dos Canticos 2:1", "Ct"),
        ]
        
        for entrada, abrev_esperada in casos:
            resultado = capturar_referencia_versiculos(entrada)
            assert len(resultado) == 1
            assert resultado[0].livro_abrev == abrev_esperada