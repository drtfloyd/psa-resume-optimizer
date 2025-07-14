from psa_license.license import get_user_mode
import streamlit as st
from PyPDF2 import PdfReader
import string
import io
import zipfile
import re
import json
import os
from collections import defaultdict
from typing import Dict, Set, List, Tuple, Optional

# --- CONFIGURATION ---

MAX_FILE_SIZE_MB = 10
MIN_WORD_LENGTH = 2
CACHE_TTL = 3600  # 1 hour

# --- ORIGINAL LICENSE VALIDATION ---

def check_license_status(license_key: str) -> Optional[str]:
    """
    Securely check license status with proper error handling.

    Args:
        license_key: License key to validate
        
    Returns:
        str or None: License tier or None if invalid
    """
    if not license_key:
        return None
        
    try:
        # Call the license validation function
        tier = get_user_mode(license_key)
        return tier if tier in ["pro", "enterprise"] else None
    except Exception as e:
        # Log error for debugging but don't expose details to user
        st.error("⚠️ License validation failed. Please check your key and try again.")
        return None

# --- TRUST & VISIBILITY TUNER ---

def calculate_trust_visibility_scores(results: Dict) -> Tuple[float, float]:
    """
    Calculate trust and visibility scores based on domain alignment.

    Trust Score: Average score of critical domains (0-100)
    Visibility Score: Hit rate for domains with gaps (0-100)

    Args:
        results: Analysis results dictionary
        
    Returns:
        tuple: (trust_score, visibility_score) both rounded to 1 decimal
    """
    domain_scores = results.get("domain_scores", {})
    critical_domains = set(results.get("critical_domains", []))
    domain_gaps = results.get("domain_gaps", {})

    # Calculate trust score (average of critical domain scores)
    trust_scores = [score for domain, score in domain_scores.items() if domain in critical_domains]
    trust_score = sum(trust_scores) / len(trust_scores) if trust_scores else 0
  
    # Calculate visibility score (domains with good coverage)
    if domain_gaps:
        visibility_hits = sum(1 for domain in domain_gaps 
                            if domain_scores.get(domain, 0) > 40)
        visibility_score = (visibility_hits / len(domain_gaps)) * 100
    else:
        visibility_score = 100 if domain_scores else 0

    return round(trust_score, 1), round(visibility_score, 1)

def generate_hyperprompt(results: Dict) -> str:
    """
    Generate an AI optimization prompt based on analysis results.

    Args:
        results: Analysis results dictionary
        
    Returns:
        str: Formatted prompt for AI resume optimization
    """
    soc_group = results.get("predicted_soc_group", "your target role")
    critical_domains = results.get("critical_domains", [])
    domain_gaps = results.get("domain_gaps", {})

    # Get top 5 missing keywords across all domains
    top_gaps = []
    for domain, gaps in domain_gaps.items():
        if domain in critical_domains:
            top_gaps.extend(gaps[:3])  # Take top 3 from each critical domain

    prompt_parts = [
        f"You are optimizing a resume for a role in {soc_group}.",
        f"Critical skill domains: {', '.join(critical_domains)}."
    ]

    if top_gaps:
        prompt_parts.append(f"Key missing terms to incorporate: {', '.join(top_gaps[:10])}.")

    prompt_parts.append("Maintain authentic voice while strategically incorporating relevant terminology.")

    return " ".join(prompt_parts)

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
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading keyword ontology...")
def load_ontology(ontology_path: str = "ontology.json") -> Optional[Dict]:
    """
    Load and cache the keyword ontology from JSON file.

    Args:
        ontology_path: Path to the ontology JSON file
        
    Returns:
        Dict or None: Ontology data or None if loading fails
    """
    if not os.path.exists(ontology_path):
        st.error(f"⚠️ Ontology file not found at '{ontology_path}'. Please ensure the file exists.")
        return None

    try:
        with open(ontology_path, 'r', encoding='utf-8') as f:
            ontology = json.load(f)
            
        # Validate ontology structure
        required_keys = ["SignalDomains", "SOC_Groups"]
        if not all(key in ontology for key in required_keys):
            st.error(f"⚠️ Invalid ontology structure. Missing required keys: {required_keys}")
            return None
            
        return ontology
    except json.JSONDecodeError as e:
        st.error(f"⚠️ Invalid JSON in ontology file: {e}")
        return None
    except Exception as e:
        st.error(f"⚠️ Error loading ontology: {e}")
        return None

def validate_file(file) -> bool:
    """
    Validate uploaded file size and type.

    Args:
        file: Streamlit UploadedFile object
        
    Returns:
        bool: True if valid, False otherwise
    """
    if file is None:
        return False
        
    # Check file size
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"⚠️ File '{file.name}' is too large. Maximum size: {MAX_FILE_SIZE_MB}MB")
        return False
        
    # Check file type
    valid_types = ["application/pdf", "text/plain"]
    if file.type not in valid_types:
        st.error(f"⚠️ Invalid file type. Please upload PDF or TXT files only.")
        return False
        
    return True

def extract_text_from_file(file) -> str:
    """
    Extract text content from uploaded file (PDF or TXT).

    Args:
        file: Streamlit UploadedFile object
        
    Returns:
        str: Extracted text content
    """
    if not validate_file(file):
        return ""
        
    try:
        file_stream = io.BytesIO(file.getvalue())
        
        if file.type == "application/pdf":
            reader = PdfReader(file_stream)
            text_parts = []
            
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    st.warning(f"⚠️ Could not extract text from page {i+1}: {e}")
                    
            return "\n".join(text_parts)
        else:
            # Handle text files with various encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            for encoding in encodings:
                try:
                    file_stream.seek(0)
                    return file_stream.read().decode(encoding)
                except UnicodeDecodeError:
                    continue
            
            st.warning("⚠️ Could not decode text file. Using fallback encoding.")
            return file_stream.read().decode('utf-8', errors='ignore')
            
    except Exception as e:
        st.error(f"⚠️ Failed to extract text from {file.name}: {e}")
        return ""

def clean_and_extract_words(text: str, preserve_phrases: bool = True) -> Set[str]:
    """
    Extract and clean words from text, optionally preserving multi-word phrases.

    Args:
        text: Raw text to process
        preserve_phrases: Whether to extract 2-3 word phrases
        
    Returns:
        Set[str]: Cleaned unique words/phrases
    """
    if not text:
        return set()

    # Normalize text
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Split camelCase
    text = re.sub(r'https?://\S+|\S+@\S+', '', text)  # Remove URLs and emails

    # Preserve hyphenated words and acronyms
    text = re.sub(r'(?<![A-Z])[^\w\s\-]|(?<=[A-Z])[^\w\s\-]', ' ', text)

    # Convert to lowercase for matching
    text_lower = text.lower()

    # Extract individual words
    words = {word for word in text_lower.split() 
            if len(word) > MIN_WORD_LENGTH and not word.isdigit()}

    # Extract 2-word phrases if requested
    if preserve_phrases:
        tokens = text_lower.split()
        for i in range(len(tokens) - 1):
            phrase = f"{tokens[i]} {tokens[i+1]}"
            if len(tokens[i]) > MIN_WORD_LENGTH and len(tokens[i+1]) > MIN_WORD_LENGTH:
                words.add(phrase)

    return words

@st.cache_data(show_spinner="Analyzing documents...")
def run_enhanced_ontological_analysis(resume_file, jd_file, ontology: Dict, soc_override: Optional[str] = None) -> Optional[Dict]:
    """
    Enhanced analysis with business-friendly ontology terms and aggressive SOC detection.
    """
    # Extract text from files
    resume_text = extract_text_from_file(resume_file)
    jd_text = extract_text_from_file(jd_file)

    if not resume_text:
        st.error("⚠️ Could not extract text from resume")
        return None
    if not jd_text:
        st.error("⚠️ Could not extract text from job description")
        return None

    # Extract words and phrases
    resume_words = clean_and_extract_words(resume_text)
    jd_words = clean_and_extract_words(jd_text)

    if not resume_words:
        st.error("⚠️ No valid content found in resume")
        return None
    if not jd_words:
        st.error("⚠️ No valid content found in job description")
        return None

    # FOCUSED BUSINESS TERMS - REDUCED DILUTION
    business_term_mappings = {
        "Leadership & Influence": [
            "project management", "project manager", "team leadership", "stakeholder management", 
            "scrum master", "product owner", "manager", "director", "coordination", "planning", 
            "execution", "delivery", "milestone", "leadership", "vision", "strategy", "oversight",
            "team lead", "cross-functional", "program management", "change management"
        ],
        "Systems & Structure": [
            "agile", "scrum", "waterfall", "kanban", "methodology", "process", "workflow", 
            "SDLC", "requirements", "specifications", "deliverables", "timeline", "budget", 
            "scope", "quality assurance", "testing", "deployment", "implementation", "integration",
            "project lifecycle", "framework", "standards", "configuration", "governance"
        ],
        "AI & Technical Literacy": [
            "technology", "software", "IT", "information technology", "technical", "systems", 
            "development", "programming", "database", "cloud", "security", "networking",
            "applications", "digital", "engineering", "hardware", "technical requirements"
        ],
        "Communication Strategy": [
            "communication", "collaboration", "documentation", "reporting", "meeting", 
            "stakeholder", "team", "coordination", "facilitation", "presentation",
            "client", "customer", "vendor", "partner", "interdisciplinary"
        ],
        "Data & Evidence": [
            "analysis", "reporting", "metrics", "performance", "measurement", "evaluation", 
            "quality", "testing", "documentation", "data", "tracking", "monitoring",
            "KPIs", "dashboard", "assessment", "review", "audit", "validation"
        ],
        "Outcomes & Impact": [
            "results", "outcomes", "success", "performance", "improvement", "efficiency", 
            "productivity", "ROI", "value", "impact", "goals", "objectives", "delivery",
            "achievements", "optimization", "cost reduction", "benefit"
        ],
        "Risk & Compliance": [
            "risk management", "compliance", "standards", "policies", "procedures", 
            "security", "safety", "audit", "quality", "regulatory", "governance"
        ],
        "Adaptation & Flexibility": [
            "change", "flexibility", "adaptability", "problem solving", "troubleshooting", 
            "innovation", "improvement", "scalability", "agility", "evolution"
        ],
        "Collaboration & Relational Work": [
            "teamwork", "collaboration", "partnership", "coordination", "support",
            "communication", "relationship", "shared goals", "trust"
        ]
    }
    
    # Create enhanced ontology
    enhanced_ontology = ontology.copy()
    
    # Add focused business terms to existing domains
    for domain, business_terms in business_term_mappings.items():
        if domain in enhanced_ontology["SignalDomains"]:
            # Replace original terms with business-focused terms
            enhanced_ontology["SignalDomains"][domain] = business_terms
        else:
            # Create new domain if it doesn't exist
            enhanced_ontology["SignalDomains"][domain] = business_terms
    
    signal_domains = enhanced_ontology.get("SignalDomains", {})
    soc_groups = enhanced_ontology.get("SOC_Groups", {})

    # Pre-compute domain keywords for efficiency
    domain_keyword_map = {}
    for domain_name, keywords in signal_domains.items():
        domain_keywords = set()
        for phrase in keywords:
            # Add both the full phrase and individual words
            phrase_lower = phrase.lower()
            domain_keywords.add(phrase_lower)
            # Also add individual words from multi-word phrases
            domain_keywords.update(phrase_lower.split())
        domain_keyword_map[domain_name] = domain_keywords

    # AGGRESSIVE SOC GROUP PREDICTION FOR IT/MANAGEMENT ROLES
    best_soc_group, max_soc_score = None, -1
    soc_scores = {}
    
    # Respect manual override if provided
    if soc_override and soc_override != "Auto Detect" and soc_override in soc_groups:
        best_soc_group = soc_override
        max_soc_score = 100.0
        for group_name in soc_groups:
            soc_scores[group_name] = 100.0 if group_name == soc_override else 0.0
    else:
        # EXPLICIT IT/MANAGEMENT DETECTION
        jd_lower = jd_text.lower()
        
        # Check for explicit IT/Management indicators
        it_indicators = [
            'project manager', 'project management', 'it project', 'agile', 'scrum', 
            'kanban', 'waterfall', 'stakeholder', 'deliverable', 'milestone', 'sdlc', 
            'requirements', 'software development', 'technical', 'technology'
        ]
        management_indicators = [
            'team lead', 'leadership', 'manager', 'management', 'director', 'supervisor', 
            'coordination', 'planning', 'strategy', 'oversight', 'cross-functional'
        ]
        
        it_score = sum(1 for term in it_indicators if term in jd_lower)
        mgmt_score = sum(1 for term in management_indicators if term in jd_lower)
        
        # FORCE CORRECT CATEGORIZATION BASED ON EXPLICIT TERMS
        if it_score >= 3 and mgmt_score >= 2:
            # Strong IT + Management indicators = Management Occupations
            best_soc_group = "Management Occupations"
            max_soc_score = 85.0
            soc_scores = {
                "Management Occupations": 85.0,
                "Computer and Mathematical Occupations": 75.0,
                "AI, Data & UX Leadership Occupations": 70.0,
                "Life, Physical, and Social Science Occupations": 15.0,
                "Education, Training, and Library Occupations": 10.0
            }
        elif it_score >= 2:
            # Strong IT indicators = Computer and Mathematical 
            best_soc_group = "Computer and Mathematical Occupations"
            max_soc_score = 80.0
            soc_scores = {
                "Computer and Mathematical Occupations": 80.0,
                "Management Occupations": 65.0,
                "AI, Data & UX Leadership Occupations": 60.0,
                "Life, Physical, and Social Science Occupations": 20.0,
                "Education, Training, and Library Occupations": 15.0
            }
        elif mgmt_score >= 2:
            # Management indicators = Management Occupations
            best_soc_group = "Management Occupations"
            max_soc_score = 75.0
            soc_scores = {
                "Management Occupations": 75.0,
                "Computer and Mathematical Occupations": 50.0,
                "Life, Physical, and Social Science Occupations": 25.0,
                "Education, Training, and Library Occupations": 20.0
            }
        else:
            # Fallback to domain-based detection with heavy penalties for wrong categories
            for group_name, group_data in soc_groups.items():
                triggered_domains = 0
                domain_scores = []
                
                for domain in group_data.get("signal_domains", []):
                    if domain in domain_keyword_map:
                        domain_keywords = domain_keyword_map[domain]
                        domain_jd_keywords = domain_keywords.intersection(jd_words)
                        if domain_jd_keywords:
                            triggered_domains += 1
                            matched_keywords = domain_jd_keywords.intersection(resume_words)
                            domain_score = len(matched_keywords) / len(domain_jd_keywords) if domain_jd_keywords else 0
                            domain_scores.append(domain_score)

                if triggered_domains >= 1:  # Lower threshold
                    avg_domain_score = sum(domain_scores) / len(domain_scores) if domain_scores else 0
                    score = avg_domain_score * 100
                    
                    # HEAVY PENALTIES FOR WRONG CATEGORIES
                    if any(term in group_name.lower() for term in ['life', 'physical', 'social', 'science']):
                        score *= 0.2  # Heavy penalty for sciences
                    elif any(term in group_name.lower() for term in ['education', 'training', 'library']):
                        score *= 0.4  # Penalty for education
                    elif 'management' in group_name.lower():
                        score *= 1.5  # Boost management
                    elif 'computer' in group_name.lower():
                        score *= 1.3  # Boost computer
                        
                    score = min(score, 100)
                else:
                    score = 0
                    
                soc_scores[group_name] = round(score, 1)
                if score > max_soc_score:
                    max_soc_score, best_soc_group = score, group_name

    # Fill in missing SOC groups with 0 score
    for group_name in soc_groups.keys():
        if group_name not in soc_scores:
            soc_scores[group_name] = 0.0

    # Calculate domain scores and gaps with enhanced matching
    domain_scores, domain_gaps = {}, {}
    all_jd_keywords = set()

    for domain_name, domain_keywords in domain_keyword_map.items():
        # Find domain keywords in job description
        domain_jd_keywords = domain_keywords.intersection(jd_words)
        
        if domain_jd_keywords:
            all_jd_keywords.update(domain_jd_keywords)
            
            # Calculate match score
            matched_keywords = domain_jd_keywords.intersection(resume_words)
            score = (len(matched_keywords) / len(domain_jd_keywords)) * 100
            domain_scores[domain_name] = round(score, 1)
            
            # Find gaps (prioritize business terms)
            gaps = domain_jd_keywords - resume_words
            if gaps:
                # Sort gaps by importance (business terms first)
                business_priority = []
                other_priority = []
                
                # Define high-priority business terms
                high_priority_terms = [
                    'project', 'management', 'agile', 'scrum', 'team', 'stakeholder', 
                    'delivery', 'planning', 'requirements', 'technical', 'strategy'
                ]
                
                for gap in gaps:
                    if any(priority_term in gap for priority_term in high_priority_terms):
                        business_priority.append(gap)
                    else:
                        other_priority.append(gap)
                
                # Combine with business terms first
                sorted_gaps = business_priority + other_priority
                domain_gaps[domain_name] = sorted_gaps[:20]  # Top 20 gaps

    # IMPROVED OVERALL SCORE CALCULATION
    if all_jd_keywords:
        overall_matched = all_jd_keywords.intersection(resume_words)
        base_score = (len(overall_matched) / len(all_jd_keywords)) * 100
        
        # Apply boost for business context
        business_boost = 1.0
        if any(term in jd_text.lower() for term in ['project manager', 'agile', 'scrum', 'stakeholder']):
            business_boost = 1.3  # 30% boost for clear business context
            
        overall_score = min(base_score * business_boost, 100)
    else:
        overall_score = 0

    # Get suggested titles and critical domains
    suggested_titles = soc_groups.get(best_soc_group, {}).get("example_titles", [])
    critical_domains = soc_groups.get(best_soc_group, {}).get("signal_domains", [])

    return {
        "predicted_soc_group": best_soc_group,
        "soc_scores": soc_scores,
        "critical_domains": critical_domains,
        "domain_scores": domain_scores,
        "domain_gaps": domain_gaps,
        "overall_score": round(overall_score, 1),
        "total_jd_keywords": len(all_jd_keywords),
        "matched_keywords": len(all_jd_keywords.intersection(resume_words)),
        "resume_text": resume_text[:500] + "..." if len(resume_text) > 500 else resume_text,
        "jd_text": jd_text[:500] + "..." if len(jd_text) > 500 else jd_text,
        "suggested_titles": suggested_titles
    }

# --- SIDEBAR UI ---

with st.sidebar:
    st.title("PSA™ Resume Optimizer")
    st.markdown("---")

    # License validation section
    st.header("🔐 Access Control")
    license_key = st.text_input(
        "Enter your PSA™ License Key", 
        type="password", 
        key="license_input_sidebar",
        help="Your PSA™ license key provides access to advanced ontological analysis. Contact support@psa.ai for license information or use 'test' for demo access."
    )

    # Initialize session state for license
    if 'license_tier' not in st.session_state:
        st.session_state.license_tier = None

    # Check license on key change
    if license_key:
        with st.spinner("Validating license..."):
            st.session_state.license_tier = check_license_status(license_key)

    # Load ontology regardless of license status
    ontology = load_ontology()

    # Optional manual SOC override
    if ontology:
        soc_options = ["Auto Detect"] + sorted(ontology.get("SOC_Groups", {}).keys())
        soc_choice = st.selectbox(
            "🎛️ Optional: Target Job Category",
            soc_options,
            help="Override automatic job category detection. Use this if PSA's auto-detection doesn't match your target role, or to test how your resume performs for different career paths."
        )
        st.session_state.soc_override = soc_choice

    # Main functionality - only available with valid license
    if st.session_state.license_tier in ["pro", "enterprise"]:
        st.success(f"✅ {st.session_state.license_tier.title()} License Active")
        st.markdown("---")
        
        # File upload section
        st.header("📂 Upload Documents")
        
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Step 1")
            resume_file = st.file_uploader(
                "Upload Resume", 
                type=["pdf", "txt"],
                key="resume_upload",
                help="Upload your current resume for analysis. PDF or TXT format, max 10MB. The system will extract text and analyze your skill signals against the target job."
            )
        
        with col2:
            st.caption("Step 2")
            jd_file = st.file_uploader(
                "Upload Job Description", 
                type=["pdf", "txt"],
                key="jd_upload",
                help="Upload the job description for your target position. PDF or TXT format, max 10MB. PSA will analyze required skills and compare against your resume."
            )

        # Store files in session state
        if resume_file:
            st.session_state.resume_file = resume_file
        if jd_file:
            st.session_state.jd_file = jd_file

        st.markdown("---")
        
        # Analysis button
        analyze_button = st.button(
            "🚀 Analyze Now", 
            use_container_width=True, 
            type="primary",
            disabled=not (resume_file and jd_file and ontology),
            help="Start PSA ontological analysis. This will compare your resume against the job description using advanced domain-based matching algorithms."
        )
        
        if analyze_button:
            if resume_file and jd_file and ontology:
                try:
                    with st.spinner("Performing deep ontological analysis..."):
                        results = run_enhanced_ontological_analysis(
                            resume_file,
                            jd_file,
                            ontology,
                            soc_override=st.session_state.get("soc_override")
                        )
                        if results:
                            st.session_state.analysis_results = results
                            st.success("✅ Analysis Complete!")
                            st.balloons()
                        else:
                            st.error("⚠️ Analysis failed. Please check your files and try again.")
                except Exception as e:
                    st.error(f"⚠️ An error occurred during analysis: {str(e)}")
            else:
                missing = []
                if not resume_file:
                    missing.append("Resume")
                if not jd_file:
                    missing.append("Job Description")
                if not ontology:
                    missing.append("Ontology configuration")
                st.warning(f"Please provide: {', '.join(missing)}")
        
        # Quick stats if analysis exists
        if 'analysis_results' in st.session_state and st.session_state.analysis_results:
            st.markdown("---")
            st.caption("📊 Quick Stats")
            results = st.session_state.analysis_results
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Match", 
                    f"{results.get('overall_score', 0):.0f}%",
                    help="Overall resume alignment with target position"
                )
            with col2:
                st.metric(
                    "Gaps", 
                    len(results.get('domain_gaps', {})),
                    help="Number of skill domains with improvement opportunities"
                )
    else:
        if license_key:
            st.error("❌ Invalid or expired license key")
        st.info("👋 Enter a valid license key to begin")
        
        # Demo mode hint
        with st.expander("🎯 Don't have a license?"):
            st.write("""
            PSA™ licenses provide access to:
            - Advanced ontological analysis
            - AI-powered optimization
            - Career path recommendations
            
            Visit [psa.ai/pricing](https://psa.ai/pricing) for more information.
            """)

    st.markdown("---")
    st.caption("© PSA™ & AIaPI™ Framework v2.0")

# --- MAIN PANEL UI ---

st.title("📄 PSA™ Resume & Career Optimizer")
st.caption("Presence Signaling Architecture (PSA™) powered by AI as Presence Interface (AIaPI™)")

# Check if we have analysis results
if 'analysis_results' not in st.session_state or st.session_state.analysis_results is None:
    # Welcome screen
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🎯 Precision Matching")
        st.write("Advanced ontological analysis identifies exact skill alignments")

    with col2:
        st.markdown("### 🔍 Gap Intelligence")
        st.write("Discover missing keywords that could unlock opportunities")

    with col3:
        st.markdown("### 🤖 AI Optimization")
        st.write("Generate targeted prompts for resume enhancement")

    st.info("👈 Enter your license key and upload documents in the sidebar to begin analysis")
    st.markdown(
        "<span style='color: #2c3e50; font-size: 16px;'>"
        "Tip: If auto‑detect picks the wrong job category, select your target category in the sidebar and re‑run the analysis."
        "</span>",
        unsafe_allow_html=True
    )

else:
    # Display analysis results
    results = st.session_state.analysis_results

    # Create tabs for different views
    tab_names = ["📊 Strategic Scorecard", "🔍 Gap Analysis", "💼 Career Paths", "🤖 AI Optimizer", "📈 Advanced Insights"]
    tabs = st.tabs(tab_names)

    with tabs[0]:  # Strategic Scorecard
        st.header("📝 Comprehensive Analysis Summary", help="Complete overview of your resume's alignment with the target position using PSA ontological analysis")
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        overall_score = results.get('overall_score', 0)
        with col1:
            st.metric(
                "Overall Match", 
                f"{overall_score:.1f}%",
                f"{results.get('matched_keywords', 0)}/{results.get('total_jd_keywords', 0)} keywords",
                help="Percentage of job description keywords found in your resume. Higher scores indicate stronger alignment with the target role."
            )
        
        trust_score, visibility_score = calculate_trust_visibility_scores(results)
        with col2:
            st.metric(
                "Trust Score", 
                f"{trust_score}%",
                delta=f"{trust_score - 50:.0f}" if trust_score != 0 else None,
                help="Average performance in critical domains for your predicted role. Measures credibility and expertise signals in essential skill areas."
            )
        
        with col3:
            st.metric(
                "Visibility Score", 
                f"{visibility_score}%",
                delta=f"{visibility_score - 50:.0f}" if visibility_score != 0 else None,
                help="Percentage of domains where you show good coverage (>40%). Indicates how well your professional presence signals across multiple skill areas."
            )
        
        with col4:
            gap_count = sum(len(gaps) for gaps in results.get('domain_gaps', {}).values())
            st.metric(
                "Improvement Areas", 
                gap_count,
                "keywords to add",
                help="Total number of strategic keywords missing from your resume. These represent optimization opportunities to increase your match score."
            )

        # Overall progress bar
        st.markdown("### 🎯 Overall Resume Alignment", help="Visual representation of your resume's match strength with the target position")
        progress_col1, progress_col2 = st.columns([3, 1])
        with progress_col1:
            st.progress(int(overall_score))
        with progress_col2:
            if overall_score >= 80:
                st.success("Excellent Match!")
            elif overall_score >= 60:
                st.warning("Good Match")
            else:
                st.error("Needs Work")

        # Predicted job category with confidence
        st.markdown("### 🏢 Job Category Analysis", help="PSA's prediction of your best-fit career category based on skill domain analysis")
        soc_group = results.get('predicted_soc_group')
        if soc_group:
            soc_scores = results.get('soc_scores', {})
            top_score = soc_scores.get(soc_group, 0) if soc_scores else 0
            
            st.info(f"**Best Match:** {soc_group} (Confidence: {top_score:.0f}%)")
            
            # Show other potential matches if close
            if soc_scores:
                other_matches = [(k, v) for k, v in soc_scores.items() 
                               if k != soc_group and v > top_score * 0.7]
                if other_matches:
                    st.caption("Other potential matches:")
                    for match, score in sorted(other_matches, key=lambda x: x[1], reverse=True)[:3]:
                        st.caption(f"• {match} ({score:.0f}%)")
        else:
            st.warning("Could not determine job category - ontology may need updating")

        # Domain scores visualization
        st.markdown("### 📊 Signal Domain Performance", help="Breakdown of your performance in each skill domain. Critical domains (🔥) are most important for your predicted role.")
        critical_domains = set(results.get('critical_domains', []))
        domain_scores = results.get('domain_scores', {})
        
        if domain_scores:
            # Sort by score and critical status
            sorted_scores = sorted(
                domain_scores.items(), 
                key=lambda x: (x[0] not in critical_domains, -x[1])
            )
            
            for domain, score in sorted_scores:
                col1, col2 = st.columns([3, 1])
                with col1:
                    label = f"**{domain}**" if domain in critical_domains else domain
                    if domain in critical_domains:
                        st.markdown(f"{label} 🔥")
                    else:
                        st.markdown(label)
                    st.progress(int(score))
                with col2:
                    if score >= 80:
                        st.success(f"{score:.0f}%")
                    elif score >= 50:
                        st.warning(f"{score:.0f}%")
                    else:
                        st.error(f"{score:.0f}%")
        else:
            st.write("No domain scores calculated - check ontology configuration")

    with tabs[1]:  # Gap Analysis
        st.header("🔍 Strategic Keyword Gap Analysis", help="Detailed breakdown of missing keywords that could strengthen your resume's alignment with the target position")
        
        domain_gaps = results.get('domain_gaps', {})
        critical_domains = set(results.get('critical_domains', []))
        
        if domain_gaps:
            # Summary stats
            total_gaps = sum(len(gaps) for gaps in domain_gaps.values())
            critical_gaps = sum(len(gaps) for domain, gaps in domain_gaps.items() 
                              if domain in critical_domains)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Total Gaps", 
                    total_gaps,
                    help="Total number of relevant keywords missing from your resume across all skill domains"
                )
            with col2:
                st.metric(
                    "Critical Gaps", 
                    critical_gaps, 
                    help="Missing keywords in domains that are most important for your target role. Focus here for maximum impact."
                )
            with col3:
                st.metric(
                    "Affected Domains", 
                    len(domain_gaps),
                    help="Number of skill domains where keyword gaps were identified. Shows breadth of optimization opportunities."
                )
            
            st.markdown("---")
            
            # Detailed gap analysis
            st.markdown("### 📋 Missing Keywords by Domain")
            st.caption("💡 Focus on critical domains (marked with 🔥) for maximum impact")
            
            # Sort domains by criticality and gap count
            sorted_domains = sorted(
                domain_gaps.keys(), 
                key=lambda d: (d not in critical_domains, -len(domain_gaps[d]))
            )
            
            for domain in sorted_domains:
                gaps = domain_gaps[domain]
                is_critical = domain in critical_domains
                # Create expander with emoji and count
                emoji = "🔥" if is_critical else "📌"
                severity = "Critical" if is_critical else "Important"
                with st.expander(
                    f"{emoji} **{domain}** - {len(gaps)} missing keywords ({severity})",
                    expanded=is_critical and len(gaps) > 3
                ):
                    # Display gaps using Streamlit-native components for safety and accessibility
                    if gaps:
                        st.markdown("#### Missing Keywords:", unsafe_allow_html=False)
                        # Use st.code for a block, or st.text for each, or st.write as a list
                        # We'll use st.write as a bulleted list for clarity and a native look
                        show_gaps = gaps[:20]
                        st.write('\n'.join([f"- {word}" for word in show_gaps]))
                        if len(gaps) > 20:
                            st.info(f"+{len(gaps) - 20} more keywords not shown")
                    # Add quick tips for critical domains
                    if is_critical:
                        st.info(f"💡 **Tip:** Adding 3-5 of these keywords could significantly improve your match score")
        else:
            st.success("🎉 Excellent! No significant keyword gaps detected.")
            st.write("Your resume appears to cover all major skill areas from the job description.")

    with tabs[2]:  # Career Paths
        st.header("💼 Career Path Recommendations", help="Suggested career trajectories and job titles based on your skill profile and domain strengths")
        
        soc_group = results.get('predicted_soc_group')
        suggested_titles = results.get("suggested_titles", [])
        
        if soc_group:
            st.markdown(f"### Based on your profile: **{soc_group}**")
            
            if suggested_titles:
                st.markdown("#### 🎯 Recommended Job Titles", help="These specific job titles align well with your demonstrated skills and experience")
                st.write("These roles align well with your demonstrated skills:")
                
                # Display titles in a nice grid
                cols = st.columns(2)
                for i, title in enumerate(suggested_titles):
                    with cols[i % 2]:
                        st.markdown(f"• **{title}**")
                
                # Add career progression hints
                st.markdown("#### 📈 Career Progression", help="Strategic next steps to advance your career trajectory in your target field")
                st.info("""
                **Next Steps:**
                1. Target roles with these exact titles in your job search
                2. Update your LinkedIn headline to match these titles
                3. Tailor your resume summary to emphasize relevant domains
                """)
            else:
                st.write("No specific title recommendations available for this category.")
                
            # Show skill development priorities
            st.markdown("#### 🎓 Skill Development Priorities", help="Areas where strengthening your expertise would have the most impact on your career advancement")
            domain_scores = results.get('domain_scores', {})
            critical_domains = results.get('critical_domains', [])
            
            # Find weak critical domains
            weak_domains = [(d, score) for d, score in domain_scores.items() 
                          if d in critical_domains and score < 60]
            
            if weak_domains:
                st.write("Focus on strengthening these critical areas:")
                for domain, score in sorted(weak_domains, key=lambda x: x[1]):
                    st.markdown(f"• **{domain}** (current: {score:.0f}%)")
            else:
                st.success("✅ You're well-positioned in all critical skill areas!")
        else:
            st.warning("Unable to determine career category - please check your uploaded files")

    with tabs[3]:  # AI Optimizer
        st.header("🤖 AI-Powered Resume Optimization", help="Generate personalized prompts for AI assistants (ChatGPT, Claude, etc.) to optimize your resume based on your specific gap analysis")
        
        st.markdown("""
        Use this customized prompt with ChatGPT, Claude, or any AI assistant to optimize your resume.
        The prompt is specifically tailored to your gap analysis results.
        """)
        
        # Generate the hyperprompt
        hyper_prompt = generate_hyperprompt(results)
        
        # Display in a nice text area with copy button
        st.markdown("### 📝 Your Personalized AI Prompt", help="This prompt is automatically generated based on your specific gaps and target role. Copy it to use with any AI assistant.")
        
        prompt_container = st.container()
        with prompt_container:
            st.text_area(
                "Copy this prompt:", 
                hyper_prompt, 
                height=150,
                help="Select all text (Ctrl/Cmd+A) and copy (Ctrl/Cmd+C). Paste this into ChatGPT, Claude, or your preferred AI assistant along with your resume."
            )
        
        # Additional instructions
        st.markdown("### 🚀 How to Use This Prompt", help="Step-by-step guide for getting the best results from AI-powered resume optimization")
        
        with st.expander("Step-by-step instructions", expanded=True):
            st.markdown("""
            1. **Copy the prompt** above
            2. **Paste your current resume** into your AI tool of choice
            3. **Add the prompt** and ask the AI to rewrite specific sections
            4. **Review suggestions** - maintain authenticity while adding keywords
            5. **Iterate** - run the analysis again after updating
            
            **Pro Tips:**
            - Focus on naturally incorporating keywords into achievements
            - Don't stuff keywords - context matters
            - Update your LinkedIn profile with the same optimizations
            """)
        
        # Quick keyword reference
        domain_gaps = results.get('domain_gaps', {})
        critical_domains = results.get('critical_domains', [])
        
        if domain_gaps:
            st.markdown("### 🎯 Priority Keywords to Incorporate", help="High-impact keywords from your critical domains. Focus on these for maximum improvement in your match score.")

            # Get top keywords from critical domains
            priority_keywords = []
            for domain in critical_domains:
                if domain in domain_gaps:
                    priority_keywords.extend(domain_gaps[domain][:5])

            if priority_keywords:
                st.write("Focus on these high-impact terms:")
                # Streamlit-safe rendering (no raw HTML)
                st.write('\n'.join([f"- {kw}" for kw in priority_keywords[:15]]))

    with tabs[4]:  # Advanced Insights
        st.header("📈 Advanced Analytics & Insights", help="Deep dive into your profile's competitive positioning, optimization potential, and strategic recommendations")
        
        # SOC Group confidence visualization
        soc_scores = results.get('soc_scores', {})
        if soc_scores and len(soc_scores) > 1:
            st.markdown("### 🎯 Job Category Confidence Analysis", help="Confidence levels for different career categories. Shows how strongly your profile aligns with various professional paths.")
            
            # Create a bar chart of top matches
            sorted_socs = sorted(soc_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for soc, score in sorted_socs:
                col1, col2 = st.columns([3, 1])
                with col1:
                    if soc == results.get('predicted_soc_group'):
                        st.markdown(f"**{soc}** ✓")
                    else:
                        st.markdown(soc)
                    st.progress(int(score))
                with col2:
                    st.write(f"{score:.0f}%")
        
        # Domain correlation insights
        st.markdown("### 🔗 Domain Synergies", help="Analysis of your strongest and weakest skill domains. Identifies areas of expertise and improvement opportunities.")
        domain_scores = results.get('domain_scores', {})
        if len(domain_scores) > 2:
            high_scoring = [d for d, s in domain_scores.items() if s > 70]
            low_scoring = [d for d, s in domain_scores.items() if s < 30]
            
            if high_scoring:
                st.success(f"**Strong domains:** {', '.join(high_scoring[:5])}")
            if low_scoring:
                st.warning(f"**Needs attention:** {', '.join(low_scoring[:5])}")
        
        # Optimization potential
        st.markdown("### 💡 Optimization Potential", help="Projected improvement in your match score based on addressing identified gaps. Shows the potential ROI of resume optimization.")
        
        current_score = results.get('overall_score', 0)
        domain_gaps = results.get('domain_gaps', {})
        critical_domains = results.get('critical_domains', [])
        
        # Calculate potential score improvement
        critical_gap_count = sum(min(5, len(gaps)) for d, gaps in domain_gaps.items() 
                               if d in critical_domains)
        potential_improvement = min(30, critical_gap_count * 3)  # Rough estimate
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Current Score", 
                f"{current_score:.0f}%",
                help="Your current resume match percentage based on PSA ontological analysis"
            )
        with col2:
            st.metric(
                "Potential Score", 
                f"{min(95, current_score + potential_improvement):.0f}%",
                f"+{potential_improvement:.0f}%",
                help="Estimated score after strategically addressing critical domain gaps. Based on adding 3-5 keywords per critical domain."
            )
        
        # Quick wins
        if domain_gaps:
            st.markdown("### 🏃 Quick Wins", help="The 5 most impactful keywords to add to your resume. These offer the highest ROI for improving your match score.")
            st.write("Add these 5 keywords for maximum impact:")
            
            # Get highest impact keywords
            quick_wins = []
            for domain in critical_domains:
                if domain in domain_gaps:
                    quick_wins.extend(domain_gaps[domain][:2])
            
            if quick_wins:
                for i, keyword in enumerate(quick_wins[:5], 1):
                    st.write(f"{i}. **{keyword}**")
            else:
                st.info("Focus on keywords from your important domains")

# Footer
st.markdown("---")
st.markdown(
"""
<div style='text-align: center; color: #7f8c8d; font-size: 14px;'>
Powered by PSA™ (Presence Signaling Architecture) |
Built with ❤️ using AIaPI™ Framework |
© 2024 All Rights Reserved
</div>
""",
unsafe_allow_html=True
)
