#!/bin/bash

# Script to initialize Ollama with required models
# This should be run after the Ollama container is up and healthy

echo "Initializing Ollama with required models..."

# Wait for Ollama to be ready
echo "Waiting for Ollama service to be ready..."
until $(curl --output /dev/null --silent --fail http://localhost:11434/api/tags); do
    printf '.'
    sleep 5
done
echo "Ollama service is ready!"

# Pull the Mistral model
echo "Pulling Mistral 7B Instruct model (this may take a while)..."
curl -X POST http://localhost:11434/api/pull -d '{"name": "mistral:7b-instruct-v0.2-q8_0"}'

# Verify the model was downloaded
echo "Verifying model installation..."
curl -s http://localhost:11434/api/tags | grep -q "mistral:7b-instruct-v0.2-q8_0"
if [ $? -eq 0 ]; then
    echo "✅ Mistral model installed successfully!"
else
    echo "❌ Mistral model installation failed. Please check the Ollama logs."
    exit 1
fi

echo "Ollama initialization complete!"