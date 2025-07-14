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
