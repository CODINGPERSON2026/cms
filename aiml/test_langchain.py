from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="llama3.2",
    temperature=0
)

response = llm.invoke("Hello, tell me  about  data science in 5 concise points")

print(response.content)