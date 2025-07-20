# PSA Resume Optimizer - Installation Guide

## 🚀 Quick Start

### 1. Basic Installation
```bash
pip install -r requirements.txt
streamlit run app.py
```

### 2. Enhanced Features Installation
```bash
pip install -r enhanced_requirements.txt
streamlit run enhanced_app_demo.py
```

## 🎯 License Keys

Use these demo license keys:

- **Freemium:** `PSA-FREE-123`
- **Pro:** `PSA-PRO-456` (recommended)
- **Enterprise:** `PSA-ENT-789`

## 🔧 Optional AI Integration

To enable AI-powered suggestions, install AI providers:

```bash
# For OpenAI integration
pip install openai>=1.3.0

# For Anthropic integration  
pip install anthropic>=0.7.0
```

Then configure your API keys in the app interface.

## 📦 What's Included

### Core Features (app.py)
- Resume analysis with PSA ontology
- Job description matching
- Basic reporting

### Enhanced Features (enhanced_app_demo.py)
- Advanced file processing (PDF, DOCX, TXT)
- Interactive visualizations
- AI-powered optimization suggestions
- Progress tracking

## 🎛️ Feature Toggles

Enhanced features are automatically detected based on installed dependencies:

- **File Processing:** Requires `python-docx`, `PyPDF2`
- **Visualizations:** Requires `plotly`, `seaborn`
- **AI Features:** Requires `openai` or `anthropic`

## 🐛 Troubleshooting

### License Issues
If you see license validation errors, ensure you're using a valid key:
- `PSA-PRO-456` (most features)
- `PSA-ENT-789` (all features)

### Import Errors
Missing dependencies are handled gracefully. Install specific packages as needed:

```bash
# For enhanced file processing
pip install python-docx PyPDF2 fpdf2

# For advanced visualizations
pip install plotly seaborn

# For AI features
pip install openai anthropic
```

## 🌟 Recommended Setup

For the best experience:

1. **Install enhanced requirements:**
   ```bash
   pip install -r enhanced_requirements.txt
   ```

2. **Run enhanced demo:**
   ```bash
   streamlit run enhanced_app_demo.py
   ```

3. **Use Pro license key:** `PSA-PRO-456`

4. **Configure AI API keys** in the sidebar for personalized suggestions

---

🎁 **Gift Edition:** This is the Human-to-Human gift version with demo keys provided for learning and exploration.