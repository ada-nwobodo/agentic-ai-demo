import streamlit as st
import random
import time
import datetime

# Gemini API support
import google.generativeai as genai

# === Sidebar Controls ===
USE_GEMINI = st.sidebar.toggle("Use Gemini AI", value=False)
st.sidebar.toggle("Simulate Failures", key="simulate_failure", value=False)

# === Secrets Setup for Gemini ===
if USE_GEMINI:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        gemini = genai.GenerativeModel("gemini-2.0")
    except Exception as e:
        st.sidebar.error(f"Gemini config error: {e}")
        USE_GEMINI = False

# === Session State Init ===
def init_session():
    for key, default in {
        "stage": 1,
        "log": [],
        "inputs": {},
        "patient_input": "",
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session()
current_step = st.session_state.stage

# === Helper: Logging Function ===
def log_event(stage, user_input, ai_output):
    st.session_state.log.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "stage": stage,
        "user_input": user_input,
        "ai_output": ai_output
    })

# === Helper: Gemini API Call or Mock ===
def gemini_generate(prompt):
    if not USE_GEMINI:
        return f"[Mock] Response for: {prompt}"

    try:
        response = gemini.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"[Gemini Error] {e}"

# === Helper: Failure Simulation ===
def maybe_fail():
    if st.session_state.simulate_failure:
        return random.choice([True, False])
    return True

# === Helper: Step Navigation ===
def go_to_step(step_number):
    st.session_state.stage = step_number
    st.rerun()

# === STAGE 1: Clinician enters patient notes ===
if current_step == 1:
    st.subheader("Step 1: Detect Patient Record Entry")
    st.markdown("A clinician begins entering patient symptoms and history:")

    patient_input = st.text_area("📝 Enter patient symptoms/history:",
                                 value=st.session_state.patient_input,
                                 height=150)
    st.session_state.patient_input = patient_input

    if st.button("➡️ Proceed to Summarization"):
        if not patient_input.strip():
            st.warning("Please enter some patient notes.")
        else:
            go_to_step(2)

# === STAGE 2: Agent summarizes input ===
elif current_step == 2:
    st.subheader("Step 2: Summarize Patient Record")

    prompt = f"Summarize the following patient entry for clarity:\n\n{st.session_state.patient_input}"
    summary = gemini_generate(prompt)

    st.success("🧠 AI Summary:")
    st.markdown(summary)

    log_event(2, st.session_state.patient_input, summary)

    if st.button("✅ Approve Summary and Continue"):
        st.session_state.inputs["summary"] = summary
        go_to_step(3)

# === STAGE 3: Ask to attach guidelines ===
elif current_step == 3:
    st.subheader("Step 3: Attach Guidelines")
    st.markdown("Agent asks: _'Would you like to attach relevant imaging guidelines to this record?'_")

    if st.button("📎 Yes, attach guidelines"):
        go_to_step(4)

# === STAGE 4: Retrieve guidelines ===
elif current_step == 4:
    st.subheader("Step 4: Retrieve Imaging Guidelines")

    prompt = f"What are the national imaging guidelines for: {st.session_state.patient_input}"
    guidelines = gemini_generate(prompt)

    st.success("📖 Guidelines Retrieved:")
    st.markdown(guidelines)

    log_event(4, st.session_state.inputs["summary"], guidelines)
    st.session_state.inputs["guidelines"] = guidelines

    if st.button("✅ Approve and Continue"):
        go_to_step(5)

# === STAGE 5: Prepare submission ===
elif current_step == 5:
    st.subheader("Step 5: Prepare Submission")

    st.markdown("Agent will now prepare structured submission with summary, guidelines, and coding.")

    if maybe_fail():
        submission = f"""
        ✅ Submission Preview:

        - **Summary**: {st.session_state.inputs['summary']}
        - **Guidelines**: {st.session_state.inputs['guidelines']}
        - **Code**: SNOMED-CT: 12345678
        """
        st.success(submission)
        st.session_state.inputs["submission"] = submission
        log_event(5, None, submission)

        if st.button("📤 Submit to Imaging System"):
            go_to_step(6)
    else:
        st.error("❌ Submission failed. Please retry or adjust input.")
        if st.button("🔄 Retry"):
            st.rerun()

# === STAGE 6: Completion ===
elif current_step == 6:
    st.balloons()
    st.success("🎉 Submission complete! Thank you.")

    st.markdown("---")
    st.subheader("📊 Interaction Log")
    for log in st.session_state.log:
        st.markdown(f"- `{log['timestamp']}` | **Stage {log['stage']}** | Input: _{log['user_input']}_, Output: _{log['ai_output']}_")


# === Reset Demo ===
st.sidebar.markdown("---")
if st.sidebar.button("🔁 Restart Demo"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.experimental_rerun()
