import pandas as pd
import numpy as np
import joblib
import os
import logging
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score
from openai import OpenAI
from .api_service import get_nutrition_data, get_exercise_data
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define file paths
model_dir = "main/models"
model_path = f"{model_dir}/cardio_risk_model.pkl"
data_path = "main/datasets/health_risk_training_data.csv"
cleaned_data_path = "main/datasets/cleaned_health_risk_data.csv"

# Create model directory if it doesn't exist
if not os.path.exists(model_dir):
    os.makedirs(model_dir)
    print(f"Created directory: {model_dir}")

# Try to create a multivariate risk score instead of just predicting chest pain
def create_risk_score(df):
    """
    Create a comprehensive risk score based on multiple factors
    """
    # Initialize risk score column
    df['Risk_Score'] = 0
    
    # Age factor (higher age = higher risk)
    df.loc[df['Age'] > 50, 'Risk_Score'] += 1
    df.loc[df['Age'] > 65, 'Risk_Score'] += 1
    
    # Blood pressure factor
    df.loc[df['Blood Pressure (Systolic)'] > 140, 'Risk_Score'] += 1
    df.loc[df['Blood Pressure (Systolic)'] > 160, 'Risk_Score'] += 1
    
    # Cholesterol factor
    df.loc[df['Cholesterol Level'] > 0, 'Risk_Score'] += 1  # Above normal
    df.loc[df['Cholesterol Level'] > 1, 'Risk_Score'] += 1  # Well above normal
    
    # Glucose factor
    df.loc[df['Glucose Level'] > 0, 'Risk_Score'] += 1  # Above normal
    df.loc[df['Glucose Level'] > 1, 'Risk_Score'] += 1  # Well above normal
    
    # Smoking factor
    df.loc[df['Smoke'] == 1, 'Risk_Score'] += 1
    df.loc[(df['Smoke'] == 1) & (df['Smoke Frequency'] == 'often'), 'Risk_Score'] += 1
    
    # Exercise factor (negative - reduces risk)
    df.loc[df['Physically Active'] == 1, 'Risk_Score'] -= 1
    
    # Chest pain is a strong direct indicator
    df.loc[df['Chest Pain'] == 1, 'Risk_Score'] += 2
    
    # ECG results
    df.loc[df['Resting ECG Results'] > 0, 'Risk_Score'] += 1
    
    # Exercise angina
    df.loc[df['Exercise-induced Angina'] == 1, 'Risk_Score'] += 1
    
    # BMI factor
    if 'BMI' in df.columns:
        df.loc[df['BMI'] > 30, 'Risk_Score'] += 1
        df.loc[df['BMI'] > 35, 'Risk_Score'] += 1
    
    # Convert to binary target (high risk vs low risk)
    # Adjust threshold based on distribution of scores
    threshold = df['Risk_Score'].median()  # Using median as threshold
    df['High_Risk'] = (df['Risk_Score'] > threshold).astype(int)
    
    return df

# Create interaction features
def create_interaction_features(df):
    """
    Create interaction features that might have predictive power
    """
    # Age and cholesterol interaction
    df['Age_Chol'] = df['Age'] * df['Cholesterol Level']
    
    # Age and blood pressure interaction
    df['Age_BP'] = df['Age'] * df['Blood Pressure (Systolic)'] / 100
    
    # BMI and blood pressure interaction (if BMI exists)
    if 'BMI' in df.columns:
        df['BMI_BP'] = df['BMI'] * df['Blood Pressure (Systolic)'] / 100
    
    # Smoking and age interaction
    df['Smoke_Age'] = df['Smoke'] * df['Age']
    
    # Physical activity and age
    df['Active_Age'] = df['Physically Active'] * df['Age']
    
    # Blood pressure and cholesterol
    df['BP_Chol'] = df['Blood Pressure (Systolic)'] * (df['Cholesterol Level'] + 1) / 100
    
    return df

# Check if model file exists
if os.path.exists(model_path):
    print(f"Model already exists at {model_path}. Skipping training.")
else:
    print("No existing model found. Starting training process...")
    print("Loading dataset...")
    try:
        df = pd.read_csv(data_path)
        
        # Data cleaning and preprocessing
        print("Preprocessing data...")
        
        # Remove duplicates
        initial_rows = len(df)
        df = df.drop_duplicates()
        if initial_rows > len(df):
            print(f"Removed {initial_rows - len(df)} duplicate rows")
        
        # Handle missing values
        df['Smoke Frequency'] = df['Smoke Frequency'].fillna('None')
        df['Alcohol Frequency'] = df['Alcohol Frequency'].fillna('None')
        df['Workout Frequency'] = df['Workout Frequency'].fillna(0)
        
        # Convert categorical to numeric
        freq_map = {"often": 2, "seldom": 1, "occasional": 1, "None": 0, None: 0}
        df['Smoke Frequency'] = df['Smoke Frequency'].map(lambda x: freq_map.get(x, 0))
        df['Alcohol Frequency'] = df['Alcohol Frequency'].map(lambda x: freq_map.get(x, 0))
        
        # Convert gender to numeric
        df['Gender'] = df['Gender'].map({"Male": 0, "Female": 1})
        
        # Calculate BMI
        df['BMI'] = df['Weight (kg)'] / ((df['Height (cm)'] / 100) ** 2)
        
        # Create interaction features
        df = create_interaction_features(df)
        
        # Create risk score
        df = create_risk_score(df)
        
        # Save cleaned and enhanced dataset
        df.to_csv(cleaned_data_path, index=False)
        print("✅ Cleaned dataset saved with new features")
        
        # Define features and target (using the new high risk target)
        X = df.drop(['Chest Pain', 'Risk_Score', 'High_Risk'], axis=1, errors='ignore')
        y = df['High_Risk']  # Using the new target instead of Chest Pain
        
        # Try different algorithms to see which works best
        print("Evaluating different models...")
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        
        # Define preprocessing pipeline
        numeric_features = X.select_dtypes(include=['int64', 'float64']).columns.tolist()
        categorical_features = X.select_dtypes(include=['object']).columns.tolist()
        
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('cat', categorical_transformer, categorical_features if categorical_features else [])
            ])
        
        # Try different classifiers
        classifiers = {
            'Random Forest': RandomForestClassifier(n_estimators=200, random_state=42),
            'Gradient Boosting': GradientBoostingClassifier(random_state=42),
            'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
            'SVM': SVC(probability=True, random_state=42)
        }
        
        best_auc = 0
        best_model_name = None
        best_pipeline = None
        
        for name, classifier in classifiers.items():
            # Create pipeline with preprocessor and classifier
            pipeline = Pipeline(steps=[
                ('preprocessor', preprocessor),
                ('classifier', classifier)
            ])
            
            # Fit the pipeline
            pipeline.fit(X_train, y_train)
            
            # Get predictions
            y_pred = pipeline.predict(X_test)
            y_prob = pipeline.predict_proba(X_test)[:, 1]
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            auc = roc_auc_score(y_test, y_prob)
            
            # Print results
            print(f"{name}:")
            print(f"  Accuracy: {accuracy:.4f}")
            print(f"  AUC: {auc:.4f}")
            print(classification_report(y_test, y_pred))
            print(confusion_matrix(y_test, y_pred))
            print()
            
            # Keep track of best model
            if auc > best_auc:
                best_auc = auc
                best_model_name = name
                best_pipeline = pipeline
        
        print(f"Best model: {best_model_name} with AUC of {best_auc:.4f}")
        
        # Save the best model
        joblib.dump(best_pipeline, model_path)
        print(f"✅ Best model ({best_model_name}) saved successfully")
        
        # Feature importance (for tree-based models)
        if hasattr(best_pipeline.named_steps['classifier'], 'feature_importances_'):
            print("\nFeature Importances:")
            
            # Get feature names after preprocessing
            if categorical_features:
                # For pipelines with both numerical and categorical features
                cat_features = best_pipeline.named_steps['preprocessor'].transformers_[1][1][-1].get_feature_names_out(categorical_features)
                feature_names = np.array(numeric_features + list(cat_features))
            else:
                # For pipelines with only numerical features
                feature_names = np.array(numeric_features)
            
            importances = best_pipeline.named_steps['classifier'].feature_importances_
            indices = np.argsort(importances)[::-1]
            
            for i in range(min(20, len(feature_names))):
                if i < len(indices) and indices[i] < len(feature_names):
                    print(f"{i+1}. {feature_names[indices[i]]} ({importances[indices[i]]:.4f})")
        
    except Exception as e:
        print(f"Error during model training: {str(e)}")
        logger.error(f"Training error: {str(e)}", exc_info=True)
        raise

def convert_form_data_to_model_format(form_data):
    # Create a copy of the form data
    model_data = form_data.copy()
    
    # Convert gender to numeric (0 for Male, 1 for Female)
    model_data["Gender"] = 0 if model_data.get("gender") == "Male" else 1
    
    # Calculate BMI if height and weight are provided
    if model_data.get("height") and model_data.get("weight"):
        height_m = float(model_data["height"]) / 100
        weight_kg = float(model_data["weight"])
        model_data["BMI"] = weight_kg / (height_m ** 2)
    
    # Map frequency values to numeric
    freq_map = {"often": 2, "seldom": 1, "occasional": 1, "None": 0, None: 0}
    model_data["Smoke Frequency"] = freq_map.get(model_data.get("smoke_frequency"), 0)
    model_data["Alcohol Frequency"] = freq_map.get(model_data.get("alco_frequency"), 0)
    
    # Create interaction features
    if model_data.get("age") and model_data.get("cholesterol_level"):
        model_data["Age_Chol"] = model_data["age"] * int(model_data["cholesterol_level"])
    
    if model_data.get("age") and model_data.get("BP"):
        model_data["Age_BP"] = model_data["age"] * int(model_data["BP"]) / 100
    
    if model_data.get("BMI") and model_data.get("BP"):
        model_data["BMI_BP"] = model_data["BMI"] * int(model_data["BP"]) / 100
    
    if model_data.get("smoke") and model_data.get("age"):
        model_data["Smoke_Age"] = int(model_data["smoke"]) * model_data["age"]
    
    if model_data.get("active") and model_data.get("age"):
        model_data["Active_Age"] = int(model_data["active"]) * model_data["age"]
    
    if model_data.get("BP") and model_data.get("cholesterol_level"):
        model_data["BP_Chol"] = int(model_data["BP"]) * (int(model_data["cholesterol_level"]) + 1) / 100
    
    # Rename fields to match model expectations
    field_mappings = {
        "age": "Age",
        "height": "Height (cm)",
        "weight": "Weight (kg)",
        "BP": "Blood Pressure (Systolic)",
        "cholesterol_level": "Cholesterol Level",
        "glucose_level": "Glucose Level",
        "smoke": "Smoke",
        "alco": "Alcohol",
        "active": "Physically Active",
        "chestpain": "Chest Pain",
        "restingrelectro": "Resting ECG Results",
        "maxheartrate": "Max Heart Rate",
        "exerciseangia": "Exercise-induced Angina",
        "workout_frequency": "Workout Frequency"
    }
    
    for form_key, model_key in field_mappings.items():
        if form_key in model_data:
            model_data[model_key] = model_data[form_key]
            if form_key != model_key:
                del model_data[form_key]
    
    # Ensure all required columns are present
    required_columns = [
        'Age', 'Gender', 'Height (cm)', 'Weight (kg)', 'Blood Pressure (Systolic)',
        'Cholesterol Level', 'Glucose Level', 'Smoke', 'Smoke Frequency', 'Alcohol',
        'Alcohol Frequency', 'Physically Active', 'Chest Pain', 'Resting ECG Results',
        'Max Heart Rate', 'Exercise-induced Angina', 'Workout Frequency', 'BMI',
        'Age_Chol', 'Age_BP', 'BMI_BP', 'Smoke_Age', 'Active_Age', 'BP_Chol'
    ]
    
    # Add any missing columns with default values
    for col in required_columns:
        if col not in model_data:
            model_data[col] = 0  # Default value for missing columns
    
    return model_data


def prepare_data_for_prediction(user_data):
    """
    Prepare user data for prediction by the model
    
    Parameters:
    user_data (dict): Dictionary containing user health data
    
    Returns:
    dict: Processed data ready for model prediction
    """
    processed_data = user_data.copy()
    
    # Convert gender to numeric
    if 'gender' in processed_data:
        processed_data['Gender'] = 1 if processed_data['gender'] == 'Female' else 0
        del processed_data['gender']
    
    # Calculate BMI
    if 'height' in processed_data and 'weight' in processed_data:
        height_m = float(processed_data['height']) / 100
        weight_kg = float(processed_data['weight'])
        processed_data['BMI'] = weight_kg / (height_m ** 2)
    
    # Create the same interaction features used in training
    # Age and cholesterol interaction
    if 'age' in processed_data and 'cholesterol_level' in processed_data:
        processed_data['Age_Chol'] = processed_data['age'] * float(processed_data['cholesterol_level'])
    
    # Age and blood pressure interaction
    if 'age' in processed_data and 'BP' in processed_data:
        processed_data['Age_BP'] = processed_data['age'] * float(processed_data['BP']) / 100
    
    # BMI and blood pressure interaction
    if 'BMI' in processed_data and 'BP' in processed_data:
        processed_data['BMI_BP'] = processed_data['BMI'] * float(processed_data['BP']) / 100
    
    # Smoking and age interaction
    if 'smoke' in processed_data and 'age' in processed_data:
        processed_data['Smoke_Age'] = int(processed_data['smoke']) * processed_data['age']
    
    # Physical activity and age
    if 'active' in processed_data and 'age' in processed_data:
        processed_data['Active_Age'] = int(processed_data['active']) * processed_data['age']
    
    # Blood pressure and cholesterol
    if 'BP' in processed_data and 'cholesterol_level' in processed_data:
        processed_data['BP_Chol'] = float(processed_data['BP']) * (float(processed_data['cholesterol_level']) + 1) / 100
    
    # Map frequency values
    freq_map = {"often": 2, "seldom": 1, "occasional": 1, None: 0}
    
    if 'smoke_frequency' in processed_data:
        processed_data['Smoke Frequency'] = freq_map.get(processed_data['smoke_frequency'], 0)
        del processed_data['smoke_frequency']
    
    if 'alco_frequency' in processed_data:
        processed_data['Alcohol Frequency'] = freq_map.get(processed_data['alco_frequency'], 0)
        del processed_data['alco_frequency']
    
    # Rename fields to match training data
    field_mappings = {
        'age': 'Age',
        'height': 'Height (cm)',
        'weight': 'Weight (kg)',
        'BP': 'Blood Pressure (Systolic)',
        'cholesterol_level': 'Cholesterol Level',
        'glucose_level': 'Glucose Level',
        'smoke': 'Smoke',
        'alco': 'Alcohol',
        'active': 'Physically Active',
        'chestpain': 'Chest Pain',
        'restingrelectro': 'Resting ECG Results',
        'maxheartrate': 'Max Heart Rate',
        'exerciseangia': 'Exercise-induced Angina',
        'workout_frequency': 'Workout Frequency'
    }
    
    for form_key, model_key in field_mappings.items():
        if form_key in processed_data:
            processed_data[model_key] = processed_data[form_key]
            if form_key != model_key:
                del processed_data[form_key]
    
    return processed_data

def predict_health_risk(user_data):
    """
    Predict health risk based on user input
    
    Parameters:
    user_data (dict): Dictionary containing user health data
    
    Returns:
    dict: Risk level and probability
    """
    try:
        # Prepare data
        processed_data = prepare_data_for_prediction(user_data)
        
        # Load the model
        model = joblib.load(model_path)
        
        # Create DataFrame
        input_df = pd.DataFrame([processed_data])
        
        # Make prediction
        prediction_proba = model.predict_proba(input_df)
        risk_probability = prediction_proba[0][1]  # Probability of high risk
        risk_level = "High" if risk_probability > 0.5 else "Low"
        
        # Calculate a risk score (0-100) for better interpretability
        risk_score = int(risk_probability * 100)
        
        return {
            "risk_level": risk_level,
            "risk_probability": float(risk_probability),
            "risk_score": risk_score
        }
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}", exc_info=True)
        # Return a default response in case of error
        return {
            "risk_level": "Unknown",
            "risk_probability": 0.5,
            "risk_score": 50,
            "error": str(e)
        }

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def generate_explanation(risk_level, risk_probability, user_data):
    print("run DEEP SEEK AI ")
    # Prepare the prompt for GPT
    prompt = f"""
    A user has been assessed for cardiovascular risk. The results are:
    - Risk Level: {risk_level}
    - Risk Probability: {risk_probability}
    - User Data: {user_data}

    Provide a detailed explanation of why this risk level was predicted and suggest ways to reduce the risk.
    """

    # Call OpenAI API

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_API_URL
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            max_tokens=2000        
        )

        # Extract the explanation
        explanation = response["choices"][0]["message"]["content"]
        return explanation
    except Exception as e:
        # Handle API errors (e.g., quota exceeded, network issues)
        print(f"Error generating explanation: {e}")

        # Fallback explanation
        fallback_explanation = (
            f"Your risk level is {risk_level} with a probability of {risk_probability:.2f}. "
            "This indicates a potential cardiovascular risk. To reduce your risk, consider adopting a healthy lifestyle, "
            "including a balanced diet, regular exercise, and regular health checkups. "
            "For personalized advice, consult a healthcare professional."
        )
        return fallback_explanation

def generate_health_report(user_data, risk_result):
    """
    Generate a personalized health report based on assessment results.
    
    Parameters:
    - user_data: Dictionary containing user input (age, gender, BP, etc.).
    - risk_result: Dictionary containing risk level and probability.
    
    Returns:
    - Dictionary containing the report details.
    """
    report = {
        "user_info": {
            "age": user_data["age"],
            "gender": "Male" if user_data["gender"] == 1 else "Female",
        },
        "assessment_summary": {
            "blood_pressure": user_data["BP"],
            "cholesterol_level": user_data["cholesterol_level"],
            "glucose_level": user_data["glucose_level"],
        },
        "risk_level": risk_result["risk_level"],
        "risk_probability": risk_result["risk_probability"],
        "explanation": risk_result.get("explanation", "No explanation available."),
        "recommendations": generate_recommendations(user_data, risk_result),
    }
    return report

def generate_recommendations(user_data, risk_level):
    """
    Generate personalized health recommendations based on risk level and user data.
    
    Parameters:
    - user_data: Dictionary containing user health metrics (e.g., age, BP, cholesterol, glucose).
    - risk_level: String indicating the risk level ("High", "Medium", "Low").
    
    Returns:
    - List of recommendations.
    """
    recommendations = []

    # Convert numeric fields to integers or floats
    try:
        cholesterol_level = int(user_data.get("cholesterol_level", 0))
        blood_pressure = int(user_data.get("BP", 0))
        glucose_level = int(user_data.get("glucose_level", 0))
    except (ValueError, TypeError):
        # Handle cases where conversion fails (e.g., invalid input)
        cholesterol_level = 0
        blood_pressure = 0
        glucose_level = 0

    # General recommendations based on risk level
    if risk_level == "High":
        recommendations.append("Consult a healthcare professional immediately.")
        recommendations.append("Adopt a low-sodium, low-fat diet.")
        recommendations.append("Engage in regular physical activity (e.g., 30 minutes of exercise daily).")
        recommendations.append("Monitor blood pressure and cholesterol levels regularly.")
    elif risk_level == "Medium":
        recommendations.append("Monitor your health regularly and consider preventive measures.")
        recommendations.append("Reduce intake of high-cholesterol and high-sugar foods.")
        recommendations.append("Increase physical activity (e.g., walking 20-30 minutes daily).")
        recommendations.append("Consider stress management techniques (e.g., meditation, yoga).")
    else:
        recommendations.append("Maintain a healthy lifestyle to keep your risk low.")
        recommendations.append("Eat a balanced diet rich in fruits, vegetables, and whole grains.")
        recommendations.append("Exercise regularly (e.g., 150 minutes of moderate activity per week).")
        recommendations.append("Avoid smoking and limit alcohol consumption.")

    # Specific recommendations based on user data
    if blood_pressure > 140:
        recommendations.append("Your blood pressure is high. Consider reducing salt intake and exercising regularly.")
    if cholesterol_level > 200:
        recommendations.append("Your cholesterol level is high. Consider a diet low in saturated fats.")
    if glucose_level > 126:
        recommendations.append("Your glucose level is high. Monitor your sugar intake and consider consulting a doctor.")

    # Add nutrition recommendations using Nutritionix API
    if risk_level in ["High", "Medium"]:
        food_query = "low-sodium low-fat foods"
        nutrition_data = get_nutrition_data(food_query)
        if nutrition_data:
            recommendations.append("Here are some low-sodium, low-fat food options:")
            for food in nutrition_data.get("foods", [])[:3]:  # Show top 3 results
                recommendations.append(f"- {food['food_name']} ({food['nf_calories']} calories)")
                
        exercises = get_exercise_data(body_part="cardio", equipment="body weight", limit=3)
        if exercises:
            recommendations.append("Here are some recommended exercises:")
            for exercise in exercises:
                recommendations.append(f"- {exercise['name']} (Targets: {exercise['bodyPart']}, Equipment: {exercise['equipment']})")

    return recommendations