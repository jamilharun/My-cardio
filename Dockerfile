# Use official Python image
FROM python:3.11

# Install Node.js & npm
RUN apt-get update 

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Collect static files (optional)
RUN python manage.py collectstatic --noinput

# Expose Django's port
EXPOSE 8000

# Start the Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
