from flask import Flask, render_template, jsonify, request
import requests
import os
from cache_manager import Cache
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Initialize cache
word_cache = Cache()

# Free Dictionary API endpoint
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")
DATAMUSE_API_URL = "https://api.datamuse.com/words"

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
        # Set timeout for all requests (5 seconds)
        timeout = 5
        
        # Define API fetch functions
        def fetch_definition():
            try:
                response = requests.get(f"{DICTIONARY_API_URL}{word}", timeout=timeout)
                return ('definition', response.json() if response.status_code == 200 else None)
            except Exception as e:
                logging.error(f"Error fetching definition: {str(e)}")
                return ('definition', None)
        
        def fetch_synonyms():
            try:
                response = requests.get(
                    DATAMUSE_API_URL,
                    params={"rel_syn": word},
                    timeout=timeout
                )
                return ('synonyms', response.json() if response.status_code == 200 else [])
            except Exception as e:
                logging.error(f"Error fetching synonyms: {str(e)}")
                return ('synonyms', [])
        
        def fetch_antonyms():
            try:
                response = requests.get(
                    DATAMUSE_API_URL,
                    params={"rel_ant": word},
                    timeout=timeout
                )
                return ('antonyms', response.json() if response.status_code == 200 else [])
            except Exception as e:
                logging.error(f"Error fetching antonyms: {str(e)}")
                return ('antonyms', [])
        
        def fetch_images():
            try:
                response = requests.get(
                    UNSPLASH_API_URL,
                    params={
                        "query": word,
                        "per_page": 10,
                        "client_id": UNSPLASH_ACCESS_KEY
                    },
                    timeout=timeout
                )
                if response.status_code != 200:
                    logging.debug(f"Unsplash API error response: {response.text}")
                return ('images', response.json() if response.status_code == 200 else None)
            except Exception as e:
                logging.error(f"Error fetching images: {str(e)}")
                return ('images', None)
        
        # Execute all API calls concurrently
        results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(fetch_definition),
                executor.submit(fetch_synonyms),
                executor.submit(fetch_antonyms),
                executor.submit(fetch_images)
            ]
            
            for future in as_completed(futures):
                key, data = future.result()
                results[key] = data
        
        dict_data = results.get('definition')
        synonyms_data = results.get('synonyms', [])
        antonyms_data = results.get('antonyms', [])
        image_data = results.get('images')

        result = {
            "definition": dict_data[0] if dict_data else None,
            "synonyms": synonyms_data,
            "antonyms": antonyms_data,
            "images": [img["urls"]["regular"] for img in image_data["results"][:10]] if image_data and "results" in image_data else []  # Ensure we only use first 10 images
        }

        # Cache the result
        word_cache.set(word, result)
        return jsonify(result)

    except requests.Timeout:
        logging.error(f"Timeout fetching word info for: {word}")
        return jsonify({"error": "Request timed out. Please try again."}), 504
    except Exception as e:
        logging.error(f"Error fetching word info: {str(e)}")
        return jsonify({"error": "Failed to fetch word information"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)