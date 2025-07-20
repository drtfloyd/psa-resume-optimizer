import streamlit as st
from PyPDF2 import PdfReader
import string

# --- License Key Utilities ---
def get_user_mode(license_key):
    license_tiers = st.secrets.get("psa", {}).get("license_tiers", {})
    return license_tiers.get(license_key.strip(), None)

# --- Placeholder Functions ---

def upload_files():
    st.subheader("Upload your documents")
    resume_file = st.file_uploader("Upload your Resume (PDF or DOCX)", type=["pdf", "docx"])
    jd_file = st.file_uploader("Upload the Job Description (PDF or TXT)", type=["pdf", "txt"])
    return resume_file, jd_file

def generate_signal_table(resume_file, jd_file):
    def extract_pdf_text(file):
        if file is None:
            st.warning("⚠️ No file provided for extraction.")
            return ""
        try:
            reader = PdfReader(file)
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception as e:
            st.warning(f"⚠️ Failed to extract text from uploaded file: {e}")
            return ""

    resume_text = extract_pdf_text(resume_file)
    jd_text = extract_pdf_text(jd_file)

    if not resume_text or not jd_text:
        return {}, 0.0, []

    resume_words = set(resume_text.lower().split())
    jd_words = set(jd_text.lower().split())

    matched = jd_words & resume_words
    missing = jd_words - resume_words

    match_table = {word: "matched" for word in matched}
    match_score = len(matched) / len(jd_words) * 100 if jd_words else 0.0
    gaps = list(missing)

    return match_table, match_score, gaps

def generate_cover_letter(resume_file, jd_file):
    return "Dear Hiring Manager,\n\nBased on your job description, I am an excellent fit for this role..."

def export_zip_bundle():
    from io import BytesIO
    import zipfile
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("placeholder.txt", "This is a placeholder file in the ZIP bundle.")
    return zip_buffer.getvalue()

def run_linkedin_optimizer(linkedin_input, resume_file, jd_file):
    return {"Headline Match": "High", "About Section Gaps": "Low"}

def generate_resume_rebuild(resume_file, jd_file):
    return ["Line 1 optimized", "Line 2 optimized"]

def generate_scorecard(resume_file, jd_file):
    return {
        "scores": {"Skills": 80, "Experience": 70, "Education": 90},
        "total_score": 80,
        "interpretation": "Solid alignment with job description."
    }

# --- Streamlit UI ---

st.set_page_config(layout="wide")
st.image("psa_logo.png", width=800)
st.caption("Part of the Presence Signaling Architecture (PSA™) and AI as Presence Interface (AIaPI™) framework.")

st.markdown("### 🔒 Privacy Disclaimer\n"
            "💡 This app does not store your files or collect any personal information. "
            "All processing is done temporarily in your browser session.")

license_key = st.text_input("🔐 Enter your PSA™ Pro License Key", type="password")
current_license_tier = get_user_mode(license_key)

st.title("📄 PSA™ Resume Optimizer")

if current_license_tier in ["pro", "enterprise"]:
    st.success("✅ Pro License Verified – Full Diagnostic Mode Enabled")
    st.markdown("---")
    st.subheader("🚀 Pro/Enterprise Features")

    try:
        resume_file, jd_file = upload_files()
        st.markdown("✅ Files uploaded")

        if resume_file and jd_file:
            st.markdown("✅ Starting signal processing...")
            match_table, match_score, gaps = generate_signal_table(resume_file, jd_file)

            st.markdown("### 📌 Basic Signal Match Table")
            st.write("**Matched Keywords:**", match_table)
            st.write("**Match Score:**", f"{match_score:.2f}%")

            st.markdown("### 🚨 Gap Flagging")
            cleaned_gaps = [word for word in gaps if all(c in string.printable for c in word) and word.strip()]
            st.write("**Missing from Resume:**", cleaned_gaps)

            st.markdown("### 🧾 PSA™ Resume Header Generator")
            st.write(" ")

            st.markdown("### 📉 ATS Visibility Alerts")
            st.warning("🚨 Some high-signal terms from the job description were not found in your resume.")

            st.markdown("### 🧠 Optimized Resume Line Suggestions")
            for line in generate_resume_rebuild(resume_file, jd_file):
                st.markdown(f"- {line}")

            st.markdown("### 📊 Machine Legibility Index (MLI)")
            st.write("**MLI Score:** 100.0%")

            st.markdown("### 📝 Summary Recommendation")
            st.info("Low alignment – consider restructuring.")

            if st.button("📋 Generate PSA™ Weighted Scorecard"):
                scorecard = generate_scorecard(resume_file, jd_file)
                st.subheader("📋 PSA™ Weighted Scorecard")
                for k, v in scorecard['scores'].items():
                    st.write(f"{k}: {v}%")
                st.write(f"**Total Weighted Score:** {scorecard['total_score']}%")
                st.info(scorecard["interpretation"])

            if st.button("✉️ Generate PSA™ Cover Letter"):
                st.subheader("✉️ PSA™ Cover Letter")
                st.text_area("Cover Letter Output", generate_cover_letter(resume_file, jd_file), height=300)

            if st.button("📦 Create Submission Bundle (ZIP)"):
                buffer = export_zip_bundle()
                st.download_button(
                    label="📥 Download ZIP",
                    data=buffer,
                    file_name="PSA_Submission_Bundle.zip",
                    mime="application/zip"
                )

            st.markdown("### 🔗 LinkedIn Optimization Alerts (Beta)")
            linkedin_input = st.text_area("Paste your LinkedIn Headline/About/Featured Section")
            if linkedin_input:
                st.markdown("**LinkedIn Match Report:**")
                results = run_linkedin_optimizer(linkedin_input, resume_file, jd_file)
                for k, v in results.items():
                    st.write(f"- {k}: {v}")
        else:
            st.info("⬆️ Please upload both your Resume and Job Description to proceed with analysis.")

    except Exception as e:
        st.error(f"❌ Error in rendering Pro tools: {e}")

else:
    st.info("🔒 Please enter a valid PSA™ Pro License Key to unlock Pro features.")
