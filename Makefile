seed:
	echo "Inserindo dados da biblia..."
	psql -U postgres -h db -d biblia -f /initial_data/biblia_psql.sql