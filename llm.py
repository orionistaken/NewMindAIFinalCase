import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

# Create the LLM
llm = ChatOpenAI(
    openai_api_key=st.secrets["OPENAI_API_KEY"],
    model=st.secrets["OPENAI_MODEL"],
    temperature=0,
    max_tokens=4000,
)

# Create the Embedding model
embeddings = OpenAIEmbeddings(
    openai_api_key=st.secrets["OPENAI_API_KEY"]
)