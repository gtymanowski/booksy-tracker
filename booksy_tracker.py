import requests
import json
import os
from datetime import datetime
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Lista miast
CITIES = [
    "warszawa", "krakow", "lodz", "wroclaw", "poznan", "gdansk", "szczecin",
    "bydgoszcz", "lublin", "bialystok", "katowice", "czestochowa", "radom",
    "kielce", "torun", "gliwice", "zabrze", "bytom", "rzeszow", "olsztyn",
    "bielsko-biala", "tarnow", "opole", "gorzow-wielkopolski", "zielona-gora"
]

DATA_FILE = "seen_businesses.json"

def load_seen():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)

def get_all_categories():
    url = "https://pl.booksy.com/api/pl_PL/categories"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()  # jeśli status != 200, wyrzuć błąd
    return [cat["slug"] for cat in resp.json()]


def fetch_new_businesses():
    seen = load_seen()
    new_entries = []
    categories = get_all_categories()

    for city in CITIES:
        for category in categories:
            url = f"https://booksy.com/pl-pl/{category}/{city}/"
            resp = requests.get(url)
            if resp.status_code == 200 and 'booksy' in resp.text.lower():
                business_id = f"{city}-{category}"
                if business_id not in seen:
                    seen.add(business_id)
                    new_entries.append({
                        "city": city,
                        "category": category,
                        "url": url
                    })

    save_seen(seen)
    return new_entries

def generate_pdf(new_entries):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, "Nowe biznesy na Booksy", ln=True, align="C")

    for entry in new_entries:
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, f"{entry['city']} - {entry['category']}", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(200, 5, entry['url'])
        pdf.ln(2)

    filename = f"booksy_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    pdf.output(filename)
    return filename

def send_email(pdf_file):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    recipient = os.environ["EMAIL_TO"]

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = "Raport Booksy"

    with open(pdf_file, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={pdf_file}")
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

def upload_to_drive(pdf_file):
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    file_drive = drive.CreateFile({"title": pdf_file})
    file_drive.SetContentFile(pdf_file)
    file_drive.Upload()

def main():
    new_entries = fetch_new_businesses()
    if new_entries:
        pdf_file = generate_pdf(new_entries)
        send_email(pdf_file)
        upload_to_drive(pdf_file)

if __name__ == "__main__":
    main()

