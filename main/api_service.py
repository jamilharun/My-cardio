import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NUTRITIONIX_API_KEY = os.getenv("NUTRITIONIX_API_KEY")
NUTRITIONIX_APP_ID = os.getenv("NUTRITIONIX_APP_ID")
NUTRITIONIX_API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

def get_nutrition_data(food_query):
    """
    Get nutrition data for a food item using the Nutritionix API.
    
    Parameters:
    - food_query: String describing the food item (e.g., "1 large apple").
    
    Returns:
    - Dictionary containing nutrition data.
    """
    headers = {
        "x-app-id": NUTRITIONIX_APP_ID,
        "x-app-key": NUTRITIONIX_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "query": food_query
    }
    
    try:
        response = requests.post(NUTRITIONIX_API_URL,  headers=headers, json=data)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching nutrition data: {e}")
        return None


# ExerciseDB API credentials
EXERCISEDB_API_KEY = os.getenv("EXERCISEDB_API_KEY")
EXERCISEDB_API_HOST = "exercisedb.p.rapidapi.com"
EXERCISEDB_API_URL = os.getenv("EXERCISEDB_API_URL")

def get_exercise_data(body_part=None, equipment=None, limit=5):
    """
    Fetch exercise data from the ExerciseDB API.
    
    Parameters:
    - body_part: String specifying the body part to target (e.g., "chest", "back").
    - equipment: String specifying the equipment to use (e.g., "body weight", "dumbbell").
    - limit: Integer specifying the maximum number of exercises to fetch.
    
    Returns:
    - List of exercises.
    """
    headers = {
        "X-RapidAPI-Key": EXERCISEDB_API_KEY,
        "X-RapidAPI-Host": EXERCISEDB_API_HOST
    }
    params = {}
    
    if body_part:
        params["bodyPart"] = body_part
    if equipment:
        params["equipment"] = equipment
    
    try:
        response = requests.get(EXERCISEDB_API_URL, headers=headers, params=params)
        response.raise_for_status()  # Raise an error for bad status codes
        exercises = response.json()
        return exercises[:limit]  # Return only the specified number of exercises
    except requests.exceptions.RequestException as e:
        print(f"Error fetching exercise data: {e}")
        return None