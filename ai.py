#!/usr/bin/env python3
import os
import subprocess
import time
import json
import urllib.request

# =================================================================
# 😈 THE ULTIMATE UNCENSORED AI - DESIGNED FOR 330GB RAM / 48 CORES
# =================================================================

# The most intelligent completely uncensored 70B model
MODEL_NAME = "dolphin-llama3:70b" 

def print_banner():
    print("\n" + "="*60)
    print(" 🚀 330GB RAM SERVER - UNCENSORED AI TERMINAL 🚀 ")
    print("="*60)
    print(f"[*] Model Selected: {MODEL_NAME}")
    print("[*] Behavior: 100% Uncensored. It will NEVER refuse a prompt.")
    print("="*60 + "\n")

def setup_env():
    # 1. Install Ollama if not present
    if not os.path.exists("/usr/local/bin/ollama"):
        print("[+] Installing AI Engine (Ollama)...")
        os.system("curl -fsSL https://ollama.com/install.sh | sh")
    else:
        print("[+] AI Engine already installed.")

    # 2. Start Ollama Server
    print("[+] Starting background AI server...")
    os.system("ollama serve > /dev/null 2>&1 &")
    time.sleep(3)

    # 3. Pull Model
    print(f"\n[+] Downloading {MODEL_NAME}...")
    print("    ⏳ (This is a 40GB+ model! It will take some time to download)")
    os.system(f"ollama pull {MODEL_NAME}")
    
def chat_loop():
    print("\n" + "="*60)
    print(" 😈 AI IS READY! TYPE 'exit' TO QUIT.")
    print("="*60)
    
    # Keep history for context
    history = []
    
    while True:
        try:
            user_input = input("\n👤 [YOU]: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("\n[+] Shutting down...")
                break
                
            history.append({"role": "user", "content": user_input})
            
            data = {
                "model": MODEL_NAME,
                "messages": history,
                "stream": True
            }
            
            req = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            print("🤖 [AI]: ", end="", flush=True)
            
            full_response = ""
            try:
                response = urllib.request.urlopen(req)
                for line in response:
                    if line:
                        chunk = json.loads(line)
                        msg_chunk = chunk.get("message", {}).get("content", "")
                        print(msg_chunk, end="", flush=True)
                        full_response += msg_chunk
                        if chunk.get("done"):
                            break
                print("\n")
                history.append({"role": "assistant", "content": full_response})
                
                # Keep history short to prevent lag
                if len(history) > 10:
                    history = history[-10:]
                    
            except Exception as e:
                print(f"\n[ERROR]: Failed to generate response -> {e}")
                
        except KeyboardInterrupt:
            print("\n[+] Exiting...")
            break

if __name__ == "__main__":
    print_banner()
    setup_env()
    chat_loop()
