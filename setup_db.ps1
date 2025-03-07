$DB_NAME = "mycardiodb"
$DB_USER = "admin"
$DB_PASS = "admin123"

Write-Output "🔄 Checking PostgreSQL service..."
Start-Service -Name postgresql -ErrorAction SilentlyContinue

Write-Output "🔨 Setting up the database..."
psql -U postgres -c "CREATE DATABASE $DB_NAME;"
psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

Write-Output "🚀 Running Django migrations..."
python manage.py migrate

Write-Output "🎉 Database setup completed!"
