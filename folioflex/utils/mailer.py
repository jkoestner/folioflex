"""Emailer."""

import logging
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from folioflex.utils import config_helper


# logging options https://docs.python.org/3/library/logging.html
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")

# provides the logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)


def send_email(message, subject, emailee):
    """Send summary of portfolios to email.

    Parameters
    ----------
    message : object
        Message to send in email
    subject : str
        Subject of email
    emailee : str
        Email address to send email to

    Returns
    ----------
    bool
        True if email was sent successfully, False otherwise.

    """
    # Check if SMTP values are set
    for key, value in config_helper.__dict__.items():
        if key.startswith("SMTP_") and not value:
            logger.warning(f"{key} is not set, email not sent")
            return False

    # Create the email
    email = MIMEMultipart()
    email["Subject"] = subject
    email["From"] = config_helper.SMTP_USERNAME
    email["To"] = emailee

    message = MIMEText(message, "html")
    email.attach(message)

    # Send the email
    try:
        with smtplib.SMTP(config_helper.SMTP_SERVER, config_helper.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(config_helper.SMTP_USERNAME, config_helper.SMTP_PASSWORD)
            smtp.send_message(email)
        logger.info("Email sent successfully")
        return True
    except smtplib.SMTPException as e:
        logger.warning(f"Error sending email: {e}")
        return False
