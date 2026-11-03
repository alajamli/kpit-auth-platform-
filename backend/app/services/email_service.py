import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailService:
    """Service pour l'envoi d'e-mails de sécurité Brevo."""

    def __init__(self):
        # Récupération dynamique depuis le .env (les noms MAIL_* et SMTP_* sont acceptés)
        self.api_key = os.getenv('BREVO_API_KEY', '')
        self.smtp_server = os.getenv('MAIL_SERVER') or os.getenv('SMTP_HOST') or 'smtp-relay.brevo.com'
        self.smtp_port = int(os.getenv('MAIL_PORT') or os.getenv('SMTP_PORT') or 587)
        self.smtp_user = os.getenv('MAIL_USERNAME') or os.getenv('SMTP_USER') or ''
        self.smtp_password = os.getenv('MAIL_PASSWORD') or os.getenv('SMTP_PASSWORD') or ''
        self.sender_email = os.getenv('MAIL_DEFAULT_SENDER', 'security@kpit-auth.com')

    def send_otp_email(self, recipient_email: str, otp_code: str, user_name: str = "User") -> bool:
        subject = f" {otp_code} is your KPIT Security Verification Code"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: 'Inter', Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 500px; background: #ffffff; border-radius: 12px; margin: 0 auto; padding: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .header {{ text-align: center; padding-bottom: 20px; border-bottom: 1px solid #f1f5f9; }}
            .title {{ font-size: 20px; font-weight: 700; color: #0f172a; margin: 0; }}
            .subtitle {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
            .alert-box {{ background-color: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px; padding: 12px 16px; margin: 20px 0; color: #991b1b; font-size: 13px; line-height: 1.4; }}
            .code-box {{ background-color: #f1f5f9; border-radius: 8px; text-align: center; padding: 20px; margin: 24px 0; letter-spacing: 6px; font-size: 32px; font-weight: 800; color: #3730a3; font-family: monospace; }}
            .footer {{ font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 16px; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h2 class="title">KPIT Auth Platform</h2>
              <p class="subtitle">AI Behavioral Risk Security Notification</p>
            </div>
            
            <p>Hello <strong>{user_name}</strong>,</p>
            
            <div class="alert-box">
              ⚠️ <strong>Suspicious Login Detected:</strong> Our AI engine (Isolation Forest ML) detected an unusual sign-in attempt on your account.
            </div>
            
            <p>Please enter the following 6-digit verification code to complete your login:</p>
            
            <div class="code-box">{otp_code}</div>
            
            <p style="font-size: 12px; color: #64748b;">This code is valid for <strong>10 minutes</strong>. If you did not attempt to sign in, please change your password immediately.</p>
            
            <div class="footer">
              &copy; 2026 KPIT Auth Platform — AI-Enhanced Security Framework
            </div>
          </div>
        </body>
        </html>
        """

        # 1) API HTTPS Brevo : fonctionne là où les ports SMTP sortants sont bloqués (ex. Render)
        if self.api_key:
            try:
                resp = requests.post(
                    'https://api.brevo.com/v3/smtp/email',
                    headers={'api-key': self.api_key, 'accept': 'application/json'},
                    json={
                        'sender': {'name': 'KPIT Security Platform', 'email': self.sender_email},
                        'to': [{'email': recipient_email}],
                        'subject': subject,
                        'htmlContent': html_content,
                    },
                    timeout=15,
                )
                if resp.status_code < 300:
                    print(f"📧 [BREVO API SUCCESS] 2FA Code sent to {recipient_email}")
                    return True
                print(f"❌ [BREVO API ERROR] {resp.status_code} {resp.text[:200]}")
            except Exception as e:
                print(f"❌ [BREVO API ERROR] {e}")

        # 2) SMTP Brevo si les identifiants sont présents
        if self.smtp_user and self.smtp_password:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = f"KPIT Security Platform <{self.sender_email}>"
                msg['To'] = recipient_email
                msg.attach(MIMEText(html_content, 'html'))

                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.sender_email, recipient_email, msg.as_string())
                
                print(f"📧 [BREVO SMTP SUCCESS] 2FA Code sent to {recipient_email}")
                return True
            except Exception as e:
                print(f"❌ [BREVO SMTP ERROR] {e}")

        # Fallback console si .env incomplet
        print(f"\n📧 [MOCK OUTBOX] OTP Code for {recipient_email}: {otp_code}\n")
        return True


email_service = EmailService()