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

#### Application

- [FastAPI](https://fastapi.tiangolo.com) for the Python backend API.
- [Pydantic](https://docs.pydantic.dev) for the data validation and configuration management.
- [PostgreSQL](https://www.postgresql.org) as the SQL database.
- [SQLAlchemy](https://www.sqlalchemy.org) for the Python SQL database interactions (ORM).
- [Alembic](https://alembic.sqlalchemy.org) for database migrations.
- [Redis](https://redis.io) for caching.
- [GeoLite2](https://www.maxmind.com) for IP-based geolocation.
- [Resend](https://resend.com)'s SMTP for passwordless email-based registration.
- [JWT](https://www.jwt.io) (JSON Web Token) for endpoint authentication.
- [Pytest](https://pytest.org) for testing.

#### CI/CD and Deployment

- [Just](https://just.systems) as the command runner.
- [Docker Compose](https://www.docker.com) for development and production.
- [GitHub Actions](https://docs.github.com/en/actions) for CI/CD.
- [Traefik](https://traefik.io) for reverse proxy and rate limiting.
- [Ansible](https://www.ansible.com) for provisioning and configuration management.
- [Pulumi](https://www.pulumi.com) for infrastructure as code.
- [1Password](https://1password.com) for secrets management.
- [Age](https://age-encryption.org) and [Rclone](https://rclone.org) for encrypted backups.
- [Healthchecks](https://healthchecks.io) for monitoring successful runs of scheduled tasks.

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

### Production

Production runs on an Ubuntu VPS provisioned and hardened with [vps-setup](https://github.com/mlops-top/vps-setup).

Create R2 bucket for backups:

```bash
just pulumi-stack-init
just pulumi up
```

Deploy to production:

```bash
just deploy-production
```

### Future improvements

#### Before the 1.0.0 release

- Improve rate limiting for login token requests and verification, refresh token rotation, and password-protected link unlocking. Add per-email send limits and verify that client identification works through the production proxy and frontend.
- Handle SMTP failures when requesting login tokens with a predictable API response and a clear retry path.
- Add essential operational logging for authentication, email delivery, and dependency failures, without exposing tokens or credentials. Review which personal data is sent to Sentry.
- Rehearse restoring an encrypted backup and document deployment, recovery, and rollback steps. Use the same pinned release image for the application and database migrations instead of `latest`.

#### Features

- Add sorting links by click count.
- Add a callback URL to the request login token endpoint and include it in the login URL, restricting destinations to approved frontend locations.
- Send email to confirm account deletion, with a link that calls the account deletion endpoint and redirects to a success page.

#### Codebase and infrastructure improvements

- Raise `LnkrError` subclasses directly from the service layer and convert them to HTTP responses via a single FastAPI exception handler, instead of catching and re-raising in every route.
- Add dedicated concurrency tests with separate database sessions and controlled synchronization to verify race-condition handling for login token consumption, user creation, refresh token rotation, and user link limits.
- Expand operational logging with structured events and request correlation across the frontend, API, and scheduled tasks.
- Automate staging deployment when a GitHub push occurs to the main branch and production deployment when a release is created.
- Use `secrets_dir="/run/secrets"` for Docker secrets in production.

<hr>

<div align="center">
    <strong>⭐ Star the repository if you found it useful ⭐</strong>
    <br>
    <a href="https://github.com/daniel-mizsak/repository-template" target="_blank">Repository Template</a> |
    <a href="https://github.com/daniel-mizsak/workflows" target="_blank">Reusable Workflows</a> |
    <a href="https://github.com/daniel-mizsak/mtjd" target="_blank">Development Environment </a>
</div>
