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

### 2. set up Project to local device

### A. Set up a virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### B. Install dependencies for Python and Node.js

```bash
# Install all requirements
pip install -r requirements.txt

# Generate requirements file (if updating dependencies)
pip freeze > requirements.txt

# install all nodejs packages
npm install
```

### C. Database Setup

```bash
# Make the script executable (Linux/Windows only)
chmod +x setup_db.py

# Run the script
python setup_db.py
```

### 3. Start the Django development server

```bash
python manage.py runserver
```

The application will be available at http://127.0.0.1:8000/

### other developemnt script

#### Compile Tailwind CSS

```bash
# Watch for Tailwind changes during development
npx tailwindcss -i ./my_cardio/static/css/main.css -o ./my_cardio/static/css/output.css --watch
```

#### View Project Structure

```bash
# To see the project file structure without venv and other unnecessary files:
tree -I "venv|__pycache__|*.pyc|*.pyo|*.pyd|node_modules|.git"
```

#### Database Management

```bash
# After making model changes:
python manage.py makemigrations
python manage.py migrate
```

```bash
#how to access database in arch linuc
psql -U admin -d mycardiodb -h localhost
```
