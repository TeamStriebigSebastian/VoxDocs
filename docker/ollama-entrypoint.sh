#!/bin/sh

# Start Ollama in the background.
/bin/ollama serve &
pid=$!

# Wait for Ollama service to start.
echo "Waiting for Ollama service to start..."
while ! ollama list 2>/dev/null; do   
  sleep 1
done

# Check if the model exists.
# We look for "mistral" in the output of 'ollama list'.
if ! ollama list | grep -q "mistral"; then
  echo "Model 'mistral' not found. Pulling now..."
  ollama pull mistral
  echo "Model 'mistral' pulled successfully."
else
  echo "Model 'mistral' already exists."
fi

# Wait for the Ollama process to exit.
wait $pid
