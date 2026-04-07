# CS2 Match Tracker

A Django REST API for tracking Counter-Strike 2 matches.

## Setup

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py migrate
```

### Populate Database

To populate the database with sample data:
```bash
python manage.py populate_db
```

## Running the Server

Start the development server:
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/`

## Testing

Run the test suite:
```bash
python manage.py test
```

## Project Structure

- **config/**: Django project configuration (settings, URLs, WSGI)
- **cs2_match_tracker/**: Main application
  - `models.py`: Database models
  - `views.py`: API viewsets and views
  - `serializers.py`: DRF serializers
  - `filters.py`: Custom filters for queries
  - `permissions.py`: Custom permission classes
  - `urls.py`: Application URL patterns
  - `management/commands/`: Custom Django management commands

## API Endpoints

Available endpoints for the CS2 Match Tracker API.

## License

MIT
