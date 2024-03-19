Bíblia Self-Hosted em português com intenção de uso doméstico, inicialmente criado para o Jogo da Bíblia, porém com pretenção de ser um rápido buscador desacoplado da nuvem com a facilidade de rodar fora de rastreamento.

## Onde queremos chegar 

- [ ] Fase 1: Apenas campo de busca com referências (Em Andamento)
- [ ] Fase 2: Criação de anotações: cada tag de anotação pode ter uma cor e um título, podemos ver a lista de todas elas
- [ ] Fase 3: Leitura corrida das escrituras ao selecionar um Livro, capítulo e versículo
- [ ] Fase 4: Busca avançada utilizando NLP e IA para buscar por sinônimos e contexto

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