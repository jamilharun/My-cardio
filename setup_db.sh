#!/bin/bash

# Database credentials
DB_NAME="mycardiodb"
DB_USER="admin"
DB_PASS="admin123"
DB_HOST="localhost"
DB_PORT="5432"

# Function to check if PostgreSQL is installed
check_postgres() {
    if ! command -v psql &> /dev/null
    then
        echo "❌ PostgreSQL is not installed. Installing it now..."
        sudo pacman -S postgresql --noconfirm
        sudo systemctl enable --now postgresql
    else
        echo "✅ PostgreSQL is installed!"
    fi
}

# Function to start PostgreSQL service
start_postgres() {
    echo "🔄 Starting PostgreSQL service..."
    sudo systemctl start postgresql
}

# Function to create the database and user
setup_database() {
    echo "🔨 Setting up the database..."
    
    # Switch to the postgres user and execute SQL commands
    sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

    echo "✅ Database $DB_NAME and user $DB_USER created!"
}

# Function to apply Django migrations
run_migrations() {
    echo "🚀 Running Django migrations..."
    source venv/bin/activate  # Activate virtual environment
    python manage.py migrate
    echo "✅ Migrations applied successfully!"
}

# Function to create a Django superuser (Optional)
create_superuser() {
    echo "🔑 Creating Django superuser..."
    echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell
    echo "✅ Superuser created!"
}

# Function to load initial data (Optional)
load_initial_data() {
    echo "📥 Loading initial data..."
    python manage.py loaddata initial_data.json
}

# Execute functions in order
check_postgres
start_postgres
setup_database
run_migrations
create_superuser
# Uncomment the next line if you have initial data to load
# load_initial_data

echo "🎉 Database setup completed!"
