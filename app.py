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

# Dictionary API endpoints (all free, no API key required)
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
DATAMUSE_API_URL = "https://api.datamuse.com/words"
LINGUEE_API_URL = "https://linguee-api.fly.dev/api/v2/translations"
PIXABAY_API_URL = "https://pixabay.com/api/"
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")

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
            """Fetch definition with fallback to multiple free dictionary APIs"""
            # Try primary API: Free Dictionary API
            try:
                response = requests.get(f"{DICTIONARY_API_URL}{word}", timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    if data:  # Ensure we have data
                        logging.info(f"Definition found for '{word}' in Free Dictionary API")
                        return ('definition', data)
            except Exception as e:
                logging.error(f"Free Dictionary API error: {str(e)}")
            
            # Fallback 1: Use Datamuse API for definitions
            try:
                response = requests.get(
                    DATAMUSE_API_URL,
                    params={"sp": word, "md": "d", "max": 1},
                    timeout=timeout
                )
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0 and "defs" in data[0]:
                        # Convert Datamuse format to our format
                        defs = data[0]["defs"]
                        meanings = {}
                        for def_str in defs:
                            parts = def_str.split("\t", 1)
                            pos = parts[0] if len(parts) > 1 else "unknown"
                            definition = parts[1] if len(parts) > 1 else parts[0]
                            if pos not in meanings:
                                meanings[pos] = []
                            meanings[pos].append({"definition": definition})
                        
                        converted = [{
                            "word": word,
                            "phonetic": "",
                            "meanings": [{
                                "partOfSpeech": pos,
                                "definitions": defs
                            } for pos, defs in meanings.items()]
                        }]
                        logging.info(f"Definition found for '{word}' in Datamuse API")
                        return ('definition', converted)
            except Exception as e:
                logging.error(f"Datamuse API error: {str(e)}")
            
            # Fallback 2: Try Linguee API (English dictionary)
            try:
                response = requests.get(
                    LINGUEE_API_URL,
                    params={"query": word, "src": "en", "dst": "en"},
                    timeout=timeout
                )
                if response.status_code == 200:
                    data = response.json()
                    if data and "translations" in data and len(data["translations"]) > 0:
                        # Convert Linguee format to our format
                        trans = data["translations"][0]
                        converted = [{
                            "word": word,
                            "phonetic": "",
                            "meanings": [{
                                "partOfSpeech": trans.get("pos", "unknown"),
                                "definitions": [{
                                    "definition": trans.get("text", "")
                                }]
                            }]
                        }]
                        logging.info(f"Definition found for '{word}' in Linguee API")
                        return ('definition', converted)
            except Exception as e:
                logging.error(f"Linguee API error: {str(e)}")
            
            logging.warning(f"No definition found for '{word}' in any API")
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
                    PIXABAY_API_URL,
                    params={
                        "key": PIXABAY_API_KEY,
                        "q": word,
                        "per_page": 10,
                        "image_type": "photo"
                    },
                    timeout=timeout
                )
                if response.status_code != 200:
                    logging.debug(f"Pixabay API error response: {response.text}")
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
            "images": [img["webformatURL"] for img in image_data["hits"][:10]] if image_data and "hits" in image_data else []  # Ensure we only use first 10 images
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
