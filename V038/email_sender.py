import subprocess
import sys
import os
import configparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

# Function to check and install dependencies
def check_and_install_dependencies():
    """Check and install required dependencies."""
    required_packages = {
        'configparser': 'configparser',
    }

    for package_name, module_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"{package_name} not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"{package_name} installed successfully.")

# Ensure dependencies are installed before importing other modules
check_and_install_dependencies()

# Path to the config file
CONFIG_DIR = os.path.join(os.getcwd(), 'config')
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, 'config.ini')

def read_email_settings():
    """Read email settings from the config.ini file."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE_PATH):
        print("Configuration file not found.")
        return None

    config.read(CONFIG_FILE_PATH)
    email_settings = {
        'smtp_server': config.get('Email', 'smtp_server', fallback=''),
        'smtp_port': config.get('Email', 'smtp_port', fallback=''),
        'smtp_username': config.get('Email', 'smtp_username', fallback=''),
        'smtp_password': config.get('Email', 'smtp_password', fallback=''),
        'email_recipient': config.get('Email', 'email_recipient', fallback=''),
    }
    return email_settings

def send_email(subject, body, attachment_path=None):
    """Send a basic email with optional attachment."""
    email_settings = read_email_settings()
    if not email_settings:
        print("Email settings not found or incomplete.")
        return False

    smtp_server = email_settings['smtp_server']
    smtp_port = email_settings['smtp_port']
    smtp_username = email_settings['smtp_username']
    smtp_password = email_settings['smtp_password']
    recipient_email = email_settings['email_recipient']

    # Include machine name in the subject
    machine_name = os.getenv('COMPUTERNAME', 'Unknown Machine')
    subject = f"{machine_name}: {subject}"

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Attach the file if provided
    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as file:
                part = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
            print(f"Attachment {attachment_path} added to the email.")
        except Exception as e:
            print(f"Error attaching file {attachment_path}: {e}")
    elif attachment_path:
        print(f"Attachment file not found: {attachment_path}")

    try:
        # Connect to the SMTP server and send the email
        print(f"Connecting to SMTP server {smtp_server}:{smtp_port}...")
        if smtp_port == "465":
            # Use SMTP_SSL if port 465 is specified
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # Use regular SMTP with TLS
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()
            server.starttls()
            print("TLS encryption enabled.")
        
        server.set_debuglevel(1)  # Enable SMTP debug output
        print("Logging in to SMTP server...")
        server.login(smtp_username, smtp_password)
        print("Logged in to SMTP server successfully.")

        print(f"Sending email to {recipient_email}...")
        server.sendmail(smtp_username, recipient_email, msg.as_string())
        print("Email sent successfully.")
        server.quit()
        print("SMTP connection closed.")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication error: {e}")
    except smtplib.SMTPConnectError as e:
        print(f"SMTP Connection error: {e}")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        try:
            server.quit()
            print("SMTP connection closed.")
        except Exception as e:
            print(f"Failed to close SMTP connection: {e}")
    return False

def get_current_csv_file():
    """Get the path of the current day's CSV file."""
    machine_name = os.getenv('COMPUTERNAME', 'Machine')
    current_date = datetime.now().strftime("%Y-%m-%d")
    csv_file_name = f"{machine_name}_{current_date}.csv"
    csv_file_path = os.path.join(os.getcwd(), csv_file_name)
    return csv_file_path

def send_daily_report():
    """Send the daily report email."""
    subject = "Daily System Monitoring Report"
    body = "Please find attached the system monitoring report for today."
    csv_file_path = get_current_csv_file()
    print("Preparing to send the daily report email...")
    return send_email(subject, body, csv_file_path)

def send_threshold_alert(exceeded_parameter):
    """Send an alert email when a threshold is exceeded."""
    subject = f"Threshold Alert: {exceeded_parameter} Exceeded"
    body = f"The {exceeded_parameter} has exceeded the defined threshold for more than three minutes."
    csv_file_path = get_current_csv_file()
    print(f"Preparing to send threshold alert for {exceeded_parameter}...")
    return send_email(subject, body, csv_file_path)

def send_drive_space_alert(drive_letter, free_space_gb):
    """Send an alert email when a drive's free space falls below the threshold."""
    subject = f"Drive Space Alert: Drive {drive_letter} Low on Space"
    body = (f"The free space on drive {drive_letter} has fallen below the defined threshold.\n"
            f"Current free space: {free_space_gb:.2f} GB.")
    csv_file_path = get_current_csv_file()
    print(f"Preparing to send drive space alert for drive {drive_letter} with free space {free_space_gb:.2f} GB...")
    return send_email(subject, body, csv_file_path)
