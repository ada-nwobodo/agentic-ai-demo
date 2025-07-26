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

# Shortcut to current step
current_step = st.session_state.stage

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

# STAGE 1: Clinician enters patient notes, agent detects input
if current_step == 1:
    st.subheader("Step 1: Detect Patient Record Entry")

    st.markdown("A clinician begins entering patient symptoms and history into the EHR.")

    # Input field for patient notes
    patient_input = st.text_area("📝 Enter patient symptoms/history:", value=session_state.get("patient_input", ""), height=150)

    # Save input in session state
    session_state["patient_input"] = patient_input

    if patient_input:
        st.success("Agent has detected the patient record entry.")
        if st.button("▶️ Proceed to summarization"):
            go_to_step(2)
    else:
        st.info("Please enter patient symptoms/history to continue.")

# STAGE 2: Extract key data
if current_step == 2:
    st.subheader("Step 2: Extract Summary from Record")

    patient_text = session_state.get("patient_input", "")

    if not patient_text:
        st.warning("No patient input detected. Please return to Step 1.")
    else:
        st.markdown("The agent will now summarize the patient’s record.")

        if st.button("🧠 Summarize with Gemini"):
            # Use Gemini or mock summary
            with st.spinner("Summarizing..."):
                try:
                    summary = gemini.summarize(patient_text)  # Or mock function
                    session_state["summary"] = summary
                except Exception as e:
                    st.error(f"Summarization failed: {e}")
                    summary = "Summary unavailable due to an error."
                    session_state["summary"] = summary

        if "summary" in session_state:
            st.success("Summary extracted:")
            st.markdown(session_state["summary"])
            if st.button("✅ Proceed to Step 3"):
                go_to_step(3)

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

