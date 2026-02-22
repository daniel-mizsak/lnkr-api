# <div align="center">🔗 lnkr-api</div>

<div align="center">
    <kbd>
        <a href="https://github.com/daniel-mizsak/lnkr-api/actions/workflows/ci.yml" target="_blank"><img src="https://github.com/daniel-mizsak/lnkr-api/actions/workflows/ci.yml/badge.svg" alt="build status"></a>
        <a href="https://codecov.io/gh/daniel-mizsak/lnkr-api" target="_blank"><img src="https://codecov.io/gh/daniel-mizsak/lnkr-api/graph/badge.svg?token=DSYX3WSAFR" alt="codecov"></a>
        <a href="https://results.pre-commit.ci/latest/github/daniel-mizsak/lnkr-api/main" target="_blank"><img src="https://results.pre-commit.ci/badge/github/daniel-mizsak/lnkr-api/main.svg" alt="pre-commit.ci status"></a>
        <a href="https://img.shields.io/github/license/daniel-mizsak/lnkr-api" target="_blank"><img src="https://img.shields.io/github/license/daniel-mizsak/lnkr-api" alt="license"></a>
    </kbd>
</div>

## Overview

Link manager REST API.

## Getting started

### Technology Stack and Features

- [FastAPI](https://fastapi.tiangolo.com) for the Python backend API.
- [SQLModel](https://sqlmodel.tiangolo.com) for the Python SQL database interactions (ORM).
- [Pydantic](https://docs.pydantic.dev), for the data validation and settings management.
- [PostgreSQL](https://www.postgresql.org) as the SQL database.
- [Redis](https://redis.io) for caching.
- [Docker Compose](https://www.docker.com) for development and production.
- [Resend](https://resend.com)'s SMTP for passwordless email based registration.
- [JWT](https://www.jwt.io) (JSON Web Token) for endpoint authentication.
- [Pytest](https://pytest.org) for testing.
- [Traefik](https://traefik.io) for reverse proxy and rate limiting.
- [GitHub Actions](https://docs.github.com/en/actions) for CI/CD.
- [Just](https://just.systems) as the command runner.
- [1Password](https://1password.com) for secrets management.

### Development

Setup Python virtual environment for development:

```bash
just install
```

Run quality assurance checks:

```bash
just check-all
```

Run the application locally using Docker Compose:

```bash
just deploy-development
```

### Future improvements

- Automatically backup database.
- Add automatic deployment to production when new release is created.
- Use `Alembic` for database migrations.
- Use refresh tokens for longer sessions.
- Add in-depth logging.
- Use `Redis` for `Traefik`'s rate limiting.
- Do not use 3rd party service for sending emails, use self hosted SMTP server.
- Use `Docker Secrets`?
- Use async?
- Update email template based on the look of the frontend and update button's link.
- Clean up old login tokens.

<hr>

<div align="center">
    <strong>⭐ Star the repository if you found it useful ⭐</strong>
    <br>
    <a href="https://github.com/daniel-mizsak/repository-template" target="_blank">Repository Template</a> |
    <a href="https://github.com/daniel-mizsak/workflows" target="_blank">Reusable Workflows</a> |
    <a href="https://github.com/daniel-mizsak/mtjd" target="_blank">Development Environment </a>
</div>
