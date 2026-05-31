import os
import json
import datetime
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.')
FILE_NAME = 'thoughts.json'

def load_data():
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_data(data):
    with open(FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.route('/')
def home():
    return send_from_directory('.', 'thought.html')

@app.route('/api/thoughts', methods=['GET'])
def get_thoughts():
    # Load all thoughts, attach original array index, and reverse for newest-first display
    data = load_data()
    indexed_data = [{'index': idx, 'time': item['time'], 'text': item['text']} for idx, item in enumerate(data)]
    indexed_data.reverse()
    return jsonify(indexed_data)

@app.route('/api/add', methods=['POST'])
def add_thought():
    text = request.json.get('text', '').strip() if request.json else ''
    if not text:
        return jsonify({'error': 'Empty thought text'}), 400
    
    # Format timestamp nicely (browser style compatibility)
    now = datetime.datetime.now()
    time_str = now.strftime('%m/%d/%Y, %I:%M:%S %p').lstrip('0').replace('/0', '/')
    
    data = load_data()
    data.append({'time': time_str, 'text': text})
    save_data(data)
    return jsonify({'status': 'success'})

@app.route('/api/edit', methods=['POST'])
def edit_thought():
    idx = request.json.get('index') if request.json else None
    text = request.json.get('text', '').strip() if request.json else ''
    
    data = load_data()
    if idx is not None and 0 <= idx < len(data) and text:
        data[idx]['text'] = text
        save_data(data)
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Invalid request parameters'}), 400

@app.route('/api/delete', methods=['POST'])
def delete_thought():
    idx = request.json.get('index') if request.json else None
    data = load_data()
    if idx is not None and 0 <= idx < len(data):
        data.pop(idx)
        save_data(data)
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Invalid index'}), 400

if __name__ == '__main__':
    # Start Flask server on port 8000
    app.run(port=8000)
