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
how to access database in arch linuc
psql -U admin -d mycardiodb -h localhost



### **📌 Summary of the Manuscript: "Web-Based Health Risk Assessment Tool with Decision Tree Model"**  

This study presents a **Web-Based Health Risk Assessment Tool** that uses an **AI Decision Tree Model** to evaluate **chronic disease risks** (such as diabetes and cardiovascular diseases) based on **user-provided health data**. The system is designed to provide **personalized health risk reports** and **preventive healthcare recommendations**, improving accessibility to medical assessments through **telemedicine and digital health technologies**.  

---

### **🔹 Key Objectives of the System**  
1. **Develop a Web-Based Health Risk Assessment Tool** for evaluating **health risks** based on user input.  
2. **Integrate an AI-powered Decision Tree Model** to analyze user data and generate accurate **risk predictions**.  
3. **Provide personalized health reports** and **preventive recommendations** to help users take proactive steps in managing their health.  
4. **Improve accessibility** to preventive healthcare, reducing hospital visits and promoting self-monitoring.  

---

### **🔹 Features You Need to Add to Your Web App**  
To fully implement the system as described in the manuscript, your Django web app should have the following features:  

### **1️⃣ User Authentication & Profile Management**  
🔹 **User Registration & Login** (via Django's authentication system)  
🔹 **User Dashboard** to track personal health history  
🔹 **Roles & Permissions:** Different access levels for **patients, doctors, and administrators**  

---

### **2️⃣ Health Risk Assessment Module**  
🔹 **User Input Form** for collecting health-related data (e.g., age, medical history, lifestyle factors, BMI, activity levels)  
🔹 **AI Decision Tree Model** (implemented using **Scikit-Learn**) for evaluating **risk levels of chronic diseases**  
🔹 **Risk Categorization** (e.g., **Low, Medium, High**) based on decision tree predictions  

---

### **3️⃣ Health Report Generation & Visualization**  
🔹 **Generate Personalized Health Reports** based on risk assessment results  
🔹 **Interactive Data Visualization** (e.g., Charts, Graphs via Chart.js or Plotly)  
🔹 **Export Reports to PDF** for easy sharing with doctors  

---

### **4️⃣ Preventive Health Recommendations**  
🔹 Provide **customized health advice** based on risk scores  
🔹 Suggest **lifestyle improvements** (e.g., diet plans, exercise routines)  
🔹 Integrate with **external health APIs** (e.g., WHO guidelines, Mayo Clinic) for more reliable recommendations  

---

### **5️⃣ Doctor & Admin Dashboard**  
🔹 **Doctors can view patient health records & analytics**  
🔹 **Admin dashboard** for managing users and overseeing system usage  

---

### **6️⃣ Secure Data Storage & Privacy**  
🔹 Use **PostgreSQL** to store user health data  
🔹 Implement **Data Encryption** (e.g., Django’s `cryptography` module)  
🔹 Ensure **compliance with data privacy regulations** (e.g., HIPAA, GDPR)  

---

### **7️⃣ Mobile & Web Responsiveness**  
🔹 Ensure **mobile-friendly design** (using Tailwind CSS & Django templates)  
🔹 Make the system accessible across **PCs, tablets, and smartphones**  

---

### **8️⃣ Telemedicine & Consultation Features (Optional)**  
🔹 Implement a **Video Consultation Module** (using WebRTC or Twilio)  
🔹 Enable **chat/messaging with doctors** for further advice  

---

### **🔹 Next Steps & Development Approach**  
🚀 **1. Set up Django Project**  
🚀 **2. Implement User Authentication**  
🚀 **3. Develop Health Risk Assessment Model** using Decision Trees  
🚀 **4. Build the Health Report & Recommendation System**  
🚀 **5. Ensure Data Security & Privacy Compliance**  
🚀 **6. Deploy the Web App** (AWS, DigitalOcean, or Heroku)  

---

### **💡 Final Thoughts**
This project is an **innovative and valuable tool** for preventive healthcare. By integrating **AI-driven risk assessment, personalized health insights, and a secure web platform**, you can **improve health awareness and reduce hospital visits**. 🚀  

🔥 Let me know if you need **help coding specific features!** 😊
