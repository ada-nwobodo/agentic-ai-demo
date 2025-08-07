import streamlit as st
import random
import time
import uuid
from datetime import datetime
from transformers import pipeline
from supabase import create_client
import json
import traceback
import httpx


# Generate or retrieve session UUID early in the app
def get_session_uuid():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id

session_id = get_session_uuid()

# --------------------
# SETUP
# --------------------

# Load Hugging Face model
@st.cache_resource
def load_hf_model():
    return pipeline("text2text-generation", model="t5-small")

hf_model = load_hf_model()


#Manually setting headers to ensure Supabase sees the correct role
headers = {
    "apikey": st.secrets["SUPABASE_KEY"],
    "Authorization": f"Bearer {st.secrets['SUPABASE_KEY']}",
}

#Creating a custom HTTP client with the headers
client = httpx.Client(headers=headers)

#Passing this client into Supabase
supabase: Client = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"],
    http_client=client
)


#Test Insert
if st.button("🚀 Test insert"):
    try:
        test_data = {
            "session_id": str(uuid.uuid4()),  # Required field
            "stage_number": 1
        }
        response = supabase.table("user_events").insert(test_data).execute()
        st.write("✅ Raw Response:", response)
        st.write("Data:", getattr(response, "data", None))
        st.write("Error:", getattr(response, "error", None))
    except Exception as e:
        st.error(f"❌ Exception during insert: {e}")

# ✅ Test insert block for stage_number
#st.markdown("## 🧪 Test: Insert with stage_number only")

#if st.button("Test insert with stage_number only"):
#    try:
#        response = supabase.table("user_events").insert({
#            "stage_number": 1  # minimal insert test
#        }).execute()
#        st.write("Insert result:", response)
#    except Exception as e:
#        st.error(f"Exception during insert: {e}")


# Checking for the DB role
#try:
#    role_check = supabase.rpc("get_current_user_role").execute()
#    st.write("Raw RPC response:", role_check)
#    st.write("🔍 Current DB role:", role_check.data)
#except Exception as e:
#    st.error(f"Exception when calling get_current_user_role: {e}")

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

stage = st.session_state.stage

# Supabase logging function
def log_to_supabase(stage_number, user_input, ai_output, button_clicked, completed=False):
    now = datetime.utcnow()
    last_start_time = st.session_state.get("stage_start_time", now)
    duration = (now - last_start_time).total_seconds()

    #Ensure sesion_id is present and valid
    session_id = st.session_state.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        st.session_state.session_id = session_id

    session_id = uuid.uuid4()
    data = {
        "session_id": str(session_id),
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

    st.subheader("🟡 Data being sent to Supabase:")
    st.code(json.dumps(data, indent=2), language="json")

    try:
        res = supabase.table("user_events").insert(data).execute()
        st.success("✅ Insert successful")
        st.code(str(res))
    except Exception as e:
        st.error("❌ Insert failed")
        st.code(str(e))
        st.subheader("🔍 Full Traceback:")
        st.code(traceback.format_exc())


    # ✅ Debug print for Supabase insert – to print to the Streamlit app
    st.markdown("#### 🔎 Supabase Insert Debug")
    st.write("📦 Insert Payload:", data)
    st.write("🔐 session_id value:", session_id)
    st.write("🔐 type(session_id):", type(session_id))

    
    #try-except block added to catch and show detailed errors 
    try:
        response = supabase.table("user_events").insert(data).execute()
        st.write("📤 Insert response:", response)
        st.write("✅ Status code:", response.status_code)
        st.write("📄 Returned data:", response.data)
        st.write("❌ Error (if any):", response.error)

        if response.status_code != 201:
            st.error("Insert failed. Check above error above for details.")
    except Exception as e:
        st.error(f"Exception during insert: {e}")

    #try-except block to test if anon role and RLS policy allowing an insert using stage_number 
    if st.button("Test insert with stage_number only"):
        try:
            response = supabase.table("user_events").insert({
                "stage_number": 1
            }).execute()
            st.write("Insert result:", response)
        except Exception as e:
            st.error(f"Exception during insert: {e}")


        #Debug Code added to show exactly what role Supabase thinks i am using during the session
#if st.button("Test minimal insert"):
    #try:
        #role_check = supabase.rpc("get_current_user_role").execute()
        #st.write("Current DB role:", role_check.data)

        # Debug: Trying a Blank insert (will only work if RLS + defaults are correct)
        #response = supabase.table("user_events").insert({}).execute()
        #st.write("Insert result:", response)
    #except Exception as e:
        #st.error(f"Exception during test insert: {e}")


    #Insert into Supabase
    st.session_state.stage_start_time = now
    st.session_state.last_activity_time = now

# AI generation function
def generate_response(prompt):
    if not USE_HF:
        return f"[Mock AI] Response for: {prompt}"
    try:
        response = hf_model(prompt, max_length=200, do_sample=False)
        return response[0]["generated_text"]
    except Exception as e:
        return f"[AI Error] {str(e)}"

# Simulate random failure
def maybe_fail():
    return random.choice([True, False]) if st.session_state.simulate_failure else True

# --------------------
# UI
# --------------------

st.title("🧠 Agentic AI Workflow Demo")

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
    st.subheader("Step 3: Attach Guidelines?")
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
        log_to_supabase(5, "Submit", "", "Submit Case")
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















import uuid

st.markdown("## 🔍 Test Minimal Insert (Debugging Only)")

if st.button("Run Minimal Insert Test"):
    try:
        test_data = {
            "session_id": str(uuid.uuid4()),  # required column with fallback
        }
        response = supabase.table("user_events").insert(test_data).execute()
        st.write("✅ Test insert result:", response)
        st.write("📄 Returned data:", response.data)
        st.write("❌ Error (if any):", response.error)

    except Exception as e:
        st.error(f"Test insert exception: {e}")

