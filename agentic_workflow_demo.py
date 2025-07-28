import streamlit as st
import random
import time
import datetime
import uuid
from transformers import pipeline

# --------------------
# SETUP
# --------------------

# Load Hugging Face model (e.g., T5 for summarization/generation)
@st.cache_resource
def load_hf_model():
    return pipeline("text2text-generation", model="t5-small")

hf_model = load_hf_model()

# Toggle AI source (Hugging Face vs. Mock)
USE_HF = st.sidebar.toggle("Use Hugging Face AI", value=True)
st.sidebar.markdown("Model: `t5-small`")

# Simulate success/failure path
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
    st.session_state.stage_start_time = time.time()

stage = st.session_state.stage

# --------------------
# LOGGING
# --------------------

def log_to_db(stage, user_input, ai_output, action="next", completed=False):
    stage_end_time = time.time()
    time_spent = round(stage_end_time - st.session_state.stage_start_time)

    log_entry = {
        "session_id": st.session_state.session_id,
        "stage": stage,
        "user_input": user_input,
        "ai_output": ai_output,
        "action": action,
        "time_spent_sec": time_spent,
        "timestamp": datetime.datetime.now().isoformat(),
        "completed": completed
    }

    st.session_state.log.append(log_entry)
    st.session_state.stage_start_time = time.time()  # Reset timer for next stage

# --------------------
# UTILS
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
# UI
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
            log_to_db(1, patient_input, summary, completed=True)
            st.success("Patient note detected and summarized.")
            st.session_state.stage = 2
            st.rerun()

# STAGE 2: Agent extracts key data
elif stage == 2:
    st.subheader("Step 2: Key Data Extracted")
    st.markdown("📑 Summary of the patient record:")
    st.info(st.session_state.inputs.get("summary", "[No summary found]"))

    if st.button("Proceed to attach summarisation"):
        log_to_db(2, "View summary", "Proceed to attach summarisation", completed=True)
        st.session_state.stage = 3
        st.rerun()

# STAGE 3: Prompt to attach guidelines
elif stage == 3:
    st.subheader("Step 3: Attach Guidelines?")
    st.markdown("📌 Would you like the agent to fetch relevant imaging guidelines?")

    if st.button("Yes, fetch guidelines"):
        log_to_db(3, "Yes", "User opted to fetch guidelines", completed=True)
        st.session_state.stage = 4
        st.rerun()

    if st.button("No, stop here"):
        log_to_db(3, "No", "User stopped at stage 3", completed=False)
        st.warning("Workflow ended.")
        st.stop()

# STAGE 4: Agent retrieves guidelines
elif stage == 4:
    st.subheader("Step 4: Retrieving Guidelines")
    success = maybe_fail()

    if success:
        guidelines = generate_response("Provide imaging guidelines based on patient symptoms.")
        st.session_state.inputs["guidelines"] = guidelines
        log_to_db(4, "Request imaging guidelines", guidelines, completed=True)
        st.success("Guidelines retrieved.")
        st.session_state.stage = 5
        st.rerun()
    else:
        st.error("⚠️ Failed to retrieve guidelines. Try again or stop.")
        if st.button("Retry"):
            log_to_db(4, "Retry", "Retry guideline fetch")
            st.rerun()
        if st.button("Stop workflow"):
            log_to_db(4, "Stop", "User stopped after failure", completed=False)
            st.stop()

# STAGE 5: Attach & Submit?
elif stage == 5:
    st.subheader("Step 5: Attach Guidelines to Record?")
    st.markdown("📎 Ready to submit this case with AI-generated documentation.")

    if st.button("Submit Case"):
        log_to_db(5, "Submit", "User submitted the case", completed=True)
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

    log_to_db(6, "Final preview", "Submission complete", completed=True)

    st.success("Submission complete!")

    if st.button("🔁 Restart Demo"):
        st.session_state.stage = 1
        st.session_state.inputs = {}
        st.session_state.log = []
        st.session_state.stage_start_time = time.time()
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# Optional: Show logs
with st.expander("📊 Interaction Log"):
    st.json(st.session_state.log)

