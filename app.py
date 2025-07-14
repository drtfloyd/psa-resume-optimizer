# === PSA™ RESUME OPTIMIZER - ENHANCED VERSION ===
# New Features: PDF Export + Progress Tracking
# Additional Dependencies Required:
# pip install reportlab pandas plotly

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
from datetime import datetime
import base64
from fpdf import FPDF
import pandas as pd

import plotly.graph_objects as go

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

def generate_pdf_report(results: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    # Add Inter font (regular and bold)
    try:
        pdf.add_font('Inter', '', 'Inter-Regular.ttf', uni=True)
        pdf.add_font('Inter', 'B', 'Inter-Bold.ttf', uni=True)
        pdf.set_font('Inter', 'B', size=14)
        pdf.cell(0, 10, "PSA™ Resume Gap Analysis Report", ln=True)
    except RuntimeError:
        # If Inter font files are missing, fall back to Arial and remove ™
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "PSA Resume Gap Analysis Report", ln=True)
        st.warning("Inter font not found. PDF report will not include special characters.")

    pdf.set_auto_page_break(auto=True, margin=15)
    domain_gaps = results.get("domain_gaps", {})
    for domain, gaps in domain_gaps.items():
        try:
            pdf.set_font('Inter', 'B', size=12)
            pdf.cell(0, 10, f"\n{domain}", ln=True)
            pdf.set_font('Inter', '', size=12)
        except:
            pdf.set_font('Arial', 'B', size=12)
            pdf.cell(0, 10, f"\n{domain}", ln=True)
            pdf.set_font('Arial', size=12)

        for kw in gaps:
            try:
                pdf.cell(0, 10, f" - {kw}", ln=True)
            except:
                kw_cleaned = kw.encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(0, 10, f" - {kw_cleaned}", ln=True)

    return pdf.output(dest='S').encode('latin-1')

def save_analysis_to_history(results: Dict):
    """Save current analysis to session history for progress tracking."""
    if 'analysis_history' not in st.session_state:
        st.session_state.analysis_history = []
    
    # Create history entry
    history_entry = {
        'timestamp': datetime.now(),
        'overall_score': results.get('overall_score', 0),
        'trust_score': calculate_trust_visibility_scores(results)[0],
        'visibility_score': calculate_trust_visibility_scores(results)[1],
        'predicted_soc_group': results.get('predicted_soc_group'),
        'domain_scores': results.get('domain_scores', {}),
        'total_gaps': sum(len(gaps) for gaps in results.get('domain_gaps', {}).values()),
        'critical_gaps': sum(len(gaps) for domain, gaps in results.get('domain_gaps', {}).items() 
                           if domain in results.get('critical_domains', []))
    }
    
    # Add to history (keep last 10 analyses)
    st.session_state.analysis_history.append(history_entry)
    if len(st.session_state.analysis_history) > 10:
        st.session_state.analysis_history = st.session_state.analysis_history[-10:]

def create_progress_chart(history: List[Dict]) -> go.Figure:
    """Create a progress tracking chart from analysis history."""
    if len(history) < 2:
        return None
    
    df = pd.DataFrame(history)
    df['analysis_number'] = range(1, len(df) + 1)
    
    fig = go.Figure()
    
    # Overall Score
    fig.add_trace(go.Scatter(
        x=df['analysis_number'],
        y=df['overall_score'],
        mode='lines+markers',
        name='Overall Match',
        line=dict(color='#3498db', width=3),
        marker=dict(size=8)
    ))
    
    # Trust Score
    fig.add_trace(go.Scatter(
        x=df['analysis_number'],
        y=df['trust_score'],
        mode='lines+markers',
        name='Trust Score',
        line=dict(color='#2ecc71', width=3),
        marker=dict(size=8)
    ))
    
    # Visibility Score
    fig.add_trace(go.Scatter(
        x=df['analysis_number'],
        y=df['visibility_score'],
        mode='lines+markers',
        name='Visibility Score',
        line=dict(color='#e74c3c', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='Your PSA Progress Over Time',
        xaxis_title='Analysis Session',
        yaxis_title='Score (%)',
        yaxis=dict(range=[0, 100]),
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig

def create_domain_comparison_chart(current_results: Dict, history: List[Dict]) -> go.Figure:
    """Create domain comparison chart showing improvement areas."""
    if len(history) < 2:
        return None
    
    current_domains = current_results.get('domain_scores', {})
    previous_domains = history[-2]['domain_scores']  # Second to last analysis
    
    domains = list(current_domains.keys())
    current_scores = [current_domains.get(d, 0) for d in domains]
    previous_scores = [previous_domains.get(d, 0) for d in domains]
    improvements = [curr - prev for curr, prev in zip(current_scores, previous_scores)]
    
    # Color code by improvement
    colors_list = ['#2ecc71' if imp > 0 else '#e74c3c' if imp < 0 else '#95a5a6' for imp in improvements]
    
    fig = go.Figure(data=[
        go.Bar(
            x=domains,
            y=improvements,
            marker_color=colors_list,
            text=[f"{imp:+.1f}%" for imp in improvements],
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title='Domain Score Changes Since Last Analysis',
        xaxis_title='Skill Domains',
        yaxis_title='Score Change (%)',
        template='plotly_white',
        xaxis_tickangle=-45
    )
    
    return fig


# --- Custom CSS for a Polished Look ---

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
    resume_text_lower = resume_text.lower()

    for domain_name, domain_keywords in domain_keyword_map.items():
        # Find domain keywords in job description
        domain_jd_keywords = domain_keywords.intersection(jd_words)
        
        if domain_jd_keywords:
            all_jd_keywords.update(domain_jd_keywords)
            
            # Calculate match score using substring matching
            matched_keywords = set()
            for keyword in domain_jd_keywords:
                if keyword.lower() in resume_text_lower:
                    matched_keywords.add(keyword)
            score = (len(matched_keywords) / len(domain_jd_keywords)) * 100
            domain_scores[domain_name] = round(score, 1)
            
            # Find gaps (prioritize business terms) using substring matching
            gaps = set()
            for keyword in domain_jd_keywords:
                if keyword.lower() not in resume_text_lower:
                    gaps.add(keyword)
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
        overall_matched = set()
        for keyword in all_jd_keywords:
            if keyword.lower() in resume_text_lower:
                overall_matched.add(keyword)
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
        "matched_keywords": len([kw for kw in all_jd_keywords if kw.lower() in resume_text_lower]),
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

        # PDF Export Section (remains between the columns)
        st.markdown("---")
        colpdf1, colpdf2, colpdf3 = st.columns([1, 2, 1])
        with colpdf2:
            if st.button("📄 Download Analysis Report"):
                if 'analysis_results' in st.session_state and st.session_state.analysis_results:
                    results = st.session_state.analysis_results
                    pdf_bytes = generate_pdf_report(results)
                    st.download_button("Download PDF", data=pdf_bytes, file_name="psa_resume_analysis.pdf", mime="application/pdf")
                else:
                    st.error("⚠️ Error generating PDF report: no analysis results available.")
                    st.info("💡 Tip: Try refreshing the page and running the analysis again.")
        st.markdown("---")

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
                            # Save to history for progress tracking
                            save_analysis_to_history(results)
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
    tab_names = ["📊 Strategic Scorecard",
                 "🔍 Gap Analysis",
                 "💼 Career Paths",
                 "🤖 AI Optimizer",
                 "📈 Advanced Insights",
                 "📋 Progress Tracking"]
    tabs = st.tabs(tab_names)

    with tabs[0]:  # Strategic Scorecard
        st.header("📊 Strategic Resume Match Scorecard", help="Understand your resume's alignment with the target role across key dimensions")

        if not results:
            st.info("Upload your resume and job description to get started.")
        else:
            # --- METRIC DISPLAY (4 COLUMNS) ---
            st.markdown("#### Key Metrics")
            col1, col2, col3, col4 = st.columns(4)
            overall_score = results.get('overall_score', 0)
            trust_score, visibility_score = calculate_trust_visibility_scores(results)
            domain_gaps = results.get("domain_gaps", {})
            improvement_areas = len(domain_gaps)

            with col1:
                st.metric("Overall Match", f"{overall_score:.1f}%", help="Resume alignment with job description")
            with col2:
                st.metric("Trust Score", f"{trust_score:.1f}%", help="Strength of critical skill signals")
            with col3:
                st.metric("Visibility Score", f"{visibility_score:.1f}%", help="Breadth of professional presence signals")
            with col4:
                st.metric("Improvement Areas", improvement_areas, help="Domains with skill gaps to address")

            # --- OVERALL RESUME ALIGNMENT PROGRESS BAR ---
            st.markdown("#### Overall Resume Alignment")
            st.progress(min(overall_score / 100, 1.0))
            if overall_score >= 80:
                st.success("Excellent alignment with the target role!")
            elif overall_score >= 60:
                st.info("Good match, but some areas for improvement.")
            else:
                st.warning("Significant gaps detected. Review the recommendations below.")

            # --- JOB CATEGORY ANALYSIS ---
            st.markdown("#### Job Category Analysis")
            soc_group = results.get('predicted_soc_group', 'Unknown')
            soc_scores = results.get('soc_scores', {})
            suggested_titles = results.get("suggested_titles", [])
            st.write(f"**Predicted SOC Group:** {soc_group}")

            # Show confidence scores for top 3 SOC groups
            if soc_scores and len(soc_scores) > 1:
                top_socs = sorted(soc_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                soc_cols = st.columns(len(top_socs))
                for i, (soc, score) in enumerate(top_socs):
                    with soc_cols[i]:
                        if soc == soc_group:
                            st.markdown(f"**{soc}** ✓")
                        else:
                            st.markdown(soc)
                        st.progress(int(score))
                        st.caption(f"{score:.1f}%")

            # Show suggested job titles if available
            if suggested_titles:
                st.markdown("**Recommended Job Titles:**")
                st.write(", ".join(suggested_titles[:4]))

            # --- SIGNAL DOMAIN PERFORMANCE ---
            st.markdown("#### Signal Domain Performance")
            domain_scores = results.get("domain_scores", {})
            critical_domains = set(results.get("critical_domains", []))
            domain_gaps = results.get("domain_gaps", {})
            # Sort: critical domains first, then by score descending
            sorted_domains = sorted(domain_scores.items(), key=lambda x: (x[0] not in critical_domains, -x[1]))
            for domain, score in sorted_domains:
                is_critical = domain in critical_domains
                # Progress bar color logic
                if score >= 80:
                    bar_color = "green"
                elif score >= 60:
                    bar_color = "blue"
                elif is_critical:
                    bar_color = "red"
                else:
                    bar_color = "orange"
                # Progress bar (simulate color via markdown, as st.progress is not color-customizable)
                bar = st.progress(score / 100)
                label = f"🔥 **{domain}**" if is_critical else f"{domain}"
                # Conditional styling for critical domains
                if is_critical:
                    st.markdown(f"{label}: <span style='color:#e74c3c'><b>{score:.1f}%</b></span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"{label}: <span style='color:#2980b9'>{score:.1f}%</span>", unsafe_allow_html=True)
                # Show improvement cues
                if is_critical and score < 60:
                    st.warning(f"⚠️ Critical domain '{domain}' needs attention!")
                # Show missing keywords for this domain (top 3)
                domain_missing = domain_gaps.get(domain, [])
                if domain_missing:
                    st.caption(f"Missing keywords: {', '.join(domain_missing[:3])}")

    with tabs[1]:  # Gap Analysis
        st.header("🔍 Strategic Keyword Gap Analysis", help="Pinpoint missing keywords across key skill domains")

        if not results:
            st.warning("Run an analysis to view your keyword gaps.")
        else:
            st.markdown("Below are the skill keywords grouped by domain. Keywords **not found** in your resume but present in the job description are listed in red.")

            # --- Restored Original Keyword Gap Analysis Logic ---
            domain_gaps = results.get("domain_gaps", {})
            for domain, jd_terms in domain_gaps.items():
                resume_terms = []  # No info, so empty
                missing_terms = list(jd_terms)

                if not jd_terms:
                    continue

                st.markdown(f"#### 📂 {domain}")
                for term in missing_terms:
                    st.markdown(f"- 🟥 **{term}**")
            # --- End Original Keyword Gap Analysis Logic ---

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
        st.header("🤖 AI-Powered Resume Optimization", help="Generate a tailored prompt based on your gap analysis results")

        st.markdown("""
        Use this customized prompt with ChatGPT, Claude, or any AI assistant to optimize your resume. The prompt is specifically tailored to your gap analysis results.
        """)

        if not results or "domain_gaps" not in results:
            st.warning("Run a resume + job description analysis first.")
        else:
            hyper_prompt = generate_hyperprompt(results)
            st.text_area("🎯 Optimization Prompt", hyper_prompt, height=400)

    with tabs[5]:  # Progress Tracking
        st.header("📋 Progress Tracking", help="Track your resume optimization journey over time with detailed analytics and improvement insights")
        
        # Check if we have history
        history = st.session_state.get('analysis_history', [])
        
        if len(history) < 1:
            st.info("🚀 **Start Your Optimization Journey!**")
            st.write("""
            This is your first PSA analysis. As you optimize your resume and re-run analyses, 
            you'll see your progress tracked here with:
            
            - **Score improvements over time**
            - **Domain-specific progress**  
            - **Before/after comparisons**
            - **Optimization trend analytics**
            
            💡 **Tip:** Run another analysis after making resume improvements to see your progress!
            """)
            
        elif len(history) == 1:
            st.info("📈 **Ready to Track Progress!**")
            st.write("""
            You've completed your baseline analysis. Make some resume improvements based on 
            your gap analysis, then run another PSA analysis to start tracking your progress!
            
            **Your Baseline Metrics:**
            """)
            
            # Show baseline metrics
            baseline = history[0]
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Overall Score", f"{baseline['overall_score']:.1f}%")
            with col2:
                st.metric("Trust Score", f"{baseline['trust_score']:.1f}%")
            with col3:
                st.metric("Visibility Score", f"{baseline['visibility_score']:.1f}%")
            with col4:
                st.metric("Total Gaps", baseline['total_gaps'])
                
        else:
            # Full progress tracking dashboard
            st.markdown("### 🎯 Your Optimization Journey")
            
            # Progress overview
            latest = history[-1]
            baseline = history[0]
            
            col1, col2, col3, col4 = st.columns(4)
            
            overall_improvement = latest['overall_score'] - baseline['overall_score']
            trust_improvement = latest['trust_score'] - baseline['trust_score']
            visibility_improvement = latest['visibility_score'] - baseline['visibility_score']
            gap_reduction = baseline['total_gaps'] - latest['total_gaps']
            
            with col1:
                st.metric(
                    "Overall Score", 
                    f"{latest['overall_score']:.1f}%",
                    delta=f"{overall_improvement:+.1f}%",
                    help="Change since your first analysis"
                )
            with col2:
                st.metric(
                    "Trust Score", 
                    f"{latest['trust_score']:.1f}%",
                    delta=f"{trust_improvement:+.1f}%",
                    help="Change in critical domain performance"
                )
            with col3:
                st.metric(
                    "Visibility Score", 
                    f"{latest['visibility_score']:.1f}%",
                    delta=f"{visibility_improvement:+.1f}%",
                    help="Change in professional presence signals"
                )
            with col4:
                st.metric(
                    "Gaps Closed", 
                    f"{gap_reduction}",
                    delta=f"{gap_reduction} fewer gaps",
                    help="Reduction in missing keywords"
                )
            
            # Progress chart
            st.markdown("### 📈 Score Trends Over Time")
            progress_fig = create_progress_chart(history)
            if progress_fig:
                st.plotly_chart(progress_fig, use_container_width=True)
            
            # Domain improvement analysis
            if len(history) >= 2:
                st.markdown("### 🔄 Domain Improvements Since Last Analysis")
                domain_fig = create_domain_comparison_chart(results, history)
                if domain_fig:
                    st.plotly_chart(domain_fig, use_container_width=True)
                
                # Improvement insights
                current_domains = results.get('domain_scores', {})
                previous_domains = history[-2]['domain_scores']
                
                improved_domains = []
                declined_domains = []
                
                for domain in current_domains:
                    current_score = current_domains.get(domain, 0)
                    previous_score = previous_domains.get(domain, 0)
                    change = current_score - previous_score
                    
                    if change > 2:  # Improvement threshold
                        improved_domains.append((domain, change))
                    elif change < -2:  # Decline threshold
                        declined_domains.append((domain, change))
                
                if improved_domains:
                    st.success("🎉 **Domains with Notable Improvement:**")
                    for domain, change in sorted(improved_domains, key=lambda x: x[1], reverse=True):
                        st.write(f"• **{domain}**: +{change:.1f}%")
                
                if declined_domains:
                    st.warning("⚠️ **Domains Needing Attention:**")
                    for domain, change in sorted(declined_domains, key=lambda x: x[1]):
                        st.write(f"• **{domain}**: {change:.1f}%")
                
                if not improved_domains and not declined_domains:
                    st.info("📊 **Stable Performance** - Scores remained consistent across domains")
            
            # Analysis history table
            if st.expander("📜 View Analysis History", expanded=False):
                history_df = pd.DataFrame(history)
                history_df['Date'] = history_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
                history_df = history_df[['Date', 'overall_score', 'trust_score', 'visibility_score', 'total_gaps', 'predicted_soc_group']]
                history_df.columns = ['Date', 'Overall %', 'Trust %', 'Visibility %', 'Total Gaps', 'Predicted Role']
                
                st.dataframe(history_df, use_container_width=True)
                
            # Clear history option
            if st.button("🗑️ Clear Analysis History", 
                        help="Remove all stored analysis history (cannot be undone)"):
                if st.button("⚠️ Confirm Clear History", type="secondary"):
                    st.session_state.analysis_history = []
                    st.success("✅ Analysis history cleared!")
                    st.experimental_rerun()

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


    # --- Progress Tracking Tab ---
    with tabs[5]:  # Progress Tracking
        st.header("📋 Progress Tracking", help="Track your resume optimization journey over time with detailed analytics and improvement insights")

        history = st.session_state.get('analysis_history', [])

        if len(history) < 1:
            st.info("🚀 **Start Your Optimization Journey!**")
            st.write("""
            Run an analysis, improve your resume, and re‑run to see your progress over time:
            • Score improvements
            • Domain‑specific changes
            • Before/after comparisons
            """)
        else:
            import pandas as pd
            # Convert history to DataFrame for easier handling
            df = pd.DataFrame(history)
            df['analysis_number'] = range(1, len(df) + 1)

            # Line chart of Overall, Trust, Visibility
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['analysis_number'], y=df['overall_score'],
                                     mode='lines+markers', name='Overall'))
            fig.add_trace(go.Scatter(x=df['analysis_number'], y=df['trust_score'],
                                     mode='lines+markers', name='Trust'))
            fig.add_trace(go.Scatter(x=df['analysis_number'], y=df['visibility_score'],
                                     mode='lines+markers', name='Visibility'))
            fig.update_layout(title='Score Progress', xaxis_title='Analysis #', yaxis_title='Score (%)')
            st.plotly_chart(fig, use_container_width=True)

            # Show simple table
            df_display = df[['analysis_number', 'overall_score', 'trust_score', 'visibility_score', 'total_gaps']]
            df_display.columns = ['Run', 'Overall %', 'Trust %', 'Visibility %', 'Total Gaps']
            st.dataframe(df_display, use_container_width=True)

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
