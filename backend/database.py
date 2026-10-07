import sqlite3
import json
from datetime import datetime
from config import DATABASE_PATH, DEFAULT_COLUMNS

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Таблица задач
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            author TEXT,
            column_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Таблица колонок
        c.execute('''CREATE TABLE IF NOT EXISTS columns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            position INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Таблица истории
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            action TEXT,
            old_value TEXT,
            new_value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        )''')
        
        # Инициализация колонок по умолчанию
        c.execute("SELECT COUNT(*) FROM columns")
        if c.fetchone()[0] == 0:
            for i, col in enumerate(DEFAULT_COLUMNS):
                col_id = f"col_{i}"
                c.execute("INSERT INTO columns (id, name, position) VALUES (?, ?, ?)",
                         (col_id, col, i))
        
        conn.commit()
        conn.close()
    
    def add_task(self, title, description="", author="", column_id="col_0"):
        """Добавить новую задачу"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''INSERT INTO tasks (title, description, author, column_id)
                     VALUES (?, ?, ?, ?)''',
                 (title, description, author, column_id))
        
        task_id = c.lastrowid
        
        # История
        c.execute('''INSERT INTO history (task_id, action, new_value)
                     VALUES (?, ?, ?)''',
                 (task_id, "created", column_id))
        
        conn.commit()
        conn.close()
        
        return task_id
    
    def get_tasks(self):
        """Получить все задачи"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''SELECT * FROM tasks ORDER BY updated_at DESC''')
        tasks = [dict(row) for row in c.fetchall()]
        
        conn.close()
        return tasks
    
    def get_tasks_by_column(self, column_id):
        """Получить задачи по колонке"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''SELECT * FROM tasks WHERE column_id = ? ORDER BY updated_at DESC''',
                 (column_id,))
        tasks = [dict(row) for row in c.fetchall()]
        
        conn.close()
        return tasks
    
    def update_task_column(self, task_id, new_column_id):
        """Переместить задачу в другую колонку"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Получить старую колонку
        c.execute("SELECT column_id FROM tasks WHERE id = ?", (task_id,))
        old_column = c.fetchone()[0]
        
        # Обновить
        c.execute('''UPDATE tasks SET column_id = ?, updated_at = CURRENT_TIMESTAMP 
                     WHERE id = ?''',
                 (new_column_id, task_id))
        
        # История
        c.execute('''INSERT INTO history (task_id, action, old_value, new_value)
                     VALUES (?, ?, ?, ?)''',
                 (task_id, "moved", old_column, new_column_id))
        
        conn.commit()
        conn.close()
    
    def get_columns(self):
        """Получить все колонки"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''SELECT * FROM columns ORDER BY position''')
        columns = [dict(row) for row in c.fetchall()]
        
        conn.close()
        return columns
    
    def add_column(self, name):
        """Добавить новую колонку"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT MAX(position) FROM columns")
        max_pos = c.fetchone()[0]
        new_pos = (max_pos or -1) + 1
        
        col_id = f"col_{int(datetime.now().timestamp())}"
        c.execute("INSERT INTO columns (id, name, position) VALUES (?, ?, ?)",
                 (col_id, name, new_pos))
        
        conn.commit()
        conn.close()
        
        return col_id
    
    def rename_column(self, col_id, new_name):
        """Переименовать колонку"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("UPDATE columns SET name = ? WHERE id = ?", (new_name, col_id))
        
        conn.commit()
        conn.close()
    
    def delete_column(self, col_id):
        """Удалить колонку"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Переместить задачи в первую колонку
        c.execute("SELECT id FROM columns ORDER BY position LIMIT 1")
        first_col = c.fetchone()
        if first_col:
            c.execute("UPDATE tasks SET column_id = ? WHERE column_id = ?",
                     (first_col[0], col_id))
        
        c.execute("DELETE FROM columns WHERE id = ?", (col_id,))
        
        conn.commit()
        conn.close()
    
    def get_history(self, task_id=None):
        """Получить историю изменений"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if task_id:
            c.execute('''SELECT * FROM history WHERE task_id = ? ORDER BY timestamp DESC''',
                     (task_id,))
        else:
            c.execute('''SELECT * FROM history ORDER BY timestamp DESC LIMIT 100''')
        
        history = [dict(row) for row in c.fetchall()]
        
        conn.close()
        return history
    
    def delete_task(self, task_id):
        """Удалить задачу"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        c.execute("DELETE FROM history WHERE task_id = ?", (task_id,))
        
        conn.commit()
        conn.close()
