import os
from dotenv import load_dotenv
from google import genai

# 1. This secretly loads your GEMINI_API_KEY from the .env file
load_dotenv()

# 2. Initialize the Gemini client
client = genai.Client()

# 3. The Core Function
def generate_vibe_check(gender, building, floor, reviews):
    """
    Takes a list of review strings and returns a brutally honest 2-sentence summary.
    Returns None if no reviews exist (Stripe NULL requirement).
    """
    if not reviews:
        return None

    # Combine all reviews into one string separated by pipes
    combined_text = " | ".join(reviews)

    # The Prompt Engineering
    prompt = f"""
    You are the 'Litterboxd' AI Critic. Summarize the state of the {gender} restroom 
    in {building}, Floor {floor} based on these student reviews:
    
    "{combined_text}"
    
    Rules:
    1. Focus on specific issues (e.g., 'no soap', 'sink pressure') first.
    2. Incorporate the general 'vibe' from informal comments like 'ew' or 'gross'.
    3. Output exactly 2 sentences. Be brutally honest and slightly witty.
    """

    # Call the Gemini 2.5 Flash model
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    return response.text

# --- TESTING BLOCK ---
if __name__ == "__main__":
    print("Testing Litterboxd AI Service...")
    
    # Fake student reviews to test our prompt
    mock_reviews = [
        "ew gross", 
        "no paper towels again", 
        "smells like old gym socks", 
        "sink pressure is basically a pressure washer"
    ]
    
    summary = generate_vibe_check("Men's", "Siebel Center", "1", mock_reviews)
    
    print("\n--- AI VIBE CHECK ---")
    print(summary)
    print("---------------------\n")