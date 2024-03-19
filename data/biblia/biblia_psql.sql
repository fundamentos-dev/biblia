--
-- Dump tables with csv
--

COPY testamento FROM '/initial_data/biblia_testamento.csv' WITH (FORMAT csv);
COPY versao FROM '/initial_data/biblia_versao.csv' WITH (FORMAT csv);
COPY livro FROM '/initial_data/biblia_livro.csv' WITH (FORMAT csv);
COPY versiculo FROM '/initial_data/biblia_versiculo.csv' WITH (FORMAT csv);
COPY livrocapitulonumeroversiculos FROM '/initial_data/biblia_livro_capitulo_numero_versiculos.csv' WITH (FORMAT csv);