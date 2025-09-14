import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    full_message = f"🏛️ *ICSID Case Monitor - ARB/23/39*\n\n{message}\n\n🔗 [Ver caso](https://icsid.worldbank.org/cases/case-database/case-detail?CaseNo=ARB/23/39)"
    
    data = {
        'chat_id': chat_id,
        'text': full_message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def extract_latest_development(soup):
    page_text = soup.get_text()
    
    patterns = [
        r'August 22, 2025[^\n\r]*(?:Respondent|rejoinder)[^\n\r]*',
        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+2025[^\n\r]*(?:files|filed|submit|issue|render|decision|order|memorial|rejoinder|award)[^\n\r]*)',
        r'(\d{1,2}[\/\-]\d{1,2}[\/\-]2025[^\n\r]*(?:files|filed|submit|issue)[^\n\r]*)',
        r'(2025[^\n\r]*(?:files|filed|submitted|issued|rendered|decision|order|memorial|rejoinder|award)[^\n\r]*)'
    ]
    
    latest_development = "No development information found"
    
    for pattern in patterns:
        matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
        if matches:
            match = max(matches, key=len).strip()
            if len(match) > 15:
                latest_development = match
                break
    
    latest_development = re.sub(r'\s+', ' ', latest_development)
    return latest_development[:400]

def extract_case_status(soup):
    page_text = soup.get_text()
    
    status_patterns = [
        r'Status[:\s]*([^\n\r]*)',
        r'Case Status[:\s]*([^\n\r]*)',
        r'(Pending|Concluded|Discontinued|Settled)'
    ]
    
    for pattern in status_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            return match.group(1).strip() if len(match.groups()) > 0 else match.group().strip()
    
    return "Pending"

def get_case_info():
    url = "https://icsid.worldbank.org/cases/case-database/case-detail?CaseNo=ARB/23/39"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        latest_development = extract_latest_development(soup)
        case_status = extract_case_status(soup)
        
        page_text = soup.get_text().lower()
        has_award_mentions = 'award' in page_text
        has_decision_mentions = 'decision' in page_text
        
        return {
            'latest_development': latest_development,
            'case_status': case_status,
            'has_award_mentions': has_award_mentions,
            'has_decision_mentions': has_decision_mentions,
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        print(f"Error fetching case data: {e}")
        return None

def format_daily_report(case_info):
    if not case_info:
        return "❌ *Error retrieving case information*\n\nUnable to connect to ICSID database."
    
    argentina_time = datetime.now().strftime('%d/%m/%Y')
    
    report = [
        f"📅 *Daily Report - {argentina_time}*",
        "",
        f"📋 *Latest Development:*",
        f"`{case_info['latest_development']}`",
        "",
        f"📊 *Case Status:* `{case_info['case_status']}`",
        ""
    ]
    
    if case_info.get('has_award_mentions'):
        report.append("🏆 *Alert:* Award mentioned in document")
        report.append("")
    
    if case_info.get('has_decision_mentions'):
        report.append("⚖️ *Note:* Decisions referenced in proceedings")
        report.append("")
    
    report.extend([
        f"🕐 *Checked:* {case_info['check_time']} UTC",
        "",
        f"*Case:* Abertis Infraestructuras v. Argentina",
        f"*Number:* ARB/23/39"
    ])
    
    return "\n".join(report)

def check_for_telegram_commands(token, chat_id):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            updates = response.json().get('result', [])
            recent_threshold = datetime.now().timestamp() - 180
            
            for update in updates[-5:]:
                message = update.get('message', {})
                message_date = message.get('date', 0)
                
                if message_date > recent_threshold:
                    text = message.get('text', '').lower().strip()
                    if text in ['/check', '/status', '/report', 'check', 'status', 'report']:
                        return text
    except Exception as e:
        print(f"Command check error: {e}")
    
    return None

def format_manual_report(case_info):
    if not case_info:
        return "❌ *Error retrieving information*\n\nUnable to connect to ICSID."
    
    argentina_time = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    report = [
        f"🔍 *Manual Query - {argentina_time}*",
        "",
        f"📋 *Latest Development:*",
        f"`{case_info['latest_development']}`",
        ""
    ]
    
    if case_info.get('has_award_mentions'):
        report.append("🏆 *Alert:* Award mentioned - verify manually")
        report.append("")
    
    report.extend([
        f"🕐 *Retrieved:* {case_info['check_time']} UTC",
        "",
        f"💡 *Available commands:*",
        f"`/check` - Immediate verification",
        f"`/status` - Case status",
        f"`/report` - Complete report"
    ])
    
    return "\n".join(report)

def main():
    print(f"ICSID Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_token or not chat_id:
        print("Configuration error: Missing environment variables")
        return
    
    command = check_for_telegram_commands(telegram_token, chat_id)
    
    if command:
        print(f"Processing manual command: {command}")
        
        case_info = get_case_info()
        
        if command in ['/check', 'check']:
            report = format_manual_report(case_info)
        elif command in ['/status', 'status']:
            if case_info:
                report = f"📊 *Status Check*\n\n📋 {case_info['latest_development'][:150]}...\n\n🕐 {case_info['check_time']}"
            else:
                report = "❌ Error retrieving status"
        else:
            report = format_manual_report(case_info) if case_info else "❌ Error retrieving information"
        
        if send_telegram_message(telegram_token, chat_id, report):
            print("Manual response sent successfully")
        else:
            print("Error sending manual response")
    
    else:
        print("Automated daily report execution")
        
        case_info = get_case_info()
        report = format_daily_report(case_info)
        
        if send_telegram_message(telegram_token, chat_id, report):
            print("Daily report sent successfully")
        else:
            print("Error sending daily report")
    
    print("Execution completed")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
