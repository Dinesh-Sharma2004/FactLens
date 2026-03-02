from transformers import pipeline
import time

generator = pipeline("text-generation", model="google/flan-t5-base")

def stream_generate(prompt):
    # Simulated streaming (token chunks)
    response = generator(prompt, max_new_tokens=100)[0]["generated_text"]

    words = response.split()
    for word in words:
        yield word + " "
        time.sleep(0.05)
