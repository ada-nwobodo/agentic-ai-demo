import streamlit as st
import random
import time
import datetime

# Optional: Gemini API (mock switch for now)
USE_GEMINI = st.sidebar.toggle("Use Gemini AI", value=False)

# Setup session state
def init_session():
    if "stage" not in st.session_state:
        st.session_state.stage = 1
    if "log" not in st.session_state:
        st.session_state.log = []
    if "inputs" not in st.session_state:
        st.session_state.inputs = {}
    if "simulate_failure" not in st.session_state:
        st.session_state.simulate_failure = False

init_session()

# Logging helper
def log_event(stage, user_input, ai_output):
    st.session_state.log.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "stage": stage,
        "user_input": user_input,
        "ai_output": ai_output
    })

# Mock Gemini API call
def gemini_generate(prompt):
    if not USE_GEMINI:
        return f"[Mock] Response for: {prompt}"
    # Replace this with real Gemini call if enabled
    time.sleep(1)  # simulate latency
    return f"[Gemini] Simulated intelligent response for: {prompt}"

# Simulate possible failure

def maybe_fail():
    if st.session_state.simulate_failure:
        return random.choice([True, False])
    return True

# STAGE 1: Detect patient entry
if st.session_state.stage == 1:
    st.subheader("Stage 1: Patient Record Detected")
    st.write("Agent has detected a new patient entry.")
    if st.button("Summarise entry"):
        user_input = "Clinician clicked to summarise"
        ai_output = gemini_generate("Summarise this patient record entry")
        log_event(1, user_input, ai_output)
        st.session_state.stage += 1

# STAGE 2: Extract key data
elif st.session_state.stage == 2:
    st.subheader("Stage 2: Data Extraction")
    sample_entry = st.text_area("Patient Record Entry", "75 year old male with dizziness and falls...")
    if st.button("Extract Key Data"):
        if maybe_fail():
            output = gemini_generate(f"Extract key clinical info from: {sample_entry}")
            log_event(2, sample_entry, output)
            st.session_state.inputs['summary'] = output
            st.session_state.stage += 1
        else:
            st.error("Extraction failed. Please try again.")

# STAGE 3: Attach summary + ask about guidelines
elif st.session_state.stage == 3:
    st.subheader("Stage 3: Summary + Guideline Prompt")
    st.write("Attached Summary:")
    st.info(st.session_state.inputs.get('summary', '[No summary found]'))
    if st.button("Attach Guidelines to Record"):
        log_event(3, "Clinician permitted guidelines attach", "Proceeding to fetch guidelines")
        st.session_state.stage += 1

# STAGE 4: Retrieve guidelines
elif st.session_state.stage == 4:
    st.subheader("Stage 4: Retrieve National Guidelines")
    if st.button("Retrieve Guidelines"):
        if maybe_fail():
            output = gemini_generate("Retrieve national guidelines for dizziness in elderly")
            log_event(4, "Clinician requested guidelines", output)
            st.session_state.inputs['guidelines'] = output
            st.session_state.stage += 1
        else:
            st.error("Failed to retrieve guidelines.")

# STAGE 5: Attach + Submit
elif st.session_state.stage == 5:
    st.subheader("Stage 5: Attach Guidelines + Submit")
    st.write("Summary:")
    st.info(st.session_state.inputs.get('summary', '...'))
    st.write("Guidelines:")
    st.success(st.session_state.inputs.get('guidelines', '...'))
    if st.button("Submit for Imaging Request"):
        log_event(5, "Clinician confirmed submission", "Packaging structured request")
        st.session_state.stage += 1

# STAGE 6: Final structured output
elif st.session_state.stage == 6:
    st.subheader("Stage 6: Final Submission Output")
    summary = st.session_state.inputs.get('summary', '...')
    guidelines = st.session_state.inputs.get('guidelines', '...')
    final_output = {
        "summary": summary,
        "guidelines": guidelines,
        "codes": ["SNOMED: 123456", "ICD10: R42"]
    }
    st.json(final_output)
    log_event(6, "Final review", str(final_output))
    st.success("Workflow complete!")

    if st.button("Restart Simulation"):
        for key in ["stage", "log", "inputs"]:
            st.session_state.pop(key, None)
        st.rerun()

# Sidebar controls
with st.sidebar:
    st.markdown("## Simulation Controls")
    st.session_state.simulate_failure = st.checkbox("Simulate Random Failures", value=False)
    st.markdown("---")
    if st.button("Show Event Log"):
        st.write(st.session_state.log)

