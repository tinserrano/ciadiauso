import requests
from bs4 import BeautifulSoup
import json
import hashlib
from datetime import datetime
import os
import time

class ICSIDMonitor:
    def __init__(self, telegram_token=None, chat_id=None):
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.case_url = "https://icsid.worldbank.org/cases/case-database/case-detail?CaseNo=ARB/23/39"
        self.data_file = "icsid_data.json"
        
    def fetch_case_data(self):
        """Obtiene los datos del caso desde la página web"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(self.case_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraer información relevante
            data = {
                'timestamp': datetime.now().isoformat(),
                'case_status': self._extract_text(soup, 'Status'),
                'latest_update': self._extract_latest_update(soup),
                'documents': self._extract_documents(soup),
                'proceedings': self._extract_proceedings(soup),
                'raw_hash': hashlib.md5(response.content).hexdigest()
            }
            
            return data
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def _extract_text(self, soup, label):
        """Extrae texto específico basado en etiquetas"""
        try:
            # Buscar por diferentes patrones comunes en ICSID
            elements = soup.find_all(text=lambda text: text and label.lower() in text.lower())
            if elements:
                parent = elements[0].parent
                if parent:
                    return parent.get_text().strip()
        except:
            pass
        return "No encontrado"
    
    def _extract_latest_update(self, soup):
        """Extrae la última actualización del caso"""
        try:
            # Buscar fechas recientes en el contenido
            date_patterns = soup.find_all(text=lambda text: text and '2024' in text or '2025' in text)
            if date_patterns:
                return date_patterns[0].strip()
        except:
            pass
        return "No encontrado"
    
    def _extract_documents(self, soup):
        """Extrae lista de documentos disponibles"""
        documents = []
        try:
            # Buscar enlaces a PDFs o documentos
            links = soup.find_all('a', href=True)
            for link in links:
                if '.pdf' in link['href'].lower() or 'document' in link.get_text().lower():
                    documents.append({
                        'title': link.get_text().strip(),
                        'url': link['href']
                    })
        except:
            pass
        return documents
    
    def _extract_proceedings(self, soup):
        """Extrae información sobre procedimientos"""
        try:
            # Buscar secciones que contengan información procesal
            proceeding_text = soup.get_text()
            if 'rejoinder' in proceeding_text.lower():
                return "Fase de alegatos - Rejoinder presentado"
            elif 'memorial' in proceeding_text.lower():
                return "Fase de alegatos"
            elif 'pending' in proceeding_text.lower():
                return "Caso pendiente"
        except:
            pass
        return "Estado no determinado"
    
    def load_previous_data(self):
        """Carga datos anteriores del archivo"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading previous data: {e}")
        return None
    
    def save_data(self, data):
        """Guarda los datos actuales"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def compare_data(self, old_data, new_data):
        """Compara datos anteriores con nuevos"""
        if not old_data:
            return ["Primera ejecución - datos guardados"]
        
        changes = []
        
        # Comparar hash general
        if old_data.get('raw_hash') != new_data.get('raw_hash'):
            changes.append("🔄 Cambios detectados en la página")
        
        # Comparar status
        if old_data.get('case_status') != new_data.get('case_status'):
            changes.append(f"📊 Status cambió: {old_data.get('case_status')} → {new_data.get('case_status')}")
        
        # Comparar documentos
        old_docs = len(old_data.get('documents', []))
        new_docs = len(new_data.get('documents', []))
        if old_docs != new_docs:
            changes.append(f"📄 Documentos: {old_docs} → {new_docs}")
        
        # Comparar proceedings
        if old_data.get('proceedings') != new_data.get('proceedings'):
            changes.append(f"⚖️ Procedimiento: {new_data.get('proceedings')}")
        
        return changes
    
    def send_telegram_message(self, message):
        """Envía mensaje a Telegram"""
        if not self.telegram_token or not self.chat_id:
            print("Telegram no configurado")
            return False
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        
        full_message = f"🏛️ *ICSID Case Update - ARB/23/39*\n\n{message}\n\n🔗 [Ver caso]({self.case_url})"
        
        data = {
            'chat_id': self.chat_id,
            'text': full_message,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False
    
    def run_check(self):
        """Ejecuta la verificación completa"""
        print(f"🔍 Verificando caso ICSID a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Obtener datos actuales
        current_data = self.fetch_case_data()
        if not current_data:
            print("❌ Error obteniendo datos")
            return
        
        # Cargar datos anteriores
        previous_data = self.load_previous_data()
        
        # Comparar
        changes = self.compare_data(previous_data, current_data)
        
        if changes:
            message = "\n".join(changes)
            print(f"📢 Cambios detectados:\n{message}")
            
            # Enviar a Telegram
            if self.send_telegram_message(message):
                print("✅ Notificación enviada a Telegram")
            else:
                print("❌ Error enviando notificación")
        else:
            print("✅ Sin cambios detectados")
        
        # Guardar datos actuales
        self.save_data(current_data)

if __name__ == "__main__":
    # Configuración - obtén estos valores de las variables de entorno
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Token de tu bot
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')       # Tu chat ID
    
    # Crear monitor
    monitor = ICSIDMonitor(TELEGRAM_TOKEN, CHAT_ID)
    
    # Ejecutar verificación
    monitor.run_check()