import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from openai import OpenAI
from .api_service import get_nutrition_data, get_exercise_data
from dotenv import load_dotenv

load_dotenv()

# Check if model already exists
# Define file paths
model_path = "main/models/cardio_risk_model.pkl"
feature_names_path = "main/models/feature_names.pkl"
data_path = "main/datasets/cardio_train.csv"
cleaned_data_path = "main/datasets/cleaned_cardio_data_V2.csv"

# Check if model exists
if os.path.exists(model_path) and os.path.exists(feature_names_path):
    print("\n✅ Existing model found. Skipping model training...")
    model = joblib.load(model_path)
    feature_names = joblib.load(feature_names_path)
else:
    print("Loading dataset...")
    df = pd.read_csv(data_path, sep=";")  # Fix separator issue

    # Rename columns for consistency
    df = df.rename(columns={
        "ap_hi": "BP",  # Systolic BP
        "cholesterol": "cholesterol_level",
        "gluc": "glucose_level",
        "cardio": "heart_disease"
    })
    
    # Select relevant columns
    selected_columns = [
        "age", "gender", "BP", "cholesterol_level", "glucose_level", "heart_disease"
    ]
    df = df[selected_columns]
    
    # Convert gender to binary
    df["gender"] = df["gender"].map({1: 0, 2: 1})  # 0: Male, 1: Female
    
    # Fill missing values
    df.fillna(df.mean(), inplace=True)
    
    # Save cleaned data
    df.to_csv(cleaned_data_path, index=False)
    print("✅ Cleaned dataset saved.")
    
    # Train model
    print("\nTraining model...")
    X = df.drop("heart_disease", axis=1)
    y = df["heart_disease"]
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train classifier
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate model
    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy: {accuracy:.2f}")
    
    # Save model & features
    joblib.dump(model, model_path)
    joblib.dump(X.columns.tolist(), feature_names_path)
    print("✅ Model saved successfully.")



def predict_health_risk(user_data):
    """
    Predict health risk based on user input
    
    Parameters:
    user_data (dict): Dictionary containing user health data
    
    Returns:
    str: Risk level ("High" or "Low")
    """
    # Load model and feature names
    loaded_model = joblib.load("main/models/cardio_risk_model.pkl")
    feature_names = joblib.load("main/models/feature_names.pkl")
    
    # Prepare input data
    input_df = pd.DataFrame([user_data])
    
    # Handle categorical variables
    input_df = pd.get_dummies(input_df, drop_first=True)
    
    # Ensure all needed columns are present
    for col in feature_names:
        if col not in input_df.columns:
            input_df[col] = 0
    
    # Select only the columns the model was trained on
    input_df = input_df[feature_names]
    
    # Make prediction
    prediction = loaded_model.predict(input_df)
    risk_level = "High" if prediction[0] == 1 else "Low"
    
    # Get prediction probability
    probabilities = loaded_model.predict_proba(input_df)[0]
    risk_probability = probabilities[1]  # Probability of high risk
    
    return {
        "risk_level": risk_level,
        "risk_probability": float(risk_probability)
    }

# Example usage:
if __name__ == "__main__":
    # Example user data
    example_data = {
        "age": 50,
        "gender": "Male",
        "BP": 130,
        "cholesterol_level": 1,
        "glucose_level": 1,
        "smoke": 0,
        "alco": 0,
        "active": 1,
        "chestpain": 1,
        "restingrelectro": 0,
        "maxheartrate": 150,
        "exerciseangia": 0
    }
    
    result = predict_health_risk(example_data)
    print(f"Risk assessment: {result['risk_level']} (Probability: {result['risk_probability']:.2f})")


DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def assess_risk(request):
    if request.method == "POST":
        # Extract user data from the request
        user_data = request.POST.dict()

        # Get the risk prediction from your existing AI model
        risk_result = predict_health_risk(user_data)

        # Prepare data for DeepSeek AI
        explanation = generate_explanation(
            risk_result["risk_level"],
            risk_result["risk_probability"],
            user_data
        )

        return JsonResponse({
            "risk_level": risk_result["risk_level"],
            "risk_probability": risk_result["risk_probability"],
            "explanation": explanation
        })
    else:
        return JsonResponse({"error": "Invalid request method"}, status=400)


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
            stream=False
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