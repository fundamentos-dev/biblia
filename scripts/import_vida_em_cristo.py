#!/usr/bin/env python3
"""
Script para importar dados de lista de leitura do arquivo vidaemcristo.json
para a tabela lista_leitura no banco de dados PostgreSQL.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

# Adiciona o diretório app ao Python path para importar os modelos
sys.path.append(str(Path(__file__).parent.parent))

from app.database import engine
from app.models.ListaLeitura import ListaLeitura
from sqlmodel import Session


def carregar_dados_json(caminho_arquivo: str) -> List[Dict[str, str]]:
    """
    Carrega os dados do arquivo JSON.
    
    Args:
        caminho_arquivo: Caminho para o arquivo vidaemcristo.json
        
    Returns:
        Lista de dicionários com título e conteúdo
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        return dados
    except FileNotFoundError:
        print(f"Erro: Arquivo {caminho_arquivo} não encontrado.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e}")
        sys.exit(1)


def inserir_dados_banco(dados: List[Dict[str, str]]) -> None:
    """
    Insere os dados na tabela lista_leitura.
    
    Args:
        dados: Lista de dicionários com título e conteúdo
    """
    try:
        with Session(engine) as session:
            # Verifica se já existem dados na tabela
            existing_count = session.query(ListaLeitura).count()
            if existing_count > 0:
                resposta = input(f"A tabela lista_leitura já possui {existing_count} registros. Deseja continuar? (s/N): ")
                if resposta.lower() != 's':
                    print("Operação cancelada.")
                    return
            
            # Insere os novos dados
            registros_inseridos = 0
            for item in dados:
                lista_leitura = ListaLeitura(
                    titulo=item["titulo"],
                    conteudo=item["conteudo"]
                )
                session.add(lista_leitura)
                registros_inseridos += 1
            
            session.commit()
            print(f"✓ {registros_inseridos} registros inseridos com sucesso na tabela lista_leitura.")
            
    except Exception as e:
        print(f"Erro ao inserir dados no banco: {e}")
        sys.exit(1)


def main():
    """Função principal do script."""
    # Caminho para o arquivo JSON
    caminho_json = Path(__file__).parent.parent / "data" / "listas" / "vidaemcristo.json"
    
    if not caminho_json.exists():
        print(f"Erro: Arquivo {caminho_json} não encontrado.")
        sys.exit(1)
    
    print(f"Carregando dados de: {caminho_json}")
    dados = carregar_dados_json(str(caminho_json))
    
    print(f"Encontrados {len(dados)} registros para importar.")
    
    # Confirma a operação
    resposta = input("Deseja prosseguir com a importação? (s/N): ")
    if resposta.lower() != 's':
        print("Operação cancelada.")
        return
    
    print("Inserindo dados no banco de dados...")
    inserir_dados_banco(dados)
    print("Importação concluída!")


if __name__ == "__main__":
    main()