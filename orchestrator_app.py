# demo_orchestrator_app.py
import streamlit as st
import subprocess

st.set_page_config(page_title="Orchestrator Demo", page_icon="📰", layout="wide")

st.title("📰 Orchestrator Demo App")
st.caption("Click the button to run orchestrator and see its terminal output here.")

if st.button("▶️ Run Orchestrator"):
    st.write("Running orchestrator... please wait ⏳")
    with st.spinner("Executing orchestrator..."):
        try:
            # Run the orchestrator script and capture output
            result = subprocess.run(
                ["/Users/kumnegermatewos/Desktop/Cognium/Codebase/RagAgent/working/venv/bin/python", "-m", "orchestrator.main"], 
                capture_output=True,
                text=True,
                check=True
            )
            st.success("Execution complete ✅")
            st.markdown("### 📜 Orchestrator Output")
            st.code(result.stdout, language="bash")
        except subprocess.CalledProcessError as e:
            st.error("❌ Error while running orchestrator.")
            st.code(e.stdout + "\n" + e.stderr, language="bash")


