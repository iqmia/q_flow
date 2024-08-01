
from smtplib import SMTPRecipientsRefused
from flask import current_app
from flask_mail import Message
from q_flow.exceptions import InvalidEmail
from q_flow.extensions import mail

class App_Mail:
    def __init__(self, recipients):
        if type(recipients) == str:
            recipients = [recipients]
        self.recipients = recipients
        self.domain = current_app.config.get('MAIL_DOMAIN')
        self.sender = current_app.config.get('MAIL_USERNAME')

    def send_verification_email(self, verification_code):
        msg = Message(
            f'{self.client_app.name} - Email Verification',
            sender=self.sender, recipients=self.recipients,
            body=f'Your verification code for {self.client_app.name} is {verification_code}'
            )
        self.send_mail(msg)

    def send_password_reset_email(self, reset_code):
        msg = Message(
            f'{self.client_app.name} - Password Reset',
            sender=self.sender, recipients=self.recipients,
            body=f'Your password reset code is {reset_code}')
        self.send_mail(msg)

    @staticmethod
    def send_mail(msg: Message):
        try:
            mail.send(msg)
        except SMTPRecipientsRefused:
            raise InvalidEmail("No such email address on the domain")
        except Exception as e:
            raise InvalidEmail(f"Error sending email {e}")