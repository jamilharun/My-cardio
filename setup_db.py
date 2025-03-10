#!/usr/bin/env python3
import os
import platform
import subprocess
import sys

# Database credentials
DB_NAME = "mycardiodb"
DB_USER = "admin"
DB_PASS = "admin123"
DB_HOST = "localhost"
DB_PORT = "5432"

def is_windows():
    return platform.system().lower() == "windows"

def is_linux():
    return platform.system().lower() == "linux"

def run_command(command, shell=True):
    """Execute a command and print its output in real-time"""
    process = subprocess.Popen(
        command,
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    for line in process.stdout:
        print(line, end='')
    
    process.wait()
    return process.returncode

def check_postgres():
    """Check if PostgreSQL is installed and available"""
    print("🔍 Checking PostgreSQL installation...")
    
    if is_windows():
        # Check if PostgreSQL is in the PATH
        try:
            subprocess.run(["psql", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("✅ PostgreSQL is installed!")
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            print("❌ PostgreSQL not found in PATH. Please install PostgreSQL and add it to your PATH.")
            return False
    
    elif is_linux():
        # Check for PostgreSQL on Linux
        result = subprocess.run(["which", "psql"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print("✅ PostgreSQL is installed!")
            return True
        else:
            print("❌ PostgreSQL is not installed. Installing it now...")
            if run_command("sudo pacman -S postgresql --noconfirm") == 0:
                run_command("sudo systemctl enable --now postgresql")
                print("✅ PostgreSQL installed successfully!")
                return True
            else:
                print("❌ Failed to install PostgreSQL.")
                return False
    
    return False

def start_postgres():
    """Start the PostgreSQL service"""
    print("🔄 Starting PostgreSQL service...")
    
    if is_windows():
        run_command("net start postgresql")
    elif is_linux():
        run_command("sudo systemctl start postgresql")
    
    print("✅ PostgreSQL service started!")

def setup_database():
    """Create the database and user with enhanced permissions"""
    print("🔨 Setting up the database with enhanced admin permissions...")
    
    if is_windows():
        # Windows commands - create user first with superuser privileges
        run_command(f'psql -U postgres -c "CREATE ROLE {DB_USER} WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD \'{DB_PASS}\';"')
        # Create database with owner as admin
        run_command(f'psql -U postgres -c "CREATE DATABASE {DB_NAME} OWNER {DB_USER};"')
        # Connect to the database and grant schema permissions
        run_command(f'psql -U postgres -d {DB_NAME} -c "GRANT ALL ON SCHEMA public TO {DB_USER};"')
        run_command(f'psql -U postgres -d {DB_NAME} -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {DB_USER};"')
        run_command(f'psql -U postgres -d {DB_NAME} -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {DB_USER};"')
        run_command(f'psql -U postgres -d {DB_NAME} -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO {DB_USER};"')
    
    elif is_linux():
        # Linux commands using heredoc - create user first with superuser privileges
        user_sql = f"""
CREATE ROLE {DB_USER} WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD '{DB_PASS}';
"""
        # Write SQL to a temporary file
        with open("temp_user_setup.sql", "w") as f:
            f.write(user_sql)
        
        # Execute the SQL file as postgres user
        run_command("sudo -u postgres psql -f temp_user_setup.sql")
        
        # Create database with owner as admin
        db_sql = f"""
CREATE DATABASE {DB_NAME} OWNER {DB_USER};
"""
        with open("temp_db_setup.sql", "w") as f:
            f.write(db_sql)
        
        run_command("sudo -u postgres psql -f temp_db_setup.sql")
        
        # Set additional permissions
        permissions_sql = f"""
GRANT ALL ON SCHEMA public TO {DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO {DB_USER};
"""
        with open("temp_perm_setup.sql", "w") as f:
            f.write(permissions_sql)
        
        run_command(f"sudo -u postgres psql -d {DB_NAME} -f temp_perm_setup.sql")
        
        # Clean up the temporary files
        try:
            os.remove("temp_user_setup.sql")
            os.remove("temp_db_setup.sql")
            os.remove("temp_perm_setup.sql")
        except:
            pass
    
    print("✅ Database and superuser created with enhanced permissions!")

def run_migrations():
    """Run Django migrations"""
    print("🚀 Running Django migrations...")
    
    if is_windows():
        # Check if virtual environment exists
        if os.path.exists("venv\\Scripts\\activate"):
            run_command("venv\\Scripts\\activate && python manage.py migrate")
        else:
            run_command("python manage.py migrate")
    
    elif is_linux():
        # Check if virtual environment exists
        if os.path.exists("venv/bin/activate"):
            run_command("source venv/bin/activate && python manage.py migrate")
        else:
            run_command("python manage.py migrate")
    
    print("✅ Migrations applied successfully!")

def create_superuser():
    """Create a Django superuser"""
    print("🔑 Creating Django superuser...")
    
    superuser_script = "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Superuser already exists')"
    
    if is_windows():
        if os.path.exists("venv\\Scripts\\activate"):
            run_command(f'venv\\Scripts\\activate && python manage.py shell -c "{superuser_script}"')
        else:
            run_command(f'python manage.py shell -c "{superuser_script}"')
    
    elif is_linux():
        if os.path.exists("venv/bin/activate"):
            run_command(f'source venv/bin/activate && python manage.py shell -c "{superuser_script}"')
        else:
            run_command(f'python manage.py shell -c "{superuser_script}"')
    
    print("✅ Superuser created!")

def load_initial_data():
    """Load initial data if available"""
    if os.path.exists("initial_data.json"):
        print("📥 Loading initial data...")
        
        if is_windows():
            if os.path.exists("venv\\Scripts\\activate"):
                run_command("venv\\Scripts\\activate && python manage.py loaddata initial_data.json")
            else:
                run_command("python manage.py loaddata initial_data.json")
        
        elif is_linux():
            if os.path.exists("venv/bin/activate"):
                run_command("source venv/bin/activate && python manage.py loaddata initial_data.json")
            else:
                run_command("python manage.py loaddata initial_data.json")
        
        print("✅ Initial data loaded!")

def main():
    """Main function to execute database setup"""
    print(f"🌐 Setting up database for {'Windows' if is_windows() else 'Linux'} environment")
    
    if not check_postgres():
        print("❌ PostgreSQL check failed. Exiting.")
        sys.exit(1)
    
    start_postgres()
    setup_database()
    run_migrations()
    
    # Ask if user wants to create a superuser
    answer = input("Do you want to create a Django superuser? (y/n): ").lower()
    if answer == 'y' or answer == 'yes':
        create_superuser()
    
    # Check for initial data
    if os.path.exists("initial_data.json"):
        answer = input("Do you want to load initial data? (y/n): ").lower()
        if answer == 'y' or answer == 'yes':
            load_initial_data()
    
    print("🎉 Database setup completed!")

if __name__ == "__main__":
    main()