# === AUTO-INSTALL REQUIREMENTS ===
import subprocess
import sys

def install_requirements():
    """Automatically install required packages"""
    required = ["websockets", "pillow", "opencv-python"]
    
    print("Checking requirements...")
    
    for package in required:
        try:
            # Try importing the package
            if package == "pillow":
                __import__("PIL")
            elif package == "opencv-python":
                __import__("cv2")
            else:
                __import__(package)
            print(f"  ✓ {package} installed")
        except ImportError:
            print(f"  ✗ {package} not found, installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"  ✓ {package} installed")
    
    print("All requirements ready!\n")

# Run installation check
install_requirements()

# === IMPORTS ===
import asyncio
import websockets
import json
from PIL import Image
import os
import cv2
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import queue
from datetime import datetime

# === MAIN APP ===
class StreamerGUI:
    def __init__(self):
        # Create main window
        self.root = tk.Tk()
        self.root.title("BABFT Block Art Streamer")
        self.root.geometry("600x600")
        
        # Streaming state
        self.streaming = False
        self.current_mode = None
        self.current_settings = None
        
        # Stores last frame pixels to detect changes
        self.last_frame = None
        
        # Thread-safe message queue for GUI updates
        self.message_queue = queue.Queue()
        
        # Build UI and start server
        self.setup_ui()
        self.start_server()
        self.process_messages()
        
    def setup_ui(self):
        # Title
        tk.Label(self.root, text="BABFT Block Art Streamer", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Status indicators
        status_frame = tk.Frame(self.root)
        status_frame.pack()
        
        tk.Label(status_frame, text="Server:").pack(side=tk.LEFT)
        self.server_status = tk.Label(status_frame, text="Starting...", fg="orange")
        self.server_status.pack(side=tk.LEFT, padx=5)
        
        tk.Label(status_frame, text="Client:").pack(side=tk.LEFT, padx=(20,0))
        self.client_status = tk.Label(status_frame, text="Not connected", fg="red")
        self.client_status.pack(side=tk.LEFT, padx=5)
        
        # Tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.setup_image_tab(notebook)
        self.setup_video_tab(notebook)
        self.setup_webcam_tab(notebook)
        self.setup_ipwebcam_tab(notebook)
        
        # Console
        console_frame = ttk.LabelFrame(self.root, text="Console")
        console_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.console = tk.Text(console_frame, height=6, bg="black", fg="lime")
        self.console.pack(fill="both", expand=True)
        
        # Stats
        self.stats_label = tk.Label(self.root, text="No active stream")
        self.stats_label.pack(pady=5)
        
        # Stop button (hidden by default)
        self.stop_button = tk.Button(self.root, text="Stop Stream", command=self.stop_stream, bg="red", fg="white")
        
    def setup_image_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Image")
        
        frame = ttk.LabelFrame(tab, text="Settings")
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Image path
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="Image:", width=10).pack(side=tk.LEFT)
        self.image_path = tk.StringVar()
        tk.Entry(row, textvariable=self.image_path, width=30).pack(side=tk.LEFT, padx=5)
        tk.Button(row, text="Browse", command=self.browse_image).pack(side=tk.LEFT)
        
        # Grid size
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="Width:", width=10).pack(side=tk.LEFT)
        self.img_width = tk.IntVar(value=16)
        tk.Spinbox(row, from_=8, to=128, textvariable=self.img_width, width=8).pack(side=tk.LEFT)
        tk.Label(row, text="Height:").pack(side=tk.LEFT, padx=(20,0))
        self.img_height = tk.IntVar(value=16)
        tk.Spinbox(row, from_=8, to=128, textvariable=self.img_height, width=8).pack(side=tk.LEFT)
        
        tk.Button(frame, text="Load Image", command=self.stream_image, bg="green", fg="white", font=("Arial", 12)).pack(pady=20)
        
    def setup_video_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Video")
        
        frame = ttk.LabelFrame(tab, text="Settings")
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Video path
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="Video:", width=10).pack(side=tk.LEFT)
        self.video_path = tk.StringVar()
        tk.Entry(row, textvariable=self.video_path, width=30).pack(side=tk.LEFT, padx=5)
        tk.Button(row, text="Browse", command=self.browse_video).pack(side=tk.LEFT)
        
        # Grid size
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="Width:", width=10).pack(side=tk.LEFT)
        self.vid_width = tk.IntVar(value=16)
        tk.Spinbox(row, from_=8, to=128, textvariable=self.vid_width, width=8).pack(side=tk.LEFT)
        tk.Label(row, text="Height:").pack(side=tk.LEFT, padx=(20,0))
        self.vid_height = tk.IntVar(value=16)
        tk.Spinbox(row, from_=8, to=128, textvariable=self.vid_height, width=8).pack(side=tk.LEFT)
        
        # FPS
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="FPS:", width=10).pack(side=tk.LEFT)
        self.vid_fps = tk.IntVar(value=10)
        tk.Spinbox(row, from_=1, to=60, textvariable=self.vid_fps, width=8).pack(side=tk.LEFT)
        self.vid_original_fps = tk.BooleanVar(value=False)
        tk.Checkbutton(row, text="Use Original FPS", variable=self.vid_original_fps).pack(side=tk.LEFT, padx=20)
        
        tk.Button(frame, text="Start Video", command=self.stream_video, bg="green", fg="white", font=("Arial", 12)).pack(pady=20)
        
    def setup_webcam_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Webcam")
        
        frame = ttk.LabelFrame(tab, text="Settings")
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Camera index
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="Camera:", width=10).pack(side=tk.LEFT)
        self.cam_index = tk.IntVar(value=0)
        tk.Spinbox(row, from_=0, to=10, textvariable=self.cam_index, width=8).pack(side=tk.LEFT)
        tk.Button(row, text="Test", command=self.test_camera).pack(side=tk.LEFT, padx=20)
        
        # Grid size
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="Width:", width=10).pack(side=tk.LEFT)
        self.cam_width = tk.IntVar(value=16)
        tk.Spinbox(row, from_=8, to=128, textvariable=self.cam_width, width=8).pack(side=tk.LEFT)
        tk.Label(row, text="Height:").pack(side=tk.LEFT, padx=(20,0))
        self.cam_height = tk.IntVar(value=16)
        tk.Spinbox(row, from_=8, to=128, textvariable=self.cam_height, width=8).pack(side=tk.LEFT)
        
        # FPS
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="FPS:", width=10).pack(side=tk.LEFT)
        self.cam_fps = tk.IntVar(value=15)
        tk.Spinbox(row, from_=1, to=60, textvariable=self.cam_fps, width=8).pack(side=tk.LEFT)
        
        tk.Button(frame, text="Start Webcam", command=self.stream_webcam, bg="green", fg="white", font=("Arial", 12)).pack(pady=20)
        
    def setup_ipwebcam_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="IP Webcam")
        
        frame = ttk.LabelFrame(tab, text="Settings")
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Instructions
        tk.Label(frame, text="1. Install 'IP Webcam' on phone\n2. Start server\n3. Enter URL", justify=tk.LEFT, fg="blue").pack(pady=5)
        
        # URL
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="URL:", width=10).pack(side=tk.LEFT)
        self.ip_url = tk.StringVar(value="http://192.168.1.100:8080")
        tk.Entry(row, textvariable=self.ip_url, width=25).pack(side=tk.LEFT, padx=5)
        tk.Button(row, text="Test", command=self.test_ip_webcam).pack(side=tk.LEFT)
        
        # Grid size
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="Width:", width=10).pack(side=tk.LEFT)
        self.ip_width = tk.IntVar(value=16)
        tk.Spinbox(row, from_=8, to=128, textvariable=self.ip_width, width=8).pack(side=tk.LEFT)
        tk.Label(row, text="Height:").pack(side=tk.LEFT, padx=(20,0))
        self.ip_height = tk.IntVar(value=16)
        tk.Spinbox(row, from_=8, to=128, textvariable=self.ip_height, width=8).pack(side=tk.LEFT)
        
        # FPS
        row = tk.Frame(frame)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text="FPS:", width=10).pack(side=tk.LEFT)
        self.ip_fps = tk.IntVar(value=15)
        tk.Spinbox(row, from_=1, to=60, textvariable=self.ip_fps, width=8).pack(side=tk.LEFT)
        
        tk.Button(frame, text="Start IP Webcam", command=self.stream_ipwebcam, bg="green", fg="white", font=("Arial", 12)).pack(pady=20)

    # === UTILITIES ===
        
    def log(self, msg):
        self.console.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.console.see(tk.END)
        
    def browse_image(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if f: self.image_path.set(f)
            
    def browse_video(self):
        f = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv")])
        if f: self.video_path.set(f)
            
    def test_camera(self):
        cap = cv2.VideoCapture(self.cam_index.get())
        if cap.isOpened() and cap.read()[0]:
            messagebox.showinfo("Success", "Camera works!")
        else:
            messagebox.showerror("Error", "Can't open camera")
        cap.release()
            
    def test_ip_webcam(self):
        cap = cv2.VideoCapture(self.ip_url.get() + "/video")
        if cap.isOpened() and cap.read()[0]:
            messagebox.showinfo("Success", "Connected!")
        else:
            messagebox.showerror("Error", "Can't connect")
        cap.release()
            
    def reset_frame_cache(self):
        self.last_frame = None
        
    def get_changed_pixels(self, grid, width, height):
        """Compare with last frame, return only changed pixels"""
        changes = []
        
        if self.last_frame is None:
            # First frame - send all pixels
            self.last_frame = {}
            for y in range(height):
                for x in range(width):
                    c = grid[y][x]
                    self.last_frame[(x, y)] = c
                    changes.append({"x": x, "y": y, "r": c[0], "g": c[1], "b": c[2]})
        else:
            # Only send changed pixels
            for y in range(height):
                for x in range(width):
                    c = grid[y][x]
                    if c != self.last_frame.get((x, y)):
                        changes.append({"x": x, "y": y, "r": c[0], "g": c[1], "b": c[2]})
                        self.last_frame[(x, y)] = c
        
        return changes

    # === STREAM SETUP ===
        
    def stream_image(self):
        if not self.image_path.get():
            messagebox.showerror("Error", "Select an image")
            return
        self.reset_frame_cache()
        self.current_mode = "image"
        self.current_settings = {"path": self.image_path.get(), "width": self.img_width.get(), "height": self.img_height.get()}
        self.log("Ready - run Roblox script")
        self.stop_button.pack_forget()
        
    def stream_video(self):
        if not self.video_path.get():
            messagebox.showerror("Error", "Select a video")
            return
        self.reset_frame_cache()
        self.current_mode = "video"
        self.current_settings = {"path": self.video_path.get(), "width": self.vid_width.get(), "height": self.vid_height.get(), "fps": self.vid_fps.get(), "use_original": self.vid_original_fps.get()}
        self.log("Ready - run Roblox script")
        self.stop_button.pack(pady=5)
        
    def stream_webcam(self):
        self.reset_frame_cache()
        self.current_mode = "webcam"
        self.current_settings = {"index": self.cam_index.get(), "width": self.cam_width.get(), "height": self.cam_height.get(), "fps": self.cam_fps.get()}
        self.log("Ready - run Roblox script")
        self.stop_button.pack(pady=5)
        
    def stream_ipwebcam(self):
        self.reset_frame_cache()
        self.current_mode = "ipwebcam"
        self.current_settings = {"url": self.ip_url.get() + "/video", "width": self.ip_width.get(), "height": self.ip_height.get(), "fps": self.ip_fps.get()}
        self.log("Ready - run Roblox script")
        self.stop_button.pack(pady=5)
        
    def stop_stream(self):
        self.streaming = False
        self.reset_frame_cache()
        self.log("Stopped")
        self.stop_button.pack_forget()

    # === SERVER ===
        
    def start_server(self):
        threading.Thread(target=self.run_server, daemon=True).start()
        
    def run_server(self):
        asyncio.new_event_loop().run_until_complete(self.websocket_server())
        
    async def websocket_server(self):
        self.message_queue.put(("server_started", None))
        async with websockets.serve(self.handle_client, "0.0.0.0", 8765):
            await asyncio.Future()
            
    async def handle_client(self, ws):
        self.message_queue.put(("client_connected", None))
        
        try:
            if not self.current_mode:
                await ws.send(json.dumps({"type": "error", "error": "Click a button first!"}))
                return
            
            self.streaming = True
            s = self.current_settings
            
            # Send config
            await ws.send(json.dumps({"type": "config", "mode": self.current_mode, "width": s["width"], "height": s["height"], "fps": s.get("fps")}))
            
            # Handle based on mode
            if self.current_mode == "image":
                await self.send_image(ws, s)
            else:
                await self.send_stream(ws, s)
                
        except websockets.exceptions.ConnectionClosed:
            self.message_queue.put(("client_disconnected", None))
        finally:
            self.streaming = False
            
    async def send_image(self, ws, s):
        """Load and send image"""
        w, h = s["width"], s["height"]
        
        # Load and resize image
        img = Image.open(s["path"]).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
        
        # Convert to grid
        grid = []
        for y in range(h):
            row = []
            for x in range(w):
                r, g, b = img.getpixel((x, y))
                row.append([round(r/255, 2), round(g/255, 2), round(b/255, 2)])
            grid.append(row)
        
        # Send changes
        changes = self.get_changed_pixels(grid, w, h)
        await ws.send(json.dumps({"type": "frame", "changes": changes}))
        await ws.send(json.dumps({"type": "end", "total_frames": 1}))
        
        self.message_queue.put(("log", f"Sent {len(changes)} pixels"))
            
    async def send_stream(self, ws, s):
        """Stream video/webcam/ipwebcam"""
        w, h = s["width"], s["height"]
        fps = s.get("fps", 15)
        
        # Open video source
        if self.current_mode == "video":
            cap = cv2.VideoCapture(s["path"])
            orig_fps = cap.get(cv2.CAP_PROP_FPS)
            if s.get("use_original"): fps = orig_fps
            skip = max(1, int(orig_fps / fps))
        else:
            cap = cv2.VideoCapture(s.get("index", s.get("url")))
            skip = 1
        
        if not cap.isOpened():
            await ws.send(json.dumps({"type": "error", "error": "Can't open source"}))
            return
        
        await ws.send(json.dumps({"type": "start"}))
        
        frame_num = 0
        read_num = 0
        delay = 1.0 / fps
        
        while self.streaming:
            ret, frame = cap.read()
            if not ret:
                if self.current_mode == "video": break
                continue
            
            read_num += 1
            if read_num % skip != 0: continue
            
            # Convert BGR to RGB and resize
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (w, h))
            
            # Build grid
            grid = []
            for y in range(h):
                row = []
                for x in range(w):
                    r, g, b = frame[y, x]
                    row.append([round(r/255, 2), round(g/255, 2), round(b/255, 2)])
                grid.append(row)
            
            # Send only changes
            changes = self.get_changed_pixels(grid, w, h)
            if changes:
                await ws.send(json.dumps({"type": "frame", "changes": changes}))
            
            frame_num += 1
            if frame_num % 30 == 0:
                self.message_queue.put(("stats", f"Frame {frame_num}: {len(changes)} changes"))
            
            await asyncio.sleep(delay)
        
        cap.release()
        await ws.send(json.dumps({"type": "end", "total_frames": frame_num}))
        self.message_queue.put(("log", f"Done: {frame_num} frames"))

    # === MESSAGE LOOP ===
            
    def process_messages(self):
        try:
            while not self.message_queue.empty():
                t, d = self.message_queue.get_nowait()
                if t == "server_started":
                    self.server_status.config(text="Running", fg="green")
                    self.log("Server ready (ws://localhost:8765)")
                elif t == "client_connected":
                    self.client_status.config(text="Connected", fg="green")
                    self.log("Client connected")
                elif t == "client_disconnected":
                    self.client_status.config(text="Disconnected", fg="red")
                    self.log("Client disconnected")
                elif t == "log":
                    self.log(d)
                elif t == "stats":
                    self.stats_label.config(text=d)
        except: pass
        self.root.after(100, self.process_messages)
            
    def run(self):
        self.root.mainloop()

# === START APP ===
if __name__ == "__main__":
    StreamerGUI().run()