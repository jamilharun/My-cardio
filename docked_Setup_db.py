#!/usr/bin/env python3
import os
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()

# Database credentials from environment variables
DB_NAME = os.getenv("DB_NAME", "mycardiodb")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "admin123")
DB_HOST = os.getenv("DB_HOST", "db")  # Must match the service name in docker-compose
DB_PORT = os.getenv("DB_PORT", "5432")

def run_command(command):
    """Execute a shell command and print output in real-time."""
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
    return process.returncode

def wait_for_postgres():
    """Wait for PostgreSQL to be ready."""
    print("⏳ Waiting for PostgreSQL to start...")
    while True:
        result = subprocess.run(
            f'PGPASSWORD={DB_PASS} psql -h {DB_HOST} -U {DB_USER} -d postgres -c "SELECT 1;"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            print("✅ PostgreSQL is ready!")
            break
        time.sleep(2)

def setup_database():
    """Create the database and user inside the running PostgreSQL container."""
    print("🔨 Setting up the database...")

    commands = f"""
    CREATE ROLE {DB_USER} WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD '{DB_PASS}';
    CREATE DATABASE {DB_NAME} OWNER {DB_USER};
    GRANT ALL ON SCHEMA public TO {DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO {DB_USER};
    """
    
    run_command(f'PGPASSWORD={DB_PASS} psql -h {DB_HOST} -U postgres -d postgres -c "{commands}"')

def run_migrations():
    """Run Django migrations inside the Django container."""
    print("🚀 Running Django migrations...")
    run_command("docker-compose exec django python manage.py migrate")

def create_superuser():
    """Create a Django superuser."""
    print("🔑 Creating Django superuser...")
    superuser_script = (
        "from django.contrib.auth import get_user_model; "
        "User = get_user_model(); "
        "User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Superuser already exists')"
    )
    run_command(f'docker-compose exec django python manage.py shell -c "{superuser_script}"')

def main():
    """Main function to execute database setup."""
    wait_for_postgres()
    setup_database()
    run_migrations()

    # Ask if user wants to create a superuser
    answer = input("Do you want to create a Django superuser? (y/n): ").strip().lower()
    if answer in ["y", "yes"]:
        create_superuser()

    print("🎉 Database setup completed!")

if __name__ == "__main__":
    main()
