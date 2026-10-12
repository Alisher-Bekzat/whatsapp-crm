from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from database import Database
from parser import WhatsAppParser
import threading
import os
from config import PARSE_INTERVAL

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

db = Database()
parser = WhatsAppParser()
parser_thread = None
is_parsing = False

# ============= TASKS API =============

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Получить все задачи"""
    tasks = db.get_tasks()
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Создать новую задачу"""
    data = request.json
    
    task_id = db.add_task(
        title=data.get('title', ''),
        description=data.get('description', ''),
        author=data.get('author', ''),
        column_id=data.get('column_id', 'col_0')
    )
    
    return jsonify({
        'id': task_id,
        'title': data.get('title'),
        'message': 'Task created'
    }), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Обновить задачу (переместить в другую колонку)"""
    data = request.json
    new_column_id = data.get('column_id')
    
    db.update_task_column(task_id, new_column_id)
    
    return jsonify({'message': 'Task updated'})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Удалить задачу"""
    db.delete_task(task_id)
    return jsonify({'message': 'Task deleted'})

# ============= COLUMNS API =============

@app.route('/api/columns', methods=['GET'])
def get_columns():
    """Получить все колонки"""
    columns = db.get_columns()
    
    # Добавить задачи в каждую колонку
    for col in columns:
        col['tasks'] = db.get_tasks_by_column(col['id'])
    
    return jsonify(columns)

@app.route('/api/columns', methods=['POST'])
def create_column():
    """Создать новую колонку"""
    data = request.json
    col_id = db.add_column(data.get('name', 'New Column'))
    
    return jsonify({
        'id': col_id,
        'name': data.get('name'),
        'message': 'Column created'
    }), 201

@app.route('/api/columns/<col_id>', methods=['PUT'])
def update_column(col_id):
    """Переименовать колонку"""
    data = request.json
    db.rename_column(col_id, data.get('name', ''))
    
    return jsonify({'message': 'Column updated'})

@app.route('/api/columns/<col_id>', methods=['DELETE'])
def delete_column_route(col_id):
    """Удалить колонку"""
    db.delete_column(col_id)
    
    return jsonify({'message': 'Column deleted'})

# ============= HISTORY API =============

@app.route('/api/history', methods=['GET'])
def get_history():
    """Получить историю изменений"""
    history = db.get_history()
    return jsonify(history)

# ============= PARSER API - GROUPS =============

@app.route('/api/parser/discover-groups', methods=['POST'])
def discover_groups():
    """Обнаружить все WhatsApp группы"""
    global is_parsing
    
    if is_parsing:
        return jsonify({'message': 'Parser already running'}), 400
    
    is_parsing = True
    
    def run_discovery():
        global is_parsing
        try:
            if not parser.init_driver():
                is_parsing = False
                return
            
            groups = parser.discover_groups()
            
            # Сохраняем найденные группы
            for group in groups:
                db.add_discovered_group(group)
            
            is_parsing = False
        except Exception as e:
            print(f"❌ Ошибка при обнаружении групп: {e}")
            is_parsing = False
    
    discovery_thread = threading.Thread(target=run_discovery, daemon=True)
    discovery_thread.start()
    
    return jsonify({'message': 'Group discovery started'})

@app.route('/api/parser/groups', methods=['GET'])
def get_discovered_groups():
    """Получить найденные группы"""
    groups = db.get_discovered_groups()
    return jsonify({'groups': groups})

@app.route('/api/parser/groups/select', methods=['POST'])
def select_groups():
    """Сохранить выбранные группы"""
    data = request.json
    selected_groups = data.get('groups', [])
    
    db.save_selected_groups(selected_groups)
    
    return jsonify({'message': 'Groups saved', 'selected': selected_groups})

@app.route('/api/parser/groups/selected', methods=['GET'])
def get_selected_groups():
    """Получить выбранные группы"""
    groups = db.get_selected_groups()
    return jsonify({'groups': groups})

# ============= PARSER API - CONTROL =============

@app.route('/api/parser/start', methods=['POST'])
def start_parser():
    """Запустить парсер WhatsApp с выбранными группами"""
    global is_parsing, parser_thread
    
    if is_parsing:
        return jsonify({'message': 'Parser already running'}), 400
    
    is_parsing = True
    selected_groups = db.get_selected_groups()
    
    if not selected_groups:
        is_parsing = False
        return jsonify({'message': 'No groups selected'}), 400
    
    def run_parser():
        global is_parsing
        try:
            if not parser.driver:
                if not parser.init_driver():
                    is_parsing = False
                    return
            
            parser.start(selected_groups, db)
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            is_parsing = False
    
    parser_thread = threading.Thread(target=run_parser, daemon=True)
    parser_thread.start()
    
    return jsonify({'message': 'Parser started', 'groups': selected_groups})

@app.route('/api/parser/stop', methods=['POST'])
def stop_parser():
    """Остановить парсер"""
    global is_parsing
    is_parsing = False
    
    if parser.driver:
        parser.stop()
        parser.close()
    
    return jsonify({'message': 'Parser stopped'})

@app.route('/api/parser/status', methods=['GET'])
def parser_status():
    """Статус парсера"""
    return jsonify({
        'is_running': is_parsing,
        'groups': db.get_selected_groups()
    })

@app.route('/api/parser/history', methods=['GET'])
def parser_history():
    """Получить историю парсинга"""
    limit = request.args.get('limit', 100, type=int)
    history = db.get_parse_history(limit)
    return jsonify(history)

# ============= SERVE FRONTEND =============

@app.route('/')
def serve_index():
    """Serve index.html"""
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('../frontend', path)

if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    print("📱 Open http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0')
