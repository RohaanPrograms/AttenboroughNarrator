from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input="what happens if i do stream = true"
)
print(interaction.output_text)