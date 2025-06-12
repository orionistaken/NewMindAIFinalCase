import streamlit as st
from utils import write_message
from agent import generate_response
import time
from neo4j import GraphDatabase
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Tuple


# --- Neo4j Bağlantı Ayarları ---
@st.cache_resource
def init_neo4j_connection():
    """Neo4j veritabanı bağlantısını başlat"""
    try:
        # Neo4j bağlantı bilgilerini buraya girin
        NEO4J_URI = st.secrets.get("NEO4J_URI", "bolt://localhost:7687")
        NEO4J_USERNAME = st.secrets.get("NEO4J_USERNAME", "neo4j")
        NEO4J_PASSWORD = st.secrets.get("NEO4J_PASSWORD", "password")

        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        return driver
    except Exception as e:
        st.error(f"Neo4j bağlantı hatası: {e}")
        return None


@st.cache_data(ttl=300)  # 5 dakika cache
def get_graph_statistics():
    """Graf istatistiklerini getir"""
    driver = init_neo4j_connection()
    if not driver:
        return {"nodes": 0, "relationships": 0, "node_types": [], "rel_types": []}

    try:
        with driver.session() as session:
            # Node sayısı
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]

            # İlişki sayısı
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

            # Node türleri
            node_types = session.run("""
                MATCH (n) 
                RETURN labels(n) as labels, count(*) as count 
                ORDER BY count DESC
            """).data()

            # İlişki türleri
            rel_types = session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) as type, count(*) as count 
                ORDER BY count DESC
            """).data()

            return {
                "nodes": node_count,
                "relationships": rel_count,
                "node_types": node_types,
                "rel_types": rel_types
            }
    except Exception as e:
        st.error(f"Veri getirme hatası: {e}")
        return {"nodes": 0, "relationships": 0, "node_types": [], "rel_types": []}


@st.cache_data(ttl=300)
def get_sample_graph_data(limit: int = 50):
    """Örnek graf verisi getir - Network graph kaldırıldığı için basitleştirildi"""
    return [], []


st.set_page_config(
    page_title="NextLevelBot - Gaming Assistant",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .main {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }

    /* Header styling */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #9147ff, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
    }

    .main-header .game-icon {
        background: linear-gradient(90deg, #9147ff, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        filter: drop-shadow(0 0 10px rgba(145, 71, 255, 0.5));
    }

    .sub-header {
        text-align: center;
        color: #a0a0a0;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        padding: 0 2rem;
    }

    /* Chat message styling */
    div.stChatMessage {
        font-size: 16px;
        padding: 1rem 1.5rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        border: 1px solid transparent;
    }

    .stChatMessage[data-testid="chat-message-user"] {
        background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);
        border: 1px solid #4a5568;
        margin-left: 2rem;
    }

    .stChatMessage[data-testid="chat-message-assistant"] {
        background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
        border: 1px solid #9147ff;
        margin-right: 2rem;
    }

    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #9147ff 0%, #00d4ff 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(145, 71, 255, 0.4);
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(145, 71, 255, 0.6);
        background: linear-gradient(135deg, #7c3aed 0%, #0891b2 100%);
    }

    /* Chat input styling */
    .stChatInput {
        border-radius: 16px;
        background-color: #2d3748;
        border: 2px solid #4a5568;
    }

    .stChatInput:focus {
        border-color: #9147ff;
        box-shadow: 0 0 0 3px rgba(145, 71, 255, 0.1);
    }

    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }

    /* Stats cards */
    .stat-card {
        background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);
        padding: 1.5rem;
        border-radius: 16px;
        text-align: center;
        margin: 1rem 0;
        border: 1px solid #4a5568;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #9147ff;
        margin-bottom: 0.5rem;
    }

    .stat-label {
        color: #a0a0a0;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Gaming theme icons */
    .game-icon {
        display: inline-block;
        margin: 0 0.5rem;
        font-size: 1.5rem;
        color: #9147ff;
        text-shadow: 0 0 10px rgba(145, 71, 255, 0.5);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { 
            opacity: 1; 
            transform: scale(1);
        }
        50% { 
            opacity: 0.7; 
            transform: scale(1.1);
        }
        100% { 
            opacity: 1; 
            transform: scale(1);
        }
    }

    /* Loading animation */
    .loading-text {
        text-align: center;
        color: #9147ff;
        font-weight: 600;
        animation: glow 1.5s ease-in-out infinite alternate;
    }

    @keyframes glow {
        from { text-shadow: 0 0 5px #9147ff; }
        to { text-shadow: 0 0 20px #9147ff, 0 0 30px #9147ff; }
    }

    /* Graph visualization */
    .graph-container {
        background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
        border-radius: 16px;
        padding: 1rem;
        margin: 1rem 0;
        border: 1px solid #4a5568;
    }

    .node-type-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        background: linear-gradient(135deg, #9147ff 0%, #00d4ff 100%);
        color: white;
    }

    .rel-type-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        background: linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%);
        color: white;
    }

    .graph-stats {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .mini-stat {
        text-align: center;
        padding: 0.5rem;
        background: rgba(145, 71, 255, 0.1);
        border-radius: 8px;
        border: 1px solid rgba(145, 71, 255, 0.3);
    }

    .mini-stat-number {
        font-size: 1.2rem;
        font-weight: 600;
        color: #9147ff;
    }

    .mini-stat-label {
        font-size: 0.7rem;
        color: #a0a0a0;
        text-transform: uppercase;
    }
    # Hide Streamlit branding
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🎮 NextLevelBot")
    st.markdown("---")

    # Neo4j Graf Bilgileri
    st.markdown("### 🔗 Database Overview")

    # Graf istatistiklerini getir
    graph_stats = get_graph_statistics()

    # Mini istatistikler
    st.markdown(f"""
        <div class="graph-stats">
            <div class="mini-stat">
                <div class="mini-stat-number">{graph_stats['nodes']:,}</div>
                <div class="mini-stat-label">Nodes</div>
            </div>
            <div class="mini-stat">
                <div class="mini-stat-number">{graph_stats['relationships']:,}</div>
                <div class="mini-stat-label">Relations</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Node türleri
    if graph_stats['node_types']:
        st.markdown("**Node Types:**")
        for node_type in graph_stats['node_types'][:5]:  # İlk 5 tür
            labels = node_type['labels']
            label_text = ', '.join(labels) if labels else 'No Label'
            count = node_type['count']
            st.markdown(f"""
                <span class="node-type-badge">{label_text} ({count})</span>
            """, unsafe_allow_html=True)

    # İlişki türleri
    if graph_stats['rel_types']:
        st.markdown("**Relationship Types:**")
        for rel_type in graph_stats['rel_types'][:5]:  # İlk 5 tür
            rel_name = rel_type['type']
            count = rel_type['count']
            st.markdown(f"""
                <span class="rel-type-badge">{rel_name} ({count})</span>
            """, unsafe_allow_html=True)

    # Graf görselleştirme
    st.markdown("### 📊 Graph Visualization")

    # Görselleştirme seçenekleri
    viz_option = st.selectbox(
        "Visualization Type:",
        ["Node Statistics", "Relationship Statistics"]
    )

    if viz_option == "Node Statistics":
        # Node istatistikleri bar chart
        if graph_stats['node_types']:
            node_df = pd.DataFrame([
                {
                    'type': ', '.join(nt['labels']) if nt['labels'] else 'No Label',
                    'count': nt['count']
                }
                for nt in graph_stats['node_types'][:10]
            ])

            fig = go.Figure(data=[
                go.Bar(
                    x=node_df['count'],
                    y=node_df['type'],
                    orientation='h',
                    marker_color='#9147ff'
                )
            ])
            fig.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig, use_container_width=True)
    elif viz_option == "Relationship Statistics":
        # İlişki istatistikleri bar chart
        if graph_stats['rel_types']:
            rel_df = pd.DataFrame([
                {'type': rt['type'], 'count': rt['count']}
                for rt in graph_stats['rel_types'][:10]
            ])

            fig = go.Figure(data=[
                go.Bar(
                    x=rel_df['count'],
                    y=rel_df['type'],
                    orientation='h',
                    marker_color='#00d4ff'
                )
            ])
            fig.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Veritabanı işlemleri
    st.markdown("### 🔄 Database Actions")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with col2:
        if st.button("📊 Query DB", use_container_width=True):
            st.session_state.show_query_input = True

    # Özel sorgu girişi
    if st.session_state.get('show_query_input', False):
        st.markdown("**Custom Cypher Query:**")
        custom_query = st.text_area(
            "Enter Cypher query:",
            placeholder="MATCH (g:Game) RETURN g.title LIMIT 5",
            height=100
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Execute", use_container_width=True):
                if custom_query:
                    try:
                        driver = init_neo4j_connection()
                        if driver:
                            with driver.session() as session:
                                result = session.run(custom_query).data()
                                st.json(result[:5])  # İlk 5 sonucu göster
                    except Exception as e:
                        st.error(f"Query error: {e}")

        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_query_input = False
                st.rerun()

    st.markdown("---")

    # Bot istatistikleri
    if "conversation_count" not in st.session_state:
        st.session_state.conversation_count = 0
    if "total_responses" not in st.session_state:
        st.session_state.total_responses = 0

    st.markdown("""
        <div class="stat-card">
            <div class="stat-number">{}</div>
            <div class="stat-label">Conversations</div>
        </div>
    """.format(st.session_state.conversation_count), unsafe_allow_html=True)

    st.markdown("""
        <div class="stat-card">
            <div class="stat-number">{}</div>
            <div class="stat-label">Responses</div>
        </div>
    """.format(st.session_state.total_responses), unsafe_allow_html=True)

    st.markdown("---")

    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi, I'm the NextLevelBot! 🎮 How can I help you with gaming today?"},
        ]
        st.rerun()

# --- Ana İçerik ---
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # --- Başlık ---
    st.markdown("""
        <div class="main-header">
            🎮 NextLevelBot
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="sub-header">
            Your AI-powered gaming assistant for recommendations, insights, and player behavior analysis
        </div>
    """, unsafe_allow_html=True)

# --- Oturum Durumu ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi, I'm the NextLevelBot! 🎮 How can I help you with gaming today?"},
    ]


# --- Mesaj Gönderimi ---
def handle_submit(message):
    # Loading animasyonu
    loading_placeholder = st.empty()
    loading_placeholder.markdown("""
        <div class="loading-text">
            🧠 Analyzing gaming data and generating response...
        </div>
    """, unsafe_allow_html=True)

    try:
        with st.spinner('Processing...'):
            response = generate_response(message)
            st.session_state.total_responses += 1
            write_message('assistant', response)
        loading_placeholder.empty()
    except Exception as e:
        loading_placeholder.empty()
        write_message('assistant', f"🚫 Sorry, I encountered an error: {str(e)}")


# --- Hızlı soru işleme ---
# Quick question bölümü kaldırıldı

# --- Chat Container ---
chat_container = st.container()

with chat_container:
    # --- Önceki Mesajlar ---
    for message in st.session_state.messages:
        write_message(message['role'], message['content'], save=False)

# --- Chat Input Section ---
st.markdown("---")

# Input alanı
col1, col2 = st.columns([4, 1])

with col1:
    if question := st.chat_input("Ask me about games, players, recommendations... 🎮"):
        write_message('user', question)
        handle_submit(question)
        st.session_state.conversation_count += 1

# --- Footer ---
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; font-size: 14px; padding: 1rem;">
        🎮 NextLevelBot | Powered by AI Gaming Intelligence | 
        <span style="color: #9147ff;">Level up your gaming experience!</span>
    </div>
""", unsafe_allow_html=True)