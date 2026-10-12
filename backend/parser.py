import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import logging
from config import FLAGS, PARSE_INTERVAL
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppParser:
    def __init__(self):
        self.driver = None
        self.is_running = False
        self.selected_groups = []
        self.discovered_groups = []
        self.parsed_messages = set()
        
    def init_driver(self):
        """Инициализация Selenium WebDriver"""
        try:
            options = Options()
            # options.add_argument("--headless")  # Раскомментируйте для фонового режима
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            logger.info("🌐 Открываю WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com")
            
            # Ждём сканирования QR кода
            logger.info("📱 Отсканируйте QR код своим телефоном...")
            time.sleep(10)  # Даём время на сканирование
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            return False
    
    def discover_groups(self):
        """Сканирование всех групп WhatsApp"""
        try:
            logger.info("🔍 Ищу WhatsApp группы...")
            self.discovered_groups = []
            
            # Ждём загрузки чат-листа
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[@data-testid='chat-list-item-container']"))
            )
            
            time.sleep(2)
            
            # Получаем все чаты
            chat_items = self.driver.find_elements(By.XPATH, "//div[@data-testid='chat-list-item-container']")
            
            for item in chat_items:
                try:
                    # Получаем имя чата
                    name_elem = item.find_element(By.XPATH, ".//span[@title]")
                    group_name = name_elem.get_attribute("title")
                    
                    # Проверяем иконку группы (в группах есть иконка с несколькими людьми)
                    try:
                        item.find_element(By.XPATH, ".//img[contains(@src, 'group')]")
                        if group_name and group_name not in self.discovered_groups:
                            self.discovered_groups.append(group_name)
                            logger.info(f"✅ Найдена группа: {group_name}")
                    except:
                        # Это не группа, пропускаем
                        pass
                except Exception as e:
                    logger.debug(f"Ошибка при парсинге чата: {e}")
                    continue
            
            logger.info(f"📊 Всего найдено групп: {len(self.discovered_groups)}")
            return self.discovered_groups
            
        except Exception as e:
            logger.error(f"❌ Ошибка при сканировании групп: {e}")
            return []
    
    def open_group(self, group_name):
        """Открыть группу по имени"""
        try:
            # Ищем чат с таким именем
            chat_items = self.driver.find_elements(By.XPATH, "//div[@data-testid='chat-list-item-container']")
            
            for item in chat_items:
                try:
                    name_elem = item.find_element(By.XPATH, ".//span[@title]")
                    if name_elem.get_attribute("title") == group_name:
                        item.click()
                        time.sleep(2)
                        logger.info(f"📂 Открыл группу: {group_name}")
                        return True
                except:
                    continue
            
            logger.warning(f"⚠️ Не найдена группа: {group_name}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка при открытии группы: {e}")
            return False
    
    def get_messages_from_group(self, group_name):
        """Получить сообщения из группы"""
        try:
            if not self.open_group(group_name):
                return []
            
            messages = []
            
            # Ждём загрузки сообщений
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[@data-testid='msg-container']"))
            )
            
            time.sleep(1)
            
            # Прокручиваем вверх для загрузки истории
            message_container = self.driver.find_element(By.XPATH, "//div[@data-testid='msg-container']")
            for _ in range(5):
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop - 1000", message_container)
                time.sleep(0.5)
            
            # Получаем все сообщения
            message_elements = self.driver.find_elements(By.XPATH, "//div[@data-testid='msg']")
            
            for msg_elem in message_elements:
                try:
                    # Получаем текст сообщения
                    text_elem = msg_elem.find_element(By.XPATH, ".//span[@class='selectable-text']")
                    message_text = text_elem.text.strip()
                    
                    if not message_text:
                        continue
                    
                    # Получаем автора (для групп)
                    try:
                        author_elem = msg_elem.find_element(By.XPATH, ".//span[@data-name]")
                        author = author_elem.get_attribute("data-name")
                    except:
                        author = "Неизвестно"
                    
                    # Получаем время
                    try:
                        time_elem = msg_elem.find_element(By.XPATH, ".//span[@data-testid='message_timestamp']")
                        timestamp = time_elem.text
                    except:
                        timestamp = datetime.now().isoformat()
                    
                    # Создаём уникальный ID сообщения
                    msg_id = f"{group_name}_{author}_{message_text}_{timestamp}"
                    
                    # Проверяем, не парсили ли это сообщение раньше
                    if msg_id not in self.parsed_messages:
                        messages.append({
                            'text': message_text,
                            'author': author,
                            'timestamp': timestamp,
                            'group': group_name,
                            'msg_id': msg_id
                        })
                        self.parsed_messages.add(msg_id)
                
                except Exception as e:
                    logger.debug(f"Ошибка при парсинге сообщения: {e}")
                    continue
            
            logger.info(f"📨 Получено сообщений из группы '{group_name}': {len(messages)}")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении сообщений: {e}")
            return []
    
    def find_flag_in_message(self, message_text):
        """Найти флаг в сообщении"""
        message_lower = message_text.lower()
        
        for flag, column_name in FLAGS.items():
            if flag.lower() in message_lower:
                return flag, column_name
        
        return None, None
    
    def close(self):
        """Закрыть браузер"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("🔚 Браузер закрыт")
    
    def start(self, selected_groups, db):
        """Запустить парсер"""
        self.is_running = True
        self.selected_groups = selected_groups
        
        if not self.driver:
            if not self.init_driver():
                self.is_running = False
                return
        
        logger.info(f"🚀 Парсер запущен для групп: {selected_groups}")
        
        while self.is_running:
            try:
                for group_name in self.selected_groups:
                    if not self.is_running:
                        break
                    
                    logger.info(f"📊 Парсю группу: {group_name}")
                    messages = self.get_messages_from_group(group_name)
                    
                    for msg in messages:
                        flag, column_name = self.find_flag_in_message(msg['text'])
                        
                        if flag:
                            # Получаем ID колонки
                            columns = db.get_columns()
                            column_id = None
                            
                            for col in columns:
                                if col['name'].lower() == column_name.lower():
                                    column_id = col['id']
                                    break
                            
                            if column_id:
                                # Создаём задачу
                                task_title = msg['text'][:100]  # Первые 100 символов
                                task_id = db.add_task(
                                    title=task_title,
                                    author=msg['author'],
                                    column_id=column_id,
                                    source='whatsapp',
                                    group_name=group_name
                                )
                                
                                # Логируем в историю парсинга
                                db.add_parse_history(
                                    group_name=group_name,
                                    message_text=msg['text'],
                                    author=msg['author'],
                                    flag_found=flag,
                                    task_created=True
                                )
                                
                                logger.info(f"✅ Создана задача #{task_id}: {task_title} (флаг: {flag})")
                            else:
                                logger.warning(f"⚠️ Колонка '{column_name}' не найдена")
                        else:
                            # Логируем сообщение без флага
                            db.add_parse_history(
                                group_name=group_name,
                                message_text=msg['text'],
                                author=msg['author'],
                                flag_found=None,
                                task_created=False
                            )
                
                # Ожидаем перед следующим циклом
                time.sleep(PARSE_INTERVAL)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле парсинга: {e}")
                time.sleep(PARSE_INTERVAL)
    
    def stop(self):
        """Остановить парсер"""
        self.is_running = False
        logger.info("⏹️ Парсер остановлен")
