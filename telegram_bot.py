import os
from dotenv import load_dotenv
import requests

load_dotenv()

class TelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(self, text):
        """텔레그램으로 메시지 전송"""
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"텔레그램 전송 오류: {e}")
            return False
    
    def get_chat_id(self):
        """봇이 받은 메시지에서 chat_id 확인"""
        url = f"{self.base_url}/getUpdates"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if data['result']:
                chat_id = data['result'][-1]['message']['chat']['id']
                print(f"Your Chat ID: {chat_id}")
                return chat_id
            else:
                print("봇에게 먼저 메시지를 보내주세요!")
                return None
        except Exception as e:
            print(f"오류: {e}")
            return None