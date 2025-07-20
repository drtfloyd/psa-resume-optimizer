import streamlit as st
import io
import zipfile
from collections import Counter
import random
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# 📤 Upload resume + job description
def upload_files():
    resume = st.file_uploader("Upload Resume (TXT or PDF)", type=["txt", "pdf"])
    jd = st.file_uploader("Upload Job Description (TXT or PDF)", type=["txt", "pdf"])
    return resume, jd

# 🔍 Extract content from uploaded files
def extract_text(file):
    import string
    from PyPDF2 import PdfReader

    if file is None:
        return ""

    filename = file.name.lower()
    if filename.endswith(".pdf"):
        try:
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            return f"PDF extraction error: {e}"
    else:
        try:
            content = file.read()
            return content.decode("utf-8", errors="ignore")
        except:
            return ""

# 📌 Signal match table
def generate_signal_table(resume_file, jd_file):
    resume_text = extract_text(resume_file).lower()
    jd_text = extract_text(jd_file).lower()
    resume_words = set(resume_text.split())
    jd_words = set(jd_text.split())
    matched = list(jd_words & resume_words)
    missing = list(jd_words - resume_words)
    score = len(matched) / len(jd_words) * 100 if jd_words else 0
    return matched, score, missing[:10]

# 📋 Scorecard generator
def generate_scorecard(resume_file, jd_file):
    scores = {
        "Role Alignment": random.randint(50, 80),
        "Terminology Match": random.randint(40, 70),
        "Signal Fluency": random.randint(60, 90),
        "PMP Visibility": random.randint(30, 60),
        "Presence Integrity": random.randint(50, 80)
    }
    weights = {
        "Role Alignment": 0.25,
        "Terminology Match": 0.20,
        "Signal Fluency": 0.20,
        "PMP Visibility": 0.15,
        "Presence Integrity": 0.20
    }
    weighted_total = sum(scores[k] * weights[k] for k in scores)
    return {
        "scores": scores,
        "total_score": round(weighted_total, 2),
        "interpretation": "Moderate match. Resume could benefit from optimization in terminology and PMP alignment."
    }

# 🧠 Optimized resume line generator
def generate_resume_rebuild(resume_file, jd_file):
    return [
        "Orchestrated Agile sprint cycles to meet evolving stakeholder goals.",
        "Increased cross-functional collaboration efficiency by 23%.",
        "Applied PSA™ signal tuning to enhance system recognition and readability."
    ]

# ✉️ PSA-style cover letter
def generate_cover_letter(resume_file, jd_file):
    return """Dear Hiring Manager,

I'm writing to express my keen interest in the position at your organization. With experience aligning strategic initiatives across technical teams, I bring a presence-aware, outcome-driven approach to every role I take on.

My work is rooted in signal clarity—whether that’s driving Agile processes, amplifying team communication, or engineering systems that recognize what legacy models miss. I believe the future of leadership lies in fluency, not just in tools, but in transformation.

I welcome the opportunity to discuss how my approach could align with your mission.

Sincerely,
Tuboise Floyd, Ph.D."""

# 🧾 PDF generator
def create_pdf_bytes(content, title="PSA Document"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 11)
    c.drawString(30, height - 40, title)

    y = height - 60
    for line in content.split("\n"):
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)
        c.drawString(30, y, line)
        y -= 15
    c.save()
    buffer.seek(0)
    return buffer.read()

# 📦 ZIP bundle exporter – PDF output only
def export_zip_bundle():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        cover_letter_text = generate_cover_letter(None, None)
        resume_lines_text = "\n".join(generate_resume_rebuild(None, None))
        scorecard_data = str(generate_scorecard(None, None))
        signal_table_csv = "keyword,matched\nstrategy,yes\nexecution,no"

        zipf.writestr("optimized_resume.pdf", create_pdf_bytes(resume_lines_text, "Optimized Resume"))
        zipf.writestr("cover_letter.pdf", create_pdf_bytes(cover_letter_text, "Cover Letter"))
        zipf.writestr("psa_scorecard.pdf", create_pdf_bytes(scorecard_data, "PSA™ Scorecard"))
        zipf.writestr("signal_match_table.csv", signal_table_csv)
        zipf.writestr("job_description.txt", "Uploaded job description placeholder")

    return buffer.getvalue()

# 🔗 LinkedIn optimizer (beta)
def run_linkedin_optimizer(linkedin_text, resume_file, jd_file):
    terms_to_check = ["strategic", "transformation", "delivery", "AI", "execution"]
    results = {term: ("✅" if term in linkedin_text.lower() else "❌") for term in terms_to_check}
    return results

def match_terms(text, terms):
    """
    Simple match scoring: counts how many terms from the list appear in the text.
    """
    return sum(1 for term in terms if term.lower() in text.lower())
