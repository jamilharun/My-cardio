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
        response = requests.post(NUTRITIONIX_API_URL, headers=headers, json=data)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching nutrition data: {e}")
        return None