import os
import json
import datetime
import uuid
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.')
FILE_NAME = 'thoughts.json'

def load_data():
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = []
    else:
        data = []

    # Migration logic: ensure every thought has a unique id, and empty inputs/outputs lists if missing
    modified = False
    for item in data:
        if 'id' not in item:
            item['id'] = str(uuid.uuid4())
            modified = True
        if 'inputs' not in item:
            item['inputs'] = []
            modified = True
        if 'outputs' not in item:
            item['outputs'] = []
            modified = True

    if modified:
        save_data(data)

    return data

def save_data(data):
    with open(FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.route('/')
def home():
    return send_from_directory('.', 'thought.html')

@app.route('/thought/<thought_id>')
def view_thought(thought_id):
    return send_from_directory('.', 'thought.html')

@app.route('/api/thoughts', methods=['GET'])
def get_thoughts():
    data = load_data()
    # Retain index for backward compatibility, but include id, inputs, and outputs
    indexed_data = []
    for idx, item in enumerate(data):
        indexed_data.append({
            'index': idx,
            'id': item['id'],
            'time': item['time'],
            'text': item['text'],
            'inputs': item['inputs'],
            'outputs': item['outputs']
        })
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
    new_thought = {
        'id': str(uuid.uuid4()),
        'time': time_str,
        'text': text,
        'inputs': [],
        'outputs': []
    }
    data.append(new_thought)
    save_data(data)
    return jsonify({'status': 'success', 'thought': new_thought})

@app.route('/api/edit', methods=['POST'])
def edit_thought():
    idx = request.json.get('index') if request.json else None
    thought_id = request.json.get('id') if request.json else None
    text = request.json.get('text', '').strip() if request.json else ''
    
    if not text:
        return jsonify({'error': 'Empty thought text'}), 400
        
    data = load_data()
    
    if thought_id:
        for item in data:
            if item['id'] == thought_id:
                item['text'] = text
                save_data(data)
                return jsonify({'status': 'success'})
        return jsonify({'error': 'Thought not found'}), 404
        
    elif idx is not None and 0 <= idx < len(data):
        data[idx]['text'] = text
        save_data(data)
        return jsonify({'status': 'success'})
        
    return jsonify({'error': 'Invalid request parameters'}), 400

@app.route('/api/delete', methods=['POST'])
def delete_thought():
    idx = request.json.get('index') if request.json else None
    thought_id = request.json.get('id') if request.json else None
    
    data = load_data()
    target_id = None
    
    if thought_id:
        target_id = thought_id
    elif idx is not None and 0 <= idx < len(data):
        target_id = data[idx]['id']
        
    if target_id:
        # Find the item to delete
        item_to_delete = None
        for item in data:
            if item['id'] == target_id:
                item_to_delete = item
                break
                
        if item_to_delete:
            # Cascade delete: clean up references in other thoughts
            for item in data:
                item['inputs'] = [conn for conn in item['inputs'] if conn['nodeId'] != target_id]
                item['outputs'] = [conn for conn in item['outputs'] if conn['nodeId'] != target_id]
            
            data.remove(item_to_delete)
            save_data(data)
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Thought not found'}), 404
        
    return jsonify({'error': 'Invalid index or ID'}), 400

@app.route('/api/spawn', methods=['POST'])
def spawn_thought():
    parent_id = request.json.get('parentId') if request.json else None
    text = request.json.get('text', '').strip() if request.json else ''
    label = request.json.get('label', '').strip() if request.json else ''
    
    if not parent_id or not text:
        return jsonify({'error': 'Missing parentId or text'}), 400
        
    data = load_data()
    
    # Verify parent exists
    parent = None
    for item in data:
        if item['id'] == parent_id:
            parent = item
            break
            
    if not parent:
        return jsonify({'error': 'Parent thought not found'}), 404
        
    # Generate child ID and new thought
    child_id = str(uuid.uuid4())
    now = datetime.datetime.now()
    time_str = now.strftime('%m/%d/%Y, %I:%M:%S %p').lstrip('0').replace('/0', '/')
    
    conn_id = str(uuid.uuid4())
    new_thought = {
        'id': child_id,
        'time': time_str,
        'text': text,
        'inputs': [{'id': conn_id, 'nodeId': parent_id, 'label': label}],
        'outputs': []
    }
    
    parent['outputs'].append({'id': conn_id, 'nodeId': child_id, 'label': label})
    data.append(new_thought)
    save_data(data)
    
    return jsonify({'status': 'success', 'thought': new_thought})

@app.route('/api/refer', methods=['POST'])
def refer_thought():
    target_id = request.json.get('targetId') if request.json else None
    text = request.json.get('text', '').strip() if request.json else ''
    label = request.json.get('label', '').strip() if request.json else ''
    
    if not target_id or not text:
        return jsonify({'error': 'Missing targetId or text'}), 400
        
    data = load_data()
    
    # Verify target exists
    target = None
    for item in data:
        if item['id'] == target_id:
            target = item
            break
            
    if not target:
        return jsonify({'error': 'Target thought not found'}), 404
        
    # Generate referring thought ID and new thought
    source_id = str(uuid.uuid4())
    now = datetime.datetime.now()
    time_str = now.strftime('%m/%d/%Y, %I:%M:%S %p').lstrip('0').replace('/0', '/')
    
    conn_id = str(uuid.uuid4())
    new_thought = {
        'id': source_id,
        'time': time_str,
        'text': text,
        'inputs': [],
        'outputs': [{'id': conn_id, 'nodeId': target_id, 'label': label}]
    }
    
    target['inputs'].append({'id': conn_id, 'nodeId': source_id, 'label': label})
    data.append(new_thought)
    save_data(data)
    
    return jsonify({'status': 'success', 'thought': new_thought})

@app.route('/api/link', methods=['POST'])
def link_thoughts():
    source_id = request.json.get('sourceId') if request.json else None
    target_id = request.json.get('targetId') if request.json else None
    label = request.json.get('label', '').strip() if request.json else ''
    
    if not source_id or not target_id:
        return jsonify({'error': 'Missing sourceId or targetId'}), 400
        
    if source_id == target_id:
        return jsonify({'error': 'Cannot link a thought to itself'}), 400
        
    data = load_data()
    
    source = None
    target = None
    for item in data:
        if item['id'] == source_id:
            source = item
        if item['id'] == target_id:
            target = item
            
    if not source or not target:
        return jsonify({'error': 'Source or target thought not found'}), 404
        
    # Check if link already exists
    for conn in source['outputs']:
        if conn['nodeId'] == target_id:
            return jsonify({'error': 'Link already exists'}), 400
            
    conn_id = str(uuid.uuid4())
    source['outputs'].append({'id': conn_id, 'nodeId': target_id, 'label': label})
    target['inputs'].append({'id': conn_id, 'nodeId': source_id, 'label': label})
    
    save_data(data)
    return jsonify({'status': 'success'})

@app.route('/api/unlink', methods=['POST'])
def unlink_thoughts():
    source_id = request.json.get('sourceId') if request.json else None
    target_id = request.json.get('targetId') if request.json else None
    
    if not source_id or not target_id:
        return jsonify({'error': 'Missing sourceId or targetId'}), 400
        
    data = load_data()
    
    source = None
    target = None
    for item in data:
        if item['id'] == source_id:
            source = item
        if item['id'] == target_id:
            target = item
            
    if source:
        source['outputs'] = [conn for conn in source['outputs'] if conn['nodeId'] != target_id]
    if target:
        target['inputs'] = [conn for conn in target['inputs'] if conn['nodeId'] != source_id]
        
    save_data(data)
    return jsonify({'status': 'success'})

@app.route('/api/link_multiple', methods=['POST'])
def link_multiple():
    source_ids = request.json.get('sourceIds', [])
    target_id = request.json.get('targetId')
    label = request.json.get('label', '').strip() if request.json else ''
    
    if not source_ids or not target_id:
        return jsonify({'error': 'Missing sourceIds or targetId'}), 400
        
    data = load_data()
    
    # Find target
    target = None
    for item in data:
        if item['id'] == target_id:
            target = item
            break
            
    if not target:
        return jsonify({'error': 'Target thought not found'}), 404
        
    # Find sources and perform linking
    linked_count = 0
    for source_id in source_ids:
        if source_id == target_id:
            continue
        
        # Find source
        source = None
        for item in data:
            if item['id'] == source_id:
                source = item
                break
                
        if not source:
            continue
            
        # Check if link already exists
        exists = False
        for conn in source['outputs']:
            if conn['nodeId'] == target_id:
                exists = True
                break
                
        if exists:
            continue
            
        conn_id = str(uuid.uuid4())
        source['outputs'].append({'id': conn_id, 'nodeId': target_id, 'label': label})
        target['inputs'].append({'id': conn_id, 'nodeId': source_id, 'label': label})
        linked_count += 1
        
    if linked_count > 0:
        save_data(data)
        
    return jsonify({'status': 'success', 'linked_count': linked_count})

@app.route('/api/add_and_link_multiple', methods=['POST'])
def add_and_link_multiple():
    source_ids = request.json.get('sourceIds', [])
    text = request.json.get('text', '').strip() if request.json else ''
    label = request.json.get('label', '').strip() if request.json else ''
    
    if not text:
        return jsonify({'error': 'Empty thought text'}), 400
        
    # Create new thought (target)
    target_id = str(uuid.uuid4())
    now = datetime.datetime.now()
    time_str = now.strftime('%m/%d/%Y, %I:%M:%S %p').lstrip('0').replace('/0', '/')
    
    new_thought = {
        'id': target_id,
        'time': time_str,
        'text': text,
        'inputs': [],
        'outputs': []
    }
    
    data = load_data()
    
    # Perform linking from sources to this new thought
    linked_count = 0
    for source_id in source_ids:
        # Find source
        source = None
        for item in data:
            if item['id'] == source_id:
                source = item
                break
                
        if not source:
            continue
            
        conn_id = str(uuid.uuid4())
        source['outputs'].append({'id': conn_id, 'nodeId': target_id, 'label': label})
        new_thought['inputs'].append({'id': conn_id, 'nodeId': source_id, 'label': label})
        linked_count += 1
        
    data.append(new_thought)
    save_data(data)
    
    return jsonify({'status': 'success', 'thought': new_thought, 'linked_count': linked_count})

if __name__ == '__main__':
    # Start Flask server on port 8000
    app.run(port=8000)
