import streamlit as st
import requests
import json
from pymongo import MongoClient
import datetime

# Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

st.set_page_config(page_title="Aimad's Chatbot", page_icon=":robot_face:", layout="wide")

styling = """
    <style>
        .stApp {
            background: linear-gradient(134deg, #726E6E, #203a43);
        }
        .title {
            text-align: center;
            color: white;
            padding: 20px;
            border-radius: 10px;
            background: rgba(0, 0, 0, 0.2);
            margin-bottom: 20px;
        }
        .stTextInput > div > div > input {
            background-color: rgba(255, 255, 255, 0.1);
            color: white;
        }
        .stButton > button {
            background-color: #4CAF50;
            color: white;
            border-radius: 10px;
            margin: 5px 0;
            width: 100%;
        }
        .chat-message {
            padding: 10px;
            border-radius: 10px;
            margin: 5px 0;
        }
        .input-container {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(32, 58, 67, 0.9);
            padding: 20px;
            z-index: 1000;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        .main-content {
            padding-bottom: 100px;
        }
        /* Saved chats styling */
        .saved-chat-button {
            margin: 5px 0;
            padding: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
            cursor: pointer;
        }
    </style>
"""

# API Configuration
with open("API") as f:
    API_KEY = f.read().strip()
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def get_gemini_response(prompt):
    """Get response from Gemini API"""
    # Custom prompt handling
    if any(phrase in prompt.lower() for phrase in ["who are you", "what are you", "introduce yourself"]):
        return "I am a large language model called Gemini, trained by Google. Aimad is using me in his project to create an interactive chatbot. I'm designed to help answer questions and engage in conversations on a wide range of topics."
    
    try:
        full_url = f"{API_URL}?key={API_KEY}"
        
        # Add system context to every prompt
        system_context = """You are Gemini, a large language model trained by Google. 
        You are being used in Aimad's project. Always be helpful and informative."""
        
        enhanced_prompt = f"{system_context}\n\nUser: {prompt}"
        
        data = {
            "contents": [{
                "parts": [{
                    "text": enhanced_prompt
                }]
            }]
        }
        
        response = requests.post(
            full_url,
            headers={"Content-Type": "application/json"},
            json=data
        )
        
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        
        response_data = response.json()
        
        if "error" in response_data:
            return f"API Error: {response_data['error']['message']}"
        
        return response_data["candidates"][0]["content"]["parts"][0]["text"]
    
    except Exception as e:
        return f"Error communicating with Gemini API: {str(e)}"

def load_chat_history(collection, chat_id):
    """Load a specific chat history from MongoDB"""
    chat = collection.find_one({"_id": chat_id})
    if chat:
        st.session_state.messages = chat["messages"]
        return True
    return False

def save_chat_history(collection, messages):
    """Save current chat history to MongoDB"""
    if messages:
        chat_data = {
            "timestamp": datetime.datetime.now(),
            "messages": messages
        }
        result = collection.insert_one(chat_data)
        return result.inserted_id
    return None

def format_datetime(dt):
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M")

def main():
    st.markdown(styling, unsafe_allow_html=True)
    st.markdown("<div class='title'><h1>💬 Aimad's Chatbot</h1></div>", unsafe_allow_html=True)
    
    # MongoDB connection
    client = MongoClient("mongodb://localhost:27017/")
    db = client["chatbot"]
    collection = db["chats"]

    # Sidebar
    with st.sidebar:
        st.title("About")
        st.markdown("""
        This chatbot uses Google's Gemini AI model to generate responses.
        
        - Type your message in the input box below
        - Press Enter to send
        - The chat history will be preserved during your session
        """)
        
        st.title("Saved Conversations")
        
        # Fetch all saved conversations with proper projection
        saved_chats = list(collection.find().sort("timestamp", -1))
        
        if saved_chats:
            st.write("Select a conversation to load:")
            for chat in saved_chats:
                if 'timestamp' in chat:  # Check if timestamp exists
                    chat_datetime = format_datetime(chat["timestamp"])
                    if st.button(f"Load chat from {chat_datetime}", key=str(chat["_id"])):
                        if load_chat_history(collection, chat["_id"]):
                            st.success("Chat loaded successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to load chat history")
        else:
            st.write("No saved conversations yet")
        
        if st.button("Clear Current Chat"):
            st.session_state.messages = []
            st.rerun()

    # Main content container with padding at bottom
    with st.container():
        st.markdown('<div class="main-content">', unsafe_allow_html=True)
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        st.markdown('</div>', unsafe_allow_html=True)

    # Fixed input container at bottom
    st.markdown("""
        <div class='input-container'>
            <div style='max-width: 1200px; margin: 0 auto;'>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Input and button in the fixed container
    col1, col2 = st.columns([6, 1])
    
    with col1:
        prompt = st.chat_input("What's on your mind?")
    
    with col2:
        save_button = st.button("Save Chat")

    if prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_gemini_response(prompt)
                st.markdown(response)
                
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Handle save functionality
    if save_button and st.session_state.messages:
        try:
            chat_data = {
                "timestamp": datetime.datetime.now(),
                "messages": st.session_state.messages
            }
            result = collection.insert_one(chat_data)
            if result.inserted_id:
                st.success("Chat history saved successfully!")
                st.rerun()
            else:
                st.warning("Failed to save chat history")
        except Exception as e:
            st.error(f"Error saving chat history: {str(e)}")

if __name__ == "__main__":
    main()
