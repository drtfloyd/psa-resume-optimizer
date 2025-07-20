import streamlit as st
import pandas as pd
from psa_auth import get_user_mode
from streamlit_io import get_clean_text
from psa_score_engine import generate_gap_analysis, get_psa_ontology, load_config
from utils import clean_text
from io import BytesIO
import base64

def resume_optimizer_view():
    st.header("PSA™ Resume Optimizer – Free Edition")
    st.markdown("Optimize your resume for a specific job using PSA signal matching.")

    license_key = st.text_input("Enter license key (optional):", type="password")
    user_mode = get_user_mode(license_key)
    st.caption(f"License Mode: {user_mode.title()}")

    col1, col2 = st.columns(2)
    with col1:
        jd_file = st.file_uploader("Upload Job Description (PDF or DOCX)", type=["pdf", "docx"])
    with col2:
        resume_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"])

    if jd_file and resume_file:
        jd_text = clean_text(get_clean_text(jd_file))
        resume_text = clean_text(get_clean_text(resume_file))

        ontology = get_psa_ontology()
        config = load_config()
        match_data, psa_score = generate_gap_analysis(resume_text, jd_text, ontology, config)

        st.subheader("Signal Match Table")
        df = pd.DataFrame(match_data)
        st.dataframe(df, use_container_width=True)

        st.metric("PSA Resume Score", f"{psa_score * 100:.1f}%")

        # --- Export Controls ---
        st.subheader("Export Results")
        export_name = "psa_resume_report"

        if st.button("Download .TXT"):
            txt = df.to_string(index=False)
            st.download_button("Click to Download .txt", txt, file_name=f"{export_name}.txt")

        if user_mode in ["pro", "enterprise"]:
            st.download_button("Download .DOCX", df.to_csv(index=False), file_name=f"{export_name}.docx")
            st.download_button("Download .PDF", df.to_csv(index=False), file_name=f"{export_name}.pdf")
        else:
            st.info("Upgrade to PRO to export as PDF or DOCX.")
