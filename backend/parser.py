from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime
from config import FLAGS
from database import Database

class WhatsAppParser:
    def __init__(self):
        self.driver = None
        self.db = Database()
        self.last_parsed_messages = set()
    
    def start(self):
        """Запустить Selenium для WhatsApp Web"""
        try:
            # Опции Chrome
            options = webdriver.ChromeOptions()
            # options.add_argument("--headless")  # Раскомментируй если не нужно окно браузера
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://web.whatsapp.com")
            
            print("✅ WhatsApp Web открыт. Отсканируй QR код в браузере")
            print("⏳ Ожидание загрузки чатов...")
            
            # Жди загрузки
            time.sleep(10)
            
            return True
        except Exception as e:
            print(f"❌ Ошибка Selenium: {e}")
            return False
    
    def get_group_messages(self, group_name):
        """Получить сообщения из группы"""
        try:
            # Поиск группы
            search_box = self.driver.find_element(By.XPATH, '//input[@placeholder="Поиск или начало диалога"]')
            search_box.clear()
            search_box.send_keys(group_name)
            
            time.sleep(1)
            
            # Клик на группу
            group = self.driver.find_element(By.XPATH, f'//span[@title="{group_name}"]/..')
            group.click()
            
            time.sleep(1)
            
            # Скролл вверх для загрузки всех сообщений
            chat_area = self.driver.find_element(By.XPATH, '//div[@role="application"]')
            
            for _ in range(5):
                self.driver.execute_script("arguments[0].scrollTop = 0", chat_area)
                time.sleep(0.5)
            
            # Получить сообщения
            messages = []
            message_elements = self.driver.find_elements(By.XPATH, '//div[@class="message-in"]//span[@class="selectable-text"]')
            
            for elem in message_elements:
                text = elem.text
                if text:
                    # Получить автора
                    try:
                        author = elem.find_element(By.XPATH, './ancestor::div[@data-author]').get_attribute('data-author')
                    except:
                        author = "Unknown"
                    
                    messages.append({
                        'text': text,
                        'author': author,
                        'timestamp': datetime.now().isoformat()
                    })
            
            return messages
        except Exception as e:
            print(f"❌ Ошибка при получении сообщений: {e}")
            return []
    
    def parse_messages(self, messages):
        """Парсить сообщения по флагам"""
        created_tasks = []
        
        for msg in messages:
            msg_text = msg['text'].lower()
            msg_id = hash(msg['text'] + msg['author'])
            
            # Пропусти если уже обработали
            if msg_id in self.last_parsed_messages:
                continue
            
            # Ищем флаги
            for flag, column in FLAGS.items():
                if flag in msg_text:
                    # Найти колонку по названию
                    columns = self.db.get_columns()
                    col_id = None
                    for col in columns:
                        if col['name'].lower() == column.lower():
                            col_id = col['id']
                            break
                    
                    if col_id:
                        # Создать задачу
                        title = msg['text']
                        author = msg['author'].split('@')[0] if '@' in msg['author'] else msg['author']
                        
                        task_id = self.db.add_task(
                            title=title,
                            description=f"Из WhatsApp группы",
                            author=author,
                            column_id=col_id
                        )
                        
                        created_tasks.append({
                            'id': task_id,
                            'title': title,
                            'column': column,
                            'author': author
                        })
                        
                        self.last_parsed_messages.add(msg_id)
                        print(f"✅ Создана задача: {title} → {column}")
                    break
        
        return created_tasks
    
    def stop(self):
        """Закрыть браузер"""
        if self.driver:
            self.driver.quit()
