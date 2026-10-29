#!/bin/bash

LLAMA="$HOME/llama.cpp/build/bin/llama-cli"

MODEL="$HOME/.cache/huggingface/hub/models--ggml-org--SmolVLM-256M-Instruct-GGUF/snapshots/b9e4379657e1450d04d02eec8e345667265b0a00/SmolVLM-256M-Instruct-Q8_0.gguf"

MMPROJ="$HOME/.cache/huggingface/hub/models--ggml-org--SmolVLM-256M-Instruct-GGUF/snapshots/b9e4379657e1450d04d02eec8e345667265b0a00/mmproj-SmolVLM-256M-Instruct-Q8_0.gguf"

IMAGE="/tmp/camera.jpg"

while true
do
    fswebcam -r 640x480 --no-banner "$IMAGE" >/dev/null 2>&1

    "$LLAMA" \
        -m "$MODEL" \
        --mmproj "$MMPROJ" \
        --image "$IMAGE" \
        -p "What is the person doing? Answer with one short sentence." \
        -n 20 \
        --temp 0.1 \
        -st 2>/dev/null |
        sed -n '/^> What is the person doing/,/^\[ Prompt:/p' |
        sed '1d;$d'

    sleep 3
done
