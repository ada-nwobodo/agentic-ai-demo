import streamlit as st
import random
import time
import uuid
from datetime import datetime
from transformers import pipeline
from supabase import create_client
import json
import traceback




# --------------------
# SETUP
# --------------------


# Create Supabase client
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

#Debug to confirm which project the app is talking to 
st.write("Supabase URL in use:", SUPABASE_URL)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# Load Hugging Face model
@st.cache_resource
def load_hf_model():
    return pipeline("text2text-generation", model="t5-small")

hf_model = load_hf_model()


# Toggle AI model source
USE_HF = st.sidebar.toggle("Use Hugging Face AI", value=True)
st.sidebar.markdown("Model: `t5-small`")

# Simulate failure mode
st.session_state.simulate_failure = st.sidebar.checkbox("Simulate random failure?", value=False)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "stage" not in st.session_state:
    st.session_state.stage = 1
if "inputs" not in st.session_state:
    st.session_state.inputs = {}
if "stage_start_time" not in st.session_state:
    st.session_state.stage_start_time = datetime.utcnow()
if "last_activity_time" not in st.session_state:
    st.session_state.last_activity_time = datetime.utcnow()
if "supabase_user" in st.session_state:
    supabase.auth.set_session(st.session_state["supabase_user"]["session"])

stage = st.session_state.stage


# --------------------
# AUTH
# --------------------
st.sidebar.header("🔐 Login")

email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Sign In"):
    try:
        # Sign in (returns user + session/JWT)
        auth_res = supabase.auth.sign_in_with_password({"email": email, "password": password})

        if not auth_res or not auth_res.session:
            st.sidebar.error("Login succeeded but no session was returned.")
        else:
            # Persist session across Streamlit reruns
            st.session_state["supabase_session"] = auth_res.session
            st.session_state["logged_in"] = True

            st.sidebar.success(f"Logged in as: {auth_res.user.email}")
    except Exception as e:
        st.sidebar.error(f"Login failed: {e}")

        

# --------------------
# LOGGING FUNCTION
# --------------------

#Supabase Logging Function
def log_to_supabase(stage_number, user_input, ai_output, button_clicked, completed=False):
    now = datetime.utcnow()
    last_start_time = st.session_state.get("stage_start_time", now)
    duration = (now - last_start_time).total_seconds()

    data = {
        "session_id": st.session_state.session_id,
        "stage_number": stage_number,
        "user_input": user_input,
        "ai_output": ai_output,
        "timestamp_start": last_start_time.isoformat(),
        "timestamp_end": now.isoformat(),
        "duration_sec": int(duration),
        "abandoned_at_stage": stage_number if not completed else None,
        "search_frequency": st.session_state.get("search_frequency", 0),
        "button_clicked": button_clicked,
        "completed": completed,
        "last_info_received_prior_to_abandonment": ai_output if not completed else None
    }

    try:
        response = supabase.table("user_events").insert(data).execute()

        # Cross-version safe checks
        err = getattr(response, "error", None)
        returned = getattr(response, "data", None)

        if err:
            st.error(f"Insert failed: {err}")
            st.code(str(err))
        else:
            st.success("✅ Logged to Supabase")
            st.write("Returned data:", returned)

    except Exception as e:
        st.error("❌ Failed to insert into Supabase")
        st.code(str(e))
        st.code(traceback.format_exc())

    # Always update activity timestamps
    st.session_state.stage_start_time = now
    st.session_state.last_activity_time = now




# --------------------
# AI
# --------------------

def generate_response(prompt):
    try:
        result = hf_model(prompt, max_length=200, do_sample=False)
        return result[0]["generated_text"]
    except Exception as e:
        return f"[AI Error] {e}"

# Simulate random failure
def maybe_fail():
    return random.choice([True, False]) if st.session_state.simulate_failure else True

# --------------------
# UI & STAGES
# --------------------

st.title("🧠 Agentic AI Workflow Demo")

stage = st.session_state.stage

# STAGE 1: Clinician enters patient notes 
if stage == 1:
    st.subheader("Step 1: Detect Patient Record Entry")
    st.markdown("Clinician enters symptoms and history.")

    patient_input = st.text_area("Enter patient symptoms/history:")
    if st.button("Detect and Summarize Entry"):
        if patient_input.strip() == "":
            st.warning("Please enter some text before proceeding.")
        else:
            summary = generate_response(f"summarize: {patient_input}")
            st.session_state.inputs["summary"] = summary
            log_to_supabase(1, patient_input, summary, "Detect and Summarize Entry")
            st.session_state.stage = 2
            st.rerun()

# STAGE 2: Agent extracts key data
elif stage == 2:
    st.subheader("Step 2: Summary Output")
    st.info(st.session_state.inputs.get("summary", "[No summary found]"))

    if st.button("Proceed to attach summarisation"):
        log_to_supabase(2, "Confirmed summary", "", "Proceed to attach summarisation")
        st.session_state.stage = 3
        st.rerun()

# STAGE 3: Prompt to attach guidelines
elif stage == 3:
    st.subheader("Step 3: Fetch Guidelines?")
    st.markdown("Would you like the agent to fetch relevant imaging guidelines?")

    if st.button("Yes, fetch guidelines"):
        log_to_supabase(3, "Yes", "", "Yes, fetch guidelines")
        st.session_state.stage = 4
        st.rerun()
    elif st.button("No, stop here"):
        log_to_supabase(3, "No", "User stopped at stage 3", "No, stop here", completed=False)
        st.warning("Workflow ended.")
        st.stop()

# STAGE 4: Agent retrieves guidelines
elif stage == 4:
    st.subheader("Step 4: Retrieving Guidelines")

    try:
        success = maybe_fail()
        if success:
            guidelines = generate_response("Provide imaging guidelines based on patient symptoms.")
            st.session_state.inputs["guidelines"] = guidelines
            log_to_supabase(4, "Request guidelines", guidelines, "Fetch guidelines")
            st.success("Guidelines retrieved.")
            st.session_state.stage = 5
            st.rerun()
        else:
            st.error("⚠️ Failed to retrieve guidelines.")
            if st.button("Retry"):
                log_to_supabase(4, "Retry", "", "Retry")
                st.rerun()
            elif st.button("Stop workflow"):
                log_to_supabase(4, "Stop", "User stopped after failure", "Stop workflow", completed=False)
                st.stop()

    except Exception as e:
        st.error(f"❌ Error in Step 4: {e}")
        import traceback
        st.text(traceback.format_exc())
        st.stop()  # Halt execution so I can see the error

# STAGE 5: Attach and submit?
elif stage == 5:
    st.subheader("Step 5: Submit Documentation")
    st.markdown("Ready to submit this case.")

    if st.button("Submit Case"):
        log_to_supabase(5, "Submit", "", "Submit Case", completed = True)
        st.session_state.stage = 6
        st.rerun()

# STAGE 6: Final output
elif stage == 6:
    st.subheader("✅ Step 6: Submission Preview")
    st.markdown("Final structured output:")

    st.code(f"""
Summary: {st.session_state.inputs.get('summary', '[Missing]')}

Guidelines: {st.session_state.inputs.get('guidelines', '[Missing]')}

Code: SNOMED-CT: 12345678
    """, language="text")

    log_to_supabase(6, "Final submission", "Completed", "Submission Preview", completed=True)
    st.success("Submission complete!")

    if st.button("🔁 Restart Demo"):
        st.session_state.stage = 1
        st.session_state.inputs = {}
        st.session_state.stage_start_time = datetime.utcnow()
        st.rerun()

# Optional: View raw log in UI
with st.expander("📊 Interaction Log"):
    st.json({"session_id": st.session_state.session_id, "log": st.session_state.inputs})

# 🔍 Debug: Check DB Role
if st.button("Check DB Role"):
    info = supabase.rpc("whoami").execute()
    st.write("DB sees:", getattr(info, "data", None))















import uuid

st.markdown("## 🔍 Test Minimal Insert (Debugging Only)")

if st.button("Run Minimal Insert Test"):
    try:
        test_data = {
            "session_id": str(uuid.uuid4()),# required column with fallback
            "stage_number": 99, 
        }
        response = supabase.table("user_events").insert(test_data).execute()
        st.write("✅ Raw response object:", response)
        st.write("📄 Status code:", getattr(response, "status_code", None))
        st.write("Data:", getattr(response, "data", None))
        st.write("❌ Error:", getattr(response, "error", None))

    except Exception as e:
        st.error(f"Test insert exception: {e}")

