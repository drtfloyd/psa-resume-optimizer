# === COMPLETE HOT FIX ===
# Replace your existing generate_pdf_report function with this:

def generate_pdf_report(results: dict) -> bytes:
    """Generate PDF report and return as bytes for download."""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Use Arial font (always available)
        pdf.set_font("Arial", 'B', size=16)
        pdf.cell(0, 10, "PSA Resume Gap Analysis Report", ln=True)
        pdf.ln(5)

        # Add summary section
        pdf.set_font("Arial", 'B', size=12)
        pdf.cell(0, 10, "Analysis Summary", ln=True)
        pdf.set_font("Arial", '', size=10)
        
        # Add key metrics
        overall_score = results.get('overall_score', 0)
        soc_group = results.get('predicted_soc_group', 'Unknown')
        total_gaps = sum(len(gaps) for gaps in results.get('domain_gaps', {}).values())
        
        pdf.cell(0, 8, f"Overall Match Score: {overall_score:.1f}%", ln=True)
        pdf.cell(0, 8, f"Predicted Job Category: {soc_group}", ln=True)
        pdf.cell(0, 8, f"Total Keywords to Add: {total_gaps}", ln=True)
        pdf.ln(8)

        # Domain gaps section
        pdf.set_font("Arial", 'B', size=12)
        pdf.cell(0, 10, "Missing Keywords by Domain", ln=True)
        
        domain_gaps = results.get("domain_gaps", {})
        for domain, gaps in domain_gaps.items():
            if not gaps:
                continue
                
            pdf.set_font('Arial', 'B', size=11)
            pdf.cell(0, 8, f"{domain}", ln=True)
            pdf.set_font('Arial', '', size=9)
                
            for kw in gaps[:10]:  # Limit to top 10
                # Clean text for PDF compatibility
                clean_kw = kw.encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(0, 6, f"    • {clean_kw}", ln=True)
            
            if len(gaps) > 10:
                pdf.cell(0, 6, f"    ... and {len(gaps) - 10} more", ln=True)
            pdf.ln(3)

        # FIXED: Return proper bytes
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, str):
            return pdf_output.encode('latin-1')
        return pdf_output
            
    except Exception:
        # Fallback minimal PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', size=14)
        pdf.cell(0, 10, "PSA Resume Analysis Report", ln=True)
        pdf.set_font("Arial", '', size=10)
        pdf.cell(0, 8, "Error generating detailed report. Please try again.", ln=True)
        
        pdf_output = pdf.output(dest='S')
        return pdf_output.encode('latin-1') if isinstance(pdf_output, str) else pdf_output


# === REPLACE THE DOWNLOAD BUTTON SECTION (around line 787) ===
# Replace this section in your sidebar:

        # PDF Export Section
        st.markdown("---")
        colpdf1, colpdf2, colpdf3 = st.columns([1, 2, 1])
        with colpdf2:
            if st.button("📄 Download Analysis Report"):
                if 'analysis_results' in st.session_state and st.session_state.analysis_results:
                    try:
                        results = st.session_state.analysis_results
                        with st.spinner("Generating PDF report..."):
                            pdf_bytes = generate_pdf_report(results)
                            
                        if pdf_bytes and len(pdf_bytes) > 0:
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                            filename = f"psa_resume_analysis_{timestamp}.pdf"
                            
                            st.download_button(
                                label="📥 Download PDF Report",
                                data=pdf_bytes,
                                file_name=filename,
                                mime="application/pdf",
                                key="pdf_download_btn"
                            )
                            st.success("✅ PDF ready for download!")
                        else:
                            st.error("⚠️ Failed to generate PDF")
                            
                    except Exception as e:
                        st.error(f"⚠️ Error generating PDF: {str(e)}")
                        st.info("💡 Try running the analysis again")
                else:
                    st.error("⚠️ No analysis results available")
                    st.info("💡 Run an analysis first")
        st.markdown("---")
