"""
Changes:
- Mini Mode 280x140 + Progress Bar
- Main Button: Green "DONE" for 2s on success
- Mini Copy Button: Flashes Green (Success) or Red "LỖI" (Error)
- Stop flash on click/new download
- Fixed Layout: Widgets expand to fill Mini Mode
"""

import customtkinter as ctk
import threading
import os
import json
import sys
import time
import random
import queue
import webbrowser # <--- Thêm thư viện mở web
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse

# Drag & Drop
try:
    from tkinterdnd2 import DND_ALL, TkinterDnD
except ImportError:
    print("Vui lòng cài đặt thư viện: pip install tkinterdnd2")
    sys.exit()

# ==============================================================================
# VERSION
# ==============================================================================
APP_VERSION = "1.8.5"
UPDATE_LINK = "https://github.com/younglonelyfeel"

# ==============================================================================
# WINDOW CONFIG
# ==============================================================================
DEFAULT_WINDOW_GEOMETRY = "540x440"
MINI_WINDOW_GEOMETRY = "280x140" 

# ==============================================================================
# LOG / THEME
# ==============================================================================
LOG_FONT_FAMILY = "Cascadia Mono"
LOG_FONT_SIZE = 11
LOG_TEXT_COLOR = "#F0F0F0"
LOG_BG_COLOR = "#000000"
LOG_BORDER_COLOR = "#333"
LOG_PADDING_X = 6
LOG_PADDING_Y = 6

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLOR_FRAME = "#242424"
COLOR_ACCENT = "#3B8ED0"
COLOR_HOVER = "#1F6AA5"
COLOR_TEXT = "#E0E0E0"
COLOR_SUCCESS = "#2CC985"
COLOR_ERROR = "#E74C3C"
COLOR_WARN = "#F1C40F"
COLOR_BTN_DEFAULT = "#555" # Màu mặc định cho nút phụ mini

# ==============================================================================
# FILES / PATHS
# ==============================================================================
CONFIG_FILE = "window_config.json"
COOKIE_FILE = "cookies.txt"
DEFAULT_DOWNLOAD_FOLDER = Path.home() / "Downloads" / "YLF-Downloads"


# ==============================================================================
# UTILITIES (Giữ nguyên 100% từ 1.7.4)
# ==============================================================================
def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def normalize_input_url(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
    s = " ".join(s.split())
    return s


def is_supported_url(url: str) -> bool:
    if not url:
        return False
    try:
        p = urlparse(url)
        if not p.scheme or not p.netloc:
            return False
        host = p.netloc.lower().split(":")[0]

        def host_is(domain: str) -> bool:
            return host == domain or host.endswith("." + domain)

        return (
            host_is("youtube.com")
            or host_is("youtu.be")
            or host_is("tiktok.com")
            or host_is("facebook.com")
            or host_is("fb.watch")
            or host_is("pinterest.com")
            or host_is("pin.it")
        )
    except Exception:
        return False


def format_duration(seconds) -> str:
    if seconds is None:
        return "N/A"
    try:
        seconds = int(seconds)
    except Exception:
        return "N/A"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def ensure_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_truncate(text: str, max_chars: int = 400) -> str:
    if not text:
        return ""
    return text if len(text) <= max_chars else (text[: max_chars - 1] + "…")


def parse_geometry_xy(geo: str) -> tuple[int | None, int | None]:
    try:
        idx = geo.find("+")
        idx2 = geo.find("-", 1)
        cut = idx if idx != -1 else idx2
        if cut == -1:
            return None, None
        pos = geo[cut:]
        pos_norm = pos.replace("-", "+-")
        parts = [p for p in pos_norm.split("+") if p.strip() != ""]
        if len(parts) < 2:
            return None, None
        x = int(parts[0])
        y = int(parts[1])
        return x, y
    except Exception:
        return None, None


# ==============================================================================
# RATE LIMIT (Giữ nguyên 100% từ 1.7.4)
# ==============================================================================
class RateLimitManager:
    def __init__(self):
        self.last_download_time: float | None = None
        self.download_count = 0
        self.reset_time: datetime | None = None
        self.current_delay = 3.0
        self.backoff_until: float | None = None

    def can_download(self) -> tuple[bool, float]:
        now = time.time()
        if self.backoff_until is not None and now < self.backoff_until:
            return False, self.backoff_until - now
        if self.last_download_time is None:
            return True, 0.0
        elapsed = now - self.last_download_time
        if elapsed < self.current_delay:
            return False, self.current_delay - elapsed
        return True, 0.0

    def record_download_attempt(self) -> None:
        self.last_download_time = time.time()
        self.download_count += 1
        self.current_delay = float(random.randint(1, 6))
        now_dt = datetime.now()
        if self.reset_time is None or now_dt > self.reset_time:
            self.reset_time = now_dt + timedelta(hours=1)
            self.download_count = 1

    def punish_backoff(self, seconds: int) -> None:
        self.backoff_until = time.time() + max(5, int(seconds))

    def get_stats(self) -> int:
        return self.download_count


# ==============================================================================
# APP
# ==============================================================================
class YLFDownloader(ctk.CTk, TkinterDnD.DnDWrapper):
    UI_UPDATE_INTERVAL_MS = 50

    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("YLF Downloader")
        self.geometry(DEFAULT_WINDOW_GEOMETRY)
        self.resizable(False, False)
        self.load_window_position()

        try:
            self.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.download_dir: Path = DEFAULT_DOWNLOAD_FOLDER
        ensure_folder(self.download_dir)

        self.is_downloading = False
        self.use_cookies = os.path.exists(COOKIE_FILE)
        self.rate_limiter = RateLimitManager()

        self._retry_after_id: str | None = None
        self._flash_timer: str | None = None # Timer cho hiệu ứng nháy
        self._flash_timeout_timer: str | None = None # Timer dừng nháy sau 60s
        self._ui_queue: "queue.Queue[tuple[str, dict]]" = queue.Queue()

        self.current_caption = ""
        self.current_channel = "Chưa có"
        self.is_mini_mode = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_widgets()

        self.drop_target_register(DND_ALL)
        self.dnd_bind("<<Drop>>", self.on_drop)

        self.after(self.UI_UPDATE_INTERVAL_MS, self._process_ui_queue)

    # -------------------------
    # Thread-safe UI dispatcher
    # -------------------------
    def ui(self, event: str, **payload) -> None:
        self._ui_queue.put((event, payload))

    def _process_ui_queue(self) -> None:
        try:
            while True:
                event, payload = self._ui_queue.get_nowait()
                self._handle_ui_event(event, payload)
        except queue.Empty:
            pass
        self.after(self.UI_UPDATE_INTERVAL_MS, self._process_ui_queue)

    def _handle_ui_event(self, event: str, p: dict) -> None:
        if event == "log":
            self.log_console(p.get("msg", ""))
        elif event == "progress":
            val = float(p.get("val", 0.0))
            percent = int(max(0.0, min(1.0, val)) * 100)
            text = p.get("text", "")
            color = p.get("color", COLOR_TEXT)
            
            # Update Main UI
            self.progress_bar.set(max(0.0, min(1.0, val)))
            self.percent_label.configure(text=f"{percent}%")
            self.progress_label.configure(text=text, text_color=color)
            
            # Update Mini UI
            if hasattr(self, 'mini_progress'):
                self.mini_progress.set(max(0.0, min(1.0, val)))

        elif event == "duration":
            self.lbl_duration.configure(
                text=f"Time: {p.get('text', 'Unknown')}",
                text_color=p.get("color", COLOR_WARN),
            )
        elif event == "button":
            # Update state/text for both buttons
            state = p.get("state", "normal")
            txt = p.get("text", "PASTE")
            fg = p.get("fg", COLOR_ACCENT)
            
            self.btn_download.configure(state=state, text=txt, fg_color=fg)
            if hasattr(self, 'btn_mini_paste'):
                self.btn_mini_paste.configure(state=state, text=txt, fg_color=fg)

        elif event == "reset_ui":
            self.reset_ui(reset_duration=p.get("reset_duration", True))
        
        elif event == "flash_mini":
            # Kích hoạt hiệu ứng nháy
            self.start_mini_flash(status=p.get("status", "success"))

        elif event == "set_downloading":
            self.is_downloading = bool(p.get("value", False))
        elif event == "auto_copy_caption":
            caption = p.get("caption", "") or ""
            channel = p.get("channel", "") or ""
            self._auto_copy_caption_mainthread(caption, channel)

    def _auto_copy_caption_mainthread(self, caption: str, channel: str) -> None:
        caption = caption or ""
        channel = channel or "Không xác định"
        self.current_caption = caption
        self.current_channel = channel

        self.progress_label.configure(text=f"Kênh: {channel}", text_color=COLOR_TEXT)

        if not caption:
            self.log_console("⚠️ Không có caption để auto-copy!")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(caption)
            self.log_console("✅ Auto-copied caption (title) vào clipboard!")
        except Exception as e:
            self.log_console(f"⚠️ Auto-copy thất bại (clipboard đang bị lock?): {e}")

    # -------------------------
    # FLASHING LOGIC (MỚI)
    # -------------------------
    def stop_mini_flash(self):
        """Dừng nhấp nháy và reset nút về mặc định"""
        # Hủy timer hoạt hình
        if self._flash_timer:
            try:
                self.after_cancel(self._flash_timer)
            except: pass
            self._flash_timer = None
        
        # Hủy timer tự động dừng (nếu có)
        if self._flash_timeout_timer:
            try:
                self.after_cancel(self._flash_timeout_timer)
            except: pass
            self._flash_timeout_timer = None
        
        if hasattr(self, 'btn_mini_copy'):
            self.btn_mini_copy.configure(fg_color=COLOR_BTN_DEFAULT, text="COPY")

    def start_mini_flash(self, status="success"):
        """Bắt đầu nhấp nháy nút Copy Mini"""
        self.stop_mini_flash() # Dừng cái cũ nếu có
        if not hasattr(self, 'btn_mini_copy'): return

        # Đặt lịch tự dừng sau 60 giây (60000ms)
        self._flash_timeout_timer = self.after(60000, self.stop_mini_flash)

        # Cấu hình màu
        if status == "error":
            colors = [COLOR_ERROR, COLOR_BTN_DEFAULT] # Đỏ <-> Xám
            text_mode = "LỖI"
        else:
            colors = [COLOR_SUCCESS, COLOR_BTN_DEFAULT] # Xanh <-> Xám
            text_mode = "COPY"

        self._flash_state_idx = 0

        def animate():
            # Chọn màu
            c = colors[self._flash_state_idx % 2]
            try:
                # Giữ nguyên text, chỉ đổi màu
                self.btn_mini_copy.configure(fg_color=c, text=text_mode)
                self._flash_state_idx += 1
                # Lặp lại sau 600ms
                self._flash_timer = self.after(600, animate)
            except Exception:
                pass

        animate()

    # -------------------------
    # OPEN BROWSER (MỚI)
    # -------------------------
    def open_update_link(self):
        try:
            webbrowser.open(UPDATE_LINK)
        except:
            pass

    # -------------------------
    # UI Creation
    # -------------------------
    def create_widgets(self):
        # --- MAIN VIEW ---
        self.main_view = ctk.CTkFrame(self, fg_color="transparent")
        self.main_view.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.main_view.grid_columnconfigure(0, weight=1)
        self.main_view.grid_rowconfigure(2, weight=1) # Log row expand

        # INPUT
        input_card = ctk.CTkFrame(self.main_view, fg_color=COLOR_FRAME, corner_radius=10)
        input_card.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        lbl_input = ctk.CTkLabel(input_card, text="🔗 Dán hoặc Kéo thả link", font=("Segoe UI", 13, "bold"), text_color="gray")
        lbl_input.pack(anchor="w", padx=12, pady=(10, 0))

        self.entry_link = ctk.CTkEntry(input_card, placeholder_text="https://...", height=28, font=("Segoe UI", 12), text_color="gray")
        self.entry_link.pack(fill="x", padx=12, pady=(5, 8))

        self.btn_download = ctk.CTkButton(input_card, text="PASTE", height=38, font=("Segoe UI", 14, "bold"),
                                          fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER, corner_radius=10,
                                          command=self.one_click_action)
        self.btn_download.pack(fill="x", padx=12, pady=(0, 10))

        # STATUS + COPY BUTTON
        status_card = ctk.CTkFrame(self.main_view, fg_color=COLOR_FRAME, corner_radius=10)
        status_card.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        status_card.grid_columnconfigure(0, weight=1)

        self.lbl_duration = ctk.CTkLabel(status_card, text="Time: Unknown", font=("Segoe UI", 13, "bold"), text_color=COLOR_WARN)
        self.lbl_duration.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 3))

        self.btn_copy_manual = ctk.CTkButton(status_card, text="📋 COPY CAPTION", width=140, height=30,
                                             font=("Segoe UI", 12, "bold"), fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER,
                                             corner_radius=8, command=self.copy_caption_manual)
        self.btn_copy_manual.grid(row=0, column=1, sticky="e", padx=12, pady=(8, 3))

        self.progress_bar = ctk.CTkProgressBar(status_card, height=8, corner_radius=5, progress_color=COLOR_ACCENT)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 3))
        self.progress_bar.set(0)

        self.percent_label = ctk.CTkLabel(status_card, text="0%", font=("Segoe UI", 12, "bold"), text_color=COLOR_ACCENT)
        self.percent_label.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 3))

        self.progress_label = ctk.CTkLabel(status_card, text="Kênh: Chưa có", font=("Segoe UI", 15, "bold"), text_color=COLOR_TEXT)
        self.progress_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))

        # LOG
        self.log_card = ctk.CTkFrame(self.main_view, fg_color=LOG_BG_COLOR, corner_radius=8, border_width=1, border_color=LOG_BORDER_COLOR)
        self.log_card.grid(row=2, column=0, sticky="nsew")

        self.txt_log = ctk.CTkTextbox(self.log_card, font=(LOG_FONT_FAMILY, LOG_FONT_SIZE), fg_color="transparent",
                                      text_color=LOG_TEXT_COLOR, wrap="word", height=80)
        self.txt_log.pack(fill="both", expand=True, padx=LOG_PADDING_X, pady=LOG_PADDING_Y)
        self.txt_log.configure(state="disabled")

        # FOOTER (Toggle Mini Mode)
        footer = ctk.CTkFrame(self.main_view, fg_color="transparent")
        footer.grid(row=3, column=0, pady=(4, 0), sticky="ew")
        
        self.btn_to_mini = ctk.CTkButton(footer, text="↗ Thu nhỏ & Gim", width=100, height=20, font=("Segoe UI", 10),
                                       fg_color="#444", hover_color="#666", command=self.toggle_mode)
        self.btn_to_mini.pack(side="left")

        # Nút Link Github (Thêm mới)
        self.btn_github = ctk.CTkButton(footer, text="🌐 Update", width=80, height=20, font=("Segoe UI", 11, "bold"),
                                        fg_color="transparent", text_color="#3B8ED0", hover_color="#2B2B2B",
                                        command=self.open_update_link)
        self.btn_github.pack(side="right", padx=(0, 2))

        version_label = ctk.CTkLabel(footer, text=f"Ver: {APP_VERSION}", font=("Segoe UI", 11, "bold"), text_color="#607D8B")
        version_label.pack(side="right", padx=(0, 5))

        # --- MINI VIEW ---
        self.mini_view = ctk.CTkFrame(self, fg_color="transparent")
        # Column weights: chia đều chiều ngang
        self.mini_view.grid_columnconfigure(0, weight=1)
        self.mini_view.grid_columnconfigure(1, weight=1)
        # Row weights: Hàng 1 (nút to) chiếm hết không gian dọc thừa
        self.mini_view.grid_rowconfigure(1, weight=1)
        
        # Row 0: Progress Bar (Giữ nguyên sticky="ew" để nằm gọn bên trên)
        self.mini_progress = ctk.CTkProgressBar(self.mini_view, height=5, corner_radius=0, progress_color=COLOR_SUCCESS)
        self.mini_progress.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 2))
        self.mini_progress.set(0)

        # Row 1: Big Button (Sửa: sticky="nsew", bỏ height cố định)
        self.btn_mini_paste = ctk.CTkButton(self.mini_view, text="PASTE", font=("Segoe UI", 20, "bold"),
                                          fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER,
                                          # height=65 -> Đã bỏ để tự giãn
                                          command=self.one_click_action)
        self.btn_mini_paste.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=2, pady=0)

        # Row 2: Tiny buttons (Sửa: sticky="nsew" để lấp đầy đáy)
        self.btn_mini_copy = ctk.CTkButton(self.mini_view, text="COPY", font=("Segoe UI", 10, "bold"),
                                         fg_color=COLOR_BTN_DEFAULT, hover_color="#777", width=60, height=22,
                                         command=self.copy_caption_manual)
        self.btn_mini_copy.grid(row=2, column=0, sticky="nsew", padx=(2, 1), pady=(2, 2))

        self.btn_expand = ctk.CTkButton(self.mini_view, text="MỞ RỘNG", font=("Segoe UI", 10, "bold"),
                                        fg_color="#333", hover_color="#555", width=60, height=22,
                                        command=self.toggle_mode)
        self.btn_expand.grid(row=2, column=1, sticky="nsew", padx=(1, 2), pady=(2, 2))

        # Startup logs
        self.log_console("=" * 45)
        self.log_console(f"YLF Downloader by @hoavaomay - Ver :{APP_VERSION} ")
        self.log_console("✅ Auto-copy caption: ON (sau extract)")
        self.log_console("💡 Tip: Kéo & Thả link trực tiếp vào cửa sổ")
        if self.use_cookies:
            self.log_console("✅ Cookie đã được tải - Giới hạn cao hơn")
        else:
            self.log_console("⚠️ Chưa có cookie - Giới hạn tiêu chuẩn")
        self.log_console(f"📁 Download folder: {self.download_dir}")
        self.log_console("=" * 45)

    # -------------------------
    # Toggle Mode Logic
    # -------------------------
    def toggle_mode(self):
        if not self.is_mini_mode:
            # Switch to Mini
            self.save_window_position()
            self.main_view.grid_forget()
            
            geo = self.geometry()
            x, y = parse_geometry_xy(geo)
            if x is None: x, y = 100, 100
            
            self.geometry(f"{MINI_WINDOW_GEOMETRY}+{x}+{y}")
            self.mini_view.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            self.attributes("-topmost", True)
            self.is_mini_mode = True
        else:
            # Switch to Normal
            self.mini_view.grid_forget()
            
            geo = self.geometry()
            x, y = parse_geometry_xy(geo)
            if x is None: x, y = 100, 100

            self.geometry(f"{DEFAULT_WINDOW_GEOMETRY}+{x}+{y}")
            self.main_view.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self.attributes("-topmost", False)
            self.is_mini_mode = False

    # -------------------------
    # Copy manual (Stop Flash)
    # -------------------------
    def copy_caption_manual(self) -> None:
        # Bấm copy -> Dừng nháy
        self.stop_mini_flash()

        if not self.current_caption:
            self.log_console("⚠️ Chưa có caption để copy!")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(self.current_caption)
            self.log_console("✅ Đã copy caption (thủ công)!")
            
            # Flash Main Button
            original = self.btn_copy_manual.cget("fg_color")
            self.btn_copy_manual.configure(fg_color=COLOR_SUCCESS)
            self.after(650, lambda: self.btn_copy_manual.configure(fg_color=original))

            # Flash Mini Button (Confirm copied)
            self.btn_mini_copy.configure(fg_color=COLOR_SUCCESS, text="COPIED")
            def reset_mini():
                try: self.btn_mini_copy.configure(fg_color=COLOR_BTN_DEFAULT, text="COPY")
                except: pass
            self.after(650, reset_mini)

        except Exception as e:
            self.log_console(f"⚠️ Copy thủ công lỗi: {e}")

    # -------------------------
    # Logging
    # -------------------------
    def log_console(self, msg: str) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", f"> {msg}\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    # -------------------------
    # DnD
    # -------------------------
    def on_drop(self, event):
        if self.is_downloading:
            self.log_console("⚠️ Đang bận tải video khác...")
            return
        url_dropped = normalize_input_url(getattr(event, "data", "") or "")
        self.log_console("📋 Phát hiện thao tác thả Link...")
        self.one_click_action(provided_link=url_dropped)

    # -------------------------
    # One-click action
    # -------------------------
    def one_click_action(self, provided_link=None):
        if self.is_downloading:
            return
        
        # Bắt đầu tải -> Dừng nháy
        self.stop_mini_flash()

        if self._retry_after_id is not None:
            try:
                self.after_cancel(self._retry_after_id)
            except Exception:
                pass
            self._retry_after_id = None

        can_download, wait_time = self.rate_limiter.can_download()
        if not can_download:
            wait_s = int(max(1, wait_time))
            self.log_console(f"Vui lòng đợi {wait_s}s để tránh bị chặn...")
            self.progress_label.configure(text=f"Đợi {wait_s}s (chống spam)", text_color=COLOR_WARN)
            self._retry_after_id = self.after(wait_s * 1000, lambda: self.one_click_action(provided_link))
            return

        try:
            if provided_link:
                content = normalize_input_url(provided_link)
            else:
                content = normalize_input_url(self.clipboard_get())

            if not is_supported_url(content):
                self.log_console("⚠️ Clipboard/Link không hợp lệ hoặc không hỗ trợ!")
                self.progress_label.configure(text="Kênh: Chưa có", text_color=COLOR_TEXT)
                return

            self.entry_link.delete(0, "end")
            self.entry_link.insert(0, content)
            self.start_download()

        except Exception as e:
            self.log_console(f"⚠️ Lỗi xử lý link: {e}")
            self.progress_label.configure(text="Kênh: Chưa có", text_color=COLOR_TEXT)

    # -------------------------
    # Download control
    # -------------------------
    def start_download(self):
        if self.is_downloading:
            return

        url = normalize_input_url(self.entry_link.get())
        if not is_supported_url(url):
            self.log_console("❌ Link không hợp lệ!")
            return

        self.is_downloading = True
        
        # Set UI to Processing
        self.ui("button", state="disabled", text="PROCESSING...", fg="#444")
        
        self.lbl_duration.configure(text="Time: Extracting…", text_color=COLOR_WARN)
        self.progress_bar.set(0)
        if hasattr(self, 'mini_progress'): self.mini_progress.set(0)
        
        self.percent_label.configure(text="0%")
        self.progress_label.configure(text="Đang xử lý...", text_color=COLOR_WARN)

        self.rate_limiter.record_download_attempt()

        threading.Thread(target=self.download_video_worker, args=(url,), daemon=True).start()

    # -------------------------
    # yt-dlp worker (Giữ nguyên logic 1.7.4)
    # -------------------------
    def download_video_worker(self, url: str):
        try:
            import yt_dlp  # type: ignore

            self.ui("log", msg=f"Bắt đầu tải: {url}")
            self.ui("log", msg="⚡ Ưu tiên H.264 + AAC (mp4)")

            outtmpl = str(self.download_dir / "%(title)s.%(ext)s")
            ydl_opts = {
                "outtmpl": outtmpl,
                "format": "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
                "merge_output_format": "mp4",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [self.progress_hook_threadsafe],
                "socket_timeout": 30,
                "retries": 3,
            }

            if self.use_cookies and os.path.exists(COOKIE_FILE):
                ydl_opts["cookiefile"] = COOKIE_FILE
                self.ui("log", msg="🍪 Đang sử dụng cookie authentication")

            final_path = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                channel_name = info.get("uploader") or info.get("channel") or "Không xác định"
                video_title = info.get("title", "") or ""
                duration_str = format_duration(info.get("duration"))

                self.ui("duration", text=duration_str, color=COLOR_WARN)
                self.ui("log", msg=f"Time video: {duration_str}")
                self.ui("log", msg=f"Kênh: {channel_name}")
                self.ui("log", msg=f"Caption: {video_title if video_title else '(trống)'}")

                self.ui("auto_copy_caption", caption=video_title, channel=channel_name)

                if isinstance(info.get("requested_downloads"), list) and info["requested_downloads"]:
                    fp = info["requested_downloads"][0].get("filepath")
                    if fp:
                        final_path = fp
                if not final_path:
                    final_path = info.get("_filename")
                if not final_path:
                    final_path = ydl.prepare_filename(info)

                pre, ext = os.path.splitext(final_path)
                if ext.lower() != ".mp4":
                    maybe = pre + ".mp4"
                    if os.path.exists(maybe):
                        final_path = maybe

            stats = self.rate_limiter.get_stats()
            self.ui("log", msg=f"✅ Tải xong: {os.path.basename(final_path)}")
            self.ui("log", msg=f"📊 Đã tải {stats} video trong giờ này")
            self.ui("progress", val=1.0, text="🎉 Xử lý thành công!", color=COLOR_SUCCESS)

            # Signal Success
            self.ui("reset_ui", reset_duration=False)
            
            # TRIGGER FLASH SUCCESS (GREEN)
            self.ui("flash_mini", status="success")

        except Exception as e:
            msg = str(e)
            self.ui("log", msg=f"❌ Lỗi: {safe_truncate(msg, 900)}")

            if "429" in msg or "Too Many Requests" in msg:
                self.ui("log", msg="🚨 429 Too Many Requests → Backoff 10 phút")
                self.ui("progress", val=0.0, text="❌ 429: Bị giới hạn tốc độ!", color=COLOR_ERROR)
                self.rate_limiter.punish_backoff(10 * 60)
            else:
                self.ui("progress", val=0.0, text=f"❌ Lỗi: {safe_truncate(msg, 120)}", color=COLOR_ERROR)

            self.ui("duration", text="N/A", color=COLOR_WARN)
            self.ui("button", state="normal", text="PASTE", fg=COLOR_ACCENT)
            self.ui("set_downloading", value=False)
            
            # TRIGGER FLASH ERROR (RED)
            self.ui("flash_mini", status="error")

        finally:
            if not self.is_downloading:
                 self.ui("button", state="normal", text="PASTE", fg=COLOR_ACCENT)
                 self.ui("set_downloading", value=False)

    # -------------------------
    # Progress hook
    # -------------------------
    def progress_hook_threadsafe(self, d: dict):
        try:
            status = d.get("status")
            if status == "downloading":
                p_str = (d.get("_percent_str") or "0%").replace("%", "").strip()
                try:
                    val = float(p_str) / 100.0
                except Exception:
                    val = 0.0
                speed = d.get("_speed_str") or "N/A"
                eta = d.get("_eta_str") or "N/A"
                percent_str = d.get("_percent_str") or "0%"

                self.ui(
                    "progress",
                    val=val,
                    text=f"Loading: {percent_str} | {speed} | ETA {eta}",
                    color=COLOR_TEXT,
                )
            elif status == "finished":
                self.ui("progress", val=1.0, text="✅ Tải hoàn tất. Đang mux MP4...", color=COLOR_SUCCESS)
        except Exception as e:
            self.ui("log", msg=f"⚠️ Progress hook error: {e}")

    # -------------------------
    # UI reset (Modified for DONE signal)
    # -------------------------
    def reset_ui(self, reset_duration=True):
        self.entry_link.delete(0, "end")
        self.progress_bar.set(0)
        if hasattr(self, 'mini_progress'): self.mini_progress.set(0)
        
        self.percent_label.configure(text="0%")
        if reset_duration:
            self.lbl_duration.configure(text="Time: Unknown", text_color=COLOR_WARN)

        self.progress_label.configure(text=f"Kênh: {self.current_channel}", text_color=COLOR_TEXT)
        self.is_downloading = False

        # Tín hiệu hoàn thành:
        if not reset_duration:
            # Thành công: Hiện DONE, Xanh lá
            self.btn_download.configure(state="normal", text="DONE", fg_color=COLOR_SUCCESS)
            if hasattr(self, 'btn_mini_paste'):
                self.btn_mini_paste.configure(state="normal", text="DONE", fg_color=COLOR_SUCCESS)
            
            # 2 giây sau quay lại PASTE
            def restore_button():
                try:
                    self.btn_download.configure(state="normal", text="PASTE", fg_color=COLOR_ACCENT)
                    if hasattr(self, 'btn_mini_paste'):
                        self.btn_mini_paste.configure(state="normal", text="PASTE", fg_color=COLOR_ACCENT)
                except: pass
            
            self.after(2000, restore_button)
        else:
            # Lỗi hoặc reset thường: Về PASTE luôn
            self.btn_download.configure(state="normal", text="PASTE", fg_color=COLOR_ACCENT)
            if hasattr(self, 'btn_mini_paste'):
                self.btn_mini_paste.configure(state="normal", text="PASTE", fg_color=COLOR_ACCENT)

    # -------------------------
    # Window position persistence
    # -------------------------
    def save_window_position(self):
        try:
            geo = self.geometry()
            x, y = parse_geometry_xy(geo)
            data = {"x": x, "y": y, "version": APP_VERSION}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Lỗi lưu vị trí: {e}")

    def load_window_position(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            x = data.get("x")
            y = data.get("y")

            if (x is None or y is None) and isinstance(data.get("geometry"), str):
                old_geo = data["geometry"]
                x2, y2 = parse_geometry_xy(old_geo)
                if x is None: x = x2
                if y is None: y = y2

            if isinstance(x, int) and isinstance(y, int):
                self.geometry(f"{DEFAULT_WINDOW_GEOMETRY}+{x}+{y}")
        except Exception as e:
            print(f"Lỗi load vị trí: {e}")
            try:
                os.remove(CONFIG_FILE)
            except Exception:
                pass

    def on_closing(self):
        if self._retry_after_id is not None:
            try:
                self.after_cancel(self._retry_after_id)
            except Exception:
                pass
            self._retry_after_id = None

        self.save_window_position()
        self.destroy()


if __name__ == "__main__":
    app = YLFDownloader()
    app.mainloop()