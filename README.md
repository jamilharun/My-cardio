pip freeze > requirements.txt

pip install -r requirments.txt

execute the script
./setup_db.sh

for windows
Set-ExecutionPolicy Unrestricted -Scope Process
.\setup_db.ps1


for crossplatform
Make it executable on Linux: 
chmod +x setup_db.py

Run it with: python setup_db.py (Windows) or ./setup_db.py (Linux)


Activate the virtual environment:
source venv/bin/activate


Start your website:
python manage.py runserver


Watch for Tailwind changes:
npx tailwindcss -i ./static/css/main.css -o ./static/css/output.css --watch

get file tree and ignore ....
tree -I "venv|__pycache__|*.pyc|*.pyo|*.pyd|node_modules|.git"
