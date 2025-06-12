import sys
import os

# cypher.py dosyasının bulunduğu dizin
current_dir = os.path.dirname(os.path.abspath(__file__))

# llm-chatbot-python ana dizinine gitmek için:
# current_dir -> tools/ -> llm-chatbot-python/
project_root = os.path.abspath(os.path.join(current_dir, '..'))

# Bu yolu Python'ın modül arama yoluna ekle
sys.path.append(project_root)

# Şimdi llm modülünü doğrudan içe aktarabilirsiniz
import streamlit as st
from llm import llm, embeddings
from graph import graph
from langchain_neo4j import Neo4jVector
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

# Create the Neo4jVector
neo4jvector = Neo4jVector.from_existing_index(
    embeddings,
    graph=graph,
    index_name="gameDescriptions",               # Bu ismin Description düğümü üzerinde oluşturulmuş bir indekse ait olduğundan emin olun
    node_label="Description",                  # Düğüm etiketi 'Description' olarak değiştirildi
    text_node_property="text",                 # Metnin bulunduğu özellik 'text' olarak değiştirildi
    embedding_node_property="embedding",       # Embedding'in bulunduğu özellik (Description düğümünde)
    retrieval_query="""
// Vektör araması bir 'Description' düğümü bulur, bu düğüme 'node' olarak erişilir.
// Bu 'node'dan yola çıkarak ilişkili 'Game' düğümünü buluyoruz.
MATCH (game:Game)-[:HAS_DESCRIPTION]->(node)

// 'game' düğümünü bulduktan sonra, onunla ilgili diğer tüm verileri topluyoruz.
MATCH (game:Game)-[:HAS_DESCRIPTION]->(node)

// Tüm ilişkili verileri toplama
OPTIONAL MATCH (game)-[:HAS_TAG]->(t:Tag)
OPTIONAL MATCH (game)-[:SUPPORTS]->(p:Platform)
OPTIONAL MATCH (game)<-[:PLAYED]-(u:User)
OPTIONAL MATCH (game)-[:REVIEWS]->(r:Review)<-[:WROTE_REVIEW]-(reviewer:User)

// Gruplama anahtarlarını açıkça belirtme
WITH 
    node, 
    game, 
    score,  // score'u burada ekliyoruz
    collect(DISTINCT t) AS tags_collected,
    collect(DISTINCT p) AS platforms_collected,
    collect(DISTINCT u) AS users_collected,
    collect(DISTINCT {review: r, reviewer: reviewer}) AS reviews_collected

// Aggregasyonları yapma
RETURN
    node.text AS text,
    score,
    {
        name: game.title,
        app_id: game.app_id,
        tags: [tag IN tags_collected | tag.name],
        platforms: [platform IN platforms_collected | platform.name],
        total_players: size(users_collected),
        reviews: [item IN reviews_collected | {
            user: item.reviewer.username,
            recommended: item.review.is_recommended,
            helpful: item.review.helpful,
            funny: item.review.funny,
            date: item.review.date
        }]
    } AS metadata
"""
)

# Create the retriever
retriever = neo4jvector.as_retriever()

instructions = (
    "You are an assistant answering questions about video games based on the provided context."
    "The context below contains descriptions of one or more video games."
    "You MUST use ONLY the information from the provided context to answer the question."
    "Do not use any of your own external knowledge."
    "If the provided context does not contain the answer to the question, you MUST state that you cannot find the information in the game descriptions."
    "Do not try to make up an answer or add information not present in the context."
    "Context: {context}"
)


# Create the prompt
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", instructions),
        ("human", "{input}"),
    ]
)
# Create the chain
question_answer_chain = create_stuff_documents_chain(llm, prompt)
game_qa_chain = create_retrieval_chain(
    retriever,               # Neo4jVector retriever
    question_answer_chain    # LLM + Prompt zinciri
)
# Create a function to call the chain
def get_game_info(user_input):
    response = game_qa_chain.invoke({"input": user_input})

    return response['answer']
