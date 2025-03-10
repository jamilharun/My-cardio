import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import openai
from .health_api_service import get_nutrition_data

# Check if model already exists
model_path = "main/models/cardio_risk_model.pkl"
feature_names_path = "main/models/feature_names.pkl"

if os.path.exists(model_path) and os.path.exists(feature_names_path):
    print("\n✅ Existing model found. Skipping model training...")
    model = joblib.load(model_path)
    feature_names = joblib.load(feature_names_path)
else:
    # Load Datasets
    print("Loading datasets...")
    df1 = pd.read_csv("main/datasets/cardio_train.csv", sep=";")  # Fix separator issue
    df2 = pd.read_csv("main/datasets/Cardiovascular_Disease_Dataset.csv")  # Default separator is ','

    print("Original columns in Dataset 1:", df1.columns.tolist())
    print("Original columns in Dataset 2:", df2.columns.tolist())

    # Check which columns are available in each dataset
    available_columns_df1 = set(df1.columns)
    available_columns_df2 = set(df2.columns)

    print("\nRenaming columns for consistency...")
    # Rename columns for consistency
    df1 = df1.rename(columns={
        "ap_hi": "BP",  # Systolic BP
        "cholesterol": "cholesterol_level",
        "gluc": "glucose_level",
        "cardio": "heart_disease"
    })

    df2 = df2.rename(columns={
        "restingBP": "BP",
        "serumcholestrol": "cholesterol_level",
        "fastingbloodsugar": "glucose_level",
        "target": "heart_disease"
    })

    print("Dataset 1 Columns after renaming:", df1.columns.tolist())
    print("Dataset 2 Columns after renaming:", df2.columns.tolist())

    # Define common columns that exist in both datasets after renaming
    # First, get the intersection of columns
    common_columns = set(df1.columns).intersection(set(df2.columns))
    print("\nCommon columns in both datasets:", common_columns)

    # Define essential columns we want to include
    target_columns = ["heart_disease"]
    demographic_columns = ["age", "gender"]
    clinical_columns = ["BP", "cholesterol_level", "glucose_level"]

    # Check which lifestyle columns are available in both datasets
    lifestyle_columns = []
    for col in ["smoke", "alco", "active"]:
        if col in common_columns:
            lifestyle_columns.append(col)

    # Check which additional clinical features are available
    additional_clinical = []
    for col in ["chestpain", "restingrelectro", "maxheartrate", "exerciseangia"]:
        if col in common_columns:
            additional_clinical.append(col)

    # Combine all selected columns
    selected_columns = demographic_columns + clinical_columns + lifestyle_columns + additional_clinical + target_columns

    print("\nSelected columns for the final dataset:", selected_columns)

    # Check if selected columns exist in both datasets
    df1_available = [col for col in selected_columns if col in df1.columns]
    df2_available = [col for col in selected_columns if col in df2.columns]

    print("\nColumns available in Dataset 1:", df1_available)
    print("Columns available in Dataset 2:", df2_available)

    # Handle missing columns by creating them with default values
    for col in selected_columns:
        if col not in df1.columns:
            print(f"Creating missing column '{col}' in Dataset 1")
            if col in ["smoke", "alco", "active", "heart_disease"]:
                df1[col] = 0  # Default for binary columns
            elif col in ["chestpain", "restingrelectro", "exerciseangia"]:
                df1[col] = 0  # Default categorical
            elif col == "maxheartrate":
                df1[col] = 120  # Default average heart rate

        if col not in df2.columns:
            print(f"Creating missing column '{col}' in Dataset 2")
            if col in ["smoke", "alco", "active", "heart_disease"]:
                df2[col] = 0  # Default for binary columns
            elif col in ["chestpain", "restingrelectro", "exerciseangia"]:
                df2[col] = 0  # Default categorical
            elif col == "maxheartrate":
                df2[col] = 120  # Default average heart rate

    # Select only the columns we want
    df1_selected = df1[selected_columns]
    df2_selected = df2[selected_columns]

    # Handle data types - ensure consistency
    for col in selected_columns:
        # Convert to the same data type (numeric for most)
        if col != "gender":  # Keep gender as is
            df1_selected[col] = pd.to_numeric(df1_selected[col], errors='coerce')
            df2_selected[col] = pd.to_numeric(df2_selected[col], errors='coerce')

    # Fill missing values
    print("\nFilling missing values...")
    # For numeric columns, fill with mean
    numeric_cols = df1_selected.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        df1_mean = df1_selected[col].mean()
        df2_mean = df2_selected[col].mean()

        df1_selected[col].fillna(df1_mean, inplace=True)
        df2_selected[col].fillna(df2_mean, inplace=True)

    # For categorical columns, fill with mode
    categorical_cols = df1_selected.select_dtypes(exclude=['number']).columns
    for col in categorical_cols:
        df1_mode = df1_selected[col].mode()[0]
        df2_mode = df2_selected[col].mode()[0]

        df1_selected[col].fillna(df1_mode, inplace=True)
        df2_selected[col].fillna(df2_mode, inplace=True)

    # Merge both datasets
    print("\nMerging datasets...")
    final_dataset = pd.concat([df1_selected, df2_selected], ignore_index=True)

    # Save the cleaned dataset
    final_dataset.to_csv("main/datasets/cleaned_cardio_data.csv", index=False)

    print("✅ Final dataset created with", final_dataset.shape[0], "rows and", final_dataset.shape[1], "columns")

    # Train model
    print("\nTraining model...")
    X = final_dataset.drop("heart_disease", axis=1)
    y = final_dataset["heart_disease"]
    
    # Handle remaining categorical variables
    X = pd.get_dummies(X, drop_first=True)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Create and train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate model
    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy: {accuracy:.2f}")
    
    # Save the model
    joblib.dump(model, "main/models/cardio_risk_model.pkl")
    print("✅ Model saved successfully")
    
    # Feature names for prediction
    feature_names = X.columns.tolist()
    joblib.dump(feature_names, "main/models/feature_names.pkl")

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


DEEPSEEK_API_URL = "https://api.deepseek.com/v1" 
DEEPSEEK_API_KEY = "sk-a3827ec6f6584fc48b150e85b6de0e47"

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
    # Prepare the prompt for GPT
    prompt = f"""
    A user has been assessed for cardiovascular risk. The results are:
    - Risk Level: {risk_level}
    - Risk Probability: {risk_probability}
    - User Data: {user_data}

    Provide a detailed explanation of why this risk level was predicted and suggest ways to reduce the risk.
    """

    # Call OpenAI API
    response = openai.ChatCompletion.create(
        model="gpt-4",  # Use GPT-4 or GPT-3.5
        messages=[
            {"role": "system", "content": "You are a helpful health assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300  # Limit the response length
    )

    # Extract the explanation
    explanation = response["choices"][0]["message"]["content"]
    return explanation


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

    return recommendations