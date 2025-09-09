from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()
client = OpenAI()

response = client.responses.create(
    model=os.getenv("OPEN_AI_MODEL"),
    input = "Top 3 equipos de la Liga de españa"
)

print(response.output_text)