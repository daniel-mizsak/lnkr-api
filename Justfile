set shell := ["bash", "-uc"]

@_:
    just --list --unsorted

[group("lifecycle")]
clean:
    rm -rf \
        .ansible \
        .artifacts \
        .cache \
        .coverage \
        .pytest_cache \
        .ruff_cache \
        coverage.xml \
        htmlcov \
        megalinter-reports \
        .venv
    find . -name ".DS_Store" -type f -delete
    find . -type d -name "__pycache__" -exec rm -r {} +

[group("lifecycle")]
install *args:
    uv sync --all-groups {{ args }}

[group("lifecycle")]
upgrade:
    just install --upgrade

[group("lifecycle")]
fresh: clean install

[group("qa")]
lint:
    uv run ruff check
    uv run ruff format --diff

[group("qa")]
type:
    uv run ty check

[group("qa")]
test *args:
    source ./deployment/.env.development && \
    uv run pytest {{ args }}

[group("qa")]
coverage:
    source ./deployment/.env.development && \
    uv run coverage run --source=tests --module pytest
    uv run coverage report --fail-under=100 --show-missing

    source ./deployment/.env.development && \
    uv run coverage run --source=lnkr --module pytest
    uv run coverage report --show-missing
    uv run coverage xml -o .artifacts/coverage.xml
    uv run coverage html -d .artifacts/htmlcov

[group("qa")]
check-all: lint type coverage

[group("qa-extra")]
megalinter:
    npx mega-linter-runner --flavor cupcake --env "MEGALINTER_CONFIG=.github/linters/.megalinter.yml"

[group("qa-extra")]
pre-commit:
    uv run pre-commit run --all-files

[group("deploy")]
[working-directory("./deployment")]
deploy-development up="up":
    source ./.env.development && \
    docker compose --file compose.development.yml {{ up }} \
    {{ if up == "up" { " --build --watch" } else { "" } }}

[confirm("Deploy to production? (y/N)")]
[group("deploy")]
[working-directory("./deployment")]
deploy-production:
    op run --env-file=".env.production" --no-masking -- ansible-playbook playbook.yml
