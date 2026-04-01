import locale
import socket
from fastapi import FastAPI, Query, Body, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import json
import uvicorn
import os
import shutil
from queue import Queue, Empty
import serial
import serial.tools.list_ports
import threading
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import webbrowser
from dotenv import load_dotenv, set_key
load_dotenv()

from src.player import Player
from src.joystick import JoystickController
from src.llm_client import LLMClient
from src.comfyui import ComfyUIClient

version_info = "OSRChat v1.4.1"
PORT = 12333
app = FastAPI(title="OSRChat", version="1.4.1")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
public_dir = os.path.join(BASE_DIR, "public")
static_dirs = ["html", "css", "js", "img", "i18n", "json", "docs"]
for dir_name in static_dirs:
    app.mount(f"/{dir_name}", StaticFiles(directory=os.path.join(public_dir, dir_name)), name=dir_name)

player = Player()
player.udp_url = os.getenv("UDP_URL", None)
player.serial_device = os.getenv("SERIAL_DEVICE", None)
player.current_mode = os.getenv("CURRENT_MODE", "serial")  # serial | udp
player.offset_value = int(os.getenv("OFFSET", 0))

joystick_controller = JoystickController()
joystick_controller.current_mode = os.getenv("CURRENT_MODE", "serial")
joystick_controller.serial_device = os.getenv("SERIAL_DEVICE", None)

llm_client = LLMClient(
    base_url = os.getenv("BASE_URL", ""),
    api_key = os.getenv("API_KEY", ""),
    model = os.getenv("MODEL", "")
)

comfyui_client = ComfyUIClient(
    os.getenv("COMFYUI_URL", ""),
    os.getenv("COMFYUI_TYPE", ""),
    os.getenv("COMFYUI_diffusion", ""),
    os.getenv("COMFYUI_CLIP", ""),
    os.getenv("COMFYUI_VAE", ""),
)

@app.get("/")
async def read_index():
    """Main route"""
    index_path = os.path.join(public_dir, "html", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
@app.get("/settings")
async def read_settings():
    """Settings page"""
    index_path = os.path.join(public_dir, "html", "settings.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
@app.get("/api/version")
async def get_version():
    """Get version information"""
    return {"version": version_info}

def get_host_ip_address():
    """Get the current host's IP address"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    return ip

@app.get("/api/host/ip")
async def get_host_ip():
    """Get the current host's IP address"""
    ip = get_host_ip_address()
    return {"ip": ip}

@app.get("/api/devices/serial")
async def list_serial_ports():
    """Get serial port list"""
    ports = serial.tools.list_ports.comports()
    usb_ports = []
    for port in ports:
        port_info = {
            "device": port.device,
            "description": port.description,
            "hwid": port.hwid,
            "is_usb": "USB" in port.hwid or "USB" in port.description
        }
        usb_ports.append(port_info)
    return {"serial_ports": usb_ports}

@app.post("/api/config")
async def set_config(
    u: str = None,
    s: str = None,
    m: str = None
):
    """Global configuration"""
    if u is not None:
        player.udp_url = u
        set_key(".env", "UDP_URL", u)
    if s is not None:
        player.serial_device = s
        set_key(".env", "SERIAL_DEVICE", s)
    if m is not None and m in ["udp", "serial"]:
        player.current_mode = m
        set_key(".env", "CURRENT_MODE", m)
    return {
        "message": "Configuration updated successfully",
        "udp_url": player.udp_url,
        "serial_device": player.serial_device,
        "mode": player.current_mode
    }

@app.get("/api/config")
async def get_config():
    return {
        "udp_url": player.udp_url,
        "serial_device": player.serial_device,
        "mode": player.current_mode,
        "offset": player.offset_value
    }

@app.post("/api/config/llm")
async def set_llm_config(
    base_url: str = Body(""),
    api_key: str = Body(""),
    model: str = Body("")
):
    """Configure LLM client"""
    if base_url and base_url != llm_client.base_url:
        set_key(".env", "BASE_URL", base_url)
    if api_key != llm_client.api_key or api_key == "":
        set_key(".env", "API_KEY", api_key)
    llm_client.new(base_url, api_key)
    if model != llm_client.model:
        llm_client.model = model
        set_key(".env", "MODEL", model)
    return {
        "message": "LLM configuration updated successfully",
        "base_url": llm_client.base_url,
        "api_key": llm_client.api_key,
        "model": llm_client.model
    }

@app.get("/api/config/llm")
async def get_llm_config():
    """Get LLM configuration"""
    return {
        "base_url": llm_client.base_url,
        "api_key": llm_client.api_key,
        "model": llm_client.model
    }

@app.post("/api/config/comfyui")
async def set_comfyui_config(
    url: str = Body(""),
    type_: str = Body("", alias="type"),
    diffusion: str = Body(""),
    clip: str = Body(""),
    vae: str = Body("")
):
    """Configure ComfyUI client"""
    global comfyui_client
    if url != os.getenv("COMFYUI_URL"):
        set_key(".env", "COMFYUI_URL", url)
    if type_ != os.getenv("COMFYUI_TYPE"):
        set_key(".env", "COMFYUI_TYPE", type_)
    if diffusion != os.getenv("COMFYUI_diffusion"):
        set_key(".env", "COMFYUI_diffusion", diffusion)
    if clip != os.getenv("COMFYUI_CLIP"):
        set_key(".env", "COMFYUI_CLIP", clip)
    if vae != os.getenv("COMFYUI_VAE"):
        set_key(".env", "COMFYUI_VAE", vae)
    load_dotenv(override=True)
    comfyui_client = ComfyUIClient(
        os.getenv("COMFYUI_URL", ""),
        os.getenv("COMFYUI_TYPE", ""),
        os.getenv("COMFYUI_diffusion", ""),
        os.getenv("COMFYUI_CLIP", ""),
        os.getenv("COMFYUI_VAE", ""),
    )
    return {
        "message": "ComfyUI configuration updated successfully",
        "url": comfyui_client.base_url,
        "type": comfyui_client.type,
        "diffusion": comfyui_client.diffusion,
        "clip": comfyui_client.clip,
        "vae": comfyui_client.vae,
    }

@app.get("/api/config/comfyui")
async def get_comfyui_config():
    """Get current ComfyUI configuration"""
    return {
        "url": os.getenv("COMFYUI_URL", ""),
        "type": os.getenv("COMFYUI_TYPE", ""),
        "diffusion": os.getenv("COMFYUI_diffusion", ""),
        "clip": os.getenv("COMFYUI_CLIP", ""),
        "vae": os.getenv("COMFYUI_VAE", ""),
    }

def load_cards():
    cards_path = os.path.join(public_dir, "json", "prompts", "cards.json")
    if os.path.exists(cards_path):
        with open(cards_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        os.makedirs(os.path.dirname(cards_path), exist_ok=True)
        with open(cards_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    return {}

def save_cards(cards):
    cards_path = os.path.join(public_dir, "json", "prompts", "cards.json")
    with open(cards_path, 'w', encoding='utf-8') as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

@app.post("/api/cards")
async def create_card(
    name: str = Body(...),
    prompt: str = Body(""),
    content: str = Body("")
):
    """Create a new card"""
    cards = load_cards()
    if name in cards:
        raise HTTPException(status_code=400, detail="card already exists")
    card = {"system_prompt": prompt}
    if content:
        card["context"] = [{"role": "assistant", "content": content}]
    cards[name] = card
    save_cards(cards)
    return {"message": "card created successfully"}

@app.put("/api/cards/{name}")
async def update_card(
    name: str,
    prompt: str = Body(""),
    content: str = Body("")
):
    """Update an existing card"""
    cards = load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    card = {"system_prompt": prompt}
    if content:
        card["context"] = [{"role": "assistant", "content": content}]
    else:
        card.pop("context", None)
    cards[name] = card
    save_cards(cards)
    return {"message": "card updated successfully"}

@app.delete("/api/cards/{name}")
async def delete_card(name: str):
    """Delete a card"""
    cards = load_cards()
    if name not in cards:
        raise HTTPException(status_code=404, detail="card not found")
    del cards[name]
    save_cards(cards)
    return {"message": "card deleted successfully"}

@app.post("/api/script")
async def load(script_data: dict):
    """Load script"""
    joystick_controller.stop_joystick()
    player.stop()
    result = player.load_script(script_data)
    return result

@app.get("/api/script/play")
async def play(at: int = Query(0, description="Start time, unit: milliseconds")):
    joystick_controller.stop_joystick()
    result = player.play(at)
    return result

@app.get("/api/script/stop")
async def stop():
    """Stop playback"""
    result = player.stop()
    return result

@app.post("/api/script/custom")
async def custom_play(
    range: int = Body(100),
    inverted: bool = Body(False),
    max_pos: int = Body(100),
    min_pos: int = Body(0),
    freq: float = Body(1.0),
    decline_ratio: float = Body(0.5),
    start_pos: int = Body(None),
    loop_count: int = Body(100),
    custom_actions: list = Body(None)
):
    """Custom playback"""
    try:
        player.custom_play(
            range=range,
            inverted=inverted,
            max_pos=max_pos,
            min_pos=min_pos,
            freq=freq,
            decline_ratio=decline_ratio,
            start_pos=start_pos,
            loop_count=loop_count,
            custom_actions=custom_actions
        )
        return {"message": "Custom play started successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})

@app.get("/api/offset")
async def adjust_offset(ms: int = Query(..., description="Offset adjustment value, unit: milliseconds")):
    """Adjust global offset"""
    global player
    old_offset = player.offset_value
    player.offset_value += int(ms)
    set_key(".env", "OFFSET", str(player.offset_value))
    return {
        "message": "Offset adjusted successfully",
        "old_offset": old_offset,
        "new_offset": player.offset_value,
        "adjustment": ms
    }

@app.post("/api/devices/joystick/start")
async def start_joystick():
    """Start joystick control"""
    player.stop()
    result = joystick_controller.start_joystick()
    return result

@app.post("/api/devices/joystick/stop")
async def stop_joystick():
    """Stop joystick control"""
    result = joystick_controller.stop_joystick()
    return result

@app.get("/api/devices/joystick")
async def joystick_status():
    """Get joystick control status"""
    result = joystick_controller.joystick_status()
    return result

@app.get("/api/llm/test")
async def test_llm_connection():
    """Test connection"""
    success = llm_client.test_connection()
    if not success:
        raise HTTPException(status_code=500, detail={"error": "Failed to connect to LLM"})
    return {"success": success}

@app.get("/api/llm/model")
async def get_llm_models():
    """Get model list"""
    models = llm_client.get_model_list()
    return {"models": models}

@app.post("/api/llm/chat")
async def chat_with_llm(
    request: Request,
    user_message: str = Body(...),
    model: str = Body(None),
    image_base64: str = Body(None),
    system_prompt: str = Body(""),
    context_messages: list = Body(None),
    temperature: float = Body(0.7),
    num_predict: int = Body(8000)
):
    """Chat with interruptible streaming"""
    async def generate_stream():
        token_queue = Queue()
        stop_event = threading.Event()

        def background_chat():
            try:
                gen = llm_client.chat(
                    user_message=user_message,
                    model=model,
                    image_base64=image_base64,
                    system_prompt=system_prompt,
                    context_messages=context_messages,
                    temperature=temperature,
                    num_predict=num_predict,
                    stop_event=stop_event
                )
                for token in gen:
                    if stop_event.is_set():
                        break
                    token_queue.put(("token", token))
                token_queue.put(("done", None))
            except Exception as e:
                if not stop_event.is_set():
                    token_queue.put(("error", str(e)))

        thread = threading.Thread(target=background_chat, daemon=True)
        thread.start()

        try:
            while True:
                if await request.is_disconnected():
                    stop_event.set()
                    break

                try:
                    item_type, value = token_queue.get(timeout=0.1)
                    if item_type == "token":
                        yield f"data: {json.dumps({'token': value})}\n\n"
                    elif item_type == "error":
                        if not await request.is_disconnected():
                            yield f"data: {json.dumps({'token': '__ERROR__ Internal stream error: ' + value})}\n\n"
                        break
                    elif item_type == "done":
                        break
                except Empty:
                    continue
        finally:
            stop_event.set()

    return StreamingResponse(generate_stream(), media_type="text/event-stream")

@app.post("/api/t2i")
async def text_to_image(prompt: str = Body(..., embed=True)):
    """Generate image from text prompt using ComfyUI"""
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    image_path = await comfyui_client.run_t2i(prompt=prompt.strip())
    if not image_path:
        raise HTTPException(status_code=500, detail="Failed to generate image via ComfyUI")
    return {"image_url": image_path}

@app.delete("/api/t2i/cache")
async def clear_t2i_cache():
    """Delete all files in the ComfyUI image output directory"""
    comfyui_img_dir = os.path.join(public_dir, "img", "comfyui")
    if not os.path.exists(comfyui_img_dir):
        return {"message": "Cache directory does not exist", "deleted_count": 0}
    deleted_count = 0
    for filename in os.listdir(comfyui_img_dir):
        file_path = os.path.join(comfyui_img_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                deleted_count += 1
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                deleted_count += 1
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete {file_path}: {str(e)}")
    return {
        "message": "ComfyUI image cache cleared successfully",
        "deleted_count": deleted_count
    }

def create_image():
    """Create tray icon from public/img/logo.png"""
    logo_path = os.path.join(public_dir, "img", "logo.png")
    try:
        image = Image.open(logo_path).convert("RGBA")
        image = image.resize((256, 256), Image.LANCZOS)
        return image
    except Exception as e:
        width, height = 64, 64
        image = Image.new('RGBA', (width, height))
        dc = ImageDraw.Draw(image)
        dc.ellipse((0, 0, width - 1, height - 1), fill=None, outline="green", width=2)
        mask = Image.new('L', (width, height), 0)
        dc_mask = ImageDraw.Draw(mask)
        dc_mask.ellipse((0, 0, width - 1, height - 1), fill=255)
        image.putalpha(mask)
        return image

def on_exit(icon, item):
    """Exit callback, close tray and terminate program"""
    icon.stop()
    os._exit(0)

def get_system_language():
    for v in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        val = os.environ.get(v)
        if val:
            return val.split('.')[0].split('_')[0].lower().strip()
    try:
        lang, _ = locale.getdefaultlocale()
        if lang:
            return lang.split('_')[0].lower()
    except:
        pass
    return 'en'

def run_tray_icon():
    """Run tray icon in a separate thread"""
    def open_chat(icon, item):
        webbrowser.open(f"http://127.0.0.1:{PORT}/")

    def open_settings(icon, item):
        webbrowser.open(f"http://127.0.0.1:{PORT}/settings")

    def open_prompts(icon, item):
        os.startfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "public", "json", "prompts"))

    def open_github(icon, item):
        webbrowser.open("https://github.com/Karasukaigan/OSRChat")

    translations = {
        "Chat": "聊天",
        "Settings": "设置",
        "Prompts": "提示词",
        "Exit": "退出"
    }

    def tr(text):
        if get_system_language() == "zh":
            return translations.get(text, text)
        else:
            return text

    icon = Icon(
        name="OSRChat",
        icon=create_image(),
        title="OSRChat",
        menu=Menu(
            MenuItem(tr("Chat"), open_chat),
            MenuItem(tr("Settings"), open_settings),
            MenuItem(tr("Prompts"), open_prompts),
            MenuItem("GitHub", open_github),
            Menu.SEPARATOR,
            MenuItem(tr("Exit"), on_exit)
        )
    )
    icon.run()

if __name__ == "__main__":
    # Start tray icon
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()

    # Open settings page
    def open_browser():
        webbrowser.open(f"http://127.0.0.1:{PORT}/settings")
    threading.Timer(1.0, open_browser).start()

    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=PORT, use_colors=False)