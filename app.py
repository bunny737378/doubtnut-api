from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configure caching to prevent browser caching issues
@app.after_request
def after_request(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def fetch_token():
    """Fetch JWT token"""
    token_url = "https://senpai-v1-jwt.vercel.app/token"
    params = {
        "uid": "3946366939",
        "password": "996020B0D42D90B2D74C3338952B6645BCEFC2AAEA7D8CE75F1509890CF6B959"
    }

    response = requests.get(token_url, params=params, timeout=10)
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("token")
    raise Exception("Failed to fetch token")

def fetch_events_data(token):
    """Fetch events data from Free Fire API - OB50 only"""

    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 13; SM-M526B Build/TP1A.220624.014)",
        'Connection': "Keep-Alive", 
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Authorization': f"Bearer {token}",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB50"
    }

    payload_hex = "A5 E1 89 0E E5 83 C7 DF 22 A0 5F 2E 7C CF FE E2"
    payload = bytes.fromhex(payload_hex.replace(" ", ""))

    response = requests.post(
        "https://client.ind.freefiremobile.com/LoginGetSplash", 
        data=payload, 
        headers=headers, 
        timeout=10
    )

    if response.status_code == 200:
        return response.text
    raise Exception("API request failed")

def extract_events(response_text):
    """Extract unique events from API response"""

    # Simple pattern to find image URLs ending in .jpg
    pattern = r'https?://[^\s]+\.jpg'
    urls = re.findall(pattern, response_text, re.IGNORECASE)

    # Remove duplicates using set
    unique_urls = list(set(urls))

    events = []
    seen_titles = set()

    for url in unique_urls:
        # Clean URL - remove everything after .jpg
        clean_url = url.split('.jpg')[0] + '.jpg'

        # Extract filename for title
        filename = clean_url.split('/')[-1].replace('.jpg', '')

        # Clean filename to create readable title
        title = (filename
                .replace('1750x1070_', '')
                .replace('1750X1070_', '')
                .replace('_', ' ')
                .replace('-', ' ')
                .strip())

        # Format title properly: handle camelCase and ensure proper spacing
        title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title) # Add space between lowercase and uppercase
        title = ' '.join(title.split()).title() # Normalize spacing and title case

        # Only add if title is valid (at least 2 chars) and not a duplicate
        if len(title) > 2 and title not in seen_titles:
            events.append({
                "title": title,
                "image_url": clean_url,
                "date": datetime.now().strftime('%Y-%m-%d')
            })
            seen_titles.add(title)

    return events

@app.route('/events', methods=['GET'])
def get_events():
    """API endpoint to get events"""
    try:
        token = fetch_token()
        response_text = fetch_events_data(token)
        events = extract_events(response_text)

        if not events:
            return jsonify({"error": "No events found"}), 404

        return jsonify(events)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/web/events', methods=['GET'])
def web_events():
    """Web page endpoint to display events"""
    try:
        token = fetch_token()
        response_text = fetch_events_data(token)
        events = extract_events(response_text)

        return render_template('events.html', events=events)

    except Exception as e:
        return render_template('events.html', events=None, error=str(e))

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "name": "Free Fire Events API",
        "version": "2.0",
        "status": "running",
        "endpoints": {
            "/events": "GET - JSON API for events",
            "/web/events": "GET - Web page with events display"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)