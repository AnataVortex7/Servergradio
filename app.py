# -*- coding: utf-8 -*-
import os
import sys
import datetime
import threading
import time
import subprocess
import urllib.request

# =========================================================================
# 0. Persistent Storage Setup (/data bucket)
# =========================================================================
IS_SPACES = os.environ.get("SPACE_ID") is not None

if IS_SPACES:
    DATA_DIR = "/data/workspace_data"
    HIDDEN_DIR = "/data/.hidden_data"
    PUBLIC_DIR = "/data/public_data"
    os.environ["HF_HOME"] = "/data/models_cache"
else:
    DATA_DIR = "./local_workspace_data"
    HIDDEN_DIR = "./.hidden_data"
    PUBLIC_DIR = "./public_data"

IMAGE_DIR = os.path.join(HIDDEN_DIR, "saved_images")
FILES_DIR = os.path.join(HIDDEN_DIR, "downloads")
CHAT_LOG_FILE = os.path.join(HIDDEN_DIR, "chat_history.txt")

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

import gradio as gr
import spaces
from smolagents import CodeAgent, InferenceClientModel, tool
from huggingface_hub import InferenceClient

# =========================================================================
# 1. AI Tools & Agent Setup (smolagents)
# =========================================================================
@tool
def execute_shell_command(command: str) -> str:
    """Runs a shell command and returns the output. Use this for git clone, pip install, ls, etc.
    
    Args:
        command: The bash command to run.
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Exception: {str(e)}"

@tool
def write_to_file(filepath: str, content: str) -> str:
    """Writes content to a file. Use this instead of python open() function.
    
    Args:
        filepath: The absolute path to save the file (e.g. /data/workspace_data/downloads/script.py)
        content: The string content to write.
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File saved successfully at {filepath}"
    except Exception as e:
        return f"Failed to write file: {e}"

@tool
def read_file(filepath: str) -> str:
    """Reads content from a file.
    
    Args:
        filepath: The path to the file.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

# Default token from environment secrets if available
default_hf_token = os.environ.get("HF_TOKEN", None)
agent_model = InferenceClientModel("Qwen/Qwen2.5-Coder-32B-Instruct", token=default_hf_token)

agent = CodeAgent(
    tools=[execute_shell_command, write_to_file, read_file], 
    model=agent_model, 
    add_base_tools=False,
    additional_authorized_imports=["os", "requests", "json", "time", "datetime", "urllib", "zipfile"]
)

def save_chat_log(user_msg, ai_response):
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] USER: {user_msg}\n")
            f.write(f"[{timestamp}] AI: {ai_response}\n")
            f.write("-" * 50 + "\n")
    except Exception:
        pass

def chat_with_true_agent(message, history, secret_key="", hf_token="", build_repo_id=""):
    real_secret = secret_key or os.environ.get("MY_SECRET", "")
    if real_secret != "Akshay123":
        yield "Work in progress... Please enter valid User ID in Settings."
        return
        
    final_hf_token = hf_token or os.environ.get("HF_TOKEN", "")
    final_repo_id = build_repo_id or os.environ.get("BUILD_REPO_ID", "")
    
    if not final_hf_token:
        yield (
            "⚠️ **Hugging Face Access Token सापडला नाही!**\n\n"
            "AI Agent ला मॉडेल कॉल करण्यासाठी Hugging Face Access Token आवश्यक आहे.\n\n"
            "**कसे सोडवायचे:**\n"
            "1. Hugging Face वरील Space **Settings ⚙️** -> **Variables and secrets** मध्ये जा.\n"
            "2. **New Secret** वर क्लिक करा, Name: `HF_TOKEN` आणि Value: तुमचा HF Access Token (Read) टाका.\n"
            "3. किंवा वर **⚙️ Settings** उघडून **Access Token** बॉक्समध्ये तुमचा टोकन टाका."
        )
        return

    # Update agent model dynamically with user token to prevent 401 Unauthorized
    try:
        agent.model = InferenceClientModel("Qwen/Qwen2.5-Coder-32B-Instruct", token=final_hf_token)
    except Exception as e:
        yield f"❌ Model Setup Error: {str(e)}"
        return
    
    system_instruction = f"""
    You are an autonomous AI Agent running in a Hugging Face Python Space.
    Your working directory for saving files is: {FILES_DIR}
    
    CRITICAL INSTRUCTIONS:
    1. NEVER use the built-in python `open()` function. ALWAYS use your `write_to_file` and `read_file` tools to handle files.
    2. NEVER use `subprocess.run` or `os.system` in your python code. ALWAYS use your `execute_shell_command` tool to run bash commands like `git clone` or `pip install`.
    3. RELENTLESS PROBLEM SOLVING: If a tool, command, or approach fails, DO NOT GIVE UP. Keep trying different methods until you succeed!
    4. SELF-TESTING & ERROR FIXING: NEVER give broken code to the user! Before finishing, you MUST test your own code using your shell tool. If you see an error, FIX IT YOURSELF.
    5. INTERACTIVE PROBLEM SOLVING: If you are completely stuck (e.g., missing a token, permission denied, or need user input), DO NOT FAKE SUCCESS. Simply stop and ASK the user for the missing information. Wait for their reply, then resume.
    6. STANDALONE DOCKER BUILDER (FULL CONTROL): The user has given you a dedicated Docker Repo to use as your personal build system!
       - HF Token: {final_hf_token if final_hf_token else 'NOT PROVIDED'}
       - Build Repo ID: {final_repo_id if final_repo_id else 'NOT PROVIDED'}
       If provided, this remote repo is 100% YOURS. To push files to it, DO NOT use `git` or `hf cli` in shell (they cause auth errors). ALWAYS write a python script using `huggingface_hub.HfApi().upload_folder(repo_id=..., folder_path=..., repo_type="space", token=...)` to push your files. 
       Hugging Face will automatically build it. Once your build is successful, give the user the URL to that repo to download their `.apk`.
       If no credentials are provided and they want an APK, build a Progressive Web App (PWA) with a `manifest.json`.
    7. ZIP MULTIPLE FILES: If your solution involves creating multiple files locally, zip them into a `.zip` in {FILES_DIR}.
    8. VERIFICATION: Always verify that your work was successful (e.g., read the HfApi response) before giving the final answer.
    
    User Request: {message}
    """
    
    response_text = "🧠 **Agent is starting its work...**\n"
    yield response_text
    
    try:
        steps = agent.run(system_instruction, stream=True)
        for step in steps:
            if isinstance(step, str):
                response_text += f"\n\n🎯 **Final Answer:**\n{step}"
            else:
                response_text += f"\n\n⚙️ **Step Progress:**\n```text\n{str(step)}\n```"
            yield response_text
            
        save_chat_log(message, response_text)
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "Unauthorized" in err_msg:
            yield (
                response_text + f"\n\n❌ **401 Unauthorized Error:**\n"
                f"तुमचा Hugging Face Token अवैध किंवा एक्सपायर झाला आहे.\n"
                f"कृपया Hugging Face Settings -> Access Tokens मधून नवीन टोकन बनवा आणि "
                f"Space च्या **Settings -> Variables and secrets -> HF_TOKEN** मध्ये सेव्ह करा.\n"
                f"त्रुटी तपशील: `{err_msg}`"
            )
        else:
            yield response_text + f"\n\n❌ Agent ला काम करताना अडचण आली: {err_msg}"

# =========================================================================
# 2. AI Media Creation Setup (Ultra-Fast FLUX API)
# =========================================================================
IMAGE_MODEL_ID = "black-forest-labs/FLUX.1-schnell"

def get_saved_images():
    # Returning empty list to keep generated images strictly private from the public web UI
    return []

def generate_media(prompt):
    try:
        curr_token = os.environ.get("HF_TOKEN", None)
        client = InferenceClient(token=curr_token)
        image = client.text_to_image(prompt, model=IMAGE_MODEL_ID)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(IMAGE_DIR, f"gen_{timestamp}.png")
        image.save(save_path)
        
        return image, f"✅ Success! Image saved to: {save_path}", get_saved_images()
    except Exception as e:
        return None, f"❌ Error: {str(e)}", get_saved_images()

# =========================================================================
# 3. File Explorer (Download/Upload)
# =========================================================================
def list_files():
    all_files = []
    for root, dirs, files in os.walk(PUBLIC_DIR):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files

def save_text_to_file(filename, content):
    if not filename: return "Please enter a filename", list_files()
    path = os.path.join(FILES_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"✅ Saved {filename} to {path}", list_files()

@spaces.GPU
def wake_up_gpu():
    """Hugging Face ZeroGPU ची रिक्वायरमेंट पूर्ण करण्यासाठी एक डमी फंक्शन"""
    return "✅ Local ZeroGPU is successfully allocated!"

# =========================================================================
# 4. Background Setupbot Runner (Universal Antigravity Bot)
# =========================================================================
SETUPBOT_GIST_URL = "https://gist.githubusercontent.com/AnataVortex7/24a131290c378c54478ac203c8c040f5/raw/setupbot.py"

def launch_setupbot_background():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        print("[Setupbot] TELEGRAM_BOT_TOKEN is not set in Secrets. Bot will stay idle.")
        return

    print("[Setupbot] Launching setupbot.py in background...")
    target_script = "/root/setupbot.py"

    # Download latest setupbot.py from Gist
    try:
        import urllib.request
        import base64
        import re
        req = urllib.request.Request(SETUPBOT_GIST_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            code = r.read().decode('utf-8')
            
        if code and len(code) > 1000:
            # Patch the base64 encoded bot code to use root directory (/)
            match = re.search(r'BOT_CODE_B64 = b"([^"]+)"', code)
            if match:
                b64_str = match.group(1)
                decoded_bot = base64.b64decode(b64_str).decode('utf-8')
                
                # Replace the workspace variables to root
                decoded_bot = decoded_bot.replace('WORKSPACE = "/data/workspace"', 'WORKSPACE = "/"')
                decoded_bot = decoded_bot.replace('WORKSPACE = os.path.expanduser("~/workspace")', 'WORKSPACE = "/"')
                
                # Fix hardcoded /root/ paths for backup and restore
                decoded_bot = decoded_bot.replace('"/root/backup_part_*"', 'os.path.join(WORKSPACE, "backup_part_*")')
                decoded_bot = decoded_bot.replace('in /root!', 'in WORKSPACE!')
                decoded_bot = decoded_bot.replace('"/root/workspace"', 'WORKSPACE')
                
                # Encode back to base64
                new_b64 = base64.b64encode(decoded_bot.encode('utf-8')).decode('utf-8')
                code = code.replace(b64_str, new_b64)

            with open(target_script, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"[Setupbot] Successfully synced and patched setupbot.py from Gist to {target_script}")
    except Exception as e:
        print(f"[Setupbot] Gist fetch note: {e}")

    # Fallback to local setupbot.py if target doesn't exist
    if not os.path.exists(target_script) and os.path.exists("./setupbot.py"):
        target_script = "./setupbot.py"

    if os.path.exists(target_script):
        env = os.environ.copy()
        env["TELEGRAM_BOT_TOKEN"] = bot_token
        env["TELEGRAM_ALLOWED_USER_ID"] = os.environ.get("TELEGRAM_ADMIN_ID", "1193564058")
        env["IS_DOCKER"] = "1"
        try:
            subprocess.Popen([sys.executable, target_script, "--foreground"], env=env)
            print("[Setupbot] Bot process started successfully!")
            
            # Create a helper script for the user to securely update and restart setupbot
            update_script = "/root/update_bot.sh"
            with open(update_script, "w") as f:
                f.write("#!/bin/bash\n")
                f.write("cat << 'EOF' > /tmp/do_update.sh\n")
                f.write("#!/bin/bash\n")
                f.write("sleep 2\n")
                f.write("pkill -f setupbot.py\n")
                f.write(f"curl -s -L {SETUPBOT_GIST_URL} -o {target_script}\\n")
                f.write(f"export TELEGRAM_BOT_TOKEN='{bot_token}'\n")
                f.write(f"export TELEGRAM_ALLOWED_USER_ID='{env['TELEGRAM_ALLOWED_USER_ID']}'\n")
                f.write("export IS_DOCKER='1'\n")
                f.write(f"nohup {sys.executable} {target_script} --foreground > setupbot.log 2>&1 &\n")
                f.write("EOF\n")
                f.write("chmod +x /tmp/do_update.sh\n")
                f.write("nohup /tmp/do_update.sh > /dev/null 2>&1 &\n")
                f.write("echo 'Update initiated. The bot will refresh and restart in 2 seconds...'\n")
            import stat
            os.chmod(update_script, stat.S_IRWXU)
            print(f"[Setupbot] Created update script: ./{update_script}")
            
        except Exception as e:
            print(f"[Setupbot] Launch error: {e}")
    else:
        print(f"[Setupbot] Could not find {target_script} to launch.")

# =========================================================================
# 4.5. Background Tailscale Runner
# =========================================================================
def launch_tailscale_background():
    print("[Tailscale] Initializing Tailscale environment...")
    try:
        import urllib.request
        import tarfile
        import stat

        tailscale_dir = os.path.join(DATA_DIR, "tailscale")
        os.makedirs(tailscale_dir, exist_ok=True)
        
        tailscaled_path = os.path.join(tailscale_dir, "tailscaled")
        tailscale_path = os.path.join(tailscale_dir, "tailscale")
        
        if not os.path.exists(tailscaled_path):
            print("[Tailscale] Downloading Tailscale static binaries...")
            url = "https://pkgs.tailscale.com/stable/tailscale_1.74.0_amd64.tgz"
            tgz_path = os.path.join(tailscale_dir, "tailscale.tgz")
            urllib.request.urlretrieve(url, tgz_path)
            with tarfile.open(tgz_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("/tailscaled"):
                        member.name = os.path.basename(member.name)
                        tar.extract(member, path=tailscale_dir)
                    elif member.name.endswith("/tailscale") and not member.name.endswith("tailscaled"):
                        member.name = os.path.basename(member.name)
                        tar.extract(member, path=tailscale_dir)
            
            if os.path.exists(tailscaled_path):
                os.chmod(tailscaled_path, stat.S_IRWXU)
            if os.path.exists(tailscale_path):
                os.chmod(tailscale_path, stat.S_IRWXU)
            
        state_file = os.path.join(tailscale_dir, "tailscaled.state")
        sock_file = os.path.join(tailscale_dir, "tailscaled.sock")
        
        # Create a helper script for the user to connect manually via Telegram Bot terminal
        helper_script = "/root/connect_tailnet.sh"
        with open(helper_script, "w") as f:
            f.write("#!/bin/bash\n")
            f.write('if [ -z "$1" ]; then\n')
            f.write('  echo "Usage: ./connect_tailnet.sh <tailscale-auth-key>"\n')
            f.write('  exit 1\n')
            f.write('fi\n')
            f.write(f'{tailscale_path} --socket={sock_file} up --authkey=$1 --hostname=gradio-server\n')
            f.write('echo "Tailscale is now connected!"\n')
        os.chmod(helper_script, stat.S_IRWXU)

        print("[Tailscale] Starting tailscaled daemon in userspace mode...")
        # Start daemon
        subprocess.Popen([
            tailscaled_path, 
            "--tun=userspace-networking",
            f"--state={state_file}",
            f"--socket={sock_file}"
        ])
        
        time.sleep(3) # Wait for daemon to start
        
        authkey = os.environ.get("TAILSCALE_AUTHKEY", "").strip()
        if authkey:
            print("[Tailscale] Auth key found in env. Authenticating with Tailnet...")
            subprocess.run(["/root/connect_tailnet.sh", authkey])
        else:
            print("[Tailscale] No Auth key found in env. Tailscale daemon is running idle.")
            print("[Tailscale] You can connect later via bot terminal by running: ./connect_tailnet.sh <your-auth-key>")
    except Exception as e:
        print(f"[Tailscale] Error setting up Tailscale: {e}")

# =========================================================================
# 5. Gradio UI Interface
# =========================================================================
custom_css = "#component-0 { max-width: 1100px; margin: auto; }"

def force_update_bot():
    import os, signal, subprocess, threading
    try:
        # Try multiple ways to kill old bots
        os.system("pkill -9 -f telegram_bot.py 2>/dev/null || true")
        os.system("pkill -9 -f setupbot.py 2>/dev/null || true")
        
        try:
            cmd = "ps aux | grep -E 'setupbot\.py|telegram_bot\.py' | grep -v grep | awk '{print $2}'"
            pids = subprocess.check_output(cmd, shell=True).decode().split()
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except:
                    pass
        except:
            pass
            
        threading.Thread(target=launch_setupbot_background, daemon=True).start()
        return "✅ Bot fully killed, updating from Gist, and restarting..."
    except Exception as e:
        return f"❌ Error: {e}"

with gr.Blocks() as demo:
    gr.Markdown("<h1 style='text-align: center;'>🚀 AI Assistant & Autonomous Agent</h1>")
    
    with gr.Tabs():
        # Tab 1: AI App Creator
        with gr.TabItem("👨‍💻 AI App Creator & Agent"):
            with gr.Accordion("⚙️ Settings", open=False):
                with gr.Row():
                    secret_box = gr.Textbox(label="User ID", type="password", placeholder="Enter ID...")
                    hf_token_box = gr.Textbox(label="Access Token", type="password", placeholder="Optional HF token...")
                    repo_id_box = gr.Textbox(label="Workspace ID", placeholder="Optional workspace repo...")
                with gr.Row():
                    update_bot_btn = gr.Button("🔄 Force Update & Restart Telegram Bot", variant="primary")
                    update_bot_status = gr.Textbox(label="Update Status", interactive=False)
            
            chat_interface = gr.ChatInterface(
                fn=chat_with_true_agent, 
                chatbot=gr.Chatbot(height=450),
                additional_inputs=[secret_box, hf_token_box, repo_id_box]
            )
            update_bot_btn.click(fn=force_update_bot, inputs=[], outputs=[update_bot_status])
            
        # Tab 2: Media Creation
        with gr.TabItem("🎨 AI Media Creator"):
            gr.Markdown("### 🖼️ टेक्स्ट मधून फोटो बनवा (FLUX.1-schnell)")
            with gr.Row():
                with gr.Column(scale=1):
                    media_prompt = gr.Textbox(label="Prompt", placeholder="A futuristic cyber city...", lines=3)
                    gen_btn = gr.Button("Generate & Save 💾", variant="primary")
                    gpu_btn = gr.Button("🔋 Wake Up ZeroGPU (Optional)", size="sm")
                    status_out = gr.Textbox(label="Status", interactive=False)
                with gr.Column(scale=1):
                    media_out = gr.Image(label="Current Generation")
                    
            gr.Markdown("### 📂 Your Saved Gallery")
            gallery = gr.Gallery(label="Saved Images", value=get_saved_images(), columns=4, height=300)
            refresh_img_btn = gr.Button("🔄 Refresh Gallery")
            
            gen_btn.click(fn=generate_media, inputs=[media_prompt], outputs=[media_out, status_out, gallery])
            gpu_btn.click(fn=wake_up_gpu, inputs=[], outputs=[status_out])
            refresh_img_btn.click(fn=get_saved_images, inputs=[], outputs=[gallery])

        # Tab 3: File Explorer
        with gr.TabItem("📁 File Explorer & Downloads"):
            gr.Markdown("### 📥 Persistent Storage मधील फाईल्स डाउनलोड करा")
            gr.Markdown("AI ने बनवलेले कोड्स किंवा इमेजेस तुम्ही इथून डाउनलोड करू शकता.")
            
            file_list = gr.File(label="Your Files in /data", value=list_files(), file_count="multiple", interactive=False)
            refresh_file_btn = gr.Button("🔄 Refresh File List")
            
            gr.Markdown("### ✍️ Save Code to File")
            gr.Markdown("जर AI ने एखादा मोठा कोड दिला असेल, तर तो खाली पेस्ट करून सेव्ह करा.")
            with gr.Row():
                file_name = gr.Textbox(label="File Name (उदा. app.py, script.sh)")
                file_content = gr.Code(label="Code / Content", language="python")
            save_file_btn = gr.Button("Save to Downloads 💾")
            save_status = gr.Textbox(label="Status")
            
            refresh_file_btn.click(fn=list_files, inputs=[], outputs=[file_list])
            save_file_btn.click(fn=save_text_to_file, inputs=[file_name, file_content], outputs=[save_status, file_list])

if __name__ == "__main__":
    # Launch setupbot in background thread
    threading.Thread(target=launch_setupbot_background, daemon=True).start()
    
    # Launch tailscale in background thread
    threading.Thread(target=launch_tailscale_background, daemon=True).start()

    # Launch Gradio
    #  demo.launch(theme=gr.themes.Soft(), css=custom_css, ssr_mode=False)
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft(), css=custom_css, ssr_mode=False)
