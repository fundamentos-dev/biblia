# Development Guidelines for Bíblia Self-Hosted

## Build/Test Commands
- **Run app**: `docker-compose up --build` or `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- **Database migrations**: `alembic revision --autogenerate -m "message"` then `alembic upgrade head`
- **Seed database**: `make seed` (requires PostgreSQL running)
- **No test framework configured** - create tests using pytest if needed

## Code Style Guidelines
- **Language**: Python 3.11+ with FastAPI, SQLModel, Alembic
- **Imports**: Group by stdlib, third-party, local with blank lines between groups
- **Naming**: snake_case for variables/functions, PascalCase for classes, Portuguese names preferred
- **Types**: Use type hints with `Optional[T]`, `str | None` syntax, SQLModel Field annotations
- **Models**: Inherit from `SQLModel, table=True`, use `Optional[int] = Field(default=None, primary_key=True)` for IDs
- **Routes**: Use FastAPI router with tags, async functions, type-annotated parameters
- **Database**: Use SQLModel Session context managers, handle exceptions gracefully
- **Error handling**: Try/except blocks with meaningful Portuguese error messages
- **Comments**: Portuguese comments explaining complex logic, especially regex patterns

## Project Structure
- Models in `app/models/`, Routers in `app/routers/`, Schemas in `app/schemas/`
- Database connection in `app/database.py`, main FastAPI app in `app/main.py`
- Use relative imports within app module (`.routers`, `.models`, `.schemas`)

## IMPORTANT: Data Management Guidelines

### Database Usage
- **NEVER CREATE MOCK DATA**: Always use real data from the PostgreSQL database
- **Read-only operations**: This project uses a pre-populated database with biblical data
- **Data location**: Biblical data is stored in PostgreSQL tables (livro, versiculo, versao, etc.)
- **CSV files**: Located in `data/biblia/` are for initial database seeding only, not for runtime use

### Working with Biblical Data
- **Fetching verses**: Use SQLModel queries with proper joins between `Versiculo`, `Livro`, and `Versao` tables
- **Example pattern for reading data**:
  ```python
  with Session(engine) as session:
      stmt = (
          select(Versiculo, Versao, Livro)
          .where(Versiculo.versao_id == Versao.id)
          .where(Versiculo.livro_id == Livro.id)
          .where(Versao.abrev == versao_abrev)
          .where(Livro.abrev == livro_abrev)
          .where(Versiculo.capitulo == capitulo)
          .where(Versiculo.numero == numero)
      )
      result = session.exec(stmt).first()
  ```
- **Error handling**: Return meaningful Portuguese error messages when data is not found
- **No hardcoded data**: Never hardcode biblical texts or create mock dictionaries with verse data

### Testing
- **Unit tests**: Can use mocks for testing purposes only (in `tests/` directory)
- **Integration tests**: Should connect to test database when available
- **Never use mock data in production code** (anything in `app/` directory)