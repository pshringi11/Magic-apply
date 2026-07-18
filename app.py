import streamlit as st
import os
import json
import urllib.parse
import re
import pdfplumber
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(
    page_title="MagicApply Sentinel - Streamlit Autofiller",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling following the "Vibrant Palette" theme (Indigo/Violet/Rose gradients, glowing cards, elegant typography)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #090a0f;
        background-image: radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
                          radial-gradient(circle at 90% 80%, rgba(244, 63, 94, 0.06) 0%, transparent 45%);
        color: #f1f5f9;
    }
    
    /* Header & Titles */
    h1, h2, h3 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
    }
    
    /* Elegant vibrant cards */
    div[data-testid="stExpander"] {
        background-color: rgba(17, 24, 39, 0.7) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5) !important;
        margin-bottom: 12px !important;
        backdrop-filter: blur(12px);
    }
    
    /* Vibrant buttons with gradients */
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 28px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        letter-spacing: -0.01em !important;
        box-shadow: 0 4px 20px -2px rgba(99, 102, 241, 0.4) !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px -2px rgba(168, 85, 247, 0.6) !important;
    }
    .stButton>button:active {
        transform: translateY(0px) !important;
    }

    /* Info and Warning Banners */
    .stAlert {
        background-color: rgba(30, 41, 59, 0.5) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        border-radius: 14px !important;
        color: #e2e8f0 !important;
    }
    
    /* Custom Sidebar Card Style */
    section[data-testid="stSidebar"] {
        background-color: #0c0e17 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    /* Mono fonts for codes */
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- IN-MEMORY SESSION STATE INITIALIZATION ---
if "profile" not in st.session_state:
    st.session_state.profile = {
        "full_name": "",
        "email": "",
        "phone": "",
        "portfolio_url": "",
        "linkedin_url": "",
        "github_url": "",
        "summary": "",
        "work_experience": "",
        "education": "",
        "skills": ""
    }

if "parsed_fields" not in st.session_state:
    st.session_state.parsed_fields = []

# --- DEMO DATA LOADER ---
DEMO_PROFILE = {
    "full_name": "Alex Rivera",
    "email": "alex.rivera@example.com",
    "phone": "+1 (555) 019-2834",
    "portfolio_url": "https://alexrivera.dev",
    "linkedin_url": "https://linkedin.com/in/alexriveradeveloper",
    "github_url": "https://github.com/alexriveradev",
    "summary": "Creative full-stack software engineer with 5+ years of experience constructing high-scale web platforms and cloud-native microservices. Passionate about AI applications and crafting flawless visual interfaces.",
    "work_experience": "Lead Engineer at CloudScale Inc (2022-Present)\n- Engineered robust NestJS and React applications serving over 500k monthly active users.\n- Integrated Gemini models to perform automated semantic classification on client support datasets.\n\nSoftware Developer at WebWeave Labs (2020-2022)\n- Standardized internal REST and GraphQL APIs, boosting response throughput by 42%.",
    "education": "B.S. in Computer Science\nUniversity of California, Berkeley (2016 - 2020)",
    "skills": "TypeScript, React, Node.js, Python, PostgreSQL, Gemini API, Docker, Google Cloud Platform, Tailwind CSS, Git"
}

# --- HELPER FUNCTIONS ---
def extract_text_from_pdf(uploaded_file):
    """Extract all text cleanly from an uploaded PDF file."""
    text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text.strip()

def clean_html_content(html: str) -> str:
    """Strip scripts, styles, SVGs, and other clutter from pasted HTML to preserve tokens and focus on fields."""
    if not html:
        return ""
    # Strip script tags
    html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html, flags=re.IGNORECASE)
    # Strip style tags
    html = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html, flags=re.IGNORECASE)
    # Strip inline SVGs
    html = re.sub(r'<svg\b[^<]*(?:(?!<\/svg>)<[^<]*)*<\/svg>', '', html, flags=re.IGNORECASE)
    # Strip HTML comments
    html = re.sub(r'<!--[\s\S]*?-->', '', html)
    # Compress multiple whitespaces
    html = re.sub(r'\s+', ' ', html)
    return html.strip()[:40000] # Safe token-saving upper boundary

# --- PYDANTIC SCHEMAS FOR STRUCTURED GEMINI RESPONSES ---
class ResumeSchema(BaseModel):
    full_name: Optional[str] = Field(default="", description="Candidate full name")
    email: Optional[str] = Field(default="", description="Email address")
    phone: Optional[str] = Field(default="", description="Phone number")
    portfolio_url: Optional[str] = Field(default="", description="Portfolio, personal website, or custom link")
    linkedin_url: Optional[str] = Field(default="", description="LinkedIn profile URL")
    github_url: Optional[str] = Field(default="", description="GitHub profile URL")
    summary: Optional[str] = Field(default="", description="A brief professional summary or elevator pitch")
    work_experience: Optional[str] = Field(default="", description="Detailed chronological work history with roles and achievements")
    education: Optional[str] = Field(default="", description="Education history, degrees, and institutions")
    skills: Optional[str] = Field(default="", description="A comma-separated list of technical and soft skills")

class FormField(BaseModel):
    id: str = Field(default="", description="The HTML 'id' attribute of the element, or a unique slugified name.")
    name: Optional[str] = Field(default="", description="The HTML 'name' attribute of the form field, if found.")
    label: str = Field(description="The literal question text or field label shown to the candidate (e.g., 'Work Authorization', 'Why do you want to join?').")
    type: str = Field(default="text", description="Field type: text | select | radio | file | checkbox")
    options: Optional[List[str]] = Field(default=None, description="List of options if this is a dropdown or radio field.")
    value: str = Field(default="", description="The best matched or generated written answer for this field based on the user's professional profile.")
    confidence: str = Field(default="medium", description="AI confidence score: high | medium | low")
    reasoning: str = Field(default="", description="Brief explanation of how the answer was matched or drafted from the resume.")

class FormMappingResponse(BaseModel):
    fields: List[FormField]

def parse_resume_with_gemini(client, text):
    """Analyze resume text and convert it into a structured schema using Gemini API."""
    try:
        prompt = (
            "You are an expert resume parsing AI. Read the following raw resume text and extract "
            "all candidate details into the requested JSON schema. Be highly accurate and do not make up values."
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, text],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResumeSchema,
                temperature=0.1,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Gemini resume parsing failed: {e}")
        return None

# --- SIDEBAR: CREDENTIALS & RESUME UPLOAD ---
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=150&q=80", width=80)
    st.title("MagicApply Sentinel")
    st.markdown("⚡ *Curate once, auto-fill everywhere securely.*")
    st.divider()
    
    # Google API Key Input
    api_key = st.text_input(
        "Google API Key",
        value=os.environ.get("GEMINI_API_KEY", ""),
        type="password",
        help="Input your Gemini API key to enable AI resume parsing and smart form mapping."
    )
    
    st.divider()
    
    # Resume Upload
    st.subheader("📁 Upload Resume")
    uploaded_file = st.file_uploader("Upload PDF Resume", type=["pdf"])
    
    if uploaded_file:
        if st.button("🚀 AI Parse Resume"):
            if not api_key:
                st.error("Please enter your Google API Key above first!")
            else:
                with st.spinner("Analyzing your resume details with Gemini..."):
                    client = genai.Client(api_key=api_key)
                    resume_text = extract_text_from_pdf(uploaded_file)
                    if resume_text:
                        parsed_data = parse_resume_with_gemini(client, resume_text)
                        if parsed_data:
                            st.session_state.profile.update(parsed_data)
                            st.success("Resume parsed successfully! Check profile details.")
                        else:
                            st.error("Could not parse resume format. Please fill in details manually.")
                    else:
                        st.error("No text found in the uploaded file.")
                        
    st.divider()
    if st.button("💡 Load Demo Candidate Data"):
        st.session_state.profile.update(DEMO_PROFILE)
        st.success("Loaded demo professional candidate data!")

# --- MAIN PAGE LAYOUT ---
st.markdown("""
<div style="display: flex; align-items: center; gap: 14px; margin-bottom: 24px;">
    <div style="background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%); width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);">
        <span style="font-size: 24px; color: white;">⚡</span>
    </div>
    <div>
        <h1 style="margin: 0; font-size: 32px; background: linear-gradient(to right, #ffffff, #a5b4fc, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">MagicApply: Intelligent Form Autofill Engine</h1>
        <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 15px;">Connect your profile, auto-map forms instantly, and secure your session with the CAPTCHA Sentinel.</p>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["👤 My Professional Profile", "🚀 Form Auto-Mapping & Bookmarklet"])

# --- TAB 1: EDIT PROFILE ---
with tab1:
    st.subheader("Candidate Information Store")
    st.write("This structured metadata serves as the ground truth source for matching job application fields.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.profile["full_name"] = st.text_input("Full Name", value=st.session_state.profile.get("full_name", ""))
        st.session_state.profile["email"] = st.text_input("Email", value=st.session_state.profile.get("email", ""))
        st.session_state.profile["phone"] = st.text_input("Phone Number", value=st.session_state.profile.get("phone", ""))
    
    with col2:
        st.session_state.profile["portfolio_url"] = st.text_input("Portfolio / Personal Website", value=st.session_state.profile.get("portfolio_url", ""))
        st.session_state.profile["linkedin_url"] = st.text_input("LinkedIn Profile URL", value=st.session_state.profile.get("linkedin_url", ""))
        st.session_state.profile["github_url"] = st.text_input("GitHub Profile URL", value=st.session_state.profile.get("github_url", ""))
        
    st.divider()
    
    st.subheader("Detailed Candidate History")
    st.session_state.profile["summary"] = st.text_area("Professional Summary / Bio", value=st.session_state.profile.get("summary", ""), height=100)
    st.session_state.profile["work_experience"] = st.text_area("Work Experience", value=st.session_state.profile.get("work_experience", ""), height=150)
    st.session_state.profile["education"] = st.text_area("Education & Certifications", value=st.session_state.profile.get("education", ""), height=100)
    st.session_state.profile["skills"] = st.text_area("Core Skills & Technologies (comma separated)", value=st.session_state.profile.get("skills", ""), height=80)

# --- TAB 2: SCRAPER & BOOKMARKLET GENERATOR ---
with tab2:
    st.subheader("Smart Form Field Extraction")
    st.write(
        "Paste the raw source code (HTML) or simply copy-paste the text/questions list directly from any job application form "
        "(e.g., Lever, Greenhouse, Workday). Gemini will parse the fields and automatically map them to your profile data!"
    )
    
    # Input Form Text/HTML Source
    pasted_content = st.text_area(
        "Paste Job Form HTML, Page Text, or Questions List",
        placeholder="Tip: Right-click the form, click 'Inspect', copy the form HTML element and paste it here for maximum field matching precision.",
        height=180
    )
    
    if st.button("🔍 Analyze & Auto-Map Answers"):
        if not api_key:
            st.error("Please enter your Google API Key in the sidebar first to run the AI Auto-Mapping!")
        elif not pasted_content.strip():
            st.error("Please paste some HTML or job form questions text first.")
        else:
            with st.spinner("Gemini is matching page questions against your profile data..."):
                try:
                    client = genai.Client(api_key=api_key)
                    cleaned_html = clean_html_content(pasted_content)
                    
                    prompt = f"""
                    You are a smart job application form-filler. Read the user's professional profile and the pasted job application questions/HTML.
                    Identify all form fields and questions. For each field, select the best matching answer or draft an appropriate response based on the candidate's profile.
                    
                    Candidate Professional Profile:
                    {json.dumps(st.session_state.profile, indent=2)}
                    
                    Form HTML/Content to analyze:
                    {cleaned_html}
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=FormMappingResponse,
                            temperature=0.1,
                        )
                    )
                    
                    parsed_res = json.loads(response.text)
                    st.session_state.parsed_fields = parsed_res.get("fields", [])
                    st.success(f"Successfully mapped {len(st.session_state.parsed_fields)} fields and questions!")
                except Exception as e:
                    st.error(f"Failed parsing form questions: {e}")

    # --- DISPLAY & EDIT MAPPED ANSWERS ---
    if st.session_state.parsed_fields:
        st.divider()
        st.markdown("### ✍ Review and Refine Matched Answers")
        st.write("You can verify and fine-tune the AI-predicted values below. Changes are compiled directly into your bookmarklet!")
        
        updated_answers = []
        for i, field in enumerate(st.session_state.parsed_fields):
            with st.expander(f"📝 {field['label']} ({field['confidence'].upper()} match)"):
                col_f1, col_f2 = st.columns([2, 1])
                with col_f1:
                    val = st.text_area(f"Value for {field['label']}", value=field.get("value", ""), key=f"ans_val_{i}")
                    field["value"] = val
                with col_f2:
                    st.markdown(f"**Field Key/ID:** `{field.get('id', 'N/A')}`")
                    st.markdown(f"**Type:** `{field.get('type', 'text')}`")
                    st.markdown(f"💡 *Match Logic:* {field.get('reasoning', 'No reasoning provided')}")
                updated_answers.append(field)
        
        st.session_state.parsed_fields = updated_answers

    # --- THE BOOKMARKLET GENERATION ENGINE ---
    st.divider()
    st.markdown("""
    <div style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 20px; padding: 24px; margin-bottom: 24px;">
        <h3 style="margin-top: 0; color: #a5b4fc; display: flex; align-items: center; gap: 8px;">
            <span>🚨</span> MagicApply Human Verification Sentinel
        </h3>
        <p style="margin: 0; font-size: 14px; color: #cbd5e1; line-height: 1.6;">
            Deploying this bookmarklet arms your browser with the <strong>MagicApply Sentinel Engine</strong>. 
            When activated, the script fills out all matched fields instantaneously. If the application page triggers a 
            <strong>CAPTCHA, Cloudflare challenge, or human check challenge</strong>, the Sentinel immediately pauses progress, 
            sounds a high-contrast synthesizer audio notification, and displays a warning banner. It safely waits 
            until you prove you are human before resuming, preventing bot-detection bans!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Compile the bookmarklet data
    items_to_embed = []
    if st.session_state.parsed_fields:
        for f in st.session_state.parsed_fields:
            items_to_embed.append({
                "label": f["label"],
                "id": f.get("id", ""),
                "name": f.get("name", ""),
                "type": f.get("type", "text"),
                "value": f["value"]
            })
    else:
        # Fallback to general profile keys if no specific form mapped
        for k, v in st.session_state.profile.items():
            if v:
                label_name = k.replace("_", " ").title()
                items_to_embed.append({
                    "label": label_name,
                    "id": k,
                    "name": k,
                    "type": "text",
                    "value": v
                })
                
    items_json = json.dumps(items_to_embed)
    
    # We construct the JS. Notice the doubling of '{' and '}' because of Python f-string formatting.
    # We also avoid backslashes before dollar signs in JS template string formatting by avoiding nested backticks.
    bookmarklet_js = f"""javascript:(function() {{
      const items = {items_json};
      console.log("Job Form Autofiller Bookmarklet initiated with " + items.length + " rules.");
      
      const banner = document.createElement("div");
      banner.style.position = "fixed";
      banner.style.top = "20px";
      banner.style.right = "20px";
      banner.style.padding = "16px";
      banner.style.backgroundColor = "#0f172a";
      banner.style.color = "#f8fafc";
      banner.style.borderRadius = "12px";
      banner.style.boxShadow = "0 20px 25px -5px rgba(0,0,0,0.4), 0 10px 10px -5px rgba(0,0,0,0.3)";
      banner.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, sans-serif";
      banner.style.zIndex = "999999";
      banner.style.maxWidth = "360px";
      banner.style.border = "1px solid #334155";
      banner.style.transition = "all 0.4s ease";
      
      banner.innerHTML = `
        <div style="font-weight: 800; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="color: #38bdf8; font-size: 16px;">⚡</span> 
            <span style="letter-spacing: -0.025em; font-weight: 800;">MagicApply Sentinel</span>
          </div>
          <span id="sentinel-badge" style="font-size: 9px; font-weight: 900; background: #1e293b; color: #94a3b8; padding: 2px 6px; border: 1px solid #334155; border-radius: 4px; text-transform: uppercase;">Active</span>
        </div>
        <div id="autofill-status" style="font-size: 12px; color: #cbd5e1; line-height: 1.4;">Analyzing page elements and applying profile data...</div>
        <div id="sentinel-action" style="display: none; margin-top: 10px; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 10px; font-size: 11px; color: #fecaca;">
          <div style="font-weight: 700; display: flex; align-items: center; gap: 4px; margin-bottom: 4px;">
            <span>🚨</span> PROVE YOU ARE HUMAN
          </div>
          <span>Please complete the verification checkbox or CAPTCHA highlighted on the page. We have paused and will wait for you.</span>
          <div style="margin-top: 8px; display: flex; gap: 6px;">
            <button id="resume-autofill-btn" style="background: #ef4444; color: white; border: none; padding: 4px 8px; border-radius: 4px; font-weight: 800; cursor: pointer; font-size: 10px; text-transform: uppercase;">I've Solved It</button>
            <button id="skip-autofill-btn" style="background: rgba(255,255,255,0.1); color: #cbd5e1; border: none; padding: 4px 8px; border-radius: 4px; font-weight: 700; cursor: pointer; font-size: 10px;">Skip Wait</button>
          </div>
        </div>
        <div id="autofill-count" style="font-size: 11px; color: #64748b; margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
          <span id="autofill-stats-text"></span>
          <button id="close-autofill-banner" style="background: none; border: none; color: #94a3b8; cursor: pointer; text-decoration: underline; font-weight: 500;">Dismiss</button>
        </div>
      `;
      document.body.appendChild(banner);
      
      document.getElementById("close-autofill-banner").addEventListener("click", () => {{
        banner.remove();
      }});
 
      function playNotificationSound() {{
        try {{
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.type = "sine";
          osc.frequency.setValueAtTime(587.33, ctx.currentTime);
          gain.gain.setValueAtTime(0.1, ctx.currentTime);
          osc.start();
          gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
          
          const osc2 = ctx.createOscillator();
          const gain2 = ctx.createGain();
          osc2.connect(gain2);
          gain2.connect(ctx.destination);
          osc2.type = "sine";
          osc2.frequency.setValueAtTime(880, ctx.currentTime + 0.15);
          gain2.gain.setValueAtTime(0.1, ctx.currentTime + 0.15);
          osc2.start();
          gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
          
          setTimeout(() => {{ osc.stop(); osc2.stop(); ctx.close(); }}, 500);
        }} catch(e) {{}}
      }}
 
      function detectHumanVerification() {{
        const bodyText = document.body.innerText.toLowerCase();
        const suspiciousPhrases = [
          "prove you are human",
          "verify you are human",
          "are you a human",
          "not a robot",
          "solve the puzzle",
          "human verification",
          "enter the code below",
          "security verification",
          "confirm you are human",
          "authenticating you are a human",
          "check the box below"
        ];
        
        const hasSuspiciousText = suspiciousPhrases.some(phrase => bodyText.includes(phrase));
        
        const selectors = [
          "iframe[src*='recaptcha']",
          "iframe[src*='hcaptcha']",
          "iframe[src*='turnstile']",
          "iframe[src*='challenge']",
          "div[class*='recaptcha']",
          "div[id*='recaptcha']",
          "div[class*='captcha']",
          "div[id*='captcha']",
          "div[class*='hcaptcha']",
          "div[id*='hcaptcha']",
          "div[class*='turnstile']",
          "div[id*='turnstile']",
          "[name*='recaptcha']",
          "[name*='captcha']",
          ".g-recaptcha",
          ".h-captcha",
          ".cf-turnstile"
        ];
        
        let detectedElement = null;
        for (const selector of selectors) {{
          const el = document.querySelector(selector);
          if (el && el.offsetWidth > 0 && el.offsetHeight > 0) {{
            detectedElement = el;
            break;
          }}
        }}
        
        if (!detectedElement && hasSuspiciousText) {{
          const allDivs = Array.from(document.querySelectorAll("div, label, span, p"));
          detectedElement = allDivs.find(el => {{
            if (el.children.length > 3) return false;
            const text = el.textContent || "";
            return suspiciousPhrases.some(p => text.toLowerCase().includes(p)) && el.offsetWidth > 0;
          }});
        }}
        
        return detectedElement;
      }}
 
      function isCaptchaSolved() {{
        const recaptcha = document.querySelector("[name='g-recaptcha-response']");
        const hcaptcha = document.querySelector("[name='h-captcha-response']");
        const turnstile = document.querySelector("[name='cf-turnstile-response']");
        if (recaptcha && recaptcha.value) return true;
        if (hcaptcha && hcaptcha.value) return true;
        if (turnstile && turnstile.value) return true;
        return false;
      }}
 
      let fillCount = 0;
      let fileInputsCount = 0;
 
      function textMatches(elText, searchLabel) {{
        if (!elText || !searchLabel) return false;
        const cleanEl = elText.toLowerCase().replace(/[^a-z0-9]/g, "");
        const cleanSearch = searchLabel.toLowerCase().replace(/[^a-z0-9]/g, "");
        if (cleanEl.includes(cleanSearch) || cleanSearch.includes(cleanEl)) return true;
        const elWords = cleanEl.split(/\\s+/);
        const searchWords = cleanSearch.split(/\\s+/);
        const common = elWords.filter(w => w.length > 3 && searchWords.includes(w));
        return common.length > 0;
      }}
 
      const inputs = Array.from(document.querySelectorAll("input, textarea, select"));
      const humanCheckElement = detectHumanVerification();
      let pausedForVerification = false;
 
      function proceedWithFilling() {{
        items.forEach(item => {{
          let matchedInput = null;
          if (item.name) matchedInput = inputs.find(inp => inp.name && inp.name.toLowerCase() === item.name);
          if (!matchedInput && item.id) matchedInput = inputs.find(inp => inp.id && inp.id.toLowerCase() === item.id);
          if (!matchedInput) {{
            matchedInput = inputs.find(inp => {{
              if (inp.placeholder && textMatches(inp.placeholder, item.label)) return true;
              if (inp.id) {{
                const lbl = document.querySelector(`label[for="${{inp.id}}"]`);
                if (lbl && textMatches(lbl.textContent, item.label)) return true;
              }}
              let parent = inp.parentElement;
              while (parent && parent !== document.body) {{
                const lbl = parent.querySelector("label");
                if (lbl && textMatches(lbl.textContent, item.label)) return true;
                if (parent.textContent && textMatches(parent.textContent, item.label)) {{
                  const siblingInputs = parent.querySelectorAll("input, textarea, select");
                  if (siblingInputs.length === 1 && siblingInputs[0] === inp) return true;
                }}
                parent = parent.parentElement;
              }}
              return false;
            }});
          }}
 
          if (matchedInput) {{
            if (item.type === "file" || matchedInput.type === "file") {{
              matchedInput.style.outline = "3px solid #f97316";
              matchedInput.style.backgroundColor = "#fff7ed";
              fileInputsCount++;
              const badge = document.createElement("span");
              badge.textContent = "👈 Drag & Drop Resume Here";
              badge.style.marginLeft = "10px";
              badge.style.padding = "4px 8px";
              badge.style.backgroundColor = "#ea580c";
              badge.style.color = "white";
              badge.style.borderRadius = "4px";
              badge.style.fontSize = "12px";
              badge.style.fontWeight = "bold";
              matchedInput.parentNode.insertBefore(badge, matchedInput.nextSibling);
            }} else if (matchedInput.tagName === "SELECT") {{
              const valStr = String(item.value).toLowerCase();
              let bestIndex = -1;
              for (let i = 0; i < matchedInput.options.length; i++) {{
                const optText = matchedInput.options[i].text.toLowerCase();
                const optVal = matchedInput.options[i].value.toLowerCase();
                if (optText.includes(valStr) || optVal === valStr || valStr.includes(optText)) {{
                  bestIndex = i;
                  break;
                }}
              }}
              if (bestIndex !== -1) {{
                matchedInput.selectedIndex = bestIndex;
                matchedInput.dispatchEvent(new Event("change", {{ bubbles: true }}));
                fillCount++;
              }}
            }} else if (matchedInput.type === "checkbox") {{
              const checkIt = (item.value === true || String(item.value).toLowerCase() === "true" || String(item.value).toLowerCase() === "yes");
              if (matchedInput.checked !== checkIt) matchedInput.click();
              fillCount++;
            }} else if (matchedInput.type === "radio") {{
              const radios = Array.from(document.querySelectorAll(`input[name="${{matchedInput.name}}"]`));
              const bestRadio = radios.find(rad => {{
                const lbl = document.querySelector(`label[for="${{rad.id}}"]`);
                const radVal = String(item.value).toLowerCase();
                if (lbl && lbl.textContent.toLowerCase().includes(radVal)) return true;
                if (rad.value.toLowerCase() === radVal) return true;
                return false;
              }});
              if (bestRadio) {{
                bestRadio.click();
                fillCount++;
              }}
            }} else {{
              matchedInput.value = item.value;
              matchedInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
              matchedInput.dispatchEvent(new Event("change", {{ bubbles: true }}));
              fillCount++;
            }}
            matchedInput.style.border = "2px solid #22c55e";
            matchedInput.style.backgroundColor = "#f0fdf4";
          }}
        }});
 
        const statusEl = document.getElementById("autofill-status");
        if (fillCount > 0) {{
          statusEl.innerHTML = `
            <span style="color: #4ade80; font-weight: bold;">✓ Successful!</span> Filled <strong>${{fillCount}}</strong> fields.
            ${{fileInputsCount > 0 ? '<div style="margin-top:8px; color: #fdba74; font-size: 11px;">⚠ Note: <strong>' + fileInputsCount + '</strong> file inputs highlighted in orange. Please drop your files manually.</div>' : ''}}
          `;
        }} else {{
          statusEl.innerHTML = `<span style="color: #ef4444;">⚠ No matching fields detected.</span> Try copy-pasting answers individually from the dashboard.`;
        }}
      }}
 
      if (humanCheckElement) {{
        pausedForVerification = true;
        playNotificationSound();
        
        humanCheckElement.style.outline = "4px dashed #ef4444";
        humanCheckElement.style.outlineOffset = "4px";
        humanCheckElement.style.boxShadow = "0 0 25px rgba(239, 68, 68, 0.5)";
        humanCheckElement.scrollIntoView({{ behavior: "smooth", block: "center" }});
 
        banner.style.backgroundColor = "#7f1d1d";
        banner.style.border = "2px solid #f87171";
        document.getElementById("sentinel-badge").textContent = "Paused";
        document.getElementById("sentinel-badge").style.backgroundColor = "#ef4444";
        document.getElementById("sentinel-badge").style.color = "white";
        
        const statusEl = document.getElementById("autofill-status");
        statusEl.innerHTML = `<span style="color: #fca5a5; font-weight: bold;">🚨 HUMAN VERIFICATION DETECTED!</span><br/>Please prove you are human (solve the CAPTCHA or click the checkbox below). We have safely paused the application process to avoid triggering bot blocks.`;
        
        const sentinelActionBlock = document.getElementById("sentinel-action");
        sentinelActionBlock.style.display = "block";
 
        let solvedCheckInterval = setInterval(() => {{
          if (isCaptchaSolved()) {{
            clearInterval(solvedCheckInterval);
            resumeAutofill();
          }}
        }}, 1500);
 
        function resumeAutofill() {{
          if (!pausedForVerification) return;
          pausedForVerification = false;
          clearInterval(solvedCheckInterval);
          
          banner.style.backgroundColor = "#0f172a";
          banner.style.border = "1px solid #334155";
          document.getElementById("sentinel-badge").textContent = "Active";
          document.getElementById("sentinel-badge").style.backgroundColor = "#1e293b";
          document.getElementById("sentinel-badge").style.color = "#94a3b8";
          sentinelActionBlock.style.display = "none";
          
          humanCheckElement.style.outline = "";
          humanCheckElement.style.boxShadow = "";
          
          statusEl.innerHTML = "✓ Human verification passed! Autofilling fields...";
          proceedWithFilling();
        }}
 
        document.getElementById("resume-autofill-btn").addEventListener("click", () => {{
          resumeAutofill();
        }});
 
        document.getElementById("skip-autofill-btn").addEventListener("click", () => {{
          resumeAutofill();
        }});
 
      }} else {{
        proceedWithFilling();
      }}
    }})();"""

    # Escape the JS to create a working URL
    bookmarklet_url = "javascript:" + urllib.parse.quote(bookmarklet_js[11:])
    
    st.markdown("### ⚡ Deploy Your Bookmarklet")
    
    col_inst1, col_inst2 = st.columns([1, 1])
    
    with col_inst1:
        st.markdown("""
        #### ① Easy Setup Guide
        1. Ensure your browser **Bookmarks Bar** is visible (`Ctrl+Shift+B` or `Cmd+Shift+B`).
        2. **Drag and Drop** the glowing button on the right straight onto your bookmarks bar.
        3. If your browser blocks dragging, simply **copy the javascript code block** below, create a new manual bookmark, and paste it into the **URL / Location** field!
        """)
        
        # We render the real draggable bookmarklet button in an isolated iframe to prevent Streamlit's markdown filters from stripping the javascript: protocol!
        iframe_html = f"""
        <div style="text-align: center; padding-top: 15px;">
            <a href="{bookmarklet_url}" target="_top" style="
                display: inline-block;
                background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
                color: white;
                padding: 16px 36px;
                border-radius: 14px;
                text-decoration: none;
                font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
                font-weight: 800;
                font-size: 16px;
                letter-spacing: -0.02em;
                box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.5);
                cursor: grab;
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            " onmouseover="this.style.transform='translateY(-3px) scale(1.03)'; this.style.boxShadow='0 15px 30px -5px rgba(168, 85, 247, 0.7)';" onmouseout="this.style.transform='translateY(0) scale(1)'; this.style.boxShadow='0 10px 25px -5px rgba(99, 102, 241, 0.5)';">
                ⚡ Drag Me: Magic Fill
            </a>
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 11px; color: #94a3b8; margin-top: 10px; font-weight: 500;">
                ← Drag this button directly into your browser's bookmarks bar!
            </div>
        </div>
        """
        st.components.v1.html(iframe_html, height=120)
        
    with col_inst2:
        st.markdown("""
        #### ② How to Use It
        1. Navigate to your target **job application form** (Lever, Greenhouse, etc.).
        2. Click the **Magic Fill** bookmarklet from your bookmarks bar.
        3. The custom **MagicApply Sentinel banner** will pop up, instantly completing the questions.
        4. If a CAPTCHA or verification checkpoint is triggered, it will notify you, emit an audio alert, and pause until solved.
        """)
        
    st.markdown("#### 📋 Copy Bookmarklet Source Code (Manual Bookmark Method)")
    st.write(
        "If dragging is disabled, create a bookmark, edit its URL, and paste this entire code block as the location:"
    )
    st.code(bookmarklet_js, language="javascript")
