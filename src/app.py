"""Streamlit user interface for the Mutual Fund FAQ Assistant."""
import streamlit as st
import logging
import uuid
import sys
import os
import json
from datetime import datetime, timezone, timedelta

# Add project root to path so 'src' module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.generation.generator import answer_query
from src.retrieval.retriever import KNOWN_SCHEMES

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set page config
st.set_page_config(
    page_title="HDFC Mutual Fund FAQ",
    page_icon="🏦",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for visual polish
st.markdown("""
<style>
    /* Gradient Title */
    .gradient-text {
        background: -webkit-linear-gradient(45deg, #005B9F, #00A67E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 5px;
    }
    
    /* Disclaimer Banner */
    .disclaimer {
        background-color: rgba(255, 193, 7, 0.1);
        color: #ffc107;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin-bottom: 25px;
        font-size: 0.9rem;
    }
    
    /* Make buttons slightly rounded */
    .stButton>button {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State for Multi-Chat
if "chats" not in st.session_state:
    st.session_state.chats = {
        "default": []
    }
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "default"

def get_ingestion_info():
    """Get the latest data ingestion information from the log."""
    log_path = os.path.join(os.path.dirname(__file__), "..", "data", "ingestion_log.json")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                data = json.load(f)
                
            if data and data.get("timestamp"):
                ts_str = data["timestamp"].replace("Z", "+00:00")
                last_run = datetime.fromisoformat(ts_str)
                now = datetime.now(timezone.utc)
                delta = now - last_run
                
                ist_time = last_run + timedelta(hours=5, minutes=30)
                formatted_time = ist_time.strftime("%Y-%m-%d %H:%M IST")
                
                return {
                    "stale": delta.total_seconds() > 48 * 3600,
                    "time_str": formatted_time,
                    "status": data.get("status")
                }
        except Exception as e:
            logging.error(f"Error reading ingestion log: {e}")
    return None

def create_new_chat():
    """Initialize a new chat session."""
    new_id = str(uuid.uuid4())[:8]
    st.session_state.chats[new_id] = []
    st.session_state.current_chat_id = new_id

def switch_chat(chat_id):
    """Switch to an existing chat session."""
    st.session_state.current_chat_id = chat_id

def clear_all_chats():
    """Clear all chat sessions."""
    st.session_state.chats = {"default": []}
    st.session_state.current_chat_id = "default"

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### 💬 Conversations")
    if st.button("➕ New Chat", use_container_width=True):
        create_new_chat()
        st.rerun()
        
    st.divider()
    
    # List existing chats
    for chat_id, messages in st.session_state.chats.items():
        # Derive a title from the first message
        if messages:
            title = messages[0]["content"][:25]
            if len(messages[0]["content"]) > 25:
                title += "..."
        else:
            title = "Empty Chat"
            
        # Highlight active chat
        button_type = "primary" if chat_id == st.session_state.current_chat_id else "secondary"
        
        if st.button(f"🗨️ {title}", key=f"btn_{chat_id}", use_container_width=True, type=button_type):
            switch_chat(chat_id)
            st.rerun()
            
    st.divider()
    
    if st.button("🗑️ Clear All History", use_container_width=True):
        clear_all_chats()
        st.rerun()
        
    # Supported Funds Accordion
    with st.expander("🏦 Supported Funds", expanded=False):
        st.caption("I can answer factual questions about these schemes:")
        for scheme in KNOWN_SCHEMES:
            # Strip some common words for display
            display_name = scheme.replace("Direct Growth", "").replace("Direct Plan Growth", "").strip()
            st.markdown(f"- **{display_name}**")

    st.divider()
    
    # Ingestion Log Info
    ingestion_info = get_ingestion_info()
    if ingestion_info:
        st.caption(f"🔄 Data last refreshed: **{ingestion_info['time_str']}**")
        if ingestion_info["stale"]:
            st.warning("⚠️ Data is older than 48 hours. Information might be stale.")


# ----------------- MAIN CONTENT -----------------
st.markdown('<h1 class="gradient-text">HDFC Mutual Fund FAQ</h1>', unsafe_allow_html=True)
st.markdown("""
<div class="disclaimer">
    <strong>⚠️ Important:</strong> I provide factual answers based on scheme documents. I do not provide financial advice, recommendations, or future predictions.
</div>
""", unsafe_allow_html=True)

current_messages = st.session_state.chats[st.session_state.current_chat_id]

# Landing Page (Empty State)
if not current_messages:
    st.markdown("### Welcome! How can I help you today?")
    st.markdown("**Try asking:**")
    
    # Display sample questions as quick-start buttons
    cols = st.columns(3)
    with cols[0]:
        if st.button("Expense ratio of HDFC Small Cap Fund?", use_container_width=True):
            prompt = "What is the expense ratio of HDFC Small Cap Fund?"
            st.session_state.chats[st.session_state.current_chat_id].append({"role": "user", "content": prompt})
            with st.spinner("Searching scheme documents..."):
                response = answer_query(prompt)
                st.session_state.chats[st.session_state.current_chat_id].append({"role": "assistant", "content": response})
            st.rerun()
    with cols[1]:
        if st.button("Exit load for HDFC Mid Cap Fund?", use_container_width=True):
            prompt = "What is the exit load for HDFC Mid Cap Fund?"
            st.session_state.chats[st.session_state.current_chat_id].append({"role": "user", "content": prompt})
            with st.spinner("Searching scheme documents..."):
                response = answer_query(prompt)
                st.session_state.chats[st.session_state.current_chat_id].append({"role": "assistant", "content": response})
            st.rerun()
    with cols[2]:
        if st.button("Min SIP for HDFC Large Cap Fund?", use_container_width=True):
            prompt = "What is the minimum SIP amount for HDFC Large Cap Fund?"
            st.session_state.chats[st.session_state.current_chat_id].append({"role": "user", "content": prompt})
            with st.spinner("Searching scheme documents..."):
                response = answer_query(prompt)
                st.session_state.chats[st.session_state.current_chat_id].append({"role": "assistant", "content": response})
            st.rerun()

# Display Chat History
for message in current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Ask about expense ratios, exit loads, minimum SIP, etc..."):
    # Add user message to state
    st.session_state.chats[st.session_state.current_chat_id].append({"role": "user", "content": prompt})
    
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Searching scheme documents..."):
            response = answer_query(prompt)
            st.markdown(response)
            
            # Save to state
            st.session_state.chats[st.session_state.current_chat_id].append({"role": "assistant", "content": response})
