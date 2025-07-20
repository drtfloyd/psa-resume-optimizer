"""
AI Integration Module for PSA Resume Optimizer
Basic AI integration framework for resume optimization
"""

import streamlit as st
import requests
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class AIResponse:
    content: str
    provider: str
    model: str
    success: bool

class AIIntegrationManager:
    def __init__(self):
        self.providers = {}
        
    def configure_api_keys(self):
        """Streamlit interface for AI API key configuration"""
        
        st.header("🔑 AI Provider Configuration")
        
        with st.expander("Configure AI API Keys", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("OpenAI")
                openai_key = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    help="Get your API key from https://platform.openai.com/api-keys"
                )
                if openai_key:
                    st.session_state.openai_key = openai_key
                    st.success("✅ OpenAI configured")
            
            with col2:
                st.subheader("Anthropic")
                anthropic_key = st.text_input(
                    "Anthropic API Key", 
                    type="password",
                    help="Get your API key from https://console.anthropic.com/"
                )
                if anthropic_key:
                    st.session_state.anthropic_key = anthropic_key
                    st.success("✅ Anthropic configured")

    def generate_resume_improvements(self, resume_text: str, job_description: str, gap_analysis: Dict) -> AIResponse:
        """Generate basic resume improvement suggestions"""
        
        # Check if API keys are configured
        if not (st.session_state.get('openai_key') or st.session_state.get('anthropic_key')):
            return AIResponse(
                content="Please configure your AI API keys in the settings to get personalized suggestions.",
                provider="none",
                model="none",
                success=False
            )
        
        # Generate basic improvement suggestions based on gap analysis
        missing_keywords = []
        for domain, gaps in gap_analysis.get('domain_gaps', {}).items():
            missing_keywords.extend(gaps[:3])
        
        suggestions = self._generate_basic_suggestions(missing_keywords, gap_analysis)
        
        return AIResponse(
            content=suggestions,
            provider="psa_basic",
            model="rule_based",
            success=True
        )

    def _generate_basic_suggestions(self, missing_keywords: List[str], gap_analysis: Dict) -> str:
        """Generate basic rule-based suggestions"""
        
        suggestions = []
        
        # Overall score based suggestions
        overall_score = gap_analysis.get('overall_score', 0)
        
        if overall_score < 60:
            suggestions.append("📈 **Overall Enhancement Needed**\n- Your resume has significant gaps. Focus on adding relevant experience and skills.")
        elif overall_score < 80:
            suggestions.append("⚡ **Good Foundation, Room for Improvement**\n- Your resume is on the right track. Target specific keywords to boost relevance.")
        else:
            suggestions.append("🎯 **Strong Match, Minor Optimizations**\n- Your resume aligns well. Consider these refinements for maximum impact.")
        
        # Keyword suggestions
        if missing_keywords:
            suggestions.append(f"\n🔑 **Key Terms to Include**\n- Consider incorporating: {', '.join(missing_keywords[:8])}")
            suggestions.append("- Add these naturally within your experience descriptions")
            suggestions.append("- Quantify achievements where possible (e.g., 'Led team of 5', 'Increased efficiency by 20%')")
        
        # Domain-specific suggestions
        domain_gaps = gap_analysis.get('domain_gaps', {})
        critical_domains = gap_analysis.get('critical_domains', [])
        
        for domain in critical_domains:
            if domain in domain_gaps and domain_gaps[domain]:
                suggestions.append(f"\n🎯 **{domain} Focus Areas**\n- Missing: {', '.join(domain_gaps[domain][:3])}")
                suggestions.append(f"- Strengthen your {domain.lower()} section with specific examples")
        
        # Structure suggestions
        suggestions.append("\n📝 **Resume Structure Tips**")
        suggestions.append("- Use action verbs (managed, developed, implemented, optimized)")
        suggestions.append("- Include quantifiable results and metrics")
        suggestions.append("- Tailor content to match job requirements")
        suggestions.append("- Ensure consistent formatting and clear section headers")
        
        return "\n".join(suggestions)

    def suggest_skills_development(self, current_skills: List[str], missing_skills: List[str]) -> Dict[str, any]:
        """Suggest skill development pathways"""
        
        return {
            "priority_skills": missing_skills[:3],
            "learning_resources": {
                skill: [f"Online course in {skill}", f"{skill} certification program", f"Practice {skill} projects"]
                for skill in missing_skills[:3]
            },
            "learning_path": [
                "1. Identify highest-impact skills from job requirements",
                "2. Find relevant online courses or certifications", 
                "3. Complete practical projects to demonstrate skills",
                "4. Update resume with new competencies",
                "5. Practice explaining skills in interview contexts"
            ],
            "time_estimate": "2-3 months for significant skill development"
        }

# Global instance
ai_manager = AIIntegrationManager()