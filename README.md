# <div align="center">🔗 lnkr-api</div>

<div align="center">
    <kbd>
        <a href="https://github.com/daniel-mizsak/lnkr-api/actions/workflows/ci.yml" target="_blank"><img src="https://github.com/daniel-mizsak/lnkr-api/actions/workflows/ci.yml/badge.svg" alt="build status"></a>
        <a href="https://codecov.io/gh/daniel-mizsak/lnkr-api" target="_blank"><img src="https://codecov.io/gh/daniel-mizsak/lnkr-api/graph/badge.svg?token=XKVAGIMLP0" alt="codecov"></a>
        <a href="https://github.com/daniel-mizsak/lnkr-api/blob/main/LICENSE" target="_blank"><img src="https://img.shields.io/github/license/daniel-mizsak/lnkr-api" alt="license"></a>
    </kbd>
</div>

## Overview

Link manager REST API.

## Getting started

### Technology Stack and Features

- [FastAPI](https://fastapi.tiangolo.com) for the Python backend API.
- [Pydantic](https://docs.pydantic.dev) for the data validation and configuration management.
- [PostgreSQL](https://www.postgresql.org) as the SQL database.
- [SQLAlchemy](https://www.sqlalchemy.org) for the Python SQL database interactions (ORM).
- [Alembic](https://alembic.sqlalchemy.org) for database migrations.
- [Redis](https://redis.io) for caching.
- [Pytest](https://pytest.org) for testing.
- [Docker Compose](https://www.docker.com) for development and production.
- [Resend](https://resend.com)'s SMTP for passwordless email-based registration.
- [JWT](https://www.jwt.io) (JSON Web Token) for endpoint authentication.
- [Traefik](https://traefik.io) for reverse proxy and rate limiting.
- [GitHub Actions](https://docs.github.com/en/actions) for CI/CD.
- [Just](https://just.systems) as the command runner.
- [1Password](https://1password.com) for secrets management.

### Development

Docker must be running for running tests and for deploying the application locally.
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

- Add tests covering api dependencies.
- Use `async` API calls in tests.
- Add callback URL to request login token endpoint and attach to login_url.
- Use `secrets_dir="/run/secrets"` for docker secrets in production.
- Remove old login tokens with a scheduled cleanup task.
- When creating login token store additional info like IP address, user agent, etc.
- Improve rate limiting.
- Automatic deployment to production when GitHub release is created.
- Add more in-depth logging.
- No 3rd party service for sending emails. Self-hosted SMTP server.
- Update email template based on the look of the frontend and update button's link.
- Raise `LnkrError` subclasses directly from the service layer and convert them to HTTP responses via a single FastAPI exception handler, instead of catching and re-raising in every route.

<hr>

<div align="center">
    <strong>⭐ Star the repository if you found it useful ⭐</strong>
    <br>
    <a href="https://github.com/daniel-mizsak/repository-template" target="_blank">Repository Template</a> |
    <a href="https://github.com/daniel-mizsak/workflows" target="_blank">Reusable Workflows</a> |
    <a href="https://github.com/daniel-mizsak/mtjd" target="_blank">Development Environment </a>
</div>
