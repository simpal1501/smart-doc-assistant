import streamlit as st
import os
import time
import html
from dotenv import load_dotenv
from rag_engine import RAGEngine

# Load local environment variables (override ensures changes to .env are applied on reload)
load_dotenv(override=True)

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="DocuMind AI - Smart Document Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import premium Google Fonts
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# Premium Custom CSS Styling for Modern Dashboard Aesthetics
st.markdown("""
<style>
    /* Hide Streamlit default branding & menus */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Global Styles */
    .stApp {
        background-color: #080B11;
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #F8FAFC;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1250px !important;
    }
    
    /* Header Section Styling */
    .header-badge {
        background: rgba(78, 101, 255, 0.12);
        color: #6C7AFA;
        padding: 5px 12px;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        display: inline-block;
        border: 1px solid rgba(78, 101, 255, 0.25);
        margin-bottom: 10px;
    }
    
    .title-text {
        font-weight: 800;
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 45%, #4E65FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.2rem;
        margin-bottom: 0px;
        letter-spacing: -1.5px;
        line-height: 1.2;
    }
    
    .subtitle-text {
        color: #8D99AE;
        font-size: 1.05rem;
        font-weight: 400;
        margin-top: 5px;
        margin-bottom: 30px;
        line-height: 1.6;
    }
    
    /* Glassmorphic Metrics Card */
    div[data-testid="stMetric"] {
        background: rgba(18, 24, 38, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.25);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    div[data-testid="stMetric"]:hover {
        border-color: rgba(78, 101, 255, 0.35);
        transform: translateY(-3px);
        box-shadow: 0 15px 35px 0 rgba(78, 101, 255, 0.15);
    }
    
    div[data-testid="stMetric"] label {
        color: #8D99AE !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }
    
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Sidebar Styles */
    section[data-testid="stSidebar"] {
        background-color: #0B0E17 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .sidebar-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-top: 10px;
        margin-bottom: 15px;
    }
    
    /* File Uploader styling */
    div[data-testid="stFileUploader"] {
        background: rgba(18, 24, 38, 0.4);
        border: 1px dashed rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 15px;
    }
    
    /* Button Styles */
    .stButton button {
        background: linear-gradient(135deg, #4E65FF 0%, #3549D1 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-weight: 700 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(78, 101, 255, 0.2) !important;
        width: 100%;
    }
    
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(78, 101, 255, 0.45) !important;
        color: #FFFFFF !important;
    }
    
    /* Custom Download Button styling (override standard streamlit styling for secondary action) */
    div[data-testid="stDownloadButton"] button {
        background: rgba(18, 24, 38, 0.6) !important;
        color: #92EFFD !important;
        border: 1px solid rgba(146, 239, 253, 0.2) !important;
        box-shadow: none !important;
    }
    
    div[data-testid="stDownloadButton"] button:hover {
        background: rgba(146, 239, 253, 0.08) !important;
        border-color: #92EFFD !important;
        transform: translateY(-1px) !important;
    }
    
    /* Custom Chat System */
    .chat-row {
        display: flex;
        margin-bottom: 24px;
        width: 100%;
        animation: chatSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    @keyframes chatSlideIn {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .user-row {
        justify-content: flex-end;
    }
    
    .assistant-row {
        justify-content: flex-start;
    }
    
    .chat-bubble {
        max-width: 75%;
        padding: 16px 20px;
        border-radius: 20px;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    .user-bubble {
        background: linear-gradient(135deg, #4E65FF 0%, #3549D1 100%);
        color: #FFFFFF;
        border-top-right-radius: 4px;
        box-shadow: 0 8px 24px rgba(78, 101, 255, 0.22);
    }
    
    .assistant-bubble {
        background: rgba(18, 24, 38, 0.85);
        color: #E2E8F0;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-top-left-radius: 4px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(12px);
    }
    
    .chat-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    
    .user-avatar {
        background: rgba(78, 101, 255, 0.15);
        border: 1px solid rgba(78, 101, 255, 0.4);
        margin-left: 14px;
    }
    
    .assistant-avatar {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
        margin-right: 14px;
    }
    
    /* Welcome Features Layout */
    .welcome-card {
        background: rgba(18, 24, 38, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 18px;
        padding: 30px;
        text-align: center;
        transition: all 0.3s ease;
        height: 100%;
    }
    
    .welcome-card:hover {
        border-color: rgba(78, 101, 255, 0.3);
        background: rgba(18, 24, 38, 0.7);
        transform: translateY(-4px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }
    
    .welcome-icon {
        font-size: 2.2rem;
        margin-bottom: 20px;
        display: inline-block;
        background: rgba(78, 101, 255, 0.1);
        color: #6C7AFA;
        padding: 14px 22px;
        border-radius: 50%;
    }
    
    /* Citations Styling */
    .citation-container {
        background: rgba(8, 11, 17, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 4px solid #FF6B6B !important;
        border-radius: 10px;
        padding: 16px 20px;
        margin-top: 15px;
        margin-bottom: 10px;
    }
    
    .source-tag {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
        color: #FFFFFF;
        padding: 3px 12px;
        border-radius: 50px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .relevance-badge {
        background: rgba(146, 239, 253, 0.08);
        color: #92EFFD;
        border: 1px solid rgba(146, 239, 253, 0.2);
        padding: 3px 12px;
        border-radius: 50px;
        font-size: 0.72rem;
        font-weight: 700;
        float: right;
    }
    
    .citation-text {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        color: #C0C9D9;
        line-height: 1.6;
        margin-top: 12px;
        background: rgba(0, 0, 0, 0.2);
        padding: 12px;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.02);
    }
    
    /* Tabs custom styling */
    div[data-testid="stTabBar"] {
        border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
        margin-bottom: 25px;
    }
    
    div[data-testid="stTabBar"] button {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        color: #8D99AE !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
    }
    
    div[data-testid="stTabBar"] button[aria-selected="true"] {
        color: #6C7AFA !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "rag_engine" not in st.session_state:
    with st.spinner("Initializing Local Embeddings Model... Please wait (takes a moment on first launch)"):
        st.session_state.rag_engine = RAGEngine()
        
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    
if "indexed_chunks" not in st.session_state:
    st.session_state.indexed_chunks = 0

if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None

# New session states for features
if "doc_summary" not in st.session_state:
    st.session_state.doc_summary = None

if "doc_quiz" not in st.session_state:
    st.session_state.doc_quiz = None

def convert_chat_to_markdown(history):
    if not history:
        return ""
    md_text = "# Chat Transcript - DocuMind AI\n\n"
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        md_text += f"### 👤 {role}:\n{msg['content']}\n\n"
        if "citations" in msg and msg["citations"]:
            md_text += "**Citations:**\n"
            for cite in msg["citations"]:
                md_text += f"- Citation {cite['index']} (Page {cite['page']} of {cite['source']}): _{cite['text']}_\n"
            md_text += "\n"
        md_text += "---\n\n"
    return md_text

# Load API Key from environment variable in background
api_key = os.getenv("GEMINI_API_KEY", "")

# Sidebar Content
with st.sidebar:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    # Isometric document database folder icon
    st.image("https://img.icons8.com/isometric/512/document.png", width=80)
    st.markdown("<div class='sidebar-header'>Database Manager</div>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Upload PDF Document",
        type=["pdf"],
        help="Upload files here to parse and index them in the local database."
    )
    
    if uploaded_file is not None:
        if st.session_state.uploaded_filename != uploaded_file.name:
            temp_dir = os.path.join(os.path.dirname(__file__), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            with st.spinner("Vectorizing document sections..."):
                start_time = time.time()
                num_chunks = st.session_state.rag_engine.process_pdf(temp_path)
                elapsed = time.time() - start_time
                
            st.session_state.indexed_chunks = num_chunks
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.doc_summary = None # Reset summary for new file
            st.session_state.doc_quiz = None # Reset quiz for new file
            st.toast(f"Successfully processed {num_chunks} chunks in {elapsed:.2f}s!", icon="✅")
            
            try:
                os.remove(temp_path)
            except Exception:
                pass
                
    if st.session_state.uploaded_filename:
        st.markdown(f"**📚 Database Source:**\n`{st.session_state.uploaded_filename}`")
        st.metric(label="Total Chunks Indexed", value=st.session_state.indexed_chunks)
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Reset Database"):
            st.session_state.rag_engine = RAGEngine()
            st.session_state.uploaded_filename = None
            st.session_state.indexed_chunks = 0
            st.session_state.chat_history = []
            st.session_state.doc_summary = None
            st.session_state.doc_quiz = None
            st.rerun()

# Main Screen Layout
st.markdown("<span class='header-badge'>Active AI Engine</span>", unsafe_allow_html=True)
st.markdown('<p class="title-text">DocuMind AI</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">Next-Generation Semantic Document Q&A Assistant built with Retrieval-Augmented Generation (RAG).</p>', unsafe_allow_html=True)

st.markdown("<div style='margin-top: -15px;'></div>", unsafe_allow_html=True)

# Render Welcome Layout if no files uploaded
if not st.session_state.uploaded_filename:
    st.markdown("### How to Get Started")
    w1, w2, w3 = st.columns(3)
    
    with w1:
        st.markdown("""
        <div class="welcome-card">
            <div class="welcome-icon">📤</div>
            <h4>1. Upload PDF</h4>
            <p style='color: #8D99AE; font-size: 0.9rem;'>Upload your study material, textbook, or certificate PDF in the left sidebar panel.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with w2:
        st.markdown("""
        <div class="welcome-card">
            <div class="welcome-icon">⚙️</div>
            <h4>2. Vector Indexing</h4>
            <p style='color: #8D99AE; font-size: 0.9rem;'>The RAG Engine splits text into overlapping semantic blocks and stores them in ChromaDB.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with w3:
        st.markdown("""
        <div class="welcome-card">
            <div class="welcome-icon">💬</div>
            <h4>3. Ask & Verify</h4>
            <p style='color: #8D99AE; font-size: 0.9rem;'>Chat with your document and get verified answers with page numbers and relevance metrics.</p>
        </div>
        """, unsafe_allow_html=True)
else:
    # Main Page tabs
    tab1, tab2, tab3 = st.tabs(["💬 Conversation Chat", "📋 Document Summary", "📝 Interactive Study Quiz"])
    
    with tab1:
        # Render Custom Styled Chat Area
        for message in st.session_state.chat_history:
            role = message["role"]
            content = message["content"]
            
            if role == "user":
                st.markdown(f"""
                <div class="chat-row user-row">
                    <div class="chat-bubble user-bubble">
                        {content}
                    </div>
                    <div class="chat-avatar user-avatar">👤</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                citations_html = ""
                if "citations" in message and message["citations"]:
                    for cite in message["citations"]:
                        citations_html += f"""
                        <div class='citation-container'>
                            <span class='source-tag'>Citation {cite['index']}</span>
                            <div style='margin-top: 8px; font-weight: 600; font-size: 0.8rem; color: #8D99AE;'>
                                Page {cite['page']} • File: {cite['source']}
                            </div>
                            <div class='citation-text'>
                                {html.escape(cite['text'])}
                            </div>
                        </div>
                        """
                
                citations_block = ""
                if citations_html:
                    citations_block = f"""
                    <details style='margin-top: 15px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px;'>
                        <summary style='cursor: pointer; color: #92EFFD; font-size: 0.85rem; font-weight: 600;'>
                            🔍 View Citations & Source Passages
                        </summary>
                        {citations_html}
                    </details>
                    """
                    
                st.markdown(f"""
                <div class="chat-row assistant-row">
                    <div class="chat-avatar assistant-avatar">🧠</div>
                    <div class="chat-bubble assistant-bubble">
                        {content}
                        {citations_block}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        # Export Button at the bottom of the chat conversation
        if st.session_state.chat_history:
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            chat_md = convert_chat_to_markdown(st.session_state.chat_history)
            st.download_button(
                label="📥 Export Chat Transcript (.md)",
                data=chat_md,
                file_name=f"documind_chat_{int(time.time())}.md",
                mime="text/markdown"
            )

    with tab2:
        st.markdown("### Document Executive Summary")
        st.markdown("Generate a structured summary of the key facts, statistics, and takeaways of your uploaded PDF.")
        
        if st.session_state.doc_summary:
            st.markdown(f"<div class='assistant-bubble' style='max-width: 100%; padding: 24px;'>{st.session_state.doc_summary}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("✨ Generate Executive Summary"):
                with st.spinner("Extracting contents and synthesizing summary..."):
                    summary = st.session_state.rag_engine.generate_summary(api_key=api_key)
                    st.session_state.doc_summary = summary
                st.rerun()
                
    with tab3:
        st.markdown("### Interactive Study Quiz")
        st.markdown("Test your comprehension of the uploaded document. The AI will generate multiple-choice questions (MCQs) and explain the correct answers based *only* on the document facts.")
        
        if st.session_state.doc_quiz:
            st.markdown(f"<div class='assistant-bubble' style='max-width: 100%; padding: 24px;'>{st.session_state.doc_quiz}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("📝 Create Interactive Study Quiz"):
                with st.spinner("Analyzing document parameters and generating MCQs..."):
                    quiz = st.session_state.rag_engine.generate_quiz(api_key=api_key)
                    st.session_state.doc_quiz = quiz
                st.rerun()

# Chat Input & RAG Execution (Triggers in Tab 1)
if query := st.chat_input("Ask a question about your uploaded document..."):
    if not st.session_state.uploaded_filename:
        st.error("Please upload a PDF file in the sidebar before asking questions!")
    else:
        # User message display
        st.markdown(f"""
        <div class="chat-row user-row">
            <div class="chat-bubble user-bubble">
                {query}
            </div>
            <div class="chat-avatar user-avatar">👤</div>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.chat_history.append({"role": "user", "content": query})
        
        # Assistant generation
        with st.spinner("Analyzing document database..."):
            start_time = time.time()
            
            # 1. Similarity Search on Vector DB
            retrieved_docs = st.session_state.rag_engine.retrieve_context(query, k=3)
            matched_docs = [doc for doc, score in retrieved_docs]
            
            # 2. Query LLM with context
            answer, citations = st.session_state.rag_engine.generate_answer(
                query=query,
                context_docs=matched_docs,
                api_key=api_key
            )
            
            elapsed = time.time() - start_time
            
        # Format citation HTML for rendering immediately
        citations_html = ""
        for i, doc_score in enumerate(retrieved_docs):
            doc, score = doc_score
            page = doc.metadata.get("page", 0) + 1
            citations_html += f"""
            <div class='citation-container'>
                <span class='source-tag'>Citation {i+1}</span>
                <span class='relevance-badge'>Distance Score: {score:.4f}</span>
                <div style='margin-top: 8px; font-weight: 600; font-size: 0.8rem; color: #8D99AE;'>
                    Page {page} • File: {os.path.basename(doc.metadata.get('source', 'Doc'))}
                </div>
                <div class='citation-text'>
                    {html.escape(doc.page_content)}
                </div>
            </div>
            """
            
        citations_block = ""
        if citations_html:
            citations_block = f"""
            <details style='margin-top: 15px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px;'>
                <summary style='cursor: pointer; color: #92EFFD; font-size: 0.85rem; font-weight: 600;'>
                    🔍 View Citations & Source Passages
                </summary>
                {citations_html}
            </details>
            """
            
        # Display assistant response
        st.markdown(f"""
        <div class="chat-row assistant-row">
            <div class="chat-avatar assistant-avatar">🧠</div>
            <div class="chat-bubble assistant-bubble">
                {answer}
                {citations_block}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Save to session history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": answer,
            "citations": citations
        })
        
        st.toast(f"Generated answer in {elapsed:.2f} seconds!", icon="⚡")
