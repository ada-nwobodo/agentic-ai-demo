import streamlit as st
import random
import time
import datetime
import uuid
import os
from transformers import pipeline
from supabase import create_client

# --------------------
# SETUP
# --------------------

# Supabase client setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load Hugging Face model (e.g., T5 for summarization/generation)
@st.cache_resource
def load_hf_model():
    return pipeline("text2text-generation", model="t5-small")

hf_model = load_hf_model()

# Sidebar controls
USE_HF = st.sidebar.toggle("Use Hugging Face AI", value=True)
st.sidebar.markdown("Model: `t5-small`")
st.session_state.simulate_failure = st.sidebar.checkbox("Simulate random failure?", value=False)

# Initialize session state
if "stage" not in st.session_state:
    st.session_state.stage = 1
if "log" not in st.session_state:
    st.session_state.log = []
if "inputs" not in st.session_state:
    st.session_state.inputs = {}
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "stage_start_time" not in st.session_state:
    st.session_state.stage_start_time = datetime.datetime.utcnow()
if "search_frequency" not in st.session_state:
    st.session_state.search_frequency = 1

# Shortcut
stage = st.session_state.stage

# --------------------
# LOGGING FUNCTION
# --------------------

def log_to_supabase(stage, user_input, ai_output, button_clicked, completed=False):
    timestamp_end = datetime.datetime.utcnow()
    timestamp_start = st.session_state.get("stage_start_time", timestamp_end)

    data = {
        "session_id": st.session_state.session_id,
        "stage_number": stage,
        "user_input": user_input,
        "ai_output": ai_output,
        "timestamp_start": timestamp_start.isoformat(),
        "timestamp_end": timestamp_end.isoformat(),
        "button_clicked": button_clicked,
        "completion_stage": completed,
        "abandoned_at_stage": None if completed else stage,
        "last_info_before_abandonment": ai_output,
        "search_frequency": st.session_state.search_frequency
    }

    try:
        supabase.table("user_events").insert(data).execute()
    except Exception as e:
        st.warning(f"Logging to Supabase failed: {e}")

    st.session_state.stage_start_time = timestamp_end

# --------------------
# AI GENERATION + FAILURE SIMULATION
# --------------------

def maybe_fail():
    return random.choice([True, False]) if st.session_state.simulate_failure else True

def generate_response(prompt):
    if not USE_HF:
        return f"[Mock AI] Response for: {prompt}"
    try:
        response = hf_model(prompt, max_length=200, do_sample=False)
        return response[0]["generated_text"]
    except Exception as e:
        return f"[AI Error] {str(e)}"

# --------------------
# UI FLOW
# --------------------

st.title("🧠 Agentic AI Workflow Demo")

# STAGE 1: Clinician enters patient notes
if stage == 1:
    st.subheader("Step 1: Detect Patient Record Entry")
    st.markdown("📝 A clinician begins entering patient symptoms and history into the EHR.")

    patient_input = st.text_area("Enter patient symptoms/history:")
    if st.button("Detect and Summarize Entry"):
        if patient_input.strip() == "":
            st.warning("Please enter some text before proceeding.")
        else:
            summary = generate_response(f"summarize: {patient_input}")
            st.session_state.inputs["summary"] = summary
            log_to_supabase(1, patient_input, summary, button_clicked="Detect", completed=False)
            st.success("Patient note detected and summarized.")
            st.session_state.stage = 2
            st.rerun()

# STAGE 2: Agent extracts key data
elif stage == 2:
    st.subheader("Step 2: Key Data Extracted")
    st.markdown("📑 Summary of the patient record:")

    st.info(st.session_state.inputs.get("summary", "[No summary found]"))

    if st.button("Proceed to attach summarisation"):
        log_to_supabase(2, "Proceed", st.session_state.inputs.get("summary", ""), button_clicked="next", completed=False)
        st.session_state.stage = 3
        st.rerun()

# STAGE 3: Prompt to attach guidelines
elif stage == 3:
    st.subheader("Step 3: Attach Guidelines?")
    st.markdown("📌 Would you like the agent to fetch relevant imaging guidelines?")

    if st.button("Yes, fetch guidelines"):
        log_to_supabase(3, "Yes", "User requested guidelines", button_clicked="yes", completed=False)
        st.session_state.stage = 4
        st.rerun()

    if st.button("No, stop here"):
        log_to_supabase(3, "No", "User stopped at stage 3", button_clicked="no", completed=False)
        st.warning("Workflow ended.")
        st.stop()

# STAGE 4: Agent retrieves guidelines
elif stage == 4:
    st.subheader("Step 4: Retrieving Guidelines")
    success = maybe_fail()

    if success:
        guidelines = generate_response("Provide imaging guidelines based on patient symptoms.")
        st.session_state.inputs["guidelines"] = guidelines
        log_to_supabase(4, "Request imaging guidelines", guidelines, button_clicked="retrieved", completed=False)
        st.success("Guidelines retrieved.")
        st.session_state.stage = 5
        st.rerun()
    else:
        st.error("⚠️ Failed to retrieve guidelines. Try again or stop.")
        if st.button("Retry"):
            log_to_supabase(4, "Retry", "Retry fetch guidelines", button_clicked="retry", completed=False)
            st.rerun()
        if st.button("Stop workflow"):
            log_to_supabase(4, "Stop", "User stopped after failure", button_clicked="stop", completed=False)
            st.stop()

# STAGE 5: Attach & Submit?
elif stage == 5:
    st.subheader("Step 5: Attach Guidelines to Record?")
    st.markdown("📎 Ready to submit this case with AI-generated documentation.")

    if st.button("Submit Case"):
        log_to_supabase(5, "Submit Case", st.session_state.inputs.get("guidelines", ""), button_clicked="submit", completed=False)
        st.session_state.stage = 6
        st.rerun()

# STAGE 6: Final Output
elif stage == 6:
    st.subheader("✅ Step 6: Submission Preview")
    st.markdown("📤 Final structured submission:")

    st.code(f"""
Summary: {st.session_state.inputs.get('summary', '[Missing]')}

Guidelines: {st.session_state.inputs.get('guidelines', '[Missing]')}

Code: SNOMED-CT: 12345678
    """, language="text")

    log_to_supabase(6, "Final submission", "Completed", button_clicked="finish", completed=True)

    st.success("Submission complete!")
    if st.button("🔁 Restart Demo"):
        st.session_state.stage = 1
        st.session_state.inputs = {}
        st.session_state.log = []
        st.session_state.search_frequency += 1
        st.rerun()

# --------------------
# Optional: Show Logs
# --------------------

with st.expander("📊 Interaction Log"):
    st.json(st.session_state.log)
