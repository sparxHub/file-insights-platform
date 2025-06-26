# File Upload Insights Platform - Agent Guide

## Commands
- **Test all**: `pdm run pytest -q`
- **Test single file**: `pdm run pytest tests/path/to/test_file.py -q`
- **Type check**: `pdm run mypy apps/ tests/`
- **Run API**: `pdm run uvicorn apps.api.app.main:app --reload`
- **Install deps**: `pdm install`

## Architecture
- **Hexagonal architecture**: Clean separation of adapters/services/controllers
- **Main apps**: `apps/api/` (FastAPI), `apps/workers/` (Lambda workers), `apps/web/` (React stub)
- **Core structure**: `models/`, `services/`, `adapters/`, `controllers/`, `api/routes/`
- **Infrastructure**: CloudFormation templates in `infrastructure/cloudformation/`
- **Database**: DynamoDB for metadata, S3 for file storage, SQS for async processing

## Code Style
- **Naming**: PascalCase classes, snake_case functions/vars, UPPER_SNAKE_CASE constants
- **Imports**: Standard → third-party → local (with blank lines), use relative imports with `..`
- **Types**: Extensive type hints, Pydantic models for validation, Optional types for nullable values
- **Async**: Use async/await consistently, `pytest.mark.asyncio` for async tests
- **Error handling**: Custom exceptions, try-except with specific handling, log before re-raise
- **Tests**: JWT auth with `Bearer {token}` headers, mock AWS services, use `conftest.py` fixtures
