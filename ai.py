#!/usr/bin/env python3
import os
import subprocess
import time
import json
import urllib.request
import urllib.error

# =================================================================
# 😈 THE ULTIMATE UNCENSORED AI - DESIGNED FOR 330GB RAM / 48 CORES
# =================================================================

MODEL_NAME = "dolphin-llama3:70b" 

def print_banner():
    print("\n" + "="*60)
    print(" 🚀 330GB RAM SERVER - UNCENSORED AI TERMINAL 🚀 ")
    print("="*60)
    print(f"[*] Model Selected: {MODEL_NAME}")
    print("[*] Behavior: 100% Uncensored. It will NEVER refuse a prompt.")
    print("="*60 + "\n")

def setup_env():
    # 0. Install required dependencies
    print("[+] 1/4 Checking and installing dependencies (zstd)...")
    os.system("apt-get update > /dev/null 2>&1")
    os.system("apt-get install -y zstd curl > /dev/null 2>&1")

    # 1. Install Ollama if not present
    print("[+] 2/4 Checking AI Engine (Ollama)...")
    if not os.path.exists("/usr/local/bin/ollama"):
        print("    --> Installing Ollama...")
        os.system("curl -fsSL https://ollama.com/install.sh | sh")
    else:
        print("    --> Ollama is already installed.")

    # 2. Start Ollama Server
    print("[+] 3/4 Starting background AI server...")
    os.system("pkill ollama > /dev/null 2>&1") # Kill any broken background instances
    time.sleep(1)
    os.system("cd / && OLLAMA_HOST=127.0.0.1:11434 ollama serve > /tmp/ollama.log 2>&1 &")
    
    # Wait for server to start
    server_ready = False
    for _ in range(15):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    server_ready = True
                    break
        except Exception:
            pass
        time.sleep(1)
        
    if not server_ready:
        print("[!] ERROR: Could not start Ollama server. Check /tmp/ollama.log")
        exit(1)
    
    print("    --> Server is LIVE!")

    # 3. Pull Model
    print(f"\n[+] 4/4 Downloading {MODEL_NAME}...")
    print("    ⏳ (This is a 40GB+ model! Wait for it to hit 100%)")
    # Using os.system so the user can see the progress bar directly in the terminal
    result = os.system(f"ollama pull {MODEL_NAME}")
    if result != 0:
        print("[!] ERROR: Failed to download the model. Are you out of disk space or internet disconnected?")
        exit(1)
    
def chat_loop():
    print("\n" + "="*60)
    print(" 😈 AI IS READY! TYPE 'exit' TO QUIT.")
    print("="*60)
    
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
                
                if len(history) > 10:
                    history = history[-10:]
                    
            except urllib.error.HTTPError as e:
                print(f"\n[ERROR]: HTTP Error {e.code} - {e.reason}")
                error_body = e.read().decode('utf-8')
                print(f"Details: {error_body}")
                history.pop() # Remove failed message
            except Exception as e:
                print(f"\n[ERROR]: Failed to generate response -> {e}")
                history.pop()
                
        except KeyboardInterrupt:
            print("\n[+] Exiting...")
            break

if __name__ == "__main__":
    print_banner()
    setup_env()
    chat_loop()
