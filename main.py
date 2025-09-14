import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

def send_telegram_message(token, chat_id, message):
    """Envía mensaje a Telegram"""
    if not token or not chat_id:
        print("❌ Telegram no configurado")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    full_message = f"🏛️ *ICSID Case Daily Report - ARB/23/39*\n\n{message}\n\n🔗 [Ver caso](https://icsid.worldbank.org/cases/case-database/case-detail?CaseNo=ARB/23/39)"
    
    data = {
        'chat_id': chat_id,
        'text': full_message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("✅ Reporte diario enviado a Telegram")
            return True
        else:
            print(f"❌ Error Telegram: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        return False

def extract_latest_development(soup):
    """Extrae el Latest Development de la página"""
    page_text = soup.get_text()
    
    print("🔍 Buscando Latest Development...")
    
    # Múltiples patrones para encontrar la información más reciente
    patterns = [
        # Patrón específico para el caso actual
        r'August 22, 2025[^\n\r]*(?:Respondent|rejoinder)[^\n\r]*',
        
        # Patrones generales para fechas de 2025
        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+2025[^\n\r]*(?:files|filed|submit|issue|render|decision|order|memorial|rejoinder|award)[^\n\r]*)',
        
        # Patrones para fechas en formato numérico
        r'(\d{1,2}[\/\-]\d{1,2}[\/\-]2025[^\n\r]*(?:files|filed|submit|issue)[^\n\r]*)',
        
        # Patrón más amplio para cualquier evento de 2025
        r'(2025[^\n\r]*(?:files|filed|submitted|issued|rendered|decision|order|memorial|rejoinder|award)[^\n\r]*)'
    ]
    
    latest_development = "No se encontró información de Latest Development"
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
        print(f"  Patrón {i+1}: {len(matches)} coincidencias")
        
        if matches:
            # Tomar la coincidencia más larga (más descriptiva)
            match = max(matches, key=len).strip()
            if len(match) > 15:  # Evitar coincidencias muy cortas
                latest_development = match
                print(f"  ✅ Encontrado con patrón {i+1}: {match[:50]}...")
                break
    
    # Limpiar el texto
    latest_development = re.sub(r'\s+', ' ', latest_development)
    latest_development = latest_development.replace('\\n', ' ').replace('\\r', '')
    
    return latest_development[:400]  # Limitar longitud

def extract_case_status(soup):
    """Extrae el status general del caso"""
    page_text = soup.get_text()
    
    # Buscar el status del caso
    status_patterns = [
        r'Status[:\s]*([^\n\r]*pending[^\n\r]*)',
        r'Case Status[:\s]*([^\n\r]*)',
        r'(Pending|Concluded|Discontinued|Settled)[^\n\r]*'
    ]
    
    for pattern in status_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            status = match.group(1).strip() if len(match.groups()) > 0 else match.group().strip()
            return status[:100]  # Limitar longitud
    
    return "Pending"

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
        
        # Extraer información clave
        latest_development = extract_latest_development(soup)
        case_status = extract_case_status(soup)
        
        # Buscar si hay menciones de award o laudo
        page_text = soup.get_text().lower()
        has_award_mentions = 'award' in page_text
        has_decision_mentions = 'decision' in page_text
        
        print(f"✅ Información extraída:")
        print(f"   Latest Development: {latest_development[:80]}...")
        print(f"   Status: {case_status}")
        print(f"   Award mentions: {has_award_mentions}")
        
        return {
            'latest_development': latest_development,
            'case_status': case_status,
            'has_award_mentions': has_award_mentions,
            'has_decision_mentions': has_decision_mentions,
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        print(f"❌ Error obteniendo información del caso: {e}")
        return None

def format_daily_report(case_info):
    """Formatea el reporte diario"""
    if not case_info:
        return "❌ *Error obteniendo información del caso*\n\nNo se pudo conectar con la página de ICSID."
    
    # Obtener fecha actual en Argentina
    argentina_time = datetime.now().strftime('%d/%m/%Y')
    
    report = [
        f"📅 *Reporte Diario - {argentina_time}*",
        "",
        f"📋 *Latest Development:*",
        f"`{case_info['latest_development']}`",
        "",
        f"📊 *Case Status:* `{case_info['case_status']}`",
        ""
    ]
    
    # Agregar información adicional si hay menciones importantes
    if case_info.get('has_award_mentions'):
        report.append("🏆 *Nota:* La página menciona 'award' - verificar manualmente")
        report.append("")
    
    if case_info.get('has_decision_mentions'):
        report.append("⚖️ *Nota:* Se mencionan decisiones en el documento")
        report.append("")
    
    report.extend([
        f"🕐 *Verificado:* {case_info['check_time']} (UTC)",
        "",
        f"*Caso:* Abertis Infraestructuras v. Argentina",
        f"*Número:* ARB/23/39"
    ])
    
    return "\n".join(report)

def main():
    """Función principal - Reporte diario"""
    print(f"🌅 ICSID Daily Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Enviando reporte diario del caso ARB/23/39")
    
    # Variables de entorno
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_token or not chat_id:
        print("❌ Variables de entorno no configuradas")
        print(f"TELEGRAM_TOKEN: {'✅' if telegram_token else '❌'}")
        print(f"TELEGRAM_CHAT_ID: {'✅' if chat_id else '❌'}")
        return
    
    # Obtener información actual del caso
    case_info = get_case_info()
    
    # Formatear reporte
    report = format_daily_report(case_info)
    
    print(f"📄 Reporte generado:")
    print(report)
    print()
    
    # Enviar reporte diario
    if send_telegram_message(telegram_token, chat_id, report):
        print("✅ Reporte diario enviado exitosamente")
    else:
        print("❌ Error enviando reporte diario")
    
    print("🏁 Reporte diario completado")

if __name__ == "__main__":
    main()
    # Ejecutar verificación
    monitor.run_check()
