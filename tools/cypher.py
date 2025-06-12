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
from llm import llm
from graph import graph
from langchain_neo4j import GraphCypherQAChain
from langchain.prompts.prompt import PromptTemplate

# --- DÜZELTİLMİŞ TEMPLATE ---
# Değişken olmayan tüm süslü parantezler çiftlenerek {{ ve }} haline getirildi.
CYPHER_GENERATION_TEMPLATE = """
Task: Generate Cypher query based on user's question.
Instructions:
- Use ONLY the provided schema
- Output ONLY the executable Cypher query
- Never include explanations, markdown, or natural language
- Start directly with Cypher keywords (MATCH, RETURN, etc.)
You are an expert Neo4j Developer translating user questions into Cypher to answer questions about video games and generate personalized recommendations.
Convert the user's question based on the provided schema.

Use only the relationship types and properties explicitly mentioned in the schema.
Do not invent or assume any other relationship types or properties.

Do not return entire nodes or any embedding-related properties.

Schema includes information about:
- Games and their properties (title, app_id, release_date, price, recommendation_count, etc.)
- Descriptions connected via (Game)-[:HAS_DESCRIPTION]->(Description)
- Tags, Platforms connected via (Game)-[:HAS_TAG]->(Tag), (Game)-[:SUPPORTS]->(Platform)
- Users and their play behavior via (User)-[:PLAYED]->(Game) including total_playtime, days_per_week, last_played_date
- Friends relationships: (User)-[:FRIENDS_WITH]-(User)
- Review statistics: (User)-[:WROTE_REVIEW]->(Review)-[:REVIEWS]->(Game)

Do not return the full Description text unless the user specifically asks for it.

Fine-Tuning:
- If a game title starts with "The", move "The" to the end for sorting or matching purposes. 
  For example, "The Witcher 3" becomes "Witcher 3, The".

Example Cypher Statements:

1. To find who played a game:
MATCH (u:User)-[p:PLAYED]->(g:Game {{title: "Stardew Valley"}})
RETURN u.username, p.total_playtime, p.days_per_week

2. To find games with a specific tag:
MATCH (g:Game)-[:HAS_TAG]->(t:Tag {{name: "RPG"}})
RETURN g.title, g.app_id

3. To get games a user's friends have played:
MATCH (u:User {{username: "gamer123"}})-[:FRIENDS_WITH]-(f:User)-[:PLAYED]->(g:Game)
RETURN g.title, count(*) AS times_played
ORDER BY times_played DESC

4. Get all games supported on a specific platform:
MATCH (g:Game)-[:SUPPORTS]->(p:Platform {{name: "Windows"}})
RETURN g.title, g.app_id, g.price

5. Retrieve top games played by a specific user (by total playtime):
MATCH (u:User {{username: "pixelninja"}})-[p:PLAYED]->(g:Game)
RETURN g.title, p.total_playtime
ORDER BY p.total_playtime DESC
LIMIT 5

6. Find games that are both RPG and Multiplayer:
MATCH (g:Game)-[:HAS_TAG]->(t1:Tag {{name: "RPG"}})
MATCH (g)-[:HAS_TAG]->(t2:Tag {{name: "Multiplayer"}})
RETURN g.title, g.app_id

7. Get games released after 2020:
MATCH (g:Game)
WHERE date(g.release_date) > date("2020-01-01")
RETURN g.title, g.release_date

8. Find which of my friends played a specific game:
MATCH (me:User {{username: "gamer123"}})-[:FRIENDS_WITH]->(f:User)-[:PLAYED]->(g:Game {{title: "Cyberpunk 2077"}})
RETURN f.username, g.name

9. Get top 10 most recommended games (based on recommendation_count):
MATCH (g:Game)
RETURN g.title, g.recommendation_count
ORDER BY g.recommendation_count DESC
LIMIT 10

10. Find games that users have recommended via reviews:
MATCH (u:User)-[:WROTE_REVIEW]->(r:Review {{is_recommended: true}})-[:REVIEWS]->(g:Game)
RETURN g.title, count(*) AS recommendation_count
ORDER BY recommendation_count DESC

11. List games played in the last 30 days:
MATCH (u:User)-[p:PLAYED]->(g:Game)
WHERE p.last_played_date >= date() - duration({{days: 30}})
RETURN DISTINCT g.title, p.last_played_date

12. Average number of days per week a specific game is played:
MATCH (u:User)-[p:PLAYED]->(g:Game {{title: "Elden Ring"}})
RETURN avg(p.days_per_week) AS avg_days_per_week

13. Tags and platforms for a specific game:
MATCH (g:Game {{name: "Hades"}})
OPTIONAL MATCH (g)-[:HAS_TAG]->(t:Tag)
OPTIONAL MATCH (g)-[:SUPPORTS]->(p:Platform)
RETURN g.title, collect(DISTINCT t.name) AS tags, collect(DISTINCT p.name) AS platforms

14. Find friends for a specific user:
MATCH (u:User {{username: "cooldragon_4617"}}) - [:FRIENDS_WITH] - (f:User)
RETURN f.username

Schema:
{schema}

Question:
{question}
"""

QA_GENERATION_TEMPLATE = """You are a helpful assistant that interprets Neo4j database query results.

The context below contains the actual results from a database query. 
Your job is to present this information in a clear, user-friendly format.

IMPORTANT: 
- If the context contains any data (usernames, game titles, numbers, etc.), that means the query WAS successful
- Do NOT say "not found" or "doesn't exist" if there is actual data in the context
- Always present the actual data from the context

Context from database: {context}

Original question: {question}

Rules:
1. If you see usernames in the context, list them
2. If you see game titles in the context, list them  
3. If you see any data in the context, present it clearly
4. Never ignore the context data
5. Format lists in a readable way

Your response:"""


cypher_prompt = PromptTemplate(
    input_variables=["schema", "question"],
    template=CYPHER_GENERATION_TEMPLATE
)

qa_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=QA_GENERATION_TEMPLATE
)

cypher_qa = GraphCypherQAChain.from_llm(
    llm,
    graph=graph,
    cypher_prompt=cypher_prompt,
    qa_prompt=qa_prompt,  # QA prompt eklendi
    verbose=True,
    validate_cypher=True,
    allow_dangerous_requests=True,
    return_intermediate_steps=False,  # Bu da önemli
    top_k=100,  # Daha fazla sonuç döndürmesi için
    return_direct=False  # Bu önemli - LLM'in sonucu işlemesi için
)
