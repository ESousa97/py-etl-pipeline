# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-09

### Added

- CSV extract with pandas and header normalisation
- Transform layer with validation and type coercion
- Bulk insert and PostgreSQL-native upsert load paths with shared utilities and audit logging
- Tenacity-based retries for transient database errors
- Optional scheduled runs via the `schedule` library
- Alembic migrations aligned with SQLAlchemy models
- Docker Compose stack (PostgreSQL 16 + ETL service)
- Optional Strawberry GraphQL ASGI app for health, version, and non-secret runtime hints
- CI (Ruff + pytest) and Dependabot configuration

[0.1.0]: https://github.com/esousa97/py-etl-pipeline/releases
