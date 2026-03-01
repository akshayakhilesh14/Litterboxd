import os
from dotenv import load_dotenv
from google import genai

# 1. This secretly loads your GEMINI_API_KEY from the .env file
load_dotenv()

# 2. Lazy client so app can start without GEMINI_API_KEY (e.g. to test UI only)
_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Add it to .env to use vibe-check.")
        _client = genai.Client(api_key=api_key)
    return _client

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
    gender = gender.replace("Sombr", "Men's").replace("Gracie Abrams", "Women's")

    # The Prompt Engineering
    prompt = f"""
    Summarize the state of the {gender} restroom in {building}, Floor {floor} based on these student reviews:
    
    "{combined_text}"
    
    Rules:
    1. Focus on specific issues mentioned (e.g., 'lack of soap', 'weak water pressure').
    2. Keep the tone objective, direct, and factual. DO NOT give advice to the user (e.g., never say "bring your own soap" or "you should").
    3. DO NOT be overly dramatic. Ban advanced vocabulary and extreme metaphors. Keep it grounded and simple.
    4. Output exactly 2 sentences.
    """

    # Call the Gemini 2.5 Flash model
    client = _get_client()
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
