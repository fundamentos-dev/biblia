Bíblia Self-Hosted em português com intenção de uso doméstico, inicialmente criado para o Jogo da Bíblia, porém com pretenção de ser um rápido buscador desacoplado da nuvem com a facilidade de rodar fora de rastreamento.

## Funcionalidades

- **Busca de Referências:** Pesquisa rápida (ex: `Jo 3:16`) com suporte a múltiplas versões.
- **Modo Leitura:** Navegação fluida por livros e capítulos com interface limpa.
- **Modo Strong:** Estudo do texto original (Hebraico/Grego) com dicionário integrado (acessível via ícone `S` na busca ou clicando no versículo no modo leitura).

## Próximos Passos (Roadmap)

- [ ] **Anotações:** Sistema de tags e notas pessoais.
- [ ] **Busca Semântica:** NLP e IA para buscar por sentido e contexto.

## Modo Strong (Texto Original)

O sistema possui uma funcionalidade de "Modo Strong" que permite visualizar o texto original (Hebraico/Grego) e as definições do dicionário Strong para cada palavra.

### Processo de Importação de Dados (Auditável)

Os dados não são distribuídos nativamente com o repositório por questões de tamanho, mas scripts são fornecidos para baixar e popular o banco de dados a partir de fontes open-source confiáveis.

**1. Dicionários Strong (Léxico)**
*   **Fonte:** [OpenScriptures/strongs](https://github.com/openscriptures/strongs)
*   **Script:** `scripts/import_full_dictionaries.py`
*   **Ação:** Baixa os arquivos JSON brutos do GitHub (Hebraico e Grego) e popula a tabela `strongs_entry`.

**2. Novo Testamento (Grego)**
*   **Fonte:** [OpenGNT](https://github.com/eliranwong/OpenGNT)
*   **Arquivo:** `OpenGNT_keyedFeatures.csv.zip`
*   **Script:** `scripts/import_opengnt_nt.py`
*   **Ação:** Baixa o CSV, mapeia os livros para os IDs internos, limpa os códigos Strong (remove sufixos e zeros à esquerda) e popula a tabela `original_token` (aprox. 138k tokens).

**3. Antigo Testamento (Hebraico)**
*   **Fonte:** [OpenScriptures/morphhb](https://github.com/openscriptures/morphhb) (Westminster Leningrad Codex)
*   **Arquivos:** XMLs OSIS por livro (`Gen.xml`, `Exod.xml`, etc.)
*   **Script:** `scripts/import_oshb_ot.py`
*   **Ação:** Baixa recursivamente os XMLs do diretório `wlc/`, parseia a estrutura OSIS (`<verse>`, `<w>`), normaliza os códigos Strong (`c/559` -> `H559`) e popula a tabela `original_token` (aprox. 305k tokens).

### Execução da Importação

Para popular sua base local:

```sh
# Dentro do container ou venv
python scripts/import_full_dictionaries.py
python scripts/import_opengnt_nt.py
python scripts/import_oshb_ot.py
```

## Alembic

```sh
alembic init alembic
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic downgrade -1
alembic downgrade base
alembic upgrade ae1

alembic current
alembic history --verbose
```

## Notas de Lançamento

### v0.5.0

- **Busca por Lema (Strong):** Nova funcionalidade que permite buscar todas as ocorrências de uma palavra original (Hebraico/Grego) na Bíblia clicando diretamente em seu código no modal de definições.
- **Interface de Busca Aprimorada:** Suporte visual e lógico para pesquisas por lema (`lema=true`), diferenciando-as claramente das buscas semânticas e por referência.
- **Experiência de Navegação:** Fluxo contínuo entre leitura, definição e busca aprofundada de termos originais.

### v0.4.1

- **Busca Híbrida (RRF):** Implementação de novo algoritmo de busca que combina **Vetorial** (pgvector) e **Lexical** (Full-Text Search) usando *Reciprocal Rank Fusion* (RRF). Isso garante resultados semanticamente ricos sem perder a precisão de palavras-chave exatas.
- **Novo Modelo de IA:** Adoção do modelo **Serafim 900m** (`PORTULAN/serafim-900m-portuguese-pt-sentence-encoder-ir`), estado da arte para recuperação de informação em português, substituindo configurações anteriores baseadas em modelos menores ou quantizados.
- **Simplificação de Arquitetura:** Remoção de dependências externas complexas (Ollama, llama.cpp) em favor de uma stack puramente Python (`sentence-transformers`) + PostgreSQL. O modelo agora é executado nativamente na aplicação.
- **Infraestrutura:** Otimização do Dockerfile com pré-download do modelo e limpeza de serviços desnecessários no docker-compose.

### v0.4.0

- **Modo Strong Completo:** Implementação da visualização do texto original (Hebraico e Grego) com morfologia e definições do dicionário Strong.
- **Integração UX:** Acesso ao original através do botão `S` na pesquisa ou clicando diretamente nos versículos no Modo Leitura.
- **Scripts de Importação:** Ferramentas automatizadas (`scripts/import_*.py`) para baixar e popular a base de dados com léxicos e textos interlineares de fontes open-source (OpenScriptures, OpenGNT, MorphHB).
- **Correções:** Melhorias na estabilidade do modal e tratamento de dados faltantes.

### v0.3.0

- Oficializa o modo Leitura com layout completo em `leitura.html`, navegação por livros/capítulos, seletor de versões e estados de carregamento, conforme o commit `5977307a01023c48d9bc7d7f95b9a71d981e9ba5`.
- Expõe o endpoint `/api/v1/biblia/versions` para abastecer o seletor de versão do modo Leitura e manter dados reais da base, também trazido por `5977307a01023c48d9bc7d7f95b9a71d981e9ba5`.
- Ajusta os rodapés e o link do Código Fonte para o repositório oficial, deixando a navegação do modo leitura consistente com a página principal (commit `3fdefe4283e3ef36ee7e93508c765a4c8d47ba31`).
