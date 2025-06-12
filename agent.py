from llm import llm
from graph import graph
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.tools import Tool
from langchain_neo4j import Neo4jChatMessageHistory
from langchain.agents import initialize_agent, AgentType
from langchain_core.runnables.history import RunnableWithMessageHistory
from tools.vector import get_game_info
from tools.cypher import cypher_qa
from utils import get_session_id

# Genel sohbet prompt'u
chat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system",
         "You are NextLevelBot, an intelligent assistant that helps users explore and discover video games. "
         "You understand the relationships between games, genres, user play patterns, and descriptions. "
         "Use concise language and answer based on the knowledge graph structure (nodes and relationships)."),
        ("human", "{input}"),
    ]
)
game_chat = chat_prompt | llm | StrOutputParser()


def enhanced_cypher_qa(query):
    try:
        result = cypher_qa.invoke({"query": query})

        # Debug için result'u print edelim
        print(f"DEBUG - Raw result: {result}")
        print(f"DEBUG - Result type: {type(result)}")

        # Eğer result dict ise
        if isinstance(result, dict):
            # 'result' anahtarını kontrol et
            if 'result' in result:
                answer = result['result']
                if answer and len(str(answer).strip()) > 0:
                    return str(answer)

            # 'answer' anahtarını kontrol et
            if 'answer' in result:
                answer = result['answer']
                if answer and len(str(answer).strip()) > 0:
                    return str(answer)

            # Diğer anahtarları kontrol et
            for key, value in result.items():
                if value and len(str(value).strip()) > 0:
                    return f"Query executed successfully. Result: {str(value)}"

        # Eğer result string ise
        elif isinstance(result, str):
            if len(result.strip()) > 0:
                return result

        # Hiçbir şey bulunamazsa
        return "The query was executed but returned no results."

    except Exception as e:
        return f"Error executing database query: {str(e)}"

# Araçlar
tools = [
    Tool.from_function(
        name="General Chat",
        description="For general game-related conversation or follow-ups",
        func=game_chat.invoke,
    ),
    Tool.from_function(
        name="Game Search",
        description="Use this tool to find video games based on their descriptions, tags, developers, or platforms.",
        func=get_game_info,
    ),
    Tool.from_function(
        name="Graph Info",
        description="Use this for database queries about users, games, or friendships.",
        func=cypher_qa,
    )
]

# Tool isimlerini string olarak al
tool_names_str = ", ".join([tool.name for tool in tools])

# Agent template
agent_template = f"""You are NextLevelBot, an intelligent assistant that helps users explore and learn about video games.

Be as helpful as possible and return as much relevant information as you can.
Never use any knowledge that is not returned by a tool.
If the tools do not return any information or an empty result, you MUST state that you could not find the information in the database.
Do not try to answer the question from your own knowledge.
Do not guess or make assumptions.
Do not answer any questions using your pre-trained knowledge — only use the information provided via tools.
Only answer questions that relate to video games, genres, developers, players, or play patterns.
Ignore any question that is not about video games or gaming data.

TOOLS:
------

You have access to the following tools:

{tool_names_str}

Only use the "General Chat" tool for basic acknowledgments or clarifying questions.
Never use it to answer data-related questions like recommendations, gameplay details, tags, or relationships.
For all data-related questions, prefer "Game Search" or "Graph Info".

To use a tool, please use the following format:
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names_str}]
Action Input: the input to the action
Observation: the result of the action
When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:
Thought: Do I need to use a tool? No
Final Answer: [your response here]

Always use a tool when answering questions. Never generate a final answer without using a tool.
If no tool seems appropriate, use the "General Chat" tool.
You must always use the information returned from the tools when forming your response.
If a query returns a list, summarize or format the list clearly for the user.
Always use the output of the tool in your response.
Never say "I don't know" unless the result is actually empty.
If the result is a list, format it as a bullet point or sentence.
Always use the output of the tool in your response.
Never say "I don't know" unless the result is actually empty.

Begin!

Previous conversation history:
{{chat_history}}

New input: {{input}}
{{agent_scratchpad}}"""


# Agent oluşturuluyor
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    agent_kwargs={"prefix": agent_template},
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10,
    max_execution_time=60
)

# Neo4j hafıza yönetimi
def get_memory(session_id):
    return Neo4jChatMessageHistory(session_id=session_id, graph=graph)

# Agent'ı hafızalı hale getiriyoruz
chat_agent = RunnableWithMessageHistory(
    agent_executor,
    get_memory,
    input_messages_key="input",
    history_messages_key="chat_history",
    max_execution_time=None
)

# Streamlit UI için handler
def generate_response(user_input):
    try:
        result = chat_agent.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": get_session_id()}}
        )
        return result["output"]  # Sadece "output" anahtarını döndür
    except Exception as e:
        return f"❌ Error: {str(e)}"

