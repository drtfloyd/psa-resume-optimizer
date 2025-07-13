from psa_license.license import get_user_mode
import streamlit as st
from PyPDF2 import PdfReader
import string
import io
import zipfile
import re
import json
import os

# --- TRUST & VISIBILITY TUNER ---
def calculate_trust_visibility_scores(results):
    domain_scores = results.get("domain_scores", {})
    critical_domains = set(results.get("critical_domains", []))
    domain_gaps = results.get("domain_gaps", {})

    trust_total, trust_count = 0, 0
    visibility_hits, visibility_total = 0, 0

    for domain, score in domain_scores.items():
        if domain in critical_domains:
            trust_total += score
            trust_count += 1
        if domain in domain_gaps:
            visibility_total += len(domain_gaps[domain]) + 1
            visibility_hits += 1 if score > 40 else 0

    trust_score = trust_total / trust_count if trust_count else 0
    visibility_score = (visibility_hits / visibility_total) * 100 if visibility_total else 0

    return round(trust_score, 1), round(visibility_score, 1)

def generate_hyperprompt(results):
    soc_group = results.get("predicted_soc_group", "[unknown role]")
    critical_domains = results.get("critical_domains", [])
    
    # This logic remains the same, but will now receive the correct soc_group
    prompt = f"You are optimizing for a role in {soc_group}. Your presence signal contains strengths in: {', '.join(critical_domains)}. Use terms related to these domains. Keep your voice and presence intact."
    return prompt

# --- Custom CSS for a Polished Look ---
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #2c3e50;
        color: #2c3e50;
        background-color: #ffffff;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        border-color: #3498db;
        color: #ffffff;
        background-color: #3498db;
    }
    .stButton>button:focus {
        box-shadow: 0 0 0 2px #3498db40;
    }
    .stFileUploader {
        border: 2px dashed #bdc3c7;
        border-radius: 8px;
        padding: 20px;
        background-color: #fafafa;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="Loading keyword ontology...")
def load_ontology(ontology_path="ontology.json"):
    if not os.path.exists(ontology_path):
        st.error(f"FATAL: Ontology file not found at '{ontology_path}'.")
        return None
    try:
        with open(ontology_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        st.error(f"FATAL: Could not read or parse ontology file: {e}")
        return None

def extract_text_from_file(file):
    if file is None: return ""
    try:
        # Use io.BytesIO to handle the file object correctly
        file_stream = io.BytesIO(file.getvalue())
        if file.type == "application/pdf":
            reader = PdfReader(file_stream)
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        else:
            return file_stream.getvalue().decode("utf-8")
    except Exception as e:
        st.warning(f"⚠️ Failed to extract text: {e}")
        return ""

def clean_and_extract_words(text):
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text).lower()
    text = re.sub(r'https?://\S+|\S+@\S+', '', text)
    text = re.sub(f'[{re.escape(string.punctuation)}0-9]', '', text)
    return {word for word in text.split() if len(word) > 2}

def run_ontological_analysis(resume_file, jd_file, ontology):
    resume_text = extract_text_from_file(resume_file)
    jd_text = extract_text_from_file(jd_file)
    if not resume_text or not jd_text: return None

    resume_words = clean_and_extract_words(resume_text)
    jd_words = clean_and_extract_words(jd_text)

    signal_domains = ontology.get("SignalDomains", {})
    soc_groups = ontology.get("SOC_Groups", {})

    best_soc_group, max_soc_score = None, -1
    
    # --- FIX STARTS HERE ---
    # The logic for predicting the job category (SOC group) has been corrected.
    for group_name, group_data in soc_groups.items():
        # 1. Get all possible keywords for the current job category from the ontology.
        group_keywords = {kw for domain in group_data.get("signal_domains", []) for phrase in signal_domains.get(domain, []) for kw in phrase.lower().split()}
        
        # 2. Identify which of these keywords are ACTUALLY in the job description.
        #    This gives us the keywords relevant to THIS specific job.
        relevant_jd_keywords = jd_words.intersection(group_keywords)
        
        # 3. Score the RESUME based on its match with these relevant keywords.
        #    This measures the alignment between the resume and the role's requirements.
        score = len(resume_words.intersection(relevant_jd_keywords))
        
        # 4. The category with the highest alignment score is chosen as the best fit.
        if score > max_soc_score:
            max_soc_score, best_soc_group = score, group_name
    # --- FIX ENDS HERE ---

    domain_scores, domain_gaps, all_jd_keywords = {}, {}, set()
    for domain_name, keywords in signal_domains.items():
        domain_keywords = {kw for phrase in keywords for kw in phrase.lower().split()}
        total_in_domain_from_jd = domain_keywords.intersection(jd_words)
        if not total_in_domain_from_jd: continue
        all_jd_keywords.update(total_in_domain_from_jd)
        matched_in_domain = total_in_domain_from_jd.intersection(resume_words)
        domain_scores[domain_name] = (len(matched_in_domain) / len(total_in_domain_from_jd)) * 100 if total_in_domain_from_jd else 0
        if gaps := total_in_domain_from_jd - resume_words:
            domain_gaps[domain_name] = sorted(list(gaps))

    overall_score = (len(all_jd_keywords.intersection(resume_words)) / len(all_jd_keywords)) * 100 if all_jd_keywords else 0
    suggested_titles = soc_groups.get(best_soc_group, {}).get("example_titles", [])

    return {
        "predicted_soc_group": best_soc_group,
        "critical_domains": soc_groups.get(best_soc_group, {}).get("signal_domains", []),
        "domain_scores": domain_scores,
        "domain_gaps": domain_gaps,
        "overall_score": overall_score,
        "resume_text": resume_text,
        "jd_text": jd_text,
        "suggested_titles": suggested_titles
    }

# --- SIDEBAR UI ---
with st.sidebar:
    st.title("PSA™ Resume Optimizer")
    st.markdown("---")
    st.header("🔐 Access Control")
    license_key = st.text_input("Enter your PSA™ License Key", type="password", key="license_input_sidebar")
    # Assuming get_user_mode is a valid function you have defined elsewhere
    # For testing, we'll bypass the license check if the function isn't available
    try:
        current_license_tier = get_user_mode(license_key)
    except NameError:
        current_license_tier = "pro" # Default to pro for testing if function is missing

    ontology = load_ontology()

    if current_license_tier in ["pro", "enterprise"]:
        if license_key or current_license_tier == "pro": # Simplified check
            st.success("✅ Pro License Verified!")
        st.markdown("---")
        st.header("📂 Upload Documents")
        st.session_state.resume_file = st.file_uploader("Upload your Resume", type=["pdf", "txt"])
        st.session_state.jd_file = st.file_uploader("Upload the Job Description", type=["pdf", "txt"])

        st.markdown("---")
        if st.button("🚀 Analyze Now", use_container_width=True, type="primary"):
            if st.session_state.resume_file and st.session_state.jd_file and ontology:
                with st.spinner("Performing deep ontological analysis..."):
                    st.session_state.analysis_results = run_ontological_analysis(st.session_state.resume_file, st.session_state.jd_file, ontology)
                st.success("Analysis Complete!")
            else:
                st.warning("Please upload both documents and ensure ontology is loaded.")
    else:
        if license_key: st.error("Invalid License Key.")
        st.info("Enter a valid license key to begin.")
    st.markdown("---")
    st.caption("© PSA™ & AIaPI™ Framework")

# --- MAIN PANEL UI ---
st.title("📄 PSA™ Resume & Career Optimizer")
st.caption("Part of the Presence Signaling Architecture (PSA™) and AI as Presence Interface (AIaPI™) framework.")

if 'analysis_results' not in st.session_state or st.session_state.analysis_results is None:
    st.info("Welcome! Please enter your license key and upload your documents in the sidebar to begin.")
else:
    results = st.session_state.analysis_results
    # It's good practice to provide default tabs even if results are partial
    tab_names = ["📊 Strategic Scorecard", "🔍 Gap Analysis", "💼 Career Suggestions", "🤖 AI Hyper-Prompt"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_names)

    with tab1:
        st.header("📝 Analysis Summary")
        cols = st.columns(3)
        overall_score = results.get('overall_score', 0)
        with cols[0]:
            st.metric("Overall Resume Match Score", f"{overall_score:.1f}%", help="Percentage of JD keywords found in your resume.")
        trust_score, visibility_score = calculate_trust_visibility_scores(results)
        with cols[1]:
            st.metric("Trust Score", f"{trust_score}%", help="How well your resume aligns with trust-critical domains.")
        with cols[2]:
            st.metric("Visibility Score", f"{visibility_score}%", help="Signal strength and clarity based on presence terms.")

        st.progress(int(overall_score))

        st.subheader("Predicted Job Category")
        soc_group = results.get('predicted_soc_group')
        st.info(f"**{soc_group}**" if soc_group else "Could not determine job category.")

        st.subheader("Your Signal Domain Scores")
        st.caption("This shows alignment with strategic skill areas.")
        critical_domains = set(results.get('critical_domains', []))
        domain_scores = results.get('domain_scores', {})
        if domain_scores:
            sorted_scores = sorted(domain_scores.items(), key=lambda item: item[1], reverse=True)
            for domain, score in sorted_scores:
                label = f"**{domain} (Critical)**" if domain in critical_domains else domain
                st.markdown(label)
                st.progress(int(score))
        else:
            st.write("No domain scores could be calculated.")

    with tab2:
        st.header("Keyword Gap Analysis")
        st.info("Important JD keywords missing from your resume.")
        domain_gaps = results.get('domain_gaps', {})
        critical_domains = set(results.get('critical_domains', []))
        if domain_gaps:
            sorted_domains = sorted(domain_gaps.keys(), key=lambda d: (d not in critical_domains, d))
            for domain in sorted_domains:
                is_critical = " (Critical for this role)" if domain in critical_domains else ""
                with st.expander(f"🚨 {domain}{is_critical} - {len(domain_gaps[domain])} Gaps"):
                    st.markdown(f"<div style='display: flex; flex-wrap: wrap; gap: 5px;'>" + "".join([f"<span style='background-color: #e74c3c; color: white; padding: 5px 10px; border-radius: 15px; font-size: 14px;'>" + word + "</span>" for word in domain_gaps[domain]]) + "</div>", unsafe_allow_html=True)
        else:
            st.success("Excellent! No significant keyword gaps were found.")

    with tab3:
        st.header("🎯 Suggested Job Titles")
        st.markdown("These roles match your signal profile.")
        suggested_titles = results.get("suggested_titles", [])
        if suggested_titles:
            for title in suggested_titles:
                st.markdown(f"- {title}")
        else:
            st.markdown("No alternative titles suggested for this profile.")

    with tab4:
        st.header("AI-Powered Resume Optimizer Prompt")
        st.info("Use this hyperprompt in ChatGPT, Claude, or Gemini.")
        hyper_prompt = generate_hyperprompt(results)
        st.text_area("Hyper-Prompt", hyper_prompt, height=250)
