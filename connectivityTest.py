from ollama import Client

SERVER_IP = '100.85.195.54'

client = Client(host='http://'+ SERVER_IP + ':11434')
response = client.chat(model='gemma2:2b', messages=[
  {'role': 'user', 'content': 'Why is the sky blue?'}
])

print(response['message']['content'])