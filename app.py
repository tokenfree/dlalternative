from flask import Flask, render_template, jsonify, request
import requests
import os
from cache_manager import Cache
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Initialize cache
word_cache = Cache()

# Free Dictionary API endpoint
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/word/<word>')
def get_word_info(word):
    # Check cache first
    cached_result = word_cache.get(word)
    if cached_result:
        return jsonify(cached_result)

    try:
        # Get definition
        dict_response = requests.get(f"{DICTIONARY_API_URL}{word}")
        dict_data = dict_response.json() if dict_response.status_code == 200 else None

        # Get images
        image_response = requests.get(
            UNSPLASH_API_URL,
            params={
                "query": word,
                "per_page": 10,  # Ensure we only request 10 images
                "client_id": UNSPLASH_ACCESS_KEY
            }
        )
        image_data = image_response.json() if image_response.status_code == 200 else None

        # Log the image response for debugging
        logging.debug(f"Unsplash API response status: {image_response.status_code}")
        if image_response.status_code != 200:
            logging.debug(f"Unsplash API error response: {image_response.text}")

        result = {
            "definition": dict_data[0] if dict_data else None,
            "images": [img["urls"]["regular"] for img in image_data["results"][:10]] if image_data and "results" in image_data else []  # Ensure we only use first 10 images
        }

        # Cache the result
        word_cache.set(word, result)
        return jsonify(result)

    except Exception as e:
        logging.error(f"Error fetching word info: {str(e)}")
        return jsonify({"error": "Failed to fetch word information"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)