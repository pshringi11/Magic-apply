import streamlit as st
import json
import urllib.parse
from google import genai
from google.genai import types

# Set page style and layout
st.set_page_config(
    page_title="MagicApply - AI Job Form Autofiller",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Custom CSS for vibrant theme aesthetic
st.markdown("""
<style>
    .main { background-color: #F0F4FF; }
    h1 { color: #1e1b4b; font-weight: 900; }
    .stButton>button {
        background-color: #4f46e5;
        color: white;
        border-radius: 12px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #4338ca;
        transform: scale(1.02);
    }
    .bookmarklet-btn {
        display: inline-block;
        padding: 12px 24px;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white !important;
        text-decoration: none !important;
        border-radius: 16px;
        font-weight: 800;
        font-size: 14px;
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.3);
        margin: 10px 0;
        cursor: grab;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "profile" not in st.session_state:
    st.session_state.profile = {
        "personalInfo": {
            "firstName": "Alex",
            "lastName": "Rivera",
            "email": "alex.rivera@example.com",
            "phone": "+1 (555) 012-3456",
            "website": "https://alexrivera.dev",
            "linkedin": "https://linkedin.com/in/alexrivera",
            "github": "https://github.com/alexrivera",
            "requiresSponsorship": False
        },
        "summary": "Experienced Software Engineer specializing in building full-stack applications with Python, React, and cloud architectures.",
        "experience": [],
        "education": [],
        "skills": ["Python", "Streamlit", "React", "SQL", "Cloud Architecture"]
    }

# Sidebar - Configuration and API Key
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/flash-on.png", width=60)
    st.title("MagicApply Config")
    
    api_key = st.text_input(
        "Google Gemini API Key",
        type="password",
        help="Input your Gemini API Key. Get one from Google AI Studio.",
        placeholder="AIzaSy..."
    )
    
    st.markdown("---")
    st.markdown("### Profile Completeness")
    # Quick calculations for completeness
    comp_score = 15
    if st.session_state.profile["personalInfo"]["firstName"]: comp_score += 15
    if st.session_state.profile["personalInfo"]["email"]: comp_score += 15
    if st.session_state.profile["personalInfo"]["phone"]: comp_score += 15
    if st.session_state.profile["summary"]: comp_score += 20
    if st.session_state.profile["skills"]: comp_score += 20
    
    st.progress(comp_score / 100)
    st.caption(f"Profile {comp_score}% Complete")

# Title Header
st.title("⚡ MagicApply: Job Form Autofiller")
st.caption("AI-Powered Form Auto-Completion with Integrated Human Verification Sentinel")

# Create Tabs
tab_autofill, tab_profile = st.tabs(["⚡ Autofill Bookmarklet", "👤 My Profile & Resume Parser"])

# ==================== TAB 1: AUTOFILL BOOKMARKLET GENERATOR ====================
with tab_autofill:
    st.subheader("Your Custom Sentinel Bookmarklet")
    st.write(
        "Below is your custom browser bookmarklet compiled instantly from your active profile. "
        "It features **Sentinel Human Verification detection**, which monitors the form page for CAPTCHAs, "
        "suspends completion, plays a gentle alarm sound, and waits for you to clear checks before completing."
    )
    
    # Map profile dict to rules list
    rules = [
        {"id": "first_name", "label": "First Name", "value": st.session_state.profile["personalInfo"]["firstName"]},
        {"id": "last_name", "label": "Last Name", "value": st.session_state.profile["personalInfo"]["lastName"]},
        {"id": "email", "label": "Email", "value": st.session_state.profile["personalInfo"]["email"]},
        {"id": "phone", "label": "Phone", "value": st.session_state.profile["personalInfo"]["phone"]},
        {"id": "website", "label": "Website", "value": st.session_state.profile["personalInfo"]["website"]},
        {"id": "linkedin", "label": "LinkedIn Profile", "value": st.session_state.profile["personalInfo"]["linkedin"]},
        {"id": "github", "label": "GitHub Profile", "value": st.session_state.profile["personalInfo"]["github"]},
        {"id": "requires_sponsorship", "label": "Requires Sponsorship", "value": "Yes" if st.session_state.profile["personalInfo"]["requiresSponsorship"] else "No"},
        {"id": "summary", "label": "Summary", "value": st.session_state.profile["summary"]},
    ]
    
    items_json = json.dumps(rules)
    
    # Complete high-performance Bookmarklet JS source with Sentinel logic
    bookmarklet_js = f"""javascript:(function() {{
      const items = {items_json};
      console.log("Job Form Autofiller initiated with " + items.length + " rules.");
      
      const banner = document.createElement("div");
      banner.style.position = "fixed";
      banner.style.top = "20px";
      banner.style.right = "20px";
      banner.style.padding = "16px";
      banner.style.backgroundColor = "#0f172a";
      banner.style.color = "#f8fafc";
      banner.style.borderRadius = "12px";
      banner.style.boxShadow = "0 20px 25px -5px rgba(0,0,0,0.4), 0 10px 10px -5px rgba(0,0,0,0.3)";
      banner.style.fontFamily = "system-ui, -apple-system, sans-serif";
      banner.style.zIndex = "999999";
      banner.style.maxWidth = "360px";
      banner.style.border = "1px solid #334155";
      banner.style.transition = "all 0.4s ease";
      
      banner.innerHTML = `
        <div style="font-weight: 800; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="color: #38bdf8; font-size: 16px;">⚡</span> 
            <span style="font-weight: 800;">MagicApply Sentinel</span>
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
          "prove you are human", "verify you are human", "are you a human", "not a robot",
          "solve the puzzle", "human verification", "enter the code below", "security verification",
          "confirm you are human", "authenticating you are a human", "check the box below"
        ];
        
        const hasSuspiciousText = suspiciousPhrases.some(phrase => bodyText.includes(phrase));
        const selectors = [
          "iframe[src*='recaptcha']", "iframe[src*='hcaptcha']", "iframe[src*='turnstile']", "iframe[src*='challenge']",
          "div[class*='recaptcha']", "div[id*='recaptcha']", "div[class*='captcha']", "div[id*='captcha']",
          ".g-recaptcha", ".h-captcha", ".cf-turnstile"
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
              if (inp.placeholder && inp.placeholder.toLowerCase().includes(item.label.toLowerCase())) return true;
              return false;
            }});
          }}

          if (matchedInput) {{
            if (matchedInput.type === "file") {{
              matchedInput.style.outline = "3px solid #f97316";
              matchedInput.style.backgroundColor = "#fff7ed";
              fileInputsCount++;
            }} else {{
              matchedInput.value = item.value;
              matchedInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
              matchedInput.dispatchEvent(new Event("change", {{ bubbles: true }}));
              fillCount++;
            }}
            matchedInput.style.border = "2px solid #22c55e";
          }}
        }});

        const statusEl = document.getElementById("autofill-status");
        statusEl.innerHTML = `<span style="color: #4ade80; font-weight: bold;">✓ Successful!</span> Filled <strong>\${{fillCount}}</strong> fields.`;
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
        statusEl.innerHTML = `<span style="color: #fca5a5; font-weight: bold;">🚨 HUMAN VERIFICATION DETECTED!</span><br/>Please prove you are human. We have safely paused the autofill engine.`;
        
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
          
          statusEl.innerHTML = "✓ Verification passed! Autofilling fields...";
          proceedWithFilling();
        }}

        document.getElementById("resume-autofill-btn").addEventListener("click", () => {{ resumeAutofill(); }});
        document.getElementById("skip-autofill-btn").addEventListener("click", () => {{ resumeAutofill(); }});
      }} else {{
        proceedWithFilling();
      }}
    }})();"""

    # URL encode for bookmarklet href
    encoded_bookmarklet = urllib.parse.quote(bookmarklet_js)
    
    st.markdown("### 📥 Step-by-Step Installation")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div style="text-align: center; margin-top: 15px;">
            <p style="font-size: 11px; font-weight: 700; color: #4f46e5; text-transform: uppercase;">Drag button to Bookmarks Bar</p>
            <a class="bookmarklet-btn" href="{bookmarklet_js}">⚡ Magic Fill</a>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        1. Ensure your browser's **Bookmarks Bar** is visible (`Ctrl+Shift+B` or `Cmd+Shift+B`).
        2. Drag the violet **⚡ Magic Fill** button directly onto your Bookmarks Bar.
        3. Go to any job board application page (Greenhouse, Lever, etc.).
        4. Click the bookmarklet in your bar. It will fill the form and monitor for verification requests!
        """)
        
    st.markdown("---")
    st.markdown("### 📋 Alternative Manual Code Block (Console Script)")
    st.write("If you cannot use your bookmarks bar, copy and paste this code directly into your Browser Inspector Console (F12):")
    st.code(bookmarklet_js, language="javascript")


# ==================== TAB 2: PROFILE EDITOR & RESUME PARSER ====================
with tab_profile:
    st.subheader("Manage Candidate Profile Data")
    
    # 📑 Resume PDF Parsing via Gemini API
    st.markdown("### 📄 AI Resume Parser")
    uploaded_file = st.file_uploader("Upload your Resume (PDF, TXT)", type=["pdf", "txt"])
    
    if uploaded_file is not None:
        if not api_key:
            st.error("Please provide your Google Gemini API Key in the sidebar to use the AI Resume Parser.")
        else:
            if st.button("Parse Resume with Gemini AI"):
                with st.spinner("AI is extraction key fields from resume..."):
                    try:
                        # Initialize Gemini modern SDK client
                        client = genai.Client(api_key=api_key)
                        
                        # Read file bytes
                        file_bytes = uploaded_file.read()
                        
                        # Set prompt instructions
                        prompt = """
                        Extract professional information from this resume and output it exactly in the following JSON format:
                        {
                            "personalInfo": {
                                "firstName": "string",
                                "lastName": "string",
                                "email": "string",
                                "phone": "string",
                                "website": "string",
                                "linkedin": "string",
                                "github": "string",
                                "requiresSponsorship": boolean
                            },
                            "summary": "string",
                            "skills": ["string"]
                        }
                        Return ONLY the raw JSON string without markdown wrappers.
                        """
                        
                        # Determine MIME type
                        mime_type = "application/pdf" if uploaded_file.name.endswith(".pdf") else "text/plain"
                        
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[
                                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                                prompt
                            ]
                        )
                        
                        # Parse JSON response
                        raw_text = response.text.strip().replace("```json", "").replace("```", "")
                        parsed_json = json.loads(raw_text)
                        
                        # Update session state
                        st.session_state.profile["personalInfo"] = parsed_json.get("personalInfo", st.session_state.profile["personalInfo"])
                        st.session_state.profile["summary"] = parsed_json.get("summary", st.session_state.profile["summary"])
                        st.session_state.profile["skills"] = parsed_json.get("skills", st.session_state.profile["skills"])
                        
                        st.success("Resume parsed successfully! Check edited fields below.")
                    except Exception as e:
                        st.error(f"Failed to parse resume: {str(e)}")

    st.markdown("---")
    
    # 📝 Manual Editing Fields
    st.markdown("### ✍️ Edit Profile Fields")
    col_f, col_l = st.columns(2)
    with col_f:
        st.session_state.profile["personalInfo"]["firstName"] = st.text_input(
            "First Name", value=st.session_state.profile["personalInfo"]["firstName"]
        )
    with col_l:
        st.session_state.profile["personalInfo"]["lastName"] = st.text_input(
            "Last Name", value=st.session_state.profile["personalInfo"]["lastName"]
        )
        
    col_e, col_p = st.columns(2)
    with col_e:
        st.session_state.profile["personalInfo"]["email"] = st.text_input(
            "Email Address", value=st.session_state.profile["personalInfo"]["email"]
        )
    with col_p:
        st.session_state.profile["personalInfo"]["phone"] = st.text_input(
            "Phone Number", value=st.session_state.profile["personalInfo"]["phone"]
        )
        
    st.session_state.profile["summary"] = st.text_area(
        "Professional Summary", value=st.session_state.profile["summary"], height=100
    )
    
    st.session_state.profile["personalInfo"]["requiresSponsorship"] = st.checkbox(
        "I require sponsorship for US work visa", value=st.session_state.profile["personalInfo"]["requiresSponsorship"]
    )
