import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_alert_email(issue_summary: str = "Data quality issues detected") -> bool:
    sender_email = os.environ.get('EMAIL_SENDER')
    sender_password = os.environ.get('EMAIL_PASSWORD')
    recipient_email = os.environ.get('EMAIL_RECIPIENT')

    if not all([sender_email, sender_password, recipient_email]):
        print("Email credentials not set in environment variables.")
        return False
    
    subject = f" Data Quality Alert - {datetime.now().strftime('%Y-%m-%d')}"

    body = f"""
Data Quality Alert!

{issue_summary}

Full report is available in the GitHub repository:
https://github.com/awaliahftr/data-quality-checker

Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("✅ Alert email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


if __name__ == "__main__":
    send_alert_email("Test alert from data quality checker.")
