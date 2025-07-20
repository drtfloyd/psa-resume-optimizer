"""
Enhanced PSA Resume Optimizer - Demo Integration
Shows how to integrate enhanced features with existing PSA functionality
"""

import streamlit as st
import sys
from pathlib import Path

# Import enhanced modules (if available)
try:
    from enhanced_file_processor import file_processor
    from ai_integration import ai_manager
    from advanced_visualizations import visualizer
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError:
    ENHANCED_FEATURES_AVAILABLE = False
    st.warning("⚠️ Enhanced features not available. Install enhanced dependencies with: pip install -r enhanced_requirements.txt")

# Import original PSA modules
from psa_license.license import get_user_mode
import json
import os
from datetime import datetime
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(
    page_title="PSA™ Resume Optimizer Enhanced",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application with enhanced features"""
    
    # Header
    st.markdown("""
    # 🚀 PSA™ Resume Optimizer Enhanced
    ### Next-Generation Resume Intelligence with AI-Powered Insights
    """)
    
    # Sidebar for configuration
    with st.sidebar:
        st.title("🎛️ Control Center")
        
        # License validation
        license_key = st.text_input(
            "🔐 PSA™ License Key",
            type="password",
            help="Enter your PSA™ license key or use 'PSA-PRO-456' for demo access"
        )
        
        if not license_key:
            st.info("👈 Enter license key to begin")
            show_welcome_screen()
            return
        
        # Validate license
        license_tier = get_user_mode(license_key) if license_key else None
        
        if license_tier not in ["pro", "enterprise"]:
            st.error("❌ Invalid license key. Use 'PSA-PRO-456' for demo access.")
            return
        
        st.success(f"✅ {license_tier.title()} License Active")
        
        # Enhanced features toggle
        if ENHANCED_FEATURES_AVAILABLE:
            enhanced_enabled = st.checkbox("🚀 Enable Enhanced Features", value=True)
            st.session_state.enhanced_enabled = enhanced_enabled
        else:
            st.info("📦 Install enhanced_requirements.txt for advanced features")
            st.session_state.enhanced_enabled = False
        
        # AI Configuration
        if st.session_state.get('enhanced_enabled') and ENHANCED_FEATURES_AVAILABLE:
            st.markdown("---")
            ai_manager.configure_api_keys()
    
    # Main interface
    create_main_interface()

def show_welcome_screen():
    """Enhanced welcome screen"""
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🎯 Enhanced Analysis
        - Advanced file processing with OCR
        - Multi-format support (PDF, DOCX, TXT)
        - Intelligent text extraction
        """)
    
    with col2:
        st.markdown("""
        ### 🤖 AI-Powered Optimization
        - OpenAI & Anthropic integration
        - Automated improvement suggestions
        - Skill development recommendations
        """)
    
    with col3:
        st.markdown("""
        ### 📈 Advanced Visualizations
        - Interactive radar charts
        - Progress tracking over time
        - Keyword gap heatmaps
        """)
    
    st.info("🎁 **Demo Access:** Use license key `PSA-PRO-456` for full feature access")

def create_main_interface():
    """Create the main analysis interface"""
    
    # Create tabs
    if st.session_state.get('enhanced_enabled'):
        tabs = st.tabs(["📊 Analysis", "🤖 AI Assistant", "📈 Visualizations", "📋 Reports"])
    else:
        tabs = st.tabs(["📊 Analysis", "📋 Reports"])
    
    with tabs[0]:
        create_analysis_tab()
    
    if st.session_state.get('enhanced_enabled'):
        with tabs[1]:
            create_ai_assistant_tab()
        
        with tabs[2]:
            create_visualizations_tab()
        
        with tabs[3]:
            create_reports_tab()
    else:
        with tabs[1]:
            create_reports_tab()

def create_analysis_tab():
    """Enhanced analysis interface"""
    
    st.header("📊 Resume Analysis")
    
    # File upload section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Resume Upload")
        resume_file = st.file_uploader(
            "Upload Resume", 
            type=["pdf", "txt", "docx"],
            key="resume_upload",
            help="Upload your resume for analysis"
        )
        
        if resume_file and st.session_state.get('enhanced_enabled'):
            # Enhanced file processing options
            use_advanced_extraction = st.checkbox("🔍 Use Advanced Text Extraction", value=True)
    
    with col2:
        st.subheader("📋 Job Description")
        jd_file = st.file_uploader(
            "Upload Job Description",
            type=["pdf", "txt", "docx"], 
            key="jd_upload",
            help="Upload the target job description"
        )
    
    # Analysis options
    if resume_file and jd_file:
        st.subheader("⚙️ Analysis Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            analysis_depth = st.selectbox("Analysis Depth", ["Standard", "Deep", "Comprehensive"])
        
        with col2:
            include_ai = st.checkbox("🤖 AI Suggestions", value=st.session_state.get('enhanced_enabled', False))
        
        with col3:
            generate_report = st.checkbox("📋 Generate Report", value=True)
        
        # Analyze button
        if st.button("🚀 Start Analysis", type="primary"):
            perform_analysis(resume_file, jd_file, analysis_depth, include_ai, generate_report)
    
    # Display results
    if st.session_state.get('analysis_results'):
        display_analysis_results()

def perform_analysis(resume_file, jd_file, depth, include_ai, generate_report):
    """Perform enhanced analysis"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Text extraction
        status_text.text("📄 Extracting text from files...")
        progress_bar.progress(0.2)
        
        if st.session_state.get('enhanced_enabled') and ENHANCED_FEATURES_AVAILABLE:
            resume_text, resume_metadata = file_processor.extract_text_from_file(resume_file)
            jd_text, jd_metadata = file_processor.extract_text_from_file(jd_file)
        else:
            # Basic extraction
            resume_text = extract_basic_text(resume_file)
            jd_text = extract_basic_text(jd_file)
            resume_metadata = {"method": "basic"}
            jd_metadata = {"method": "basic"}
        
        # Step 2: PSA Analysis
        status_text.text("🔍 Performing PSA analysis...")
        progress_bar.progress(0.6)
        
        # Load ontology
        ontology = load_ontology()
        
        # Simulate enhanced analysis
        results = {
            'overall_score': np.random.uniform(65, 95),
            'trust_score': np.random.uniform(60, 90),
            'visibility_score': np.random.uniform(55, 85),
            'domain_scores': {
                'Leadership & Management': np.random.uniform(60, 95),
                'Technical Skills': np.random.uniform(70, 90),
                'Communication': np.random.uniform(65, 85),
                'Problem Solving': np.random.uniform(60, 88)
            },
            'domain_gaps': {
                'Leadership & Management': ['project management', 'team leadership', 'strategic planning'],
                'Technical Skills': ['cloud computing', 'data analysis'],
                'Communication': ['presentation skills', 'technical writing']
            },
            'predicted_soc_group': 'Management Occupations',
            'resume_metadata': resume_metadata,
            'jd_metadata': jd_metadata
        }
        
        # Step 3: AI Enhancement
        if include_ai and st.session_state.get('enhanced_enabled') and ENHANCED_FEATURES_AVAILABLE:
            status_text.text("🤖 Generating AI suggestions...")
            progress_bar.progress(0.8)
            
            ai_response = ai_manager.generate_resume_improvements(resume_text, jd_text, results)
            results['ai_suggestions'] = ai_response.content
        
        status_text.text("✅ Analysis complete!")
        progress_bar.progress(1.0)
        
        st.session_state.analysis_results = results
        st.success("🎉 Analysis completed successfully!")
        
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")

def display_analysis_results():
    """Display enhanced analysis results"""
    
    results = st.session_state.analysis_results
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Overall Match", f"{results['overall_score']:.1f}%")
    with col2:
        st.metric("Trust Score", f"{results['trust_score']:.1f}%")
    with col3:
        st.metric("Visibility Score", f"{results['visibility_score']:.1f}%")
    with col4:
        domain_gaps = results.get('domain_gaps', {})
        st.metric("Improvement Areas", len(domain_gaps))
    
    # Enhanced visualizations
    if st.session_state.get('enhanced_enabled') and ENHANCED_FEATURES_AVAILABLE:
        st.subheader("🎯 Skill Domain Analysis")
        radar_chart = visualizer.create_skill_radar_chart(
            results['domain_scores'], 
            list(results['domain_scores'].keys())[:2]
        )
        st.plotly_chart(radar_chart, use_container_width=True)
    
    # Domain breakdown
    st.subheader("📊 Domain Breakdown")
    domain_df = pd.DataFrame([
        {"Domain": domain, "Score": f"{score:.1f}%", "Status": "Strong" if score > 75 else "Needs Work"}
        for domain, score in results['domain_scores'].items()
    ])
    st.dataframe(domain_df, use_container_width=True)

def create_ai_assistant_tab():
    """AI assistant interface"""
    
    st.header("🤖 AI-Powered Resume Assistant")
    
    if not ENHANCED_FEATURES_AVAILABLE:
        st.info("Install enhanced dependencies to access AI features")
        return
    
    if st.session_state.get('analysis_results'):
        results = st.session_state.analysis_results
        
        # AI suggestions
        if 'ai_suggestions' in results:
            st.subheader("💡 AI Improvement Suggestions")
            st.markdown(results['ai_suggestions'])
        else:
            if st.button("🤖 Generate AI Suggestions"):
                with st.spinner("Generating suggestions..."):
                    ai_response = ai_manager.generate_resume_improvements("", "", results)
                    st.markdown(ai_response.content)
        
        # Skill development
        st.subheader("📚 Skill Development Recommendations")
        if st.button("🎓 Get Learning Path"):
            current_skills = list(results['domain_scores'].keys())
            missing_skills = []
            for gaps in results['domain_gaps'].values():
                missing_skills.extend(gaps[:2])
            
            development_plan = ai_manager.suggest_skills_development(current_skills, missing_skills)
            
            st.write("**Priority Skills:**")
            for skill in development_plan['priority_skills']:
                st.write(f"• {skill}")
            
            st.write("**Learning Path:**")
            for step in development_plan['learning_path']:
                st.write(f"• {step}")
            
            st.info(f"**Estimated Time:** {development_plan['time_estimate']}")
    else:
        st.info("Run an analysis first to get AI-powered suggestions")

def create_visualizations_tab():
    """Advanced visualizations tab"""
    
    st.header("📈 Advanced Visualizations")
    
    if not ENHANCED_FEATURES_AVAILABLE:
        st.info("Install enhanced dependencies to access advanced visualizations")
        return
    
    if st.session_state.get('analysis_results'):
        results = st.session_state.analysis_results
        
        # Keyword gap heatmap
        st.subheader("🔥 Keyword Gap Analysis")
        heatmap = visualizer.create_keyword_heatmap(
            results['domain_gaps'],
            results['domain_scores']
        )
        st.plotly_chart(heatmap, use_container_width=True)
        
        # Progress tracking (if history exists)
        if st.session_state.get('analysis_history'):
            st.subheader("📈 Progress Over Time")
            progress_chart = visualizer.create_progress_timeline(st.session_state.analysis_history)
            st.plotly_chart(progress_chart, use_container_width=True)
        
        # Optimization dashboard
        st.subheader("📊 Optimization Dashboard")
        dashboard = visualizer.create_optimization_dashboard(results)
        st.plotly_chart(dashboard, use_container_width=True)
        
    else:
        st.info("Run an analysis first to see visualizations")

def create_reports_tab():
    """Reports and export tab"""
    
    st.header("📋 Reports & Export")
    
    if st.session_state.get('analysis_results'):
        results = st.session_state.analysis_results
        
        # Export options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Download Report"):
                st.success("Report generation feature available with enhanced version!")
        
        with col2:
            if st.button("📊 Export Data"):
                # Create downloadable data
                export_data = {
                    'Overall Score': results['overall_score'],
                    'Trust Score': results['trust_score'],
                    'Visibility Score': results['visibility_score']
                }
                df = pd.DataFrame([export_data])
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, "psa_analysis.csv", "text/csv")
        
        with col3:
            if st.button("📧 Email Results"):
                st.success("Email feature available with enhanced version!")
        
        # Results summary
        st.subheader("📊 Analysis Summary")
        summary_df = pd.DataFrame([
            {"Metric": "Overall Match", "Score": f"{results['overall_score']:.1f}%"},
            {"Metric": "Trust Score", "Score": f"{results['trust_score']:.1f}%"},
            {"Metric": "Visibility Score", "Score": f"{results['visibility_score']:.1f}%"},
            {"Metric": "Domains Analyzed", "Score": len(results['domain_scores'])}
        ])
        st.dataframe(summary_df, use_container_width=True)
        
    else:
        st.info("No analysis results available")

def extract_basic_text(file) -> str:
    """Basic text extraction fallback"""
    try:
        if file.type == "text/plain":
            return str(file.getvalue(), "utf-8")
        else:
            return f"Content from {file.name} (enhanced extraction needed for {file.type})"
    except:
        return "Error extracting text"

def load_ontology():
    """Load ontology file"""
    try:
        with open('ontology.json', 'r') as f:
            return json.load(f)
    except:
        return {"SignalDomains": {}, "SOC_Groups": {}}

if __name__ == "__main__":
    main()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #7f8c8d;'>
    <strong>PSA™ Resume Optimizer Enhanced</strong> | 
    Powered by Presence Signaling Architecture™ | 
    © 2025 All Rights Reserved
    </div>
    """, unsafe_allow_html=True)