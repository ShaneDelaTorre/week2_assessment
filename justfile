# CS2 Match Tracker - common commands

# Run dev server
run:
    python manage.py runserver

# Apply migrations
migrate:
    python manage.py migrate

# Make migrations
mm:
    python manage.py makemigrations

# Both at once
m:
    python manage.py makemigrations && python manage.py migrate

# Create superuser
su:
    python manage.py createsuperuser

# Open Django shell
shell:
    python manage.py shell

# Lint
lint:
    ruff check .

# Lint and auto-fix
fix:
    ruff check . --fix && ruff format .

# Run tests
test:
    python manage.py test

# Run checks
check:
    python manage.py check

# Sync all dependencies
sync:
    uv sync