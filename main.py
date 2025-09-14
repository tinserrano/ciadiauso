import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re
import json

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, message):
        """Envía mensaje a Telegram"""
        url = f"{self.base_url}/sendMessage"
        
        full_message = f"🏛️ *ICSID Case Monitor - ARB/23/39*\n\n{message}\n\n🔗 [Ver caso](https://icsid.worldbank.org/cases/case-database/case-detail?CaseNo=ARB/23/39)"
        
        data = {
            'chat_id': self.chat_id,
            'text': full_message,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            return False
    
    def get_updates(self):
        """Obtiene mensajes recientes del chat"""
        url = f"{self.base_url}/getUpdates"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json().get('result', [])
        except Exception as e:
            print(f"❌ Error obteniendo updates: {e}")
        return []
    
    def check_for_commands(self):
        """Verifica si hay comandos pendientes en el chat"""
        updates = self.get_updates()
        
        # Buscar mensajes recientes (últimos 5 minutos)
        recent_threshold = datetime.now().timestamp() - 300  # 5 minutos
        
        commands = []
        for update in updates[-10:]:  # Solo últimos 10 mensajes
            message = update.get('message', {})
            message_date = message.get('date', 0)
            
            if message_date > recent_threshold:
                text = message.get('text', '').lower().strip()
                if text in ['/check', '/status', '/report', '/update', 'check', 'status']:
                    commands.append({
                        'command': text,
                        'date': message_date,
                        'message_id': message.get('message_id')
                    })
        
        return commands

def extract_latest_development(soup):
    """Extrae el Latest Development de la página"""
    page_text = soup.get_text()
    
    print("🔍 Buscando Latest Development...")
    
    patterns = [
        r'August 22, 2025[^\n\r]*(?:Respondent|rejoinder)[^\n\r]*',
        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+2025[^\n\r]*(?:files|filed|submit|issue|render|decision|order|memorial|rejoinder|award)[^\n\r]*)',
        r'(\d{1,2}[\/\-]\d{1,2}[\/\-]2025[^\n\r]*(?:files|filed|submit|issue)[^\n\r]*)',
        r'(2025[^\n\r]*(?:files|filed|submitted|issued|rendered|decision|order|memorial|rejoinder|award)[^\n\r]*)'
    ]
    
    latest_development = "No se encontró información de Latest Development"
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
        
        if matches:
            match = max(matches, key=len).strip()
            if len(match) > 15:
                latest_development = match
                break
    
    latest_development = re.sub(r'\s+', ' ', latest_development)
    return latest_development[:400]

def get_case_info():
    """Obtiene información actual del caso ICSID"""
    url = "https://icsid.worldbank.org/cases/case-database/case-detail?CaseNo=ARB/23/39"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("🌐 Descargando página ICSID...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        latest_development = extract_latest_development(soup)
        
        page_text = soup.get_text().lower()
        
        return {
            'latest_development': latest_development,
            'has_award_mentions': 'award' in page_text,
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'requested_by_user': True
        }
        
    except Exception as e:
        print(f"❌ Error obteniendo información: {e}")
        return None

def format_manual_report(case_info):
    """Formatea reporte manual solicitado por el usuario"""
    if not case_info:
        return "❌ *Error obteniendo información*\n\nNo se pudo conectar con ICSID."
    
    argentina_time = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    report = [
        f"🔍 *Consulta Manual - {argentina_time}*",
        "",
        f"📋 *Latest Development:*",
        f"`{case_info['latest_development']}`",
        ""
    ]
    
    if case_info.get('has_award_mentions'):
        report.append("🏆 *Alerta:* Se menciona 'award' - ¡Verificar!")
        report.append("")
    
    report.extend([
        f"🕐 *Consultado:* {case_info['check_time']} UTC",
        "",
        f"💡 *Comandos disponibles:*",
        f"`/check` - Verificar ahora",
        f"`/status` - Estado del caso",
        f"`/report` - Reporte completo"
    ])
    
    return "\n".join(report)

def main():
    """Función principal con soporte para comandos"""
    print(f"🤖 ICSID Bot con Comandos - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Variables de entorno
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_token or not chat_id:
        print("❌ Variables de entorno no configuradas")
        return
    
    # Inicializar bot
    bot = TelegramBot(telegram_token, chat_id)
    
    # Verificar si hay comandos pendientes
    commands = bot.check_for_commands()
    
    if commands:
        print(f"📱 {len(commands)} comando(s) detectado(s)")
        
        # Procesar el comando más reciente
        latest_command = max(commands, key=lambda x: x['date'])
        command_text = latest_command['command']
        
        print(f"⚡ Procesando comando: {command_text}")
        
        # Obtener información del caso
        case_info = get_case_info()
        
        # Formatear respuesta
        if command_text in ['/check', 'check']:
            response = format_manual_report(case_info)
        elif command_text in ['/status', 'status']:
            if case_info:
                response = f"📊 *Status Actual*\n\n📋 {case_info['latest_development']}\n\n🕐 Verificado: {case_info['check_time']}"
            else:
                response = "❌ Error obteniendo status"
        elif command_text in ['/report', 'report']:
            response = format_manual_report(case_info)
        else:
            response = format_manual_report(case_info)
        
        # Enviar respuesta
        if bot.send_message(response):
            print("✅ Respuesta enviada al usuario")
        else:
            print("❌ Error enviando respuesta")
    
    else:
        print("📅 Ejecución automática - Reporte diario")
        
        # Lógica del reporte diario normal
        case_info = get_case_info()
        
        if case_info:
            argentina_time = datetime.now().strftime('%d/%m/%Y')
            
            daily_report = [
                f"📅 *Reporte Diario - {argentina_time}*",
                "",
                f"📋 *Latest Development:*",
                f"`{case_info['latest_development']}`",
                "",
                f"🕐 *Verificado:* {case_info['check_time']} UTC",
                "",
                f"💡 *Tip:* Envía `/check` para consulta manual"
            ]
            
            report = "\n".join(daily_report)
            
            if bot.send_message(report):
                print("✅ Reporte diario enviado")
            else:
                print("❌ Error enviando reporte diario")
    
    print("🏁 Ejecución completada")

if __name__ == "__main__":
    main()
