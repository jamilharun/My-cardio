# MyCardio - Django Application

This is a Django application with PostgreSQL database and Tailwind CSS for styling.

## Prerequisites

- Python 3.x
- PostgreSQL
- Node.js and npm (for Tailwind CSS)
- Git

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/jamilharun/My-cardio
cd mycardiodb
```

### 2. Set up a virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
# Install all requirements
pip install -r requirements.txt

# Generate requirements file (if updating dependencies)
pip freeze > requirements.txt
```

### 4. Install Node.js dependencies

```bash
npm install
```

### 5. Database Setup

Choose the appropriate method for your operating system:

#### Cross-platform (Recommended)

```bash
# Make the script executable (Linux/Windows only)
chmod +x setup_db.py

# Run the script
python setup_db.py
```

## Running the Application

### Start the Django development server

```bash
python manage.py runserver
```

The application will be available at http://127.0.0.1:8000/

### Compile Tailwind CSS

```bash
# Watch for Tailwind changes during development
npx tailwindcss -i ./static/css/main.css -o ./static/css/output.css --watch
```

## Development

### View Project Structure

To see the project file structure without venv and other unnecessary files:

```bash
tree -I "venv|__pycache__|*.pyc|*.pyo|*.pyd|node_modules|.git"
```

### Database Management

After making model changes:

```bash
python manage.py makemigrations
python manage.py migrate
```
