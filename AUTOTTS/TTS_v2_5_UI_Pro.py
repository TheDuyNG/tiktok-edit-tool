# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'TTS_v2_5.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.colorchooser import askcolor
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets.scrolled import ScrolledText
import threading
import os
os.environ.setdefault('MPLCONFIGDIR', os.path.abspath('.mpl_cache'))
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_HF_CACHE_DIR = os.path.join(_APP_DIR, '.hf_cache')
os.makedirs(_HF_CACHE_DIR, exist_ok=True)
os.environ.setdefault('HF_HOME', _HF_CACHE_DIR)
os.environ.setdefault('HUGGINGFACE_HUB_CACHE', os.path.join(_HF_CACHE_DIR, 'hub'))
os.environ['FLAGS_use_onednn'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['FLAGS_enable_onednn_ops'] = ''
import sys
import site
import subprocess
import logging
import shutil
import copy
from datetime import datetime
import time
import random
import re
import webbrowser
import textwrap
import json
import hashlib
import multiprocessing
import unicodedata
import pysrt
import warnings

# AUTOTTS configures the bundled imageio-ffmpeg executable immediately below.
# Pydub probes PATH while it is imported and otherwise emits a misleading
# warning before its converter is assigned to that bundled executable.
warnings.filterwarnings(
    'ignore',
    message=r"Couldn't find ffmpeg or avconv.*",
    category=RuntimeWarning,
    module=r'pydub\.utils'
)
from pydub import AudioSegment
from pydub.playback import play
from pydub.silence import detect_nonsilent
from gtts import gTTS
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import requests
import numpy as np
import os
import imageio_ffmpeg
try:
    _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    _ffmpeg_dir = os.path.dirname(_ffmpeg_exe)
    if _ffmpeg_dir not in os.environ['PATH']:
        os.environ['PATH'] = _ffmpeg_dir + os.pathsep + os.environ['PATH']
    os.environ['FFMPEG_BINARY'] = _ffmpeg_exe
    os.environ['IMAGEIO_FFMPEG_EXE'] = _ffmpeg_exe
except Exception:
    _ffmpeg_exe = 'ffmpeg'
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx.all import speedx, mirror_x, mirror_y
from pydub import AudioSegment as _AS_cfg
_AS_cfg.converter = _ffmpeg_exe
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageFont
import moviepy.editor as mp
from dotenv import load_dotenv
load_dotenv()
ENV_FILE = '.env'
SETTINGS_FILE = 'settings.json'
ACTIVE_FFMPEG_PROCESSES = []
APP_BUILD = 'AUDIO FIX 2026-07-20'
SRT_TTS_CACHE_VERSION = 'srt_tts_cache_v1'
OMNIVOICE_MODEL_CACHE = {}
OMNIVOICE_PROMPT_CACHE = {}
OMNIVOICE_SAMPLE_RATE = 24000
VIENEU_MODEL_CACHE = {}
VIENEU_REF_VOICE_CACHE = {}
VIENEU_SAMPLE_RATE = 48000
VIENEU_CLONE_STYLE = 'tu_nhien'
VIENEU_REF_TARGET_MS = 8000
VIENEU_REF_MAX_WINDOWS = 3
VIENEU_REF_CACHE_VERSION = 'vieneu_ref_power_v2'
VIENEU_CLONE_CACHE_VERSION = 'vieneu_clone_power_v2'
VIENEU_TTS_CACHE_VERSION = 'vieneu_clone_power_v4'
LOCAL_GPU_TTS_PROVIDERS = ('vieneu',)
OMNIVOICE_ALLOWED_INSTRUCTS = {
    'american accent',
    'australian accent',
    'british accent',
    'canadian accent',
    'child',
    'chinese accent',
    'elderly',
    'female',
    'high pitch',
    'indian accent',
    'japanese accent',
    'korean accent',
    'low pitch',
    'male',
    'middle-aged',
    'moderate pitch',
    'portuguese accent',
    'russian accent',
    'teenager',
    'very high pitch',
    'very low pitch',
    'whisper',
    'young adult'
}

# ==============================
# GIAO DIỆN PRO - CHỈ THAY ĐỔI UI, KHÔNG ĐỤNG LOGIC XỬ LÝ
# ==============================
APP_TITLE = f'🎬 AUTOTTS PRO v2.5 — Studio Edition | {APP_BUILD}'
APP_THEME = 'cyborg'  # Có thể đổi: superhero, darkly, cyborg, vapor, solar
APP_FONT = 'Segoe UI'
COLOR_ACCENT = '#00e5ff'
COLOR_SUCCESS = '#00d084'
COLOR_WARNING = '#ffb020'
COLOR_DANGER = '#ff4d6d'
COLOR_MUTED = '#a9b4c2'
COLOR_PANEL = '#111827'
COLOR_CANVAS = '#0b1020'


def apply_modern_style(root):
    """Áp dụng font, khoảng cách và style chung cho toàn app."""
    try:
        root.option_add('*Font', (APP_FONT, 10))
        root.option_add('*TCombobox*Listbox.font', (APP_FONT, 10))
    except Exception:
        pass

    try:
        style = tb.Style()
        style.configure('TLabelframe.Label', font=(APP_FONT, 10, 'bold'))
        style.configure('TNotebook.Tab', font=(APP_FONT, 10, 'bold'), padding=(16, 8))
        style.configure('TButton', font=(APP_FONT, 10, 'bold'), padding=(10, 6))
        style.configure('TEntry', padding=(8, 5))
        style.configure('TCombobox', padding=(8, 5))
        style.configure('Horizontal.TProgressbar', thickness=14)
    except Exception:
        pass


def nice_path(path, max_len=95):
    """Rút gọn đường dẫn dài để giao diện gọn hơn."""
    if not path:
        return ''
    path = str(path)
    if len(path) <= max_len:
        return path
    return path[:38] + ' ... ' + path[-52:]

def normalize_filename_key(text):
    text = str(text or '').replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()

def resolve_existing_media_path(path):
    path = str(path or '').strip()
    if not path:
        return None
    if os.path.isfile(path):
        return path

    basename = os.path.basename(path.replace('\\', '/'))
    if not basename:
        return None
    target_key = normalize_filename_key(basename)
    search_roots = [
        os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads'),
        _APP_DIR
    ]
    for root in search_roots:
        if not root or not os.path.isdir(root):
            continue
        try:
            for current_root, _dirs, files in os.walk(root):
                for filename in files:
                    if normalize_filename_key(filename) == target_key:
                        candidate = os.path.join(current_root, filename)
                        if os.path.isfile(candidate):
                            return candidate
        except Exception:
            continue
    return None

def filter_existing_media_paths(paths):
    resolved_paths = []
    seen = set()
    for path in paths or []:
        resolved = resolve_existing_media_path(path)
        if not resolved:
            continue
        key = os.path.normcase(os.path.abspath(resolved))
        if key in seen:
            continue
        seen.add(key)
        resolved_paths.append(resolved)
    return resolved_paths

def get_env_var(name, default=''):
    return os.getenv(name, default)
def set_env_vars(pairs: dict):
    existing = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                else:
                    k, v = line.split('=', 1)
                    existing[k.strip()] = v
    for k, v in pairs.items():
        existing[k] = v
    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        for k, v in existing.items():
            f.write(f'{k}={v}\n')
    load_dotenv(override=True)
def get_api_keys_list(provider_env_var):
    raw = get_env_var(provider_env_var, '')
    return [k.strip() for k in raw.split(',') if k.strip()]
def save_app_settings(data):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f'Lỗi khi lưu cấu hình: {e}')


def load_app_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f'Lỗi khi đọc cấu hình: {e}')
        return {}
class Tooltip:
    def __init__(self, widget, text, delay=350):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._id = None
        self._tip = None
        widget.bind('<Enter>', self._schedule)
        widget.bind('<Leave>', self._hide)
        widget.bind('<ButtonPress>', self._hide)
    def _schedule(self, _event=None):
        self._unschedule()
        self._id = self.widget.after(self.delay, self._show)
    def _unschedule(self):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
    def _show(self):
        if self._tip or not self.text:
            return None
        else:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            tw = tk.Toplevel(self.widget)
            self._tip = tw
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f'+{x}+{y}')
            frame = tb.Frame(tw, relief='solid', borderwidth=1, bootstyle='secondary')
            frame.pack(ipadx=8, ipady=5)
            label = tb.Label(frame, text=self.text, justify='left', wraplength=320, bootstyle='inverse-dark')
            label.pack()
    def _hide(self, _event=None):
        self._unschedule()
        if self._tip:
            self._tip.destroy()
            self._tip = None
class UpdatePopup(tb.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title('✨ AUTOTTS Pro — Có gì mới?')
        self.geometry('620x360')
        self.resizable(False, False)
        self.update_idletasks()
        x = master.winfo_x() + master.winfo_width() // 2 - 250
        y = master.winfo_y() + master.winfo_height() // 2 - 140
        self.geometry(f'+{x}+{y}')
        top_frame = tb.Frame(self)
        top_frame.pack(fill=X, padx=15, pady=10)
        tb.Label(top_frame, text='✨ AUTOTTS PRO v2.5 — Studio Edition', font=(APP_FONT, 15, 'bold'), bootstyle='info').pack(side=LEFT)
        btn_close_corner = tb.Button(top_frame, text='✖', bootstyle='danger-link', command=self.destroy)
        btn_close_corner.pack(side=RIGHT)
        content = '✅ 1. Nâng cấp lên v2.5 - Giao diện Pro & Dark Mode:\n   - Thanh tiêu đề gradient, header neon, badge version sáng bóng.\n   - Button render có hiệu ứng hover sáng, icon đẹp hơn.\n\n✅ 2. Render Engine v2 - Siêu Tốc Cải Tiến:\n   - Tự động chọn số thread tối ưu (ultrafast khi CPU yếu).\n   - Batch TTS thông minh: ít API delay, tăng 40% tốc độ.\n\n✅ 3. Progress Bar thông minh & ETA hiển thị thời gian còn lại.\n\n✅ 4. Tự động lưu cấu hình & khôi phục khi mở lại tool.'
        lbl_content = tb.Label(self, text=content, justify=LEFT, font=(APP_FONT, 10), bootstyle='light')
        lbl_content.pack(fill=BOTH, expand=YES, padx=25, pady=5)
        tb.Button(self, text='🚀 Bắt đầu sử dụng', bootstyle='success', width=28, command=self.destroy).pack(pady=15)
        self.transient(master)
        self.grab_set()
class GuideDialog(tb.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title('📖 Hướng dẫn lấy API Key & Mẹo dùng Free vô hạn')
        self.geometry('700x550')
        self.resizable(True, True)
        txt = ScrolledText(self, padding=10, font=(APP_FONT, 10), bootstyle='info')
        txt.pack(fill=BOTH, expand=YES)
        def open_url(url):
            webbrowser.open_new(url)
        txt.insert(END, '=== HƯỚNG DẪN LẤY API KEY ===\n\n', 'bold')
        txt.insert(END, '1. FPT AI:\n')
        txt.insert(END, '- Bước 1: Truy cập ')
        txt.insert(END, 'https://console.fpt.ai', 'link_fpt')
        txt.insert(END, ' và đăng nhập.\n')
        txt.insert(END, '- Bước 2: Tạo một Project mới -> \'Trí tuệ nhân tạo\' -> \'Text to Speech\'.\n- Bước 3: Tạo API Key, copy và dán vào Tool.\n\n')
        txt.insert(END, '2. ZALO AI:\n')
        txt.insert(END, '- Bước 1: Truy cập ')
        txt.insert(END, 'https://ai.zalo.me', 'link_zalo')
        txt.insert(END, '.\n')
        txt.insert(END, '- Bước 2: Tạo ứng dụng mới -> Lấy API Key ở tab \'Cài đặt\'.\n\n')
        txt.insert(END, '3. VBEE:\n')
        txt.insert(END, '- Bước 1: Truy cập ')
        txt.insert(END, 'https://vbee.vn', 'link_vbee')
        txt.insert(END, '.\n')
        txt.insert(END, '- Bước 2: Nhận API Key dùng thử miễn phí ở phần Quản lý API.\n\n')
        txt.insert(END, '=== 💡 MẸO DÙNG FREE VÔ HẠN ===\n\n', 'bold')
        txt.insert(END, 'Sử dụng email ảo để tạo nhiều tài khoản. Dán toàn bộ Key lấy được vào ô nhập Key, cách nhau bằng dấu phẩy (,).\nVí dụ: key1,key2,key3\nTool sẽ chia luồng chạy song song siêu tốc!')
        txt.tag_config('bold', font=(APP_FONT, 10, 'bold'))
        link_tags = ['link_fpt', 'link_zalo', 'link_vbee']
        urls = ['https://console.fpt.ai', 'https://ai.zalo.me', 'https://vbee.vn']
        for tag, url in zip(link_tags, urls):
            txt.tag_config(tag, foreground='#00bc8c', underline=True)
            txt.tag_bind(tag, '<Button-1>', lambda e, u=url: open_url(u))
            txt.tag_bind(tag, '<Enter>', lambda e: txt.config(cursor='hand2'))
            txt.tag_bind(tag, '<Leave>', lambda e: txt.config(cursor=''))
        txt.config(state=DISABLED)
class ApiKeyDialog(tb.Toplevel):
    def __init__(self, master, on_saved=None):
        super().__init__(master)

        self.title('🔑 Quản lý API Keys — Studio')
        self.resizable(False, False)
        self.on_saved = on_saved

        # Tăng chiều cao vì Vbee cần thêm App ID
        self.geometry('720x430')
        self.columnconfigure(1, weight=1)

        top_frame = tb.Frame(self)
        top_frame.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky='ew',
            pady=(10, 5),
            padx=10
        )

        lbl_info = tb.Label(
            top_frame,
            text='Mẹo: Nhập nhiều key cách nhau bằng dấu phẩy (,) để chạy song song.',
            font=(APP_FONT, 9, 'italic'),
            bootstyle='warning'
        )
        lbl_info.pack(side=LEFT)

        btn_guide = tb.Button(
            top_frame,
            text='📖 Hướng dẫn',
            bootstyle='info-outline',
            command=self.open_guide
        )
        btn_guide.pack(side=RIGHT)

        # FPT
        tb.Label(
            self,
            text='FPT_API_KEY:'
        ).grid(
            row=1,
            column=0,
            padx=10,
            pady=10,
            sticky='e'
        )

        self.entry_fpt = tb.Entry(
            self,
            show='*',
            bootstyle='info'
        )
        self.entry_fpt.grid(
            row=1,
            column=1,
            padx=10,
            pady=10,
            sticky='ew'
        )
        self.entry_fpt.insert(
            0,
            get_env_var('FPT_API_KEY', '')
        )

        # Zalo
        tb.Label(
            self,
            text='ZALO_API_KEY:'
        ).grid(
            row=2,
            column=0,
            padx=10,
            pady=10,
            sticky='e'
        )

        self.entry_zalo = tb.Entry(
            self,
            show='*',
            bootstyle='info'
        )
        self.entry_zalo.grid(
            row=2,
            column=1,
            padx=10,
            pady=10,
            sticky='ew'
        )
        self.entry_zalo.insert(
            0,
            get_env_var('ZALO_API_KEY', '')
        )

        # Vbee Access Token
        tb.Label(
            self,
            text='VBEE_ACCESS_TOKEN:'
        ).grid(
            row=3,
            column=0,
            padx=10,
            pady=10,
            sticky='e'
        )

        self.entry_vbee_token = tb.Entry(
            self,
            show='*',
            bootstyle='info'
        )
        self.entry_vbee_token.grid(
            row=3,
            column=1,
            padx=10,
            pady=10,
            sticky='ew'
        )
        self.entry_vbee_token.insert(
            0,
            get_env_var('VBEE_ACCESS_TOKEN', '')
        )

        # Vbee App ID
        tb.Label(
            self,
            text='VBEE_APP_ID:'
        ).grid(
            row=4,
            column=0,
            padx=10,
            pady=10,
            sticky='e'
        )

        self.entry_vbee_app_id = tb.Entry(
            self,
            show='*',
            bootstyle='info'
        )
        self.entry_vbee_app_id.grid(
            row=4,
            column=1,
            padx=10,
            pady=10,
            sticky='ew'
        )
        self.entry_vbee_app_id.insert(
            0,
            get_env_var('VBEE_APP_ID', '')
        )

        # Khung nút
        btns_frame = tb.Frame(self)
        btns_frame.grid(
            row=5,
            column=0,
            columnspan=2,
            padx=10,
            pady=(10, 20),
            sticky='e'
        )

        def toggle_show(entry):
            entry.config(
                show='' if entry.cget('show') == '*' else '*'
            )

        tb.Button(
            btns_frame,
            text='👁 FPT',
            width=7,
            bootstyle='outline-secondary',
            command=lambda: toggle_show(self.entry_fpt)
        ).pack(
            side=tk.LEFT,
            padx=(0, 2)
        )

        tb.Button(
            btns_frame,
            text='👁 Zalo',
            width=7,
            bootstyle='outline-secondary',
            command=lambda: toggle_show(self.entry_zalo)
        ).pack(
            side=tk.LEFT,
            padx=(0, 2)
        )

        tb.Button(
            btns_frame,
            text='👁 Token',
            width=8,
            bootstyle='outline-secondary',
            command=lambda: toggle_show(
                self.entry_vbee_token
            )
        ).pack(
            side=tk.LEFT,
            padx=(0, 2)
        )

        tb.Button(
            btns_frame,
            text='👁 App ID',
            width=8,
            bootstyle='outline-secondary',
            command=lambda: toggle_show(
                self.entry_vbee_app_id
            )
        ).pack(
            side=tk.LEFT,
            padx=(0, 12)
        )

        tb.Button(
            btns_frame,
            text='Hủy',
            bootstyle='danger',
            command=self.destroy
        ).pack(
            side=tk.LEFT,
            padx=(0, 6)
        )

        tb.Button(
            btns_frame,
            text='Lưu',
            bootstyle='success',
            command=self.save_keys
        ).pack(
            side=tk.LEFT
        )

        self.grab_set()

    def open_guide(self):
        GuideDialog(self)

    def save_keys(self):
        set_env_vars({
            'FPT_API_KEY':
                self.entry_fpt.get().strip(),

            'ZALO_API_KEY':
                self.entry_zalo.get().strip(),

            'VBEE_ACCESS_TOKEN':
                self.entry_vbee_token.get().strip(),

            'VBEE_APP_ID':
                self.entry_vbee_app_id.get().strip()
        })

        if self.on_saved:
            self.on_saved()

        messagebox.showinfo(
            'Thành công',
            'Đã lưu API keys, Vbee Access Token và App ID.'
        )

        self.destroy()
def srt_time_to_ms(srt_time):
    return (srt_time.hours * 3600 + srt_time.minutes * 60 + srt_time.seconds) * 1000 + srt_time.milliseconds
def safe_play_audiosegment(seg: AudioSegment):
    try:
        play(seg)
        return None
    except Exception:
        tmp = 'tts_preview_temp.mp3'
        try:
            seg.export(tmp, format='mp3')
            if os.name == 'nt':
                os.startfile(tmp)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', tmp])
            else:
                subprocess.Popen(['xdg-open', tmp])
        except Exception:
            return None
def apply_audio_speed_pitch(audio_seg, speed=1.0, pitch=1.0):
    try:
        if speed == 1.0 and pitch == 1.0:
            return audio_seg

        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        temp_in = f'temp_in_{random.randint(1000, 9999)}.wav'
        temp_out = f'temp_out_{random.randint(1000, 9999)}.wav'

        audio_seg.export(temp_in, format='wav')
        sr = audio_seg.frame_rate
        new_sr = int(sr * pitch)
        tempo = speed / pitch
        tempo_filter = _build_atempo_chain(tempo) or 'atempo=1.0'

        cmd = [
            ffmpeg_path, '-y',
            '-i', temp_in,
            '-filter:a', f'asetrate={new_sr},aresample={sr},{tempo_filter}',
            temp_out
        ]

        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo
            )
        else:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        out_seg = AudioSegment.from_wav(temp_out)
        return out_seg

    except Exception as e:
        print(f'Lỗi khi apply speed/pitch: {e}')
        return audio_seg

    finally:
        for tmp in ['temp_in', 'temp_out']:
            path = locals().get(tmp)
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
def text_to_speech_gTTS(text, lang='vi', **kwargs):
    try:
        tts = gTTS(text, lang=lang)
        temp_file = f'temp_tts_{random.randint(1000, 9999)}.mp3'
        tts.save(temp_file)
        audio = load_audiosegment_with_ffmpeg(temp_file)
        os.remove(temp_file)
        return audio
    except Exception:
        return AudioSegment.silent(duration=0)
def _http_get_with_retry(url, max_wait=90, first_delay=0.8, backoff=1.6):
    deadline = time.time() + max_wait
    delay = first_delay

    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=30)

            if resp.status_code == 200:
                return resp.content

            if resp.status_code in (429, 403, 404) or 500 <= resp.status_code < 600:
                time.sleep(delay)
                delay = min(delay * backoff, 10)
                continue

            return None

        except requests.exceptions.RequestException:
            time.sleep(delay)
            delay = min(delay * backoff, 6)

    return None
def text_to_speech_fpt(text, voice_id, api_key, speed=1.0):
    try:
        url = 'https://api.fpt.ai/hmi/tts/v5'
        headers = {'api-key': api_key, 'speed': str(speed), 'voice': voice_id}
        resp = requests.post(url, data=text.encode('utf-8'), headers=headers, timeout=30)
        if resp.status_code!= 200:
            return AudioSegment.silent(duration=0)
        else:
            ctype = resp.headers.get('content-type', '')
            data = resp.json() if ctype.startswith('application/json') else {}
            async_url = data.get('async')
            if not async_url:
                return AudioSegment.silent(duration=0)
            else:
                content = _http_get_with_retry(async_url, max_wait=90)
                if not content:
                    return AudioSegment.silent(duration=0)
                else:
                    tmpf = f'_fpt_part_{random.randint(1000, 9999)}.mp3'
                    with open(tmpf, 'wb') as f:
                        f.write(content)
                    seg = load_audiosegment_with_ffmpeg(tmpf)
                    os.remove(tmpf)
                    return seg
    except Exception:
        return AudioSegment.silent(duration=0)
def text_to_speech_zalo(text, speaker_id, api_key):
    try:
        url = 'https://api.zalo.ai/v1/tts/synthesize'
        headers = {'apikey': api_key}
        data = {'input': text, 'speaker_id': int(speaker_id), 'speed': 1.0}

        response = requests.post(url, json=data, headers=headers, timeout=60)

        if response.status_code == 200:
            temp_file = f'temp_tts_zalo_{random.randint(1000, 9999)}.mp3'
            with open(temp_file, 'wb') as f:
                f.write(response.content)

            audio = load_audiosegment_with_ffmpeg(temp_file)
            os.remove(temp_file)
            return audio

        return AudioSegment.silent(duration=0)

    except Exception:
        return AudioSegment.silent(duration=0)

def normalize_omnivoice_instruct(instruct):
    items = []
    for raw_item in str(instruct or '').split(','):
        item = raw_item.strip().lower()
        if item in OMNIVOICE_ALLOWED_INSTRUCTS:
            items.append(item)
    return ', '.join(items)

def parse_omnivoice_voice_config(voice_config):
    if isinstance(voice_config, dict):
        return voice_config

    if isinstance(voice_config, str):
        try:
            data = json.loads(voice_config)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return {'instruct': str(voice_config or '')}

def build_omnivoice_voice_config(instruct='', ref_audio='', ref_text=''):
    data = {
        'instruct': normalize_omnivoice_instruct(instruct),
        'ref_audio': str(ref_audio or '').strip(),
        'ref_text': str(ref_text or '').strip()
    }
    return json.dumps(data, ensure_ascii=False, sort_keys=True)

def parse_vieneu_voice_config(voice_config):
    if isinstance(voice_config, dict):
        return voice_config

    if isinstance(voice_config, str):
        try:
            data = json.loads(voice_config)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return {
        'voice': str(voice_config or '').strip(),
        'ref_audio': '',
        'ref_text': ''
    }

def build_vieneu_voice_config(voice='', ref_audio='', ref_text=''):
    ref_audio = str(ref_audio or '').strip()
    data = {
        # VieNeu trong AUTOTTS chỉ dùng clone, không dùng preset.
        'voice': '',
        'ref_audio': ref_audio,
        'ref_text': str(ref_text or '').strip()
    }
    return json.dumps(data, ensure_ascii=False, sort_keys=True)

def build_continuous_srt_text(subs):
    lines = []
    for sub in subs:
        text = str(getattr(sub, 'text', '') or '')
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
        if not text:
            continue
        if text[-1] not in '.!?…。！？':
            text += '.'
        lines.append(text)
    return ' '.join(lines).strip()

def srt_active_duration_seconds(subs):
    total_ms = 0
    for sub in subs or []:
        try:
            start_ms = srt_time_to_ms(sub.start)
            end_ms = srt_time_to_ms(sub.end)
        except Exception:
            continue
        if end_ms > start_ms:
            total_ms += end_ms - start_ms
    return total_ms / 1000.0

def build_omnivoice_smart_chunks(
    subs,
    target_seconds=6.0,
    max_gap_seconds=1.2,
    max_text_chars=170
):
    chunks = []
    current_items = []
    current_start = None
    current_end = None

    target_ms = max(3000, int(float(target_seconds or 12.0) * 1000))
    max_gap_ms = max(0, int(float(max_gap_seconds or 1.2) * 1000))
    max_text_chars = max(60, int(max_text_chars or 170))

    def flush():
        nonlocal current_items, current_start, current_end
        if not current_items or current_start is None or current_end is None:
            current_items = []
            current_start = None
            current_end = None
            return

        text = build_continuous_srt_text(current_items)
        if text:
            chunks.append(
                {
                    'sub': _SimpleSub(current_start / 1000.0, current_end / 1000.0),
                    'text': text,
                    'source_count': len(current_items),
                    'start_ms': current_start,
                    'end_ms': current_end
                }
            )

        current_items = []
        current_start = None
        current_end = None

    for sub in subs or []:
        try:
            start_ms = srt_time_to_ms(sub.start)
            end_ms = srt_time_to_ms(sub.end)
        except Exception:
            continue

        if end_ms <= start_ms:
            continue

        should_flush = False
        if current_items:
            gap_ms = start_ms - current_end
            duration_if_added = end_ms - current_start
            text_if_added = build_continuous_srt_text(current_items + [sub])
            if (
                gap_ms > max_gap_ms
                or duration_if_added > target_ms
                or len(text_if_added) > max_text_chars
            ):
                should_flush = True

        if should_flush:
            flush()

        if not current_items:
            current_start = start_ms

        current_items.append(sub)
        current_end = end_ms

    flush()
    return chunks

def _numpy_audio_to_segment(audio_array, sample_rate=OMNIVOICE_SAMPLE_RATE):
    temp_file = (
        f'_omnivoice_{os.getpid()}_'
        f'{threading.get_ident()}_{random.randint(1000, 9999)}.wav'
    )
    try:
        import soundfile as sf
        sf.write(temp_file, audio_array, sample_rate)
        return AudioSegment.from_file(temp_file)
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass

def _load_omnivoice_model(use_gpu=True):
    try:
        import torch
        from omnivoice import OmniVoice
    except ImportError as error:
        raise RuntimeError(
            'Chưa cài OmniVoice local. Cài trong Python đang chạy app:\n'
            'pip install omnivoice soundfile\n'
            'Nếu muốn GPU NVIDIA, cài PyTorch CUDA trước theo README OmniVoice.'
        ) from error

    cuda_ready = bool(
        use_gpu
        and hasattr(torch, 'cuda')
        and torch.cuda.is_available()
    )
    device_map = 'cuda:0' if cuda_ready else 'cpu'
    dtype = torch.float16 if cuda_ready else torch.float32
    cache_key = f'{device_map}|{str(dtype)}'

    model = OMNIVOICE_MODEL_CACHE.get(cache_key)
    if model is None:
        try:
            model = OmniVoice.from_pretrained(
                'k2-fsa/OmniVoice',
                device_map=device_map,
                dtype=dtype
            )
        except OSError as error:
            if 'paging file is too small' in str(error).lower():
                raise RuntimeError(
                    'OmniVoice không nạp được model vì bộ nhớ ảo '
                    '(Windows paging file) quá thấp. Hãy đóng bớt app '
                    'nặng hoặc tăng Virtual Memory/Pagefile rồi mở lại '
                    'AUTOTTS.'
                ) from error
            raise
        OMNIVOICE_MODEL_CACHE[cache_key] = model

    return model

def _get_omnivoice_clone_prompt(model, ref_audio, ref_text, log_callback=None):
    ref_audio = str(ref_audio or '').strip()
    ref_text = str(ref_text or '').strip()

    if not ref_audio or not ref_text:
        return None

    try:
        stat = os.stat(ref_audio)
        key = (
            os.path.abspath(ref_audio),
            stat.st_size,
            int(stat.st_mtime),
            ref_text,
            str(getattr(model, 'device', ''))
        )
    except Exception:
        key = (
            os.path.abspath(ref_audio),
            ref_text,
            str(getattr(model, 'device', ''))
        )

    prompt = OMNIVOICE_PROMPT_CACHE.get(key)
    if prompt is None:
        if log_callback:
            log_callback('OmniVoice clone: đang tạo voice clone prompt từ audio mẫu...')
        started_at = time.time()
        prompt = model.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=ref_text,
            preprocess_prompt=True
        )
        OMNIVOICE_PROMPT_CACHE[key] = prompt
        if log_callback:
            log_callback(
                'OmniVoice clone: tạo voice clone prompt xong '
                f'sau {time.time() - started_at:.1f}s.'
            )
    elif log_callback:
        log_callback('OmniVoice clone: dùng voice clone prompt đã cache.')

    return prompt

def text_to_speech_omnivoice_batch(texts, instruct='', use_gpu=True, ref_audio='', ref_text='', log_callback=None):
    texts = [str(text or '').strip() for text in texts]
    if not texts or any(not text for text in texts):
        raise ValueError('Văn bản OmniVoice không được để trống.')

    already_loaded = bool(OMNIVOICE_MODEL_CACHE)
    if log_callback:
        if already_loaded:
            log_callback('OmniVoice: dùng model đã nạp sẵn.')
        else:
            log_callback(
                'OmniVoice: đang nạp model '
                f'({"GPU/CUDA" if use_gpu else "CPU"})...'
            )
    model = _load_omnivoice_model(use_gpu=use_gpu)
    if log_callback and not already_loaded:
        log_callback('OmniVoice: model đã sẵn sàng.')
    instruct = normalize_omnivoice_instruct(instruct)
    ref_audio = str(ref_audio or '').strip()
    ref_text = str(ref_text or '').strip()

    generate_kwargs = {'text': texts}

    if ref_audio:
        if not os.path.isfile(ref_audio):
            raise RuntimeError(
                f'Không tìm thấy audio mẫu OmniVoice:\n{ref_audio}'
            )
        clone_prompt = _get_omnivoice_clone_prompt(
            model,
            ref_audio,
            ref_text,
            log_callback=log_callback
        )
        if clone_prompt is not None:
            generate_kwargs['voice_clone_prompt'] = [clone_prompt] * len(texts)
        else:
            generate_kwargs['ref_audio'] = [ref_audio] * len(texts)
            if ref_text:
                generate_kwargs['ref_text'] = [ref_text] * len(texts)
    elif instruct:
        generate_kwargs['instruct'] = [instruct] * len(texts)

    if log_callback:
        log_callback(f'OmniVoice: bắt đầu generate {len(texts)} đoạn audio...')
    audios = model.generate(**generate_kwargs)
    if log_callback:
        log_callback(f'OmniVoice: generate xong {len(texts)} đoạn audio.')
    if audios is None or len(audios) != len(texts):
        raise RuntimeError('OmniVoice không trả đủ dữ liệu audio.')

    return [
        _numpy_audio_to_segment(audio, OMNIVOICE_SAMPLE_RATE)
        for audio in audios
    ]

def text_to_speech_omnivoice(text, instruct='', use_gpu=True, ref_audio='', ref_text='', log_callback=None):
    temp_file = None

    try:
        text = str(text or '').strip()
        if not text:
            raise ValueError('Văn bản OmniVoice không được để trống.')

        audios = text_to_speech_omnivoice_batch(
            [text],
            instruct=instruct,
            use_gpu=use_gpu,
            ref_audio=ref_audio,
            ref_text=ref_text,
            log_callback=log_callback
        )
        return audios[0]

    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass

def _load_vieneu_model(use_gpu=True, max_batch_size=8, log_callback=None):
    try:
        import torch
        from vieneu import Vieneu
    except ImportError as error:
        raise RuntimeError(
            'Chưa cài VieNeu local trong Python 3.12.\n'
            'Cài bằng: py -3.12 -m pip install vieneu\n'
            'Muốn chạy GPU cần PyTorch CUDA hoạt động.'
        ) from error

    cuda_ready = bool(
        use_gpu
        and hasattr(torch, 'cuda')
        and torch.cuda.is_available()
    )
    if use_gpu and not cuda_ready:
        raise RuntimeError(
            'VieNeu GPU được bật nhưng PyTorch CUDA chưa sẵn sàng. '
            'Hãy kiểm tra torch.cuda.is_available() trong Python 3.12.'
        )

    device = 'cuda' if cuda_ready else 'cpu'
    backend = 'pytorch' if cuda_ready else 'onnx'
    batch_size = max(1, min(8, int(max_batch_size or 8)))
    cache_key = f'{device}|{backend}|batch={batch_size}'

    model = VIENEU_MODEL_CACHE.get(cache_key)
    if model is None:
        if log_callback:
            log_callback(
                'VieNeu: đang nạp model '
                f'({"GPU/CUDA" if cuda_ready else "CPU/ONNX"})...'
            )
        model = Vieneu(
            mode='v3turbo',
            device=device,
            backend=backend,
            max_batch_size=batch_size
        )
        VIENEU_MODEL_CACHE[cache_key] = model
        if log_callback:
            log_callback(
                'VieNeu: model đã sẵn sàng '
                f'(backend={getattr(model, "backend", backend)}, device={device}).'
            )
    elif log_callback:
        log_callback('VieNeu: dùng model đã nạp sẵn.')

    return model

def _safe_audio_dbfs(audio, fallback=-60.0):
    try:
        dbfs = float(audio.dBFS)
        if dbfs == float('-inf') or np.isnan(dbfs):
            return fallback
        return dbfs
    except Exception:
        return fallback

def _vieneu_ref_cache_path(ref_audio, slot='main'):
    ref_audio = os.path.abspath(str(ref_audio or '').strip())
    slot = str(slot or 'main')
    try:
        stat = os.stat(ref_audio)
        raw_key = (
            f'{ref_audio}|{stat.st_size}|{getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1000))}|'
            f'{VIENEU_REF_CACHE_VERSION}|{VIENEU_REF_TARGET_MS}|{slot}'
        )
    except Exception:
        raw_key = f'{ref_audio}|{VIENEU_REF_CACHE_VERSION}|{VIENEU_REF_TARGET_MS}|{slot}'
    digest = hashlib.sha1(raw_key.encode('utf-8', errors='ignore')).hexdigest()[:20]
    cache_dir = os.path.join(_APP_DIR, '.vieneu_ref_cache')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f'{digest}.wav')

def _trim_vieneu_reference_window(window, intervals, base_start=0):
    local_intervals = [
        (
            max(0, item_start - base_start),
            min(len(window), item_end - base_start)
        )
        for item_start, item_end in intervals
        if min(item_end, base_start + len(window)) > max(item_start, base_start)
    ]
    if not local_intervals:
        return window

    trim_start = max(0, local_intervals[0][0] - 120)
    trim_end = min(len(window), local_intervals[-1][1] + 180)
    trimmed = window[trim_start:trim_end]
    return trimmed if len(trimmed) >= 2500 else window

def _score_vieneu_reference_window(audio, intervals, start, target_ms):
    end = min(len(audio), start + target_ms)
    window_ms = max(1, end - start)
    window = audio[start:end]
    voiced_ms = sum(
        max(0, min(item_end, end) - max(item_start, start))
        for item_start, item_end in intervals
    )
    coverage = voiced_ms / window_ms
    window_dbfs = _safe_audio_dbfs(window)
    try:
        peak_dbfs = float(window.max_dBFS)
        if peak_dbfs == float('-inf') or np.isnan(peak_dbfs):
            peak_dbfs = -60.0
    except Exception:
        peak_dbfs = -60.0

    # Prefer clear, energetic speech windows over long but weak/flat regions.
    return (
        voiced_ms
        + coverage * 1800.0
        + (window_dbfs + 60.0) * 45.0
        + (peak_dbfs + 24.0) * 18.0
    )

def _select_vieneu_reference_windows(
    audio,
    target_ms=VIENEU_REF_TARGET_MS,
    max_windows=VIENEU_REF_MAX_WINDOWS
):
    if audio is None or len(audio) <= 0:
        return [AudioSegment.silent(duration=0)]

    target_ms = max(2500, int(target_ms or VIENEU_REF_TARGET_MS))
    max_windows = max(1, int(max_windows or 1))
    if len(audio) <= target_ms:
        return [audio]

    base_dbfs = _safe_audio_dbfs(audio)
    silence_thresh = max(-50.0, min(-30.0, base_dbfs - 16.0))
    try:
        intervals = detect_nonsilent(
            audio,
            min_silence_len=260,
            silence_thresh=silence_thresh,
            seek_step=20
        )
    except Exception:
        intervals = []

    intervals = [
        (max(0, int(start)), min(len(audio), int(end)))
        for start, end in intervals
        if int(end) - int(start) >= 180
    ]
    if not intervals:
        return [audio[:target_ms]]

    candidate_starts = {0}
    for start, _end in intervals:
        candidate_starts.add(max(0, start - 180))

    ranked = []
    for start in sorted(candidate_starts):
        ranked.append(
            (
                _score_vieneu_reference_window(audio, intervals, start, target_ms),
                start
            )
        )
    ranked.sort(reverse=True)

    selected = []
    selected_starts = []
    min_distance = int(target_ms * 0.55)
    for _score, start in ranked:
        if any(abs(start - old_start) < min_distance for old_start in selected_starts):
            continue
        end = min(len(audio), start + target_ms)
        window = _trim_vieneu_reference_window(audio[start:end], intervals, start)
        if len(window) > target_ms:
            window = window[:target_ms]
        if len(window) >= 1200:
            selected.append(window)
            selected_starts.append(start)
        if len(selected) >= max_windows:
            break

    if not selected:
        selected = [_trim_vieneu_reference_window(audio[:target_ms], intervals, 0)]
    return selected

def _select_vieneu_reference_window(audio, target_ms=VIENEU_REF_TARGET_MS):
    windows = _select_vieneu_reference_windows(
        audio,
        target_ms=target_ms,
        max_windows=1
    )
    window = windows[0] if windows else AudioSegment.silent(duration=0)
    if len(window) > target_ms:
        window = window[:target_ms]
    return window

def _normalize_vieneu_reference_segment(selected):
    selected = selected.set_channels(1)
    dbfs = _safe_audio_dbfs(selected)
    if dbfs > -60.0:
        gain = max(-12.0, min(12.0, -18.5 - dbfs))
        selected = selected.apply_gain(gain)
        try:
            if selected.max_dBFS > -1.4:
                selected = selected.apply_gain(-1.4 - selected.max_dBFS)
        except Exception:
            pass
    return selected.set_frame_rate(44100).set_sample_width(2)

def _load_vieneu_reference_audiosegment(ref_audio):
    try:
        return load_audiosegment_with_ffmpeg(ref_audio)
    except Exception:
        decoded_path = _vieneu_ref_cache_path(ref_audio, slot='decoded')
        if not os.path.isfile(decoded_path):
            cmd = [
                _ffmpeg_exe,
                '-y',
                '-hide_banner',
                '-loglevel',
                'error',
                '-i',
                ref_audio,
                '-vn',
                '-ac',
                '1',
                '-ar',
                '44100',
                '-sample_fmt',
                's16',
                decoded_path
            ]
            result = _run_ffmpeg_command(cmd, timeout=120)
            if (
                result.returncode != 0
                or not os.path.exists(decoded_path)
                or os.path.getsize(decoded_path) <= 0
            ):
                raise RuntimeError(
                    'Không decode được audio mẫu bằng ffmpeg: '
                    f'{result.stderr or result.stdout or "unknown error"}'
                )
        return AudioSegment.from_wav(decoded_path)

def _prepare_vieneu_ref_audio_candidates(ref_audio, log_callback=None):
    ref_audio = str(ref_audio or '').strip()
    if not ref_audio or not os.path.isfile(ref_audio):
        return [ref_audio] if ref_audio else []

    cached_paths = [
        _vieneu_ref_cache_path(ref_audio, slot=f'win{i + 1}')
        for i in range(VIENEU_REF_MAX_WINDOWS)
    ]
    existing = [path for path in cached_paths if os.path.isfile(path)]
    if existing:
        return existing

    try:
        source = _load_vieneu_reference_audiosegment(ref_audio)
        source = source.set_channels(1)
        selected_windows = _select_vieneu_reference_windows(source)
        out_paths = []
        for index, selected in enumerate(selected_windows[:VIENEU_REF_MAX_WINDOWS]):
            if len(selected) < 1200:
                continue
            cache_path = cached_paths[index]
            selected = _normalize_vieneu_reference_segment(selected)
            selected.export(cache_path, format='wav')
            out_paths.append(cache_path)

        if not out_paths:
            return [ref_audio]

        if log_callback:
            log_callback(
                'VieNeu clone: đã chọn/chuẩn hóa '
                f'{len(out_paths)} đoạn mẫu để lấy embedding giọng có lực hơn.'
            )
        return out_paths
    except Exception as error:
        if log_callback:
            log_callback(
                'VieNeu clone: không chuẩn hóa được audio mẫu, dùng file gốc. '
                f'Lý do: {error}'
            )
        return [ref_audio]

def _prepare_vieneu_ref_audio_for_clone(ref_audio, log_callback=None):
    candidates = _prepare_vieneu_ref_audio_candidates(
        ref_audio,
        log_callback=log_callback
    )
    return candidates[0] if candidates else ref_audio

def _get_vieneu_clone_voice(model, ref_audio, log_callback=None):
    prepared_ref_audios = _prepare_vieneu_ref_audio_candidates(
        ref_audio,
        log_callback=log_callback
    )
    if not prepared_ref_audios:
        prepared_ref_audios = [ref_audio]
    primary_ref_audio = prepared_ref_audios[0]
    try:
        stat = os.stat(ref_audio)
        key = (
            os.path.abspath(ref_audio),
            stat.st_size,
            getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1000)),
            tuple(os.path.abspath(path) for path in prepared_ref_audios),
            str(getattr(model, 'backend', '')),
            VIENEU_CLONE_CACHE_VERSION
        )
    except Exception:
        key = (
            os.path.abspath(ref_audio),
            tuple(os.path.abspath(path) for path in prepared_ref_audios),
            str(getattr(model, 'backend', '')),
            VIENEU_CLONE_CACHE_VERSION
        )

    cached_voice = VIENEU_REF_VOICE_CACHE.get(key)
    if cached_voice is not None:
        if log_callback:
            log_callback('VieNeu clone: dùng embedding giọng đã cache.')
        return cached_voice, primary_ref_audio

    if log_callback:
        log_callback('VieNeu clone: đang enroll audio mẫu thành speaker embedding...')

    started_at = time.time()
    speaker_embs = []
    speaker_norms = []
    ref_codes = None
    for prepared_ref_audio in prepared_ref_audios:
        try:
            speaker_emb, candidate_codes = model.encode_reference(
                prepared_ref_audio,
                denoise=False
            )
        except TypeError:
            speaker_emb, candidate_codes = model.encode_reference(
                prepared_ref_audio
            )
        speaker_emb = np.asarray(speaker_emb, dtype=np.float32)
        norm = float(np.linalg.norm(speaker_emb))
        if norm > 1e-6:
            speaker_embs.append(speaker_emb)
            speaker_norms.append(norm)
        if ref_codes is None and candidate_codes is not None:
            ref_codes = candidate_codes

    if not speaker_embs:
        raise RuntimeError('VieNeu clone: không tạo được speaker embedding từ audio mẫu.')

    speaker_emb = np.mean(np.stack(speaker_embs, axis=0), axis=0).astype(np.float32)
    target_norm = float(np.median(speaker_norms)) if speaker_norms else 0.0
    current_norm = float(np.linalg.norm(speaker_emb))
    if target_norm > 1e-6 and current_norm > 1e-6:
        speaker_emb = speaker_emb * (target_norm / current_norm)

    clone_voice = {
        'speaker_emb': np.asarray(speaker_emb, dtype=np.float32),
        'codes': (
            None
            if ref_codes is None
            else np.asarray(ref_codes, dtype=np.int64)
        ),
        'style': VIENEU_CLONE_STYLE
    }
    VIENEU_REF_VOICE_CACHE[key] = clone_voice
    if log_callback:
        log_callback(
            'VieNeu clone: enroll xong '
            f'{len(speaker_embs)} đoạn sau {time.time() - started_at:.1f}s.'
        )
    return clone_voice, primary_ref_audio

def text_to_speech_vieneu_batch(
    texts,
    voice='Phạm Tuyên',
    use_gpu=True,
    batch_size=8,
    log_callback=None,
    max_retries=3
):
    texts = [sanitize_vieneu_text(text) for text in texts]
    if not texts or any(not text for text in texts):
        raise ValueError('Văn bản VieNeu không được để trống.')

    voice_config = parse_vieneu_voice_config(voice)
    ref_audio = str(voice_config.get('ref_audio') or '').strip()
    if not ref_audio:
        raise RuntimeError(
            'VieNeu hiện chỉ dùng giọng clone. '
            'Hãy bấm "Chọn audio mẫu clone" trước khi nghe thử hoặc render.'
        )
    if not os.path.isfile(ref_audio):
        raise RuntimeError(f'Không tìm thấy audio mẫu VieNeu:\n{ref_audio}')

    model = _load_vieneu_model(
        use_gpu=use_gpu,
        max_batch_size=batch_size,
        log_callback=log_callback
    )
    batch_size = max(1, min(8, int(batch_size or 8)))
    clone_voice, active_ref_audio = _get_vieneu_clone_voice(
        model,
        ref_audio,
        log_callback=log_callback
    )

    if log_callback:
        if ref_audio:
            log_callback(
                'VieNeu local: chỉ dùng GIỌNG CLONE từ audio mẫu; tạo '
                f'{len(texts)} đoạn, batch={batch_size}. '
                f'Mẫu: {os.path.basename(ref_audio)}, style={VIENEU_CLONE_STYLE}.'
            )
            if active_ref_audio != ref_audio:
                log_callback(
                    'VieNeu clone: đang dùng bản mẫu đã lọc cho embedding '
                    f'({os.path.basename(active_ref_audio)}).'
                )

    infer_kwargs = {
        'voice': clone_voice,
        'style': VIENEU_CLONE_STYLE,
        'batch_size': batch_size,
        'apply_watermark': False,
        'temperature': 0.75,
        'top_k': 25,
        'top_p': 0.95,
        'repetition_penalty': 1.2,
        'max_chars': 180,
        'max_new_frames': 420,
        'silence_p': 0.18,
        'crossfade_p': 0.0,
        'use_ref_codes': True
    }

    last_error = None
    attempts = max(1, int(max_retries or 1))
    for attempt in range(1, attempts + 1):
        try:
            current_batch_size = batch_size
            if attempt >= 2:
                current_batch_size = max(1, min(batch_size, batch_size // 2 or 1))
            if attempt >= 3:
                current_batch_size = 1
            infer_kwargs['batch_size'] = current_batch_size
            if attempt >= 2:
                infer_kwargs['temperature'] = 0.65
                infer_kwargs['top_p'] = 0.92
                infer_kwargs['repetition_penalty'] = 1.25
            if log_callback and attempt > 1:
                log_callback(
                    'VieNeu: thử tạo lại '
                    f'lần {attempt}/{attempts}, batch={current_batch_size}.'
                )
                try:
                    import torch
                    if hasattr(torch, 'cuda') and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass
                time.sleep(min(2.0, 0.5 * attempt))
            audios = model.infer_batch(texts, **infer_kwargs)
            break
        except Exception as error:
            last_error = error
            if log_callback:
                log_callback(
                    'VieNeu tạo batch lỗi '
                    f'lần {attempt}/{attempts}: {error}'
                )
            if attempt >= attempts:
                raise RuntimeError(
                    f'VieNeu tạo batch thất bại sau {attempts} lần: {last_error}'
                ) from error

    if audios is None or len(audios) != len(texts):
        raise RuntimeError('VieNeu không trả đủ dữ liệu audio.')

    if log_callback:
        log_callback(f'VieNeu local: tạo xong {len(audios)} đoạn.')

    return [
        _numpy_audio_to_segment(audio, VIENEU_SAMPLE_RATE)
        for audio in audios
    ]

def text_to_speech_vieneu(text, voice='Phạm Tuyên', use_gpu=True, batch_size=8, log_callback=None, max_retries=3):
    audios = text_to_speech_vieneu_batch(
        [text],
        voice=voice,
        use_gpu=use_gpu,
        batch_size=batch_size,
        log_callback=log_callback,
        max_retries=max_retries
    )
    return audios[0]

def sanitize_vbee_text(text):
    text = str(text or '').replace('\ufeff', '').strip()
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\{[^}]+\}', ' ', text)
    text = re.sub(r'\[[^\]]+\]', ' ', text)
    text = text.replace('|', ' ')
    text = ''.join(
        ch
        for ch in text
        if ch in '\n\r\t '
        or ch.isalnum()
        or ch in '.,!?;:()/%+-"\'…'
        or '\u00c0' <= ch <= '\u1ef9'
    )
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def sanitize_vieneu_text(text):
    text = str(text or '').replace('\ufeff', '').strip()
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\{[^}]+\}', ' ', text)
    text = re.sub(r'\[[^\]]+\]', ' ', text)
    text = text.replace('|', ' ')
    text = ''.join(
        ch
        for ch in text
        if ch in '\n\r\t '
        or ch.isalnum()
        or ch in '.,!?;:()/%+-"\'…'
        or '\u00c0' <= ch <= '\u1ef9'
    )
    text = re.sub(r'\s+', ' ', text).strip()
    if text and text[-1] not in '.!?…。！？':
        text += '.'
    return text

def _tts_cache_dir(output_path):
    base = os.path.splitext(os.path.abspath(output_path or 'autotts_output'))[0]
    cache_dir = f'{base}_tts_cache'
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def _tts_srt_cache_dir(srt_signature):
    if not srt_signature:
        return None
    cache_dir = os.path.join(
        _APP_DIR,
        '.tts_srt_cache',
        str(srt_signature)[:2],
        str(srt_signature)
    )
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def _normalize_srt_cache_text(text):
    text = str(text or '').replace('\ufeff', ' ')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return re.sub(r'\s+', ' ', text).strip()

def build_srt_cache_signature(subs):
    digest = hashlib.sha1()
    digest.update(SRT_TTS_CACHE_VERSION.encode('utf-8'))
    count = 0
    for sub in subs or []:
        try:
            start_ms = srt_time_to_ms(sub.start)
            end_ms = srt_time_to_ms(sub.end)
            text = _normalize_srt_cache_text(getattr(sub, 'text', ''))
        except Exception:
            continue
        digest.update(
            f'{count}|{start_ms}|{end_ms}|{text}\n'.encode(
                'utf-8',
                errors='ignore'
            )
        )
        count += 1
    digest.update(f'count={count}'.encode('utf-8'))
    return digest.hexdigest()[:24]

def _tts_cache_path(cache_dir, provider, voice, sub_index, text):
    digest = hashlib.sha1(
        f'{provider}|{voice}|{sub_index}|{text}'.encode(
            'utf-8',
            errors='ignore'
        )
    ).hexdigest()[:16]
    return os.path.join(
        cache_dir,
        f'{sub_index + 1:05d}_{provider}_{digest}.wav'
    )

def build_tts_cache_voice_key(provider, voice):
    if provider == 'vieneu':
        data = parse_vieneu_voice_config(voice)
        ref_audio = str(data.get('ref_audio') or '').strip()
        if ref_audio:
            try:
                stat = os.stat(ref_audio)
                ref_key = (
                    f'{os.path.abspath(ref_audio)}|'
                    f'{stat.st_size}|{int(stat.st_mtime)}'
                )
            except Exception:
                ref_key = os.path.abspath(ref_audio)
            return f'{VIENEU_TTS_CACHE_VERSION}|style={VIENEU_CLONE_STYLE}|{ref_key}'
        return f'{VIENEU_TTS_CACHE_VERSION}|style={VIENEU_CLONE_STYLE}|missing_ref_audio'

    if provider == 'omnivoice':
        data = parse_omnivoice_voice_config(voice)
        ref_audio = str(data.get('ref_audio') or '').strip()
        if ref_audio:
            try:
                stat = os.stat(ref_audio)
                ref_key = (
                    f'{os.path.abspath(ref_audio)}|'
                    f'{stat.st_size}|{int(stat.st_mtime)}'
                )
            except Exception:
                ref_key = os.path.abspath(ref_audio)
            return f'omni_clone|{ref_key}|{data.get("ref_text", "")}'
        return f'omni_preset|{data.get("instruct", "")}'

    return voice

def _load_cached_tts_audio(cache_path):
    if (
        cache_path
        and os.path.exists(cache_path)
        and os.path.getsize(cache_path) > 0
    ):
        return AudioSegment.from_file(cache_path)
    return None

def _save_cached_tts_audio(audio, cache_path):
    if audio is None or not cache_path:
        return
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    temp_path = f'{cache_path}.tmp.wav'
    audio.export(temp_path, format='wav')
    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
        shutil.move(temp_path, cache_path)

def _copy_cached_tts_audio_file(src_path, dst_path):
    if (
        not src_path
        or not dst_path
        or not os.path.exists(src_path)
        or os.path.getsize(src_path) <= 0
    ):
        return False
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    temp_path = f'{dst_path}.tmp.wav'
    shutil.copyfile(src_path, temp_path)
    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
        shutil.move(temp_path, dst_path)
        return True
    return False

def _legacy_tts_cache_candidates(cache_dir, provider, sub_index):
    if not cache_dir or not os.path.isdir(cache_dir):
        return []
    safe_provider = re.sub(r'[^a-zA-Z0-9_-]+', '_', str(provider or 'tts'))
    prefix = f'{int(sub_index) + 1:05d}_{safe_provider}_'
    try:
        paths = [
            os.path.join(cache_dir, name)
            for name in os.listdir(cache_dir)
            if name.startswith(prefix) and name.lower().endswith('.wav')
        ]
        paths = [
            path for path in paths
            if os.path.isfile(path) and os.path.getsize(path) > 0
        ]
        return sorted(
            paths,
            key=lambda path: os.path.getmtime(path),
            reverse=True
        )
    except Exception:
        return []

def estimate_tts_min_duration_ms(text, expected_min_ms=None):
    clean = re.sub(r'\s+', ' ', str(text or '')).strip()
    if not clean:
        return 250

    # A real spoken segment should not be only a tiny click/silence.
    word_count = len(clean.split())
    short_floor_ms = 300 if len(clean) <= 8 or word_count <= 2 else 450
    char_based_ms = min(8000, max(short_floor_ms, len(clean) * 18))
    word_based_ms = min(8000, max(short_floor_ms, word_count * 170))
    min_ms = max(char_based_ms, word_based_ms)
    if expected_min_ms:
        min_ms = max(min_ms, int(expected_min_ms))
    return int(min_ms)

def estimate_tts_max_duration_ms(text):
    clean = re.sub(r'\s+', ' ', str(text or '')).strip()
    if not clean:
        return 1200

    words = clean.split()
    word_count = len(words)
    char_count = len(clean)
    # Upper bound for short review-style Vietnamese narration. VieNeu can
    # sometimes repeat a short sentence to fill time; catch that early.
    if word_count <= 3:
        floor_ms = 1150
        char_based_ms = char_count * 55
        word_based_ms = word_count * 390
    elif word_count <= 5:
        floor_ms = 1450
        char_based_ms = char_count * 58
        word_based_ms = word_count * 420
    else:
        floor_ms = 1900
        char_based_ms = char_count * 62
        word_based_ms = word_count * 470
    comma_pause_ms = clean.count(',') * 180 + clean.count(';') * 220
    sentence_pause_ms = len(re.findall(r'[.!?…]+', clean)) * 220
    return int(max(floor_ms, char_based_ms, word_based_ms) + comma_pause_ms + sentence_pause_ms)

def detect_overlong_tts_audio(audio, text='', label='audio'):
    if audio is None or len(audio) <= 0:
        return None

    clean = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(clean) < 2:
        return None

    max_ms = estimate_tts_max_duration_ms(clean)
    # Avoid false positives on long, naturally slow paragraphs.
    hard_limit_ms = max_ms if len(clean) <= 90 else int(max_ms * 1.25)
    if len(audio) <= hard_limit_ms:
        return None

    return (
        f'{label}: audio dài bất thường so với câu '
        f'({len(audio) / 1000:.2f}s > mức hợp lý {hard_limit_ms / 1000:.2f}s), '
        'nghi TTS tự lặp/kéo câu.'
    )

def pad_short_tts_audio(audio, text='', label='audio', log_callback=None):
    # Đoạn ngắn nhưng có âm vẫn hợp lệ; timeline sẽ tự co/giãn video theo độ dài thật.
    return audio

def validate_tts_audio(
    audio,
    text='',
    label='audio',
    expected_min_ms=None,
    expected_max_ms=None
):
    if audio is None:
        return f'{label}: không có audio.'
    if len(audio) <= 0:
        return f'{label}: audio rỗng.'

    if expected_min_ms:
        min_ms = estimate_tts_min_duration_ms(text, expected_min_ms)
        if len(audio) < min_ms:
            return (
                f'{label}: audio quá ngắn ({len(audio) / 1000:.2f}s, '
                f'cần tối thiểu khoảng {min_ms / 1000:.2f}s).'
            )

    if expected_max_ms:
        max_ms = max(1, int(expected_max_ms))
        if len(audio) > max_ms:
            return (
                f'{label}: audio dài hơn timeline '
                f'({len(audio) / 1000:.2f}s > {max_ms / 1000:.2f}s), '
                'nghi TTS kéo/lặp câu.'
            )

    try:
        if audio.max_dBFS == float('-inf') or audio.max_dBFS < -45:
            return f'{label}: audio gần như im lặng (max {audio.max_dBFS:.1f} dBFS).'
    except Exception:
        pass

    overlong_reason = detect_overlong_tts_audio(audio, text=text, label=label)
    if overlong_reason:
        return overlong_reason

    repeat_reason = detect_repeated_tts_audio(audio, text=text, label=label)
    if repeat_reason:
        return repeat_reason

    return None

def detect_repeated_tts_audio(audio, text='', label='audio'):
    if audio is None or len(audio) < 1800:
        return None

    clean_text = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(clean_text) < 6:
        return None

    try:
        sample = audio.set_channels(1).set_frame_rate(16000)
        raw = np.array(sample.get_array_of_samples()).astype(np.float32)
        if raw.size < 16000:
            return None

        peak = float(np.max(np.abs(raw))) if raw.size else 0.0
        if peak <= 1.0:
            return None
        raw = raw / peak

        frame = int(0.12 * 16000)
        energies = []
        for start in range(0, max(0, raw.size - frame + 1), frame):
            chunk = raw[start:start + frame]
            if chunk.size:
                energies.append(float(np.sqrt(np.mean(chunk * chunk))))
        if len(energies) < 14:
            return None

        arr = np.array(energies, dtype=np.float32)
        active = arr[arr > max(0.015, float(np.percentile(arr, 35)))]
        if active.size < 8:
            return None

        max_lag = min(int(1.8 * 16000), raw.size // 2)
        min_lag = min(int(0.45 * 16000), max_lag)
        if max_lag > min_lag:
            step = int(0.05 * 16000)
            best_similarity = 0.0
            best_lag = 0
            for lag in range(min_lag, max_lag + 1, max(1, step)):
                a = raw[:-lag]
                b = raw[lag:]
                repeat_count = raw.size / max(float(lag), 1.0)
                if repeat_count < 2.6:
                    continue
                denom = (float(np.linalg.norm(a)) * float(np.linalg.norm(b))) + 1e-6
                similarity = float(np.dot(a, b) / denom)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_lag = lag

            if best_similarity >= 0.82:
                return (
                    f'{label}: nghi audio bị lặp theo chu kỳ '
                    f'{best_lag / 16000:.1f}s (độ giống {best_similarity:.2f}).'
                )

        norm = arr - float(np.mean(arr))
        std = float(np.std(norm))
        if std < 1e-4:
            return None
        norm = norm / std

        suspicious_hits = []
        # Windows from 0.6s to 1.44s catch common TTS stuck/repeated phrases.
        for win in range(5, 13):
            for i in range(0, len(norm) - (win * 2) + 1):
                a = norm[i:i + win]
                b = norm[i + win:i + win * 2]
                denom = (float(np.linalg.norm(a)) * float(np.linalg.norm(b))) + 1e-6
                similarity = float(np.dot(a, b) / denom)
                if similarity < 0.97:
                    continue
                loud_a = float(np.mean(arr[i:i + win]))
                loud_b = float(np.mean(arr[i + win:i + win * 2]))
                if max(loud_a, loud_b) < 0.018:
                    continue
                suspicious_hits.append((i, win, similarity))
                break

        if len(suspicious_hits) >= 3:
            start_frame, win, similarity = suspicious_hits[0]
            start_s = start_frame * 0.12
            span_s = win * 0.12
            return (
                f'{label}: nghi audio bị lặp đoạn quanh {start_s:.1f}s '
                f'(chu kỳ khoảng {span_s:.1f}s, độ giống {similarity:.2f}).'
            )
    except Exception:
        return None

    return None

def get_valid_cached_tts_audio(
    cache_path,
    text='',
    label='cache',
    expected_min_ms=None,
    expected_max_ms=None,
    log_callback=None
):
    cached_audio = _load_cached_tts_audio(cache_path)
    if cached_audio is None:
        return None

    bad_reason = validate_tts_audio(
        cached_audio,
        text=text,
        label=label,
        expected_min_ms=expected_min_ms,
        expected_max_ms=expected_max_ms
    )
    if not bad_reason:
        return cached_audio

    if log_callback:
        log_callback(f'Bỏ cache TTS lỗi: {bad_reason}')
    try:
        os.remove(cache_path)
    except Exception:
        pass
    return None

def ensure_valid_tts_audio(
    audio,
    text='',
    label='audio',
    expected_min_ms=None,
    expected_max_ms=None
):
    bad_reason = validate_tts_audio(
        audio,
        text=text,
        label=label,
        expected_min_ms=expected_min_ms,
        expected_max_ms=expected_max_ms
    )
    if bad_reason:
        raise RuntimeError(bad_reason)
    return audio

def is_usable_tts_audio(audio):
    if audio is None or len(audio) <= 0:
        return False
    try:
        if audio.max_dBFS == float('-inf') or audio.max_dBFS < -45:
            return False
    except Exception:
        pass
    return True

def smooth_tts_segment(
    audio,
    fade_ms=35,
    pad_ms=20,
    tail_pad_ms=80,
    fade_in_ms=None,
    fade_out_ms=None
):
    if audio is None or len(audio) <= 0:
        return AudioSegment.silent(duration=0)

    if fade_in_ms is None:
        fade_in_ms = fade_ms
    if fade_out_ms is None:
        fade_out_ms = fade_ms
    fade_in_ms = max(0, min(int(fade_in_ms), max(1, len(audio) // 3)))
    fade_out_ms = max(0, min(int(fade_out_ms), max(1, len(audio) // 3)))
    pad_ms = max(0, int(pad_ms))
    tail_pad_ms = max(0, int(tail_pad_ms))
    out = audio

    if pad_ms:
        out = (
            AudioSegment.silent(duration=pad_ms)
            + out
            + AudioSegment.silent(duration=max(pad_ms, tail_pad_ms))
        )

    if fade_in_ms:
        out = out.fade_in(fade_in_ms)
    if fade_out_ms:
        out = out.fade_out(fade_out_ms)

    return out

def _limit_audio_peak(audio, target_peak_dbfs=-1.2):
    try:
        if audio.max_dBFS != float('-inf') and audio.max_dBFS > target_peak_dbfs:
            return audio.apply_gain(target_peak_dbfs - audio.max_dBFS)
    except Exception:
        pass
    return audio

def strengthen_vieneu_voice_body(audio, target_dbfs=-17.8):
    if audio is None or len(audio) <= 0:
        return AudioSegment.silent(duration=0)

    out = audio
    try:
        out = out.set_channels(1)
    except Exception:
        pass

    try:
        body = out.high_pass_filter(85).low_pass_filter(420).apply_gain(-5.0)
        chest = out.high_pass_filter(70).low_pass_filter(210).apply_gain(-9.0)
        presence = out.high_pass_filter(1600).low_pass_filter(4200).apply_gain(-10.0)
        out = out.overlay(body).overlay(chest).overlay(presence)
    except Exception:
        pass

    try:
        out = out.compress_dynamic_range(
            threshold=-24.0,
            ratio=1.45,
            attack=4,
            release=90
        )
    except Exception:
        pass

    try:
        if out.dBFS != float('-inf'):
            gain = max(-4.0, min(7.0, float(target_dbfs) - out.dBFS))
            out = out.apply_gain(gain)
    except Exception:
        pass

    return _limit_audio_peak(out, target_peak_dbfs=-1.2)

def clarify_vieneu_segment(audio, label='VieNeu', log_callback=None):
    if audio is None or len(audio) <= 0:
        return AudioSegment.silent(duration=0)

    out = audio
    try:
        if out.channels != 1:
            out = out.set_channels(1)
    except Exception:
        pass

    try:
        if out.dBFS != float('-inf') and out.dBFS < -26.0:
            gain = min(6.0, -22.0 - out.dBFS)
            out = out.apply_gain(gain)
            if log_callback:
                log_callback(
                    f'{label}: tăng âm đoạn nhỏ thêm {gain:.1f} dB để rõ chữ.'
                )
    except Exception:
        pass

    out = strengthen_vieneu_voice_body(out)

    # Giữ fade rất ngắn để không ăn chữ.
    return smooth_tts_segment(
        out,
        fade_ms=5,
        pad_ms=8,
        tail_pad_ms=35,
        fade_in_ms=2,
        fade_out_ms=8
    )

def ffmpeg_polish_voice_segment(audio):
    if audio is None or len(audio) <= 0:
        return AudioSegment.silent(duration=0)

    temp_in = (
        f'_voice_polish_in_{os.getpid()}_'
        f'{threading.get_ident()}_{random.randint(1000, 9999)}.wav'
    )
    temp_out = (
        f'_voice_polish_out_{os.getpid()}_'
        f'{threading.get_ident()}_{random.randint(1000, 9999)}.wav'
    )

    try:
        audio.export(temp_in, format='wav')
        filters = (
            'highpass=f=70,'
            'dynaudnorm=f=180:g=6:p=0.80:m=6,'
            'acompressor=threshold=-24dB:ratio=2.4:attack=4:release=120:makeup=1.5dB,'
            'loudnorm=I=-17:TP=-1.2:LRA=6,'
            'alimiter=limit=0.97'
        )
        cmd = [
            _ffmpeg_exe,
            '-y',
            '-i',
            temp_in,
            '-af',
            filters,
            temp_out
        ]
        result = _run_ffmpeg_command(cmd, timeout=60)
        if (
            result.returncode == 0
            and os.path.exists(temp_out)
            and os.path.getsize(temp_out) > 0
        ):
            return AudioSegment.from_file(temp_out)
    except Exception:
        pass
    finally:
        for path in (temp_in, temp_out):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    return audio

def polish_omnivoice_segment(audio):
    if audio is None or len(audio) <= 0:
        return AudioSegment.silent(duration=0)

    out = ffmpeg_polish_voice_segment(audio)
    try:
        if out.dBFS != float('-inf'):
            target_dbfs = -17.0
            gain = max(-6.0, min(6.0, target_dbfs - out.dBFS))
            out = out.apply_gain(gain)
    except Exception:
        pass

    try:
        out = out.compress_dynamic_range(
            threshold=-25.0,
            ratio=2.6,
            attack=5,
            release=100
        )
    except Exception:
        pass

    out = smooth_tts_segment(
        out,
        fade_ms=45,
        pad_ms=35,
        tail_pad_ms=160,
        fade_in_ms=4,
        fade_out_ms=45
    )
    try:
        if out.dBFS != float('-inf'):
            final_gain = max(-3.0, min(8.0, -18.0 - out.dBFS))
            out = out.apply_gain(final_gain)
    except Exception:
        pass

    return out

def append_tts_segment(base_audio, segment, provider=''):
    if segment is None or len(segment) <= 0:
        return base_audio

    if (
        provider == 'omnivoice'
        and base_audio is not None
        and len(base_audio) > 0
    ):
        crossfade_ms = min(8, len(base_audio) // 4, len(segment) // 4)
        if crossfade_ms > 0:
            try:
                return base_audio.append(segment, crossfade=crossfade_ms)
            except Exception:
                pass

    return base_audio + segment

def overlay_audio_extending(base_audio, overlay_audio, position=0):
    position = max(0, int(position))
    if overlay_audio is None or len(overlay_audio) <= 0:
        return base_audio

    needed_ms = position + len(overlay_audio)
    if len(base_audio) < needed_ms:
        base_audio += AudioSegment.silent(duration=needed_ms - len(base_audio))

    return base_audio.overlay(overlay_audio, position=position)

def limit_tts_audio_to_timeline_slot(
    audio,
    start_ms,
    end_ms,
    next_start_ms=None,
    label='audio',
    log_callback=None
):
    if audio is None or len(audio) <= 0:
        return audio

    slot_end_ms = end_ms
    if next_start_ms is not None and next_start_ms > start_ms:
        slot_end_ms = min(slot_end_ms, next_start_ms)

    max_ms = max(1, int(slot_end_ms) - int(start_ms))
    # Leave a tiny safety gap so the next sentence cannot start on top of this tail.
    max_ms = max(1, max_ms - 12)
    if len(audio) <= max_ms:
        return audio

    clipped = audio[:max_ms]
    fade_ms = min(45, max(8, len(clipped) // 8))
    try:
        clipped = clipped.fade_out(fade_ms)
    except Exception:
        pass

    if log_callback:
        log_callback(
            f'{label}: TTS dài {len(audio) / 1000:.2f}s, '
            f'ô timeline chỉ {max_ms / 1000:.2f}s; đã cắt/fade để không chồng câu sau.'
        )
    return clipped

def fit_tts_audio_to_timeline_slot(
    audio,
    start_ms,
    end_ms,
    next_start_ms=None,
    label='audio',
    log_callback=None
):
    if audio is None or len(audio) <= 0:
        return audio

    slot_end_ms = end_ms
    if next_start_ms is not None and next_start_ms > start_ms:
        slot_end_ms = min(slot_end_ms, next_start_ms)

    max_ms = max(1, int(slot_end_ms) - int(start_ms) - 12)
    if len(audio) <= max_ms:
        return audio

    speed = len(audio) / max(float(max_ms), 1.0)
    if speed <= 1.35:
        try:
            fitted = apply_audio_speed_pitch(audio, speed=speed, pitch=1.0)
            if len(fitted) <= max_ms + 12:
                if log_callback:
                    log_callback(
                        f'{label}: TTS dài hơn ô timeline '
                        f'({len(audio) / 1000:.2f}s > {max_ms / 1000:.2f}s), '
                        f'đã tăng tốc audio x{speed:.2f} để không chồng câu sau.'
                    )
                return fitted[:max_ms].fade_out(min(30, max(5, max_ms // 8)))
        except Exception:
            pass

    return limit_tts_audio_to_timeline_slot(
        audio,
        start_ms,
        end_ms,
        next_start_ms=next_start_ms,
        label=label,
        log_callback=log_callback
    )

def run_with_heartbeat(task_func, heartbeat_callback=None, heartbeat_seconds=15):
    result_box = {}
    error_box = {}

    def worker():
        try:
            result_box['value'] = task_func()
        except Exception as error:
            error_box['error'] = error

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    started_at = time.time()
    next_heartbeat = started_at + heartbeat_seconds

    while thread.is_alive():
        thread.join(timeout=0.5)
        now = time.time()
        if heartbeat_callback and now >= next_heartbeat:
            heartbeat_callback(int(now - started_at))
            next_heartbeat = now + heartbeat_seconds

    if 'error' in error_box:
        raise error_box['error']

    return result_box.get('value')

VBEE_RETRY_STATUS = {429, 500, 502, 503, 504}


def vbee_json_request(
    method,
    url,
    headers=None,
    payload=None,
    timeout=45,
    max_attempts=7
):
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            request_kwargs = {
                "headers": headers or {},
                "timeout": timeout
            }

            if payload is not None:
                request_kwargs["json"] = payload

            response = requests.request(
                method,
                url,
                **request_kwargs
            )

            content_type = response.headers.get(
                "Content-Type",
                ""
            ).lower()

            if response.status_code in VBEE_RETRY_STATUS:
                last_error = RuntimeError(
                    f"Vbee tạm lỗi HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )

            elif "json" not in content_type:
                last_error = RuntimeError(
                    "Vbee không trả JSON. "
                    f"HTTP {response.status_code}, "
                    f"Content-Type={content_type}, "
                    f"body={response.text[:300]}"
                )

            else:
                try:
                    return response, response.json()
                except ValueError as error:
                    last_error = RuntimeError(
                        "Vbee trả JSON không hợp lệ: "
                        f"{response.text[:300]}"
                    )

        except requests.RequestException as error:
            last_error = error

        if attempt >= max_attempts:
            break

        delay = min(45, 2 ** attempt) + random.uniform(0, 1.5)

        print(
            f"[VBEE RETRY] Lần {attempt}/{max_attempts} lỗi: "
            f"{last_error}. Thử lại sau {delay:.1f} giây."
        )

        time.sleep(delay)

    raise RuntimeError(
        f"Vbee vẫn lỗi sau {max_attempts} lần thử: {last_error}"
    )
def text_to_speech_vbee(
    text,
    voice_id,
    access_token,
    app_id,
    speed=1.0,
    timeout_seconds=300
):
    """
    Tạo giọng đọc bằng Vbee Create Speech API.

    Luồng:
    1. Gửi yêu cầu tạo speech.
    2. Nhận request_id.
    3. Poll Get Request đến khi SUCCESS.
    4. Tải audio_link.
    5. Trả về AudioSegment.
    """

    temp_file = None

    try:
        original_text = str(text)
        text = sanitize_vbee_text(original_text)

        if not text:
            raise ValueError(
                "Văn bản Vbee không được để trống."
            )

        if not access_token:
            raise ValueError(
                "Chưa nhập Vbee Access Token."
            )

        if not app_id:
            raise ValueError(
                "Chưa nhập Vbee App ID."
            )

        speed = round(float(speed), 1)

        if not 0.5 <= speed <= 2.0:
            raise ValueError(
                "Tốc độ Vbee phải từ 0.5 đến 2.0."
            )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        legacy_payload = {
            "app_id": app_id,
            "response_type": "indirect",
            "callback_url": "https://example.com/vbee-callback",
            "input_text": text,
            "voice_code": voice_id,
            "audio_type": "mp3",
            "bitrate": 128,
            "speed_rate": speed
        }

        # ==============================
        # BƯỚC 1: CREATE SPEECH
        # ==============================

        create_url = "https://vbee.vn/api/v1/tts"
        get_base_url = "https://vbee.vn/api/v1/tts"


        create_response, create_data = vbee_json_request(
    method="POST",
    url=create_url,
    headers=headers,
    payload=legacy_payload,
    timeout=60,
    max_attempts=7
)

        if create_response.status_code != 200:
            raise RuntimeError(
                f"Vbee Create Speech HTTP "
                f"{create_response.status_code}: "
                f"{create_data}"
            )

        if create_data.get("status") != 1:
            raise RuntimeError(
                "Vbee Create Speech thất bại: "
                f"{create_data.get('error_code', '')} "
                f"{create_data.get('error_message', '')} "
                f"| text='{text[:120]}' | voice='{voice_id}'"
            )

        create_result = create_data.get("result", {})
        request_id = create_result.get("request_id")

        if not request_id:
            raise RuntimeError(
                f"Vbee không trả request_id: {create_data}"
            )

        # ==============================
        # BƯỚC 2: POLL GET REQUEST
        # ==============================

        get_url = f"{get_base_url}/{request_id}"

        deadline = time.time() + timeout_seconds
        last_status = ""
        last_progress = 0

        while time.time() < deadline:
            get_response, get_data = vbee_json_request(
    method="GET",
    url=get_url,
    headers={
        "Authorization": f"Bearer {access_token}"
    },
    timeout=45,
    max_attempts=7
)

            if get_response.status_code != 200:
                raise RuntimeError(
                    f"Vbee Get Request HTTP "
                    f"{get_response.status_code}: "
                    f"{get_data}"
                )

            if get_data.get("status") != 1:
                raise RuntimeError(
                    "Vbee Get Request thất bại: "
                    f"{get_data.get('error_code', '')} "
                    f"{get_data.get('error_message', '')}"
                )

            result = get_data.get("result", {})

            request_status = str(
                result.get("status", "")
            ).upper()

            progress = result.get("progress", 0)

            last_status = request_status
            last_progress = progress

            print(
                f"[VBEE] Request {request_id} | "
                f"Status: {request_status} | "
                f"Progress: {progress}%"
            )

            if request_status == "SUCCESS":
                audio_link = result.get("audio_link")

                if not audio_link:
                    raise RuntimeError(
                        "Vbee báo SUCCESS nhưng không có audio_link."
                    )

                if result.get("audio_expired") is True:
                    raise RuntimeError(
                        "Audio Vbee đã hết hạn."
                    )

                break

            if request_status in {
                "FAILED",
                "FAIL",
                "ERROR",
                "CANCELLED",
                "CANCELED"
            }:
                raise RuntimeError(
                    f"Vbee xử lý thất bại. "
                    f"Trạng thái: {request_status}"
                )

            time.sleep(1.0)

        else:
            raise TimeoutError(
                "Vbee xử lý quá thời gian. "
                f"Trạng thái cuối: {last_status}, "
                f"tiến độ: {last_progress}%."
            )

        # ==============================
        # BƯỚC 3: TẢI AUDIO
        # ==============================

        audio_response = None
        last_audio_error = None

        for attempt in range(1, 6):
            try:
                audio_response = requests.get(
                    audio_link,
                    timeout=60
                )
                if audio_response.status_code == 200:
                    break
                last_audio_error = RuntimeError(
                    f'HTTP {audio_response.status_code}'
                )
            except requests.RequestException as error:
                last_audio_error = error

            if attempt < 5:
                delay = min(20, 2 ** attempt) + random.uniform(0, 1)
                print(
                    f'[VBEE RETRY] Tải audio lỗi lần '
                    f'{attempt}/5: {last_audio_error}. '
                    f'Thử lại sau {delay:.1f} giây.'
                )
                time.sleep(delay)

        if audio_response is None:
            raise RuntimeError(
                f'Không tải được audio Vbee: {last_audio_error}'
            )

        if audio_response.status_code != 200:
            raise RuntimeError(
                f"Không tải được audio Vbee. "
                f"HTTP {audio_response.status_code}"
            )

        content_type = audio_response.headers.get(
            "Content-Type",
            ""
        ).lower()

        extension = ".wav" if "wav" in content_type else ".mp3"

        temp_file = (
            f"temp_tts_vbee_"
            f"{random.randint(1000, 9999)}"
            f"{extension}"
        )

        with open(temp_file, "wb") as audio_file:
            audio_file.write(audio_response.content)

        if (
            not os.path.exists(temp_file)
            or os.path.getsize(temp_file) == 0
        ):
            raise RuntimeError(
                "File audio Vbee tải về bị rỗng."
            )

        audio = load_audiosegment_with_ffmpeg(temp_file)

        return audio

    except requests.Timeout as e:
        print("[VBEE ERROR] Request quá thời gian.")
        raise RuntimeError(
            "Vbee phản hồi quá thời gian."
        ) from e

    except requests.ConnectionError as e:
        print("[VBEE ERROR] Lỗi kết nối.")
        raise RuntimeError(
            "Không thể kết nối tới máy chủ Vbee."
        ) from e

    except Exception as e:
        print(f"[VBEE ERROR] {e}")
        raise

    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
def check_gpu_available():
    try:
        nvidia_check = subprocess.run(
            ['nvidia-smi'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        ffmpeg_check = subprocess.run(
            [_ffmpeg_exe, '-encoders'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors='replace'
        )

        has_nvenc = 'h264_nvenc' in (ffmpeg_check.stdout or '')

        if nvidia_check.returncode == 0 and has_nvenc:
            return True, 'GPU/NVENC khả dụng', 'green', True

        if nvidia_check.returncode == 0:
            return True, 'Có GPU, không NVENC', 'orange', False

        return False, 'Không có GPU', 'red', False

    except Exception:
        return False, 'Lỗi kiểm tra GPU', 'red', False
def _fmt_ffmpeg_seconds(ms):
    return f'{max(0, ms) / 1000.0:.6f}'

def _build_atempo_chain(speed):
    if not speed or abs(speed - 1.0) <= 0.000001:
        return None
    filters = []
    value = float(speed)
    while value > 2.0:
        filters.append('atempo=2.0')
        value /= 2.0
    while value < 0.5:
        filters.append('atempo=0.5')
        value /= 0.5
    filters.append(f'atempo={value:.6f}')
    return ','.join(filters)

def _run_ffmpeg_command(cmd, timeout=None):
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors='replace',
        timeout=timeout,
        startupinfo=startupinfo
    )

def _probe_media_duration_seconds(media_path):
    if not media_path or not os.path.exists(media_path):
        return None
    result = _run_ffmpeg_command([_ffmpeg_exe, '-i', media_path], timeout=30)
    text = (result.stderr or '') + '\n' + (result.stdout or '')
    match = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', text)
    if not match:
        return None
    return (
        int(match.group(1)) * 3600
        + int(match.group(2)) * 60
        + float(match.group(3))
    )

def load_audiosegment_with_ffmpeg(audio_path, log_callback=None):
    try:
        return AudioSegment.from_file(audio_path)
    except Exception as first_error:
        temp_wav = (
            f'_audio_decode_{os.getpid()}_'
            f'{threading.get_ident()}_{random.randint(1000, 9999)}.wav'
        )
        try:
            cmd = [
                _ffmpeg_exe,
                '-y',
                '-hide_banner',
                '-loglevel',
                'error',
                '-i',
                audio_path,
                '-vn',
                '-ac',
                '2',
                '-ar',
                '44100',
                '-sample_fmt',
                's16',
                temp_wav
            ]
            result = _run_ffmpeg_command(cmd, timeout=180)
            if (
                result.returncode != 0
                or not os.path.exists(temp_wav)
                or os.path.getsize(temp_wav) <= 0
            ):
                detail = (result.stderr or result.stdout or str(first_error)).strip()
                raise RuntimeError(detail or str(first_error))
            return AudioSegment.from_wav(temp_wav)
        except Exception as error:
            if log_callback:
                log_callback(f'Không decode được audio bằng ffmpeg bundled: {error}')
            raise RuntimeError(str(error)) from first_error
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

def get_audio_duration_seconds(audio_path):
    duration = _probe_media_duration_seconds(audio_path)
    if duration and duration > 0:
        return duration
    audio = load_audiosegment_with_ffmpeg(audio_path)
    return len(audio) / 1000.0 if len(audio) > 0 else None

def split_rendered_video_parts(video_path, parts=1, log_callback=None):
    try:
        parts = int(parts or 1)
    except Exception:
        parts = 1
    if parts <= 1 or not video_path or not os.path.exists(video_path):
        return []

    duration = _probe_media_duration_seconds(video_path)
    if not duration or duration <= 0:
        if log_callback:
            log_callback('Không lấy được thời lượng video để chia phần, giữ nguyên file gốc.')
        return []

    base, ext = os.path.splitext(video_path)
    ext = ext or '.mp4'
    part_duration = duration / parts
    outputs = []

    if log_callback:
        log_callback(f'Bắt đầu chia video thành {parts} phần, mỗi phần khoảng {part_duration:.2f}s.')

    for index in range(parts):
        start = part_duration * index
        out_path = f'{base}_part{index + 1:02d}of{parts:02d}{ext}'
        cmd = [
            _ffmpeg_exe,
            '-y',
            '-ss',
            f'{start:.3f}',
            '-i',
            video_path,
        ]
        if index < parts - 1:
            cmd += ['-t', f'{part_duration:.3f}']
        cmd += [
            '-c',
            'copy',
            '-avoid_negative_ts',
            'make_zero',
            out_path
        ]
        result = _run_ffmpeg_command(cmd, timeout=None)
        if result.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            outputs.append(out_path)
            if log_callback:
                log_callback(f'Đã tạo phần {index + 1}/{parts}: {out_path}')
        else:
            if log_callback:
                err = (result.stderr or '').strip().splitlines()
                log_callback(
                    f'Lỗi chia phần {index + 1}/{parts}: '
                    f'{err[-1] if err else "FFmpeg không trả về lỗi cụ thể"}'
                )
            break

    if len(outputs) != parts and log_callback:
        log_callback('Chia video chưa hoàn tất đủ phần, file video gốc vẫn được giữ nguyên.')
    return outputs

def _parse_ffmpeg_time_to_seconds(line):
    match = re.search(r'time=(\d+):(\d+):(\d+(?:\.\d+)?)', line or '')
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds

def _run_ffmpeg_command_with_progress(cmd, duration=None, progress_callback=None, log_callback=None, phase='FFmpeg/NVENC Render'):
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors='replace',
        startupinfo=startupinfo
    )
    ACTIVE_FFMPEG_PROCESSES.append(process)
    stderr_lines = []
    last_percent = -1
    last_log_time = 0

    try:
        while True:
            line = process.stderr.readline()
            if line:
                stderr_lines.append(line)
                seconds = _parse_ffmpeg_time_to_seconds(line)
                if seconds is not None and duration and duration > 0:
                    percent = max(0, min(99, int(seconds / duration * 100)))
                    if progress_callback and percent != last_percent:
                        progress_callback(percent, 100, phase)
                        last_percent = percent
                    now = time.time()
                    if log_callback and now - last_log_time >= 5:
                        speed_match = re.search(r'speed=\s*([0-9.]+x)', line)
                        speed_txt = f" | speed={speed_match.group(1)}" if speed_match else ''
                        log_callback(f'{phase} đang render: {percent}%{speed_txt}')
                        last_log_time = now
            elif process.poll() is not None:
                break

        remaining = process.stderr.read()
        if remaining:
            stderr_lines.append(remaining)
        stdout = process.stdout.read() if process.stdout else ''
        return subprocess.CompletedProcess(
            cmd,
            process.returncode,
            stdout=stdout,
            stderr=''.join(stderr_lines)
        )
    finally:
        try:
            ACTIVE_FFMPEG_PROCESSES.remove(process)
        except ValueError:
            pass

class _SimpleSrtTime:
    def __init__(self, seconds=0.0):
        total_ms = max(0, int(seconds * 1000))
        self.hours = total_ms // 3600000
        total_ms %= 3600000
        self.minutes = total_ms // 60000
        total_ms %= 60000
        self.seconds = total_ms // 1000
        self.milliseconds = total_ms % 1000

class _SimpleSub:
    def __init__(self, start_s, end_s):
        self.start = _SimpleSrtTime(start_s)
        self.end = _SimpleSrtTime(end_s)

def _escape_drawtext_text(text):
    return (
        str(text)
        .replace('\\', '\\\\')
        .replace(':', '\\:')
        .replace(',', '\\,')
        .replace(';', '\\;')
        .replace('[', '\\[')
        .replace(']', '\\]')
        .replace("'", "\\'")
        .replace('%', '\\%')
        .replace('\r', ' ')
        .replace('\n', '\\n')
    )

def _wrap_drawtext_text(text, max_chars=22):
    clean = re.sub(r'\s+', ' ', str(text or '')).strip()
    if not clean:
        return ''
    return '\n'.join(textwrap.wrap(clean, width=max(8, int(max_chars))))

def _clean_subtitle_text_for_draw(text):
    text = str(text or '').replace('\\N', '\n')
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\{[^}]+\}', ' ', text)
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
    return text

def _ffmpeg_filter_path(path):
    return (
        str(path)
        .replace('\\', '/')
        .replace(':', '\\:')
        .replace("'", "\\'")
    )

def _ffmpeg_font_file():
    for path in ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/segoeui.ttf'):
        if os.path.exists(path):
            return _ffmpeg_filter_path(path)
    return ''

def _safe_boxblur_radius(width, height, desired=20):
    # FFmpeg boxblur giới hạn radius theo kích thước vùng crop.
    # Với video yuv420p, chroma plane nhỏ hơn nên cần kẹp chặt hơn luma.
    limit = max(1, min(int(width), int(height)) // 4 - 1)
    return max(1, min(int(desired), limit))

def _probe_video_dimensions(video_path):
    width = 0
    height = 0
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if cap and cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
    except Exception:
        width = 0
        height = 0
    finally:
        if cap:
            try:
                cap.release()
            except Exception:
                pass
    return width, height

def _infer_region_coordinate_space(regions, video_width, video_height):
    if not regions or video_width <= 0 or video_height <= 0:
        return video_width, video_height

    max_x = max(max(float(x1), float(x2)) for x1, _y1, x2, _y2 in regions)
    max_y = max(max(float(y1), float(y2)) for _x1, y1, _x2, y2 in regions)
    if max_x <= video_width and max_y <= video_height:
        return video_width, video_height

    video_ratio = video_width / max(1, video_height)
    common_spaces = (
        (768, 432), (1280, 720), (1366, 768), (1600, 900),
        (1920, 1080), (2560, 1440), (3840, 2160), (720, 1280),
        (1080, 1920)
    )
    for cand_w, cand_h in common_spaces:
        if max_x <= cand_w and max_y <= cand_h:
            cand_ratio = cand_w / max(1, cand_h)
            if abs(cand_ratio - video_ratio) <= 0.08:
                return cand_w, cand_h

    return max(max_x, video_width), max(max_y, video_height)

def _normalize_ffmpeg_regions(regions, video_width, video_height):
    if not regions or video_width <= 0 or video_height <= 0:
        return []

    coord_w, coord_h = _infer_region_coordinate_space(
        regions,
        video_width,
        video_height
    )
    sx = video_width / max(1, float(coord_w))
    sy = video_height / max(1, float(coord_h))
    normalized = []

    for region in regions:
        try:
            x1, y1, x2, y2 = [float(v) for v in region]
        except Exception:
            continue

        left, right = sorted((x1 * sx, x2 * sx))
        top, bottom = sorted((y1 * sy, y2 * sy))
        left = max(0, min(video_width - 1, int(round(left))))
        top = max(0, min(video_height - 1, int(round(top))))
        right = max(0, min(video_width, int(round(right))))
        bottom = max(0, min(video_height, int(round(bottom))))
        if right > left and bottom > top:
            normalized.append((left, top, right, bottom))

    return normalized

def _default_subtitle_blur_region(video_width, video_height):
    if video_width <= 0 or video_height <= 0:
        return None
    margin_x = max(12, int(video_width * 0.06))
    bottom_margin = max(10, int(video_height * 0.055))
    band_h = max(56, int(video_height * 0.16))
    x1 = margin_x
    x2 = max(x1 + 1, video_width - margin_x)
    y2 = max(1, video_height - bottom_margin)
    y1 = max(0, y2 - band_h)
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2, y2)

def _boxblur_filter(radius):
    radius = max(1, int(radius))
    return f'boxblur=luma_radius={radius}:luma_power=1:chroma_radius={radius}:chroma_power=1'

def _effect_strength_config(strength):
    presets = {
        'Nhẹ': {'line_alpha': 0.05, 'line_step': 25, 'line_color': 'gray', 'blur_radius': 8, 'preview_blur_div': 10},
        'Vừa': {'line_alpha': 0.08, 'line_step': 22, 'line_color': 'gray', 'blur_radius': 12, 'preview_blur_div': 8},
        'Mạnh': {'line_alpha': 0.15, 'line_step': 15, 'line_color': 'white', 'blur_radius': 20, 'preview_blur_div': 5},
    }
    return presets.get(strength, presets['Nhẹ'])

def _ffmpeg_drawgrid_filter(line_mode, strength):
    cfg = _effect_strength_config(strength)
    color = cfg['line_color']
    alpha = cfg['line_alpha']
    step = cfg['line_step']
    mode = (line_mode or '').lower()
    if 'ngang' in mode:
        return f"drawgrid=w=iw:h=max(10\\,ih/{step}):t=1:c={color}@{alpha:.2f}"
    if 'dọc' in mode or 'doc' in mode:
        return f"drawgrid=w=max(10\\,iw/{step}):h=ih:t=1:c={color}@{alpha:.2f}"
    if 'lưới' in mode or 'luoi' in mode:
        return f"drawgrid=w=max(10\\,iw/{step}):h=max(10\\,ih/{step}):t=1:c={color}@{alpha:.2f}"
    return None

def _blur_strength_to_radius(value):
    try:
        value = int(value)
    except Exception:
        value = 35
    value = max(1, min(100, value))
    return max(1, int(4 + value * 0.28))

def _blur_strength_to_preview_div(value):
    try:
        value = int(value)
    except Exception:
        value = 35
    value = max(1, min(100, value))
    return max(3, int(14 - value * 0.10))

def _output_quality_height(value):
    text = str(value or '').lower()
    if '720' in text:
        return 720
    if '1080' in text:
        return 1080
    if '1440' in text or '2k' in text:
        return 1440
    if '2160' in text or '4k' in text:
        return 2160
    return None

def _ffmpeg_output_quality_filter(value):
    target_h = _output_quality_height(value)
    if not target_h:
        return None
    return f'scale=w=-2:h={target_h}:flags=lanczos'

def _pad_audio_file_to_duration(audio_path, target_duration_s, log_callback=None):
    if not audio_path or not os.path.exists(audio_path) or not target_duration_s or target_duration_s <= 0:
        return
    try:
        audio = load_audiosegment_with_ffmpeg(audio_path, log_callback=log_callback)
        target_ms = int(target_duration_s * 1000)
        if len(audio) >= target_ms:
            return
        audio += AudioSegment.silent(duration=target_ms - len(audio))
        audio.export(audio_path, format='mp3')
        if log_callback:
            log_callback(f'Đã đệm im lặng vào audio tới {target_duration_s:.2f}s để giữ đủ video.')
    except Exception as e:
        if log_callback:
            log_callback(f'Không đệm được audio im lặng: {e}')

def _mix_tts_with_vocal_reduced_video_audio(video_path, tts_audio_path, duration_s=None, log_callback=None):
    if not video_path or not os.path.exists(video_path) or not tts_audio_path or not os.path.exists(tts_audio_path):
        return tts_audio_path
    base, ext = os.path.splitext(tts_audio_path)
    mixed_path = f'{base}_mixed_effects{ext or ".mp3"}'
    bg_volume = 0.18
    tts_volume = 4.80
    fallback_tts_volume = 4.20

    # Ưu tiên TTS rõ lời: giảm rất mạnh phần giọng gốc ở center channel,
    # giữ nền nhỏ và giới hạn đỉnh âm để tránh rè.
    filter_complex = (
        '[0:a]aformat=channel_layouts=stereo,'
        'pan=stereo|c0=0.5*c0-0.5*c1|c1=0.5*c1-0.5*c0,'
        'highpass=f=80,lowpass=f=12000,'
        'dynaudnorm=f=250:g=5:p=0.85,'
        f'volume={bg_volume:.2f}[bg];'
        '[1:a]aformat=channel_layouts=stereo,'
        f'volume={tts_volume:.2f},'
        'acompressor=threshold=-14dB:ratio=1.8:attack=5:release=90,'
        'alimiter=limit=0.96,'
        'asplit=2[tts_sc][tts_mix];'
        '[bg][tts_sc]sidechaincompress=threshold=0.020:ratio=12:attack=12:release=300[ducked_bg];'
        '[ducked_bg][tts_mix]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,'
        'volume=0.90,alimiter=limit=0.96[aout]'
    )

    def build_mix_cmd(filter_text):
        cmd = [
            _ffmpeg_exe,
            '-y',
            '-i', video_path,
            '-i', tts_audio_path,
            '-filter_complex', filter_text,
            '-map', '[aout]',
            '-vn',
            '-c:a', 'libmp3lame',
            '-b:a', '192k',
        ]
        if duration_s and duration_s > 0:
            cmd += ['-t', f'{duration_s:.3f}']
        cmd += [mixed_path]
        return cmd

    if log_callback:
        log_callback(
            f'Đang tách giọng gốc kiểu center-cancel, giữ nền={bg_volume:.2f}, '
            f'TTS={tts_volume:.2f}, ducking mạnh.'
        )

    result = _run_ffmpeg_command(build_mix_cmd(filter_complex), timeout=None)

    if result.returncode != 0:
        fallback_filter = (
            '[0:a]aformat=channel_layouts=stereo,'
            'pan=stereo|c0=0.5*c0-0.5*c1|c1=0.5*c1-0.5*c0,'
            f'volume={bg_volume:.2f}[bg];'
            f'[1:a]aformat=channel_layouts=stereo,volume={fallback_tts_volume:.2f},alimiter=limit=0.96[tts];'
            '[bg][tts]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,'
            'volume=0.90,alimiter=limit=0.96[aout]'
        )
        if log_callback:
            log_callback('Công thức cân bằng âm nâng cao lỗi, thử lại bằng chế độ tương thích...')
        result = _run_ffmpeg_command(build_mix_cmd(fallback_filter), timeout=None)

    if result.returncode == 0 and os.path.exists(mixed_path) and os.path.getsize(mixed_path) > 0:
        try:
            shutil.move(mixed_path, tts_audio_path)
        except Exception:
            shutil.copyfile(mixed_path, tts_audio_path)
            try:
                os.remove(mixed_path)
            except Exception:
                pass
        if log_callback:
            log_callback('Đã trộn âm: giữ nền/hiệu ứng sau tách giọng, TTS được tăng mạnh.')
    elif log_callback:
        log_callback('Không tách/trộn được âm hiệu ứng video gốc, dùng audio TTS như bình thường.')
    return tts_audio_path

def _build_background_music_audio(
    music_paths,
    target_duration_s,
    volume_percent=12,
    fade_ms=1800,
    crossfade_ms=2500,
    log_callback=None
):
    valid_paths = [
        path for path in (music_paths or [])
        if path and os.path.isfile(path)
    ]

    if not valid_paths or not target_duration_s or target_duration_s <= 0:
        return None

    target_ms = max(1, int(target_duration_s * 1000))
    fade_ms = max(0, int(fade_ms))
    crossfade_ms = max(0, int(crossfade_ms))
    volume_percent = max(0, min(100, float(volume_percent or 0)))

    if volume_percent <= 0:
        return None

    # 12% tương đương nền rất nhỏ dưới TTS; tăng theo phần trăm nhưng giữ an toàn.
    gain_db = 20 * np.log10(max(0.01, volume_percent / 100.0))
    playlist = AudioSegment.silent(duration=0)
    index = 0

    while len(playlist) < target_ms + crossfade_ms and valid_paths:
        path = valid_paths[index % len(valid_paths)]
        try:
            track = load_audiosegment_with_ffmpeg(path, log_callback=log_callback)
        except Exception as error:
            if log_callback:
                log_callback(
                    f'Bỏ qua nhạc nền lỗi: {os.path.basename(path)} | {error}'
                )
            valid_paths = [p for p in valid_paths if p != path]
            continue

        if len(track) <= 0:
            index += 1
            continue

        track = track.set_channels(2)
        edge_fade = min(fade_ms, max(0, len(track) // 3))
        if edge_fade:
            track = track.fade_in(edge_fade).fade_out(edge_fade)

        if len(playlist) <= 0:
            playlist = track
        else:
            overlap = min(crossfade_ms, len(playlist) // 3, len(track) // 3)
            if overlap > 0:
                playlist = playlist.append(track, crossfade=overlap)
            else:
                playlist += track

        index += 1

    if len(playlist) <= 0:
        return None

    playlist = playlist[:target_ms]
    final_fade = min(fade_ms, max(0, len(playlist) // 4))
    if final_fade:
        playlist = playlist.fade_in(final_fade).fade_out(final_fade)

    return playlist.apply_gain(gain_db)

def _mix_background_music_into_audio(
    audio_path,
    music_paths,
    duration_s=None,
    volume_percent=12,
    log_callback=None
):
    if (
        not audio_path
        or not os.path.exists(audio_path)
        or not music_paths
    ):
        return audio_path

    try:
        base_audio = load_audiosegment_with_ffmpeg(audio_path, log_callback=log_callback)
        target_duration_s = duration_s or (len(base_audio) / 1000.0)
        music = _build_background_music_audio(
            music_paths,
            target_duration_s,
            volume_percent=volume_percent,
            log_callback=log_callback
        )

        if music is None:
            return audio_path

        target_ms = len(base_audio)
        if duration_s and duration_s > 0:
            target_ms = max(target_ms, int(duration_s * 1000))

        if len(base_audio) < target_ms:
            base_audio += AudioSegment.silent(duration=target_ms - len(base_audio))

        mixed = base_audio.overlay(music[:target_ms])
        temp_path = f'{audio_path}.bgmix.tmp.mp3'
        mixed.export(temp_path, format='mp3', bitrate='192k')
        shutil.move(temp_path, audio_path)

        if log_callback:
            log_callback(
                f'Đã chèn nhạc nền {len(music_paths)} file, '
                f'âm lượng {volume_percent:.0f}%, '
                f'tự lặp/cắt tới {target_ms / 1000.0:.2f}s.'
            )

    except Exception as error:
        if log_callback:
            log_callback(f'Không chèn được nhạc nền: {error}')

    return audio_path

def _force_mux_audio_to_video(video_path, audio_path, log_callback=None, audio_speed=1.0):
    if (
        not video_path
        or not audio_path
        or not os.path.exists(video_path)
        or not os.path.exists(audio_path)
    ):
        raise RuntimeError(
            'Không thể khóa audio TTS: thiếu file MP4 hoặc file audio TTS.'
        )

    if os.path.getsize(audio_path) <= 0:
        raise RuntimeError(
            f'Không thể khóa audio TTS: file audio rỗng:\n{audio_path}'
        )

    base, ext = os.path.splitext(video_path)
    temp_output = f'{base}_tts_mux_tmp{ext or ".mp4"}'
    final_tts_volume = 6.00
    audio_filters = []
    try:
        audio_speed = float(audio_speed or 1.0)
    except Exception:
        audio_speed = 1.0
    if audio_speed and abs(audio_speed - 1.0) > 0.000001:
        atempo = _build_atempo_chain(audio_speed)
        if atempo:
            audio_filters.append(atempo)
    audio_filters.extend([
        f'volume={final_tts_volume:.2f}',
        'loudnorm=I=-13:TP=-1.0:LRA=7',
        'alimiter=limit=0.97'
    ])
    cmd = [
        _ffmpeg_exe,
        '-y',
        '-i', video_path,
        '-i', audio_path,
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-af',
        ','.join(audio_filters),
        '-shortest',
        '-movflags', '+faststart',
        temp_output
    ]

    if log_callback:
        log_callback(f'Audio TTS dùng để khóa: {audio_path}')
        speed_note = (
            f', speed audio x{audio_speed:.4f}'
            if audio_speed and abs(audio_speed - 1.0) > 0.000001
            else ''
        )
        log_callback(
            f'Đang khóa audio TTS vào MP4 cuối, '
            f'tăng TTS x{final_tts_volume:.2f}{speed_note}...'
        )

    result = _run_ffmpeg_command(cmd, timeout=None)

    if (
        result.returncode == 0
        and os.path.exists(temp_output)
        and os.path.getsize(temp_output) > 0
    ):
        try:
            shutil.move(temp_output, video_path)
        except Exception:
            shutil.copyfile(temp_output, video_path)
            try:
                os.remove(temp_output)
            except Exception:
                pass
        if log_callback:
            log_callback(f'Đã khóa audio TTS vào video: {video_path}')
    else:
        error_tail = ''
        if log_callback:
            log_callback('Không khóa được audio TTS bằng mux nhanh.')
            if result.stderr:
                err_lines = [
                    line.strip()
                    for line in result.stderr.splitlines()
                    if line.strip()
                ]
                for line in err_lines[-4:]:
                    log_callback(f'FFmpeg mux audio: {line[:220]}')
                error_tail = '\n'.join(err_lines[-6:])
        try:
            if os.path.exists(temp_output):
                os.remove(temp_output)
        except Exception:
            pass
        raise RuntimeError(
            'Không khóa được audio TTS vào MP4 cuối.\n'
            f'MP4: {video_path}\n'
            f'Audio TTS: {audio_path}\n'
            f'{error_tail}'
        )

    return video_path

def render_video_with_ffmpeg_timeline(
    video_path,
    audio_path,
    output_video_path,
    subs,
    audio_by_index,
    base_duration,
    keep_silence=True,
    use_gpu=True,
    fast_render=True,
    video_speed=1.0,
    adjust_audio_speed=True,
    editor_effects=None,
    subtitle_timeline_subs=None,
    progress_callback=None,
    log_callback=None
):
    if not video_path or not os.path.exists(video_path):
        return False

    parts = []
    filter_lines = []
    filter_temp_files = []
    current_end_ms = 0

    for i, sub in enumerate(subs):
        start_ms = srt_time_to_ms(sub.start)
        end_ms = srt_time_to_ms(sub.end)
        if start_ms >= end_ms:
            continue

        if keep_silence and start_ms > current_end_ms:
            parts.append((current_end_ms, start_ms, 1.0, None))

        original_duration = (end_ms - start_ms) / 1000.0
        tts_audio = audio_by_index.get(i, AudioSegment.silent(duration=0))
        target_duration = len(tts_audio) / 1000.0 if len(tts_audio) > 0 else original_duration
        speed_factor = original_duration / target_duration if target_duration > 0 else 1.0
        parts.append((start_ms, end_ms, speed_factor, i))
        current_end_ms = end_ms

    if keep_silence and base_duration and current_end_ms < base_duration * 1000:
        parts.append((current_end_ms, int(base_duration * 1000), 1.0, None))

    if not parts:
        return False

    video_width, video_height = _probe_video_dimensions(video_path)
    editor_effects = editor_effects or {}
    raw_blur_regions = list(editor_effects.get('blur_regions', []))
    blur_regions = _normalize_ffmpeg_regions(
        raw_blur_regions,
        video_width,
        video_height
    )
    if raw_blur_regions and log_callback and len(blur_regions) != len(raw_blur_regions):
        log_callback(
            'FFmpeg: đã bỏ qua vùng mờ nằm ngoài khung video hoặc quá nhỏ.'
        )
    subtitle_in_blur = bool(editor_effects.get('subtitle_in_blur'))
    subtitle_region = None
    raw_subtitle_region = editor_effects.get('subtitle_region')
    if raw_subtitle_region:
        subtitle_regions = _normalize_ffmpeg_regions(
            [raw_subtitle_region],
            video_width,
            video_height
        )
        if subtitle_regions:
            subtitle_region = subtitle_regions[0]
            if subtitle_region not in blur_regions:
                blur_regions.append(subtitle_region)
    if subtitle_in_blur and not blur_regions:
        default_subtitle_region = _default_subtitle_blur_region(
            video_width,
            video_height
        )
        if default_subtitle_region:
            subtitle_region = default_subtitle_region
            blur_regions.append(default_subtitle_region)
            if log_callback:
                log_callback(
                    'FFmpeg: chưa có vùng mờ cho phụ đề, '
                    'dùng vùng mặc định phía dưới video.'
                )
    subtitle_blur_region = None
    subtitle_draw_entries = []
    if subtitle_in_blur and blur_regions:
        subtitle_blur_region = subtitle_region or blur_regions[0]
        subtitle_source = subtitle_timeline_subs or subs
        use_source_timestamps = bool(
            subtitle_timeline_subs is not None
            and subtitle_timeline_subs is not subs
        )

        if use_source_timestamps:
            for sub in subtitle_source or []:
                try:
                    text_draw = _clean_subtitle_text_for_draw(
                        getattr(sub, 'text', '')
                    )
                    if not text_draw:
                        continue
                    start_s = srt_time_to_ms(sub.start) / 1000.0
                    end_s = srt_time_to_ms(sub.end) / 1000.0
                    if end_s > start_s:
                        subtitle_draw_entries.append((start_s, end_s, text_draw))
                except Exception:
                    continue
        else:
            output_cursor_s = 0.0
            for start_ms, end_ms, speed_factor, sub_index in parts:
                part_duration_s = max(
                    0.0,
                    (end_ms - start_ms) / 1000.0 / max(float(speed_factor), 0.001)
                )
                if sub_index is not None and 0 <= sub_index < len(subs):
                    text_draw = _clean_subtitle_text_for_draw(
                        getattr(subs[sub_index], 'text', '')
                    )
                    if text_draw and part_duration_s > 0:
                        subtitle_draw_entries.append(
                            (
                                output_cursor_s,
                                output_cursor_s + part_duration_s,
                                text_draw
                            )
                        )
                output_cursor_s += part_duration_s

    timeline_pad_s = 0.0
    try:
        video_timeline_s_raw = sum(
            max(0.0, (end_ms - start_ms) / 1000.0 / max(float(speed_factor), 0.001))
            for start_ms, end_ms, speed_factor, _sub_index in parts
        )
        timeline_floor_s = 0.0
        if keep_silence and base_duration:
            timeline_floor_s = float(base_duration)
        elif subs:
            timeline_floor_s = max(
                srt_time_to_ms(sub.end) / 1000.0
                for sub in subs
            )
        if timeline_floor_s and video_timeline_s_raw + 0.05 < timeline_floor_s:
            timeline_pad_s = timeline_floor_s - video_timeline_s_raw
            if subtitle_draw_entries:
                last_start_s, last_end_s, last_text = subtitle_draw_entries[-1]
                subtitle_draw_entries[-1] = (
                    last_start_s,
                    last_end_s + timeline_pad_s,
                    last_text
                )
            if log_callback:
                log_callback(
                    'FFmpeg timeline: video TTS ngắn hơn mốc cuối cần giữ '
                    f'{timeline_pad_s:.3f}s, sẽ giữ khung cuối để không cắt đoạn cuối.'
                )
    except Exception as error:
        if log_callback:
            log_callback(f'FFmpeg timeline pad check lỗi: {error}')

    if log_callback:
        log_callback(f'FFmpeg timeline: {len(parts)} đoạn video, GPU={use_gpu}, fast={fast_render}')
        try:
            video_timeline_s = sum(
                max(0.0, (end_ms - start_ms) / 1000.0 / max(float(speed_factor), 0.001))
                for start_ms, end_ms, speed_factor, _sub_index in parts
            )
            video_timeline_s += timeline_pad_s
            if video_speed and abs(float(video_speed) - 1.0) > 0.000001:
                video_timeline_s = video_timeline_s / max(float(video_speed), 0.001)
            audio_s = get_audio_duration_seconds(audio_path)
            expected_audio_s = (
                audio_s / max(float(video_speed), 0.001)
                if adjust_audio_speed and video_speed and abs(float(video_speed) - 1.0) > 0.000001
                else audio_s
            )
            diff_s = expected_audio_s - video_timeline_s
            log_callback(
                'FFmpeg timeline check: '
                f'video dự kiến={video_timeline_s:.3f}s | '
                f'audio dự kiến={expected_audio_s:.3f}s | '
                f'lệch={diff_s:+.3f}s'
            )
        except Exception as error:
            log_callback(f'FFmpeg timeline check lỗi: {error}')

    if subtitle_blur_region and log_callback:
        if subtitle_draw_entries:
            log_callback(
                'FFmpeg: sẽ chèn phụ đề SRT sau lớp mờ '
                f'({len(subtitle_draw_entries)} dòng).'
            )
        else:
            log_callback(
                'FFmpeg: bật chèn SRT nhưng không có dòng phụ đề hợp lệ để vẽ.'
            )

    for idx, (start_ms, end_ms, speed_factor, sub_index) in enumerate(parts):
        start_s = _fmt_ffmpeg_seconds(start_ms)
        end_s = _fmt_ffmpeg_seconds(end_ms)
        speed_expr = f'{max(speed_factor, 0.001):.8f}'
        segment_filters = [
            f'trim=start={start_s}:end={end_s}',
            f'setpts=(PTS-STARTPTS)/{speed_expr}'
        ]
        filter_lines.append(f'[0:v]{",".join(segment_filters)}[v{idx}]')

    concat_inputs = ''.join(f'[v{idx}]' for idx in range(len(parts)))
    filter_lines.append(f'{concat_inputs}concat=n={len(parts)}:v=1:a=0[vcat]')

    video_label = 'vcat'
    if timeline_pad_s > 0:
        filter_lines.append(
            f'[vcat]tpad=stop_mode=clone:stop_duration={timeline_pad_s:.6f}[vpad]'
        )
        video_label = 'vpad'
    effect_filters = []
    if editor_effects.get('flip_h'):
        effect_filters.append('hflip')
    if editor_effects.get('flip_v'):
        effect_filters.append('vflip')
    line_mode = editor_effects.get('line_mode', '')
    if line_mode and line_mode not in ('Kh\u00f4ng c\u00f3', 'Kh\xc3\xb4ng c\xc3\xb3', 'Không có'):
        grid_filter = _ffmpeg_drawgrid_filter(line_mode, editor_effects.get('line_strength', editor_effects.get('effect_strength', 'Nhẹ')))
        if grid_filter:
            effect_filters.append(grid_filter)
    ratio_val = editor_effects.get('export_ratio', '')
    if ratio_val and ratio_val not in ('B\u1ea3n G\u1ed1c', 'B\u00e1\u00ba\u00a3n G\u00e1\u00bb\u2018c', 'Bản Gốc'):
        if '16:9' in ratio_val:
            effect_filters.append("pad=ceil(max(iw\\,ih*16/9)/2)*2:ceil(max(ih\\,iw*9/16)/2)*2:(ow-iw)/2:(oh-ih)/2:black")
        elif '9:16' in ratio_val:
            effect_filters.append("pad=ceil(max(iw\\,ih*9/16)/2)*2:ceil(max(ih\\,iw*16/9)/2)*2:(ow-iw)/2:(oh-ih)/2:black")
        elif '1:1' in ratio_val:
            effect_filters.append("pad=ceil(max(iw\\,ih)/2)*2:ceil(max(iw\\,ih)/2)*2:(ow-iw)/2:(oh-ih)/2:black")
    if editor_effects.get('review_mode'):
        font_size = max(10, int(editor_effects.get('text_font_size', 40)))
        band_h = max(48, font_size * 2)
        font_file = _ffmpeg_font_file()
        font_opt = f":fontfile='{font_file}'" if font_file else ''
        top_text = _escape_drawtext_text(editor_effects.get('top_text', ''))
        bottom_text = _escape_drawtext_text(editor_effects.get('bottom_text', ''))
        top_color = editor_effects.get('text_color_top', '#FFFF00')
        bot_color = editor_effects.get('text_color_bot', '#FFFFFF')
        bg_color = editor_effects.get('text_bg_color', '#000000')
        effect_filters.append(f"drawbox=x=0:y=0:w=iw:h={band_h}:color={bg_color}@0.70:t=fill")
        effect_filters.append(f"drawbox=x=0:y=ih-{band_h}:w=iw:h={band_h}:color={bg_color}@0.70:t=fill")
        if top_text:
            effect_filters.append(f"drawtext=text='{top_text}'{font_opt}:fontsize={font_size}:fontcolor={top_color}:x=(w-text_w)/2:y=({band_h}-text_h)/2")
        if bottom_text:
            effect_filters.append(f"drawtext=text='{bottom_text}'{font_opt}:fontsize={font_size}:fontcolor={bot_color}:x=(w-text_w)/2:y=h-{band_h}+({band_h}-text_h)/2")
    if effect_filters:
        filter_lines.append(f'[vcat]{",".join(effect_filters)}[veff]')
        video_label = 'veff'

    for blur_idx, (x1, y1, x2, y2) in enumerate(blur_regions):
        w = max(1, int(x2) - int(x1))
        h = max(1, int(y2) - int(y1))
        blur_radius = _safe_boxblur_radius(w, h, _blur_strength_to_radius(editor_effects.get('blur_strength', 35)))
        blur_filter = _boxblur_filter(blur_radius)
        next_label = f'vblur{blur_idx}'
        filter_lines.append(
            f'[{video_label}]split[base{blur_idx}][tmp{blur_idx}];'
            f'[tmp{blur_idx}]crop={w}:{h}:{int(x1)}:{int(y1)},{blur_filter}[blur{blur_idx}];'
            f'[base{blur_idx}][blur{blur_idx}]overlay={int(x1)}:{int(y1)}[{next_label}]'
        )
        video_label = next_label

    if subtitle_blur_region and subtitle_draw_entries:
        try:
            x1, y1, x2, y2 = [int(v) for v in subtitle_blur_region]
            region_w = max(1, x2 - x1)
            region_h = max(1, y2 - y1)
            font_size = max(14, int(editor_effects.get('text_font_size', 40)))
            font_size = min(font_size, max(14, int(region_h * 0.46)))
            font_file = _ffmpeg_font_file()
            font_opt = f":fontfile='{font_file}'" if font_file else ''
            text_color = editor_effects.get('text_color_bot', '#FFFFFF')
            wrap_chars = max(8, int(region_w / max(1, font_size * 0.58)))
            for subtitle_idx, (start_s, end_s, text_raw) in enumerate(subtitle_draw_entries):
                if end_s <= start_s:
                    continue
                next_label = f'vsub{subtitle_idx}'
                text_draw = _wrap_drawtext_text(text_raw, wrap_chars)
                if not text_draw:
                    continue
                text_file = f'_ffmpeg_sub_{random.randint(1000, 9999)}_{subtitle_idx}.txt'
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text_draw)
                filter_temp_files.append(text_file)
                filter_lines.append(
                    f'[{video_label}]drawtext='
                    f"textfile='{_ffmpeg_filter_path(text_file)}'{font_opt}:"
                    f'fontsize={font_size}:'
                    f'fontcolor={text_color}:'
                    'borderw=3:bordercolor=black@0.85:'
                    'line_spacing=4:'
                    f'x={x1}+({region_w}-text_w)/2:'
                    f'y={y1}+({region_h}-text_h)/2:'
                    f"enable='between(t,{start_s:.6f},{end_s:.6f})'"
                    f'[{next_label}]'
                )
                video_label = next_label
        except Exception as error:
            if log_callback:
                log_callback(f'Không dựng được filter chèn phụ đề SRT: {error}')

    logo_path = editor_effects.get('logo_path')
    logo_pos = editor_effects.get('logo_pos')
    if logo_path and logo_pos:
        logo_input_label = '2:v'
        logo_h = max(16, int(editor_effects.get('logo_height', 80)))
        logo_opacity = max(0.0, min(1.0, float(editor_effects.get('logo_opacity', 1.0))))
        filter_lines.append(
            f'[{logo_input_label}]scale=-1:{logo_h},format=rgba,colorchannelmixer=aa={logo_opacity:.3f}[logo];'
            f'[{video_label}][logo]overlay={int(logo_pos[0])}:{int(logo_pos[1])}[vlogo]'
        )
        if log_callback:
            log_callback(f'FFmpeg logo overlay: dùng input [{logo_input_label}] cho ảnh chèn.')
        video_label = 'vlogo'

    quality_filter = _ffmpeg_output_quality_filter(editor_effects.get('output_quality'))
    if quality_filter:
        filter_lines.append(f'[{video_label}]{quality_filter}[vquality]')
        video_label = 'vquality'

    if video_speed and abs(video_speed - 1.0) > 0.000001:
        filter_lines.append(f'[{video_label}]setpts=PTS/{float(video_speed):.8f}[vout]')
        video_label = 'vout'

    audio_label = '1:a'
    if log_callback and adjust_audio_speed and video_speed and abs(video_speed - 1.0) > 0.000001:
        log_callback(
            'FFmpeg timeline: audio sẽ được chỉnh tốc độ ở bước khóa MP4 cuối.'
        )
    audio_map = f'[{audio_label}]' if audio_label != '1:a' else '1:a'

    filter_script = f'_ffmpeg_timeline_{random.randint(1000, 9999)}.txt'
    try:
        with open(filter_script, 'w', encoding='utf-8') as f:
            f.write(';\n'.join(filter_lines))

        codec = 'h264_nvenc' if use_gpu else 'libx264'
        preset = 'p1' if use_gpu and fast_render else 'p4' if use_gpu else 'medium'
        video_params = [
            '-rc', 'vbr',
            '-cq', '23' if fast_render else '18',
            '-b:v', '0',
            '-maxrate', '35M' if fast_render else '25M',
            '-bufsize', '50M',
            '-bf', '0',
        ] if use_gpu else [
            '-crf', '21' if fast_render else '18',
        ]

        cmd = [
            _ffmpeg_exe,
            '-y',
            '-i', video_path,
            '-i', audio_path,
        ]
        if logo_path and logo_pos:
            cmd += ['-loop', '1', '-i', logo_path]
        cmd += [
            '-filter_complex_script', filter_script,
            '-map', '[vout]' if video_label == 'vout' else f'[{video_label}]',
            '-map', audio_map,
            '-c:v', codec,
            '-preset', preset,
            *video_params,
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
        ]

        render_duration = 0.0
        if parts:
            render_duration = sum(
                max(0.0, (end_ms - start_ms) / 1000.0 / max(float(speed_factor), 0.001))
                for start_ms, end_ms, speed_factor, _sub_index in parts
            )
        render_duration += timeline_pad_s
        if video_speed and abs(video_speed - 1.0) > 0.000001:
            render_duration = render_duration / max(float(video_speed), 0.001)

        if render_duration > 0 and (keep_silence or timeline_pad_s > 0):
            cmd += ['-t', f'{render_duration:.3f}']
        else:
            cmd += ['-shortest']
        cmd += [output_video_path]

        render_phase = 'FFmpeg/NVENC Render' if use_gpu else 'FFmpeg/CPU Render'
        if progress_callback:
            progress_callback(0, 100, render_phase)
        if log_callback:
            log_callback(f'Bắt đầu render {render_phase}...')

        result = _run_ffmpeg_command_with_progress(
            cmd,
            duration=render_duration,
            progress_callback=progress_callback,
            log_callback=log_callback,
            phase=render_phase
        )
        if result.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
            if progress_callback:
                progress_callback(100, 100, render_phase)
            if log_callback:
                log_callback(f'{render_phase} hoàn tất, đã gắn audio TTS vào video: {output_video_path}')
            return True

        if log_callback:
            log_callback(f'{render_phase} lỗi, sẽ fallback sang MoviePy.')
            if result.stderr:
                err_lines = [
                    line.strip()
                    for line in result.stderr.splitlines()
                    if line.strip()
                ]
                for line in err_lines[-6:]:
                    log_callback(f'FFmpeg: {line[:220]}')
        print('[FFMPEG FAST RENDER ERROR]')
        print(result.stderr[-4000:] if result.stderr else 'No stderr')
        return False

    finally:
        if os.path.exists(filter_script):
            try:
                os.remove(filter_script)
            except Exception:
                pass
        for temp_file in filter_temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

def render_video_effects_only(
    video_path,
    output_video_path,
    use_gpu=True,
    fast_render=True,
    video_speed=1.0,
    editor_effects=None,
    subtitle_timeline_subs=None,
    progress_callback=None,
    log_callback=None
):
    if not video_path or not os.path.exists(video_path):
        raise RuntimeError('Chưa chọn video hoặc video không tồn tại.')

    editor_effects = editor_effects or {}
    filter_lines = []
    filter_temp_files = []
    video_label = '0:v'
    effect_filters = []
    video_width, video_height = _probe_video_dimensions(video_path)

    if editor_effects.get('flip_h'):
        effect_filters.append('hflip')
    if editor_effects.get('flip_v'):
        effect_filters.append('vflip')

    line_mode = editor_effects.get('line_mode', '')
    if line_mode and line_mode not in ('Không có', 'Kh\xc3\xb4ng c\xc3\xb3', 'Kh\u00f4ng c\u00f3'):
        grid_filter = _ffmpeg_drawgrid_filter(line_mode, editor_effects.get('line_strength', editor_effects.get('effect_strength', 'Nhẹ')))
        if grid_filter:
            effect_filters.append(grid_filter)

    ratio_val = editor_effects.get('export_ratio', '')
    if ratio_val and ratio_val not in ('Bản Gốc', 'B\u1ea3n G\u1ed1c', 'B\u00e1\u00ba\u00a3n G\u00e1\u00bb\u2018c'):
        if '16:9' in ratio_val:
            effect_filters.append("pad=ceil(max(iw\\,ih*16/9)/2)*2:ceil(max(ih\\,iw*9/16)/2)*2:(ow-iw)/2:(oh-ih)/2:black")
        elif '9:16' in ratio_val:
            effect_filters.append("pad=ceil(max(iw\\,ih*9/16)/2)*2:ceil(max(ih\\,iw*16/9)/2)*2:(ow-iw)/2:(oh-ih)/2:black")
        elif '1:1' in ratio_val:
            effect_filters.append("pad=ceil(max(iw\\,ih)/2)*2:ceil(max(iw\\,ih)/2)*2:(ow-iw)/2:(oh-ih)/2:black")

    if editor_effects.get('review_mode'):
        font_size = max(10, int(editor_effects.get('text_font_size', 40)))
        band_h = max(48, font_size * 2)
        font_file = _ffmpeg_font_file()
        font_opt = f":fontfile='{font_file}'" if font_file else ''
        top_text = _escape_drawtext_text(editor_effects.get('top_text', ''))
        bottom_text = _escape_drawtext_text(editor_effects.get('bottom_text', ''))
        top_color = editor_effects.get('text_color_top', '#FFFF00')
        bot_color = editor_effects.get('text_color_bot', '#FFFFFF')
        bg_color = editor_effects.get('text_bg_color', '#000000')
        effect_filters.append(f"drawbox=x=0:y=0:w=iw:h={band_h}:color={bg_color}@0.70:t=fill")
        effect_filters.append(f"drawbox=x=0:y=ih-{band_h}:w=iw:h={band_h}:color={bg_color}@0.70:t=fill")
        if top_text:
            effect_filters.append(f"drawtext=text='{top_text}'{font_opt}:fontsize={font_size}:fontcolor={top_color}:x=(w-text_w)/2:y=({band_h}-text_h)/2")
        if bottom_text:
            effect_filters.append(f"drawtext=text='{bottom_text}'{font_opt}:fontsize={font_size}:fontcolor={bot_color}:x=(w-text_w)/2:y=h-{band_h}+({band_h}-text_h)/2")

    if effect_filters:
        filter_lines.append(f'[{video_label}]{",".join(effect_filters)}[veff]')
        video_label = 'veff'

    raw_blur_regions = list(editor_effects.get('blur_regions', []))
    blur_regions = _normalize_ffmpeg_regions(
        raw_blur_regions,
        video_width,
        video_height
    )
    if raw_blur_regions and log_callback and len(blur_regions) != len(raw_blur_regions):
        log_callback(
            'FFmpeg: đã bỏ qua vùng mờ nằm ngoài khung video hoặc quá nhỏ.'
        )
    subtitle_in_blur = bool(editor_effects.get('subtitle_in_blur'))
    subtitle_region = None
    raw_subtitle_region = editor_effects.get('subtitle_region')
    if raw_subtitle_region:
        subtitle_regions = _normalize_ffmpeg_regions(
            [raw_subtitle_region],
            video_width,
            video_height
        )
        if subtitle_regions:
            subtitle_region = subtitle_regions[0]
            if subtitle_region not in blur_regions:
                blur_regions.append(subtitle_region)
    if subtitle_in_blur and not blur_regions:
        default_subtitle_region = _default_subtitle_blur_region(
            video_width,
            video_height
        )
        if default_subtitle_region:
            subtitle_region = default_subtitle_region
            blur_regions.append(default_subtitle_region)
            if log_callback:
                log_callback(
                    'FFmpeg: chưa có vùng mờ cho phụ đề, '
                    'dùng vùng mặc định phía dưới video.'
                )
    if subtitle_in_blur and not subtitle_timeline_subs:
        if log_callback:
            log_callback(
                'FFmpeg hiệu ứng-only: bật chèn SRT nhưng '
                'chưa có dữ liệu SRT, bỏ qua phần phụ đề.'
            )
        subtitle_in_blur = False
        if not raw_blur_regions:
            blur_regions = []
    subtitle_blur_region = (subtitle_region or blur_regions[0]) if subtitle_in_blur and blur_regions else None
    subtitle_draw_entries = []
    if subtitle_blur_region:
        for sub in subtitle_timeline_subs or []:
            try:
                text_draw = _clean_subtitle_text_for_draw(
                    getattr(sub, 'text', '')
                )
                if not text_draw:
                    continue
                start_s = srt_time_to_ms(sub.start) / 1000.0
                end_s = srt_time_to_ms(sub.end) / 1000.0
                if end_s > start_s:
                    subtitle_draw_entries.append((start_s, end_s, text_draw))
            except Exception:
                continue
        if log_callback:
            if subtitle_draw_entries:
                log_callback(
                    'FFmpeg hiệu ứng-only: sẽ chèn phụ đề SRT '
                    f'({len(subtitle_draw_entries)} dòng).'
                )
            else:
                log_callback(
                    'FFmpeg hiệu ứng-only: bật chèn SRT nhưng '
                    'không có dòng phụ đề hợp lệ để vẽ.'
                )
    for blur_idx, (x1, y1, x2, y2) in enumerate(blur_regions):
        w = max(1, int(x2) - int(x1))
        h = max(1, int(y2) - int(y1))
        blur_radius = _safe_boxblur_radius(w, h, _blur_strength_to_radius(editor_effects.get('blur_strength', 35)))
        next_label = f'vblur{blur_idx}'
        filter_lines.append(
            f'[{video_label}]split[base{blur_idx}][tmp{blur_idx}];'
            f'[tmp{blur_idx}]crop={w}:{h}:{int(x1)}:{int(y1)},{_boxblur_filter(blur_radius)}[blur{blur_idx}];'
            f'[base{blur_idx}][blur{blur_idx}]overlay={int(x1)}:{int(y1)}[{next_label}]'
        )
        video_label = next_label

    if subtitle_blur_region and subtitle_draw_entries:
        try:
            x1, y1, x2, y2 = [int(v) for v in subtitle_blur_region]
            region_w = max(1, x2 - x1)
            region_h = max(1, y2 - y1)
            font_size = max(14, int(editor_effects.get('text_font_size', 40)))
            font_size = min(font_size, max(14, int(region_h * 0.46)))
            font_file = _ffmpeg_font_file()
            font_opt = f":fontfile='{font_file}'" if font_file else ''
            text_color = editor_effects.get('text_color_bot', '#FFFFFF')
            wrap_chars = max(8, int(region_w / max(1, font_size * 0.58)))
            for subtitle_idx, (start_s, end_s, text_raw) in enumerate(subtitle_draw_entries):
                if end_s <= start_s:
                    continue
                next_label = f'vesub{subtitle_idx}'
                text_draw = _wrap_drawtext_text(text_raw, wrap_chars)
                if not text_draw:
                    continue
                text_file = f'_ffmpeg_effect_sub_{random.randint(1000, 9999)}_{subtitle_idx}.txt'
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text_draw)
                filter_temp_files.append(text_file)
                filter_lines.append(
                    f'[{video_label}]drawtext='
                    f"textfile='{_ffmpeg_filter_path(text_file)}'{font_opt}:"
                    f'fontsize={font_size}:'
                    f'fontcolor={text_color}:'
                    'borderw=3:bordercolor=black@0.85:'
                    'line_spacing=4:'
                    f'x={x1}+({region_w}-text_w)/2:'
                    f'y={y1}+({region_h}-text_h)/2:'
                    f"enable='between(t,{start_s:.6f},{end_s:.6f})'"
                    f'[{next_label}]'
                )
                video_label = next_label
        except Exception as error:
            if log_callback:
                log_callback(f'Không dựng được filter chèn phụ đề SRT: {error}')

    logo_path = editor_effects.get('logo_path')
    logo_pos = editor_effects.get('logo_pos')
    if logo_path and logo_pos:
        logo_h = max(16, int(editor_effects.get('logo_height', 80)))
        logo_opacity = max(0.0, min(1.0, float(editor_effects.get('logo_opacity', 1.0))))
        filter_lines.append(
            f'[1:v]scale=-1:{logo_h},format=rgba,colorchannelmixer=aa={logo_opacity:.3f}[logo];'
            f'[{video_label}][logo]overlay={int(logo_pos[0])}:{int(logo_pos[1])}[vlogo]'
        )
        video_label = 'vlogo'

    quality_filter = _ffmpeg_output_quality_filter(editor_effects.get('output_quality'))
    if quality_filter:
        filter_lines.append(f'[{video_label}]{quality_filter}[vquality]')
        video_label = 'vquality'

    audio_label = '0:a'
    atempo = _build_atempo_chain(video_speed)
    if video_speed and abs(float(video_speed) - 1.0) > 0.000001:
        filter_lines.append(f'[{video_label}]setpts=PTS/{float(video_speed):.8f}[vspeed]')
        video_label = 'vspeed'
        if atempo:
            filter_lines.append(f'[0:a]{atempo}[aout]')
            audio_label = 'aout'

    codec = 'h264_nvenc' if use_gpu else 'libx264'
    preset = 'p1' if use_gpu and fast_render else 'p4' if use_gpu else 'medium'
    video_params = [
        '-rc', 'vbr',
        '-cq', '23' if fast_render else '18',
        '-b:v', '0',
        '-maxrate', '35M' if fast_render else '25M',
        '-bufsize', '50M',
        '-bf', '0',
    ] if use_gpu else [
        '-crf', '21' if fast_render else '18',
    ]

    def probe_duration():
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            if fps > 0 and frames > 0:
                duration_value = frames / fps
                if video_speed and abs(float(video_speed) - 1.0) > 0.000001:
                    duration_value = duration_value / max(float(video_speed), 0.001)
                return duration_value
        except Exception:
            return None
        return None

    simple_filter_supported = not blur_regions and not (logo_path and logo_pos)
    if simple_filter_supported:
        simple_filters = list(effect_filters)
        if quality_filter:
            simple_filters.append(quality_filter)
        if video_speed and abs(float(video_speed) - 1.0) > 0.000001:
            simple_filters.append(f'setpts=PTS/{float(video_speed):.8f}')
        simple_filters.append('format=yuv420p')
        vf_filter = ','.join(simple_filters)
        cmd = [
            _ffmpeg_exe,
            '-y',
            '-i', video_path,
            '-vf', vf_filter,
            '-map', '0:v',
            '-map', '0:a?',
            '-c:v', codec,
            '-preset', preset,
            *video_params,
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
        ]
        if atempo:
            cmd += ['-af', atempo]
        cmd += [output_video_path]

        duration = probe_duration()
        if progress_callback:
            progress_callback(0, 100, 'Render hiệu ứng')
        if log_callback:
            log_callback(f'Bắt đầu render hiệu ứng-only bằng -vf: GPU={use_gpu}, fast={fast_render}')
            log_callback(f'FFmpeg -vf: {vf_filter[-500:]}')

        result = _run_ffmpeg_command_with_progress(
            cmd,
            duration=duration,
            progress_callback=progress_callback,
            log_callback=log_callback,
            phase='Render hiệu ứng'
        )

        if result.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
            if progress_callback:
                progress_callback(100, 100, 'Render hiệu ứng')
            if log_callback:
                log_callback(f'Đã xuất video hiệu ứng: {output_video_path}')
            return output_video_path

        if result.stderr and log_callback:
            for line in [x.strip() for x in result.stderr.splitlines() if x.strip()][-8:]:
                log_callback(f'FFmpeg: {line[:220]}')
        raise RuntimeError('Render hiệu ứng bằng FFmpeg thất bại.')

    filter_script = None
    try:
        if not filter_lines:
            filter_lines = [f'[{video_label}]null[vout]']
            video_label = 'vout'
        filter_graph = ';'.join(filter_lines)

        cmd = [_ffmpeg_exe, '-y', '-i', video_path]
        if logo_path and logo_pos:
            cmd += ['-loop', '1', '-i', logo_path]
        cmd += [
            '-filter_complex', filter_graph,
            '-map', f'[{video_label}]',
            '-map', f'[{audio_label}]' if audio_label != '0:a' else '0:a?',
            '-c:v', codec,
            '-preset', preset,
            *video_params,
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
        ]
        cmd += [output_video_path]

        duration = probe_duration()

        if progress_callback:
            progress_callback(0, 100, 'Render hiệu ứng')
        if log_callback:
            log_callback(f'Bắt đầu render hiệu ứng-only: GPU={use_gpu}, fast={fast_render}')

        result = _run_ffmpeg_command_with_progress(
            cmd,
            duration=duration,
            progress_callback=progress_callback,
            log_callback=log_callback,
            phase='Render hiệu ứng'
        )
        if result.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
            if progress_callback:
                progress_callback(100, 100, 'Render hiệu ứng')
            if log_callback:
                log_callback(f'Đã xuất video hiệu ứng: {output_video_path}')
            return output_video_path

        if result.stderr and log_callback:
            try:
                log_callback(f'FFmpeg filter cuối: {filter_graph[-500:]}')
            except Exception:
                pass
            for line in [x.strip() for x in result.stderr.splitlines() if x.strip()][-6:]:
                log_callback(f'FFmpeg: {line[:220]}')
        raise RuntimeError('Render hiệu ứng bằng FFmpeg thất bại.')
    finally:
        if filter_script and os.path.exists(filter_script):
            try:
                os.remove(filter_script)
            except Exception:
                pass
        for temp_file in filter_temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

def process_audio_and_video(
    srt_path,
    output_path,
    provider,
    voice,
    keys,
    video_path=None,
    video_clip=None,
    keep_silence=True,
    use_gpu=False,
    progress_callback=None,
    video_speed=1.0,
    tts_speed=1.0,
    tts_pitch=1.0,
    fast_render=False,
    editor_effects=None,
    log_callback=None,
    existing_audio_path=None,
    keep_video_effect_audio=False,
    keep_original_audio_in_silence=False,
    stop_event=None,
    omnivoice_batch_size=8,
    omnivoice_continuous=False,
    omnivoice_mode='Từng dòng',
    omnivoice_lock_continuous_audio_speed=True,
    background_music_paths=None,
    background_music_volume=12,
    split_video_parts=1
):
    def log(message):
        if log_callback:
            log_callback(message)

    if keep_video_effect_audio:
        log('Chế độ giữ nền/giảm giọng gốc đã được gỡ, bỏ qua cài đặt cũ.')
    keep_video_effect_audio = False
    keep_original_audio_in_silence = bool(keep_silence)
    if keep_original_audio_in_silence and video_path:
        log('Giữ khoảng im lặng: giữ lại âm gốc của video ở các đoạn không có TTS.')

    def finalize_video_output(video_output):
        if video_output and os.path.exists(video_output):
            split_rendered_video_parts(
                video_output,
                parts=split_video_parts,
                log_callback=log
            )
        return video_output

    def should_stop():
        return bool(stop_event and stop_event.is_set())

    def ensure_not_stopped():
        if should_stop():
            raise RuntimeError('Đã dừng theo yêu cầu người dùng.')

    original_video_audio = None
    cache_dir = None
    legacy_cache_dir = None
    srt_cache_signature = None
    loose_legacy_cache_enabled = False

    def get_original_audio_segment(start_ms, end_ms):
        nonlocal original_video_audio
        if (
            not keep_original_audio_in_silence
            or keep_video_effect_audio
            or not video_path
            or end_ms <= start_ms
        ):
            return AudioSegment.silent(duration=max(0, end_ms - start_ms))

        try:
            if original_video_audio is None:
                original_video_audio = load_audiosegment_with_ffmpeg(video_path, log_callback=log)
                log('Đã bật giữ âm gốc trong khoảng lặng SRT.')
            segment = original_video_audio[
                max(0, int(start_ms)):max(0, int(end_ms))
            ]
            expected_ms = max(0, int(end_ms) - int(start_ms))
            if len(segment) < expected_ms:
                segment += AudioSegment.silent(duration=expected_ms - len(segment))
            return segment
        except Exception as error:
            log(f'Không lấy được âm gốc khoảng lặng, dùng im lặng: {error}')
            return AudioSegment.silent(duration=max(0, end_ms - start_ms))

    def tts_cache_text_key(text_content):
        return f'{text_content}|speed={tts_speed:.3f}|pitch={tts_pitch:.3f}'

    def tts_cache_path_for_key(cache_root, sub_index, cache_text):
        if not cache_root:
            return None
        return _tts_cache_path(
            cache_root,
            provider,
            build_tts_cache_voice_key(provider, voice),
            sub_index,
            cache_text
        )

    def audio_cache_path_for_segment(sub_index, text_content):
        return tts_cache_path_for_key(
            cache_dir,
            sub_index,
            tts_cache_text_key(text_content)
        )

    def get_cached_tts_audio_for_key(
        sub_index,
        cache_text,
        spoken_text,
        label,
        expected_min_ms=None,
        expected_max_ms=None
    ):
        cache_path = tts_cache_path_for_key(
            cache_dir,
            sub_index,
            cache_text
        )
        cached_audio = get_valid_cached_tts_audio(
            cache_path,
            text=spoken_text,
            label=label,
            expected_min_ms=expected_min_ms,
            expected_max_ms=expected_max_ms,
            log_callback=log
        )
        if cached_audio is not None:
            return cache_path, cached_audio

        legacy_cache_path = tts_cache_path_for_key(
            legacy_cache_dir,
            sub_index,
            cache_text
        )
        same_cache = False
        if cache_path and legacy_cache_path:
            try:
                same_cache = (
                    os.path.normcase(os.path.abspath(cache_path))
                    == os.path.normcase(os.path.abspath(legacy_cache_path))
                )
            except Exception:
                same_cache = cache_path == legacy_cache_path

        if legacy_cache_path and not same_cache:
            cached_audio = get_valid_cached_tts_audio(
                legacy_cache_path,
                text=spoken_text,
                label=f'{label} cũ',
                expected_min_ms=expected_min_ms,
                expected_max_ms=expected_max_ms,
                log_callback=log
            )
            if cached_audio is not None:
                if cache_path:
                    migrated = _copy_cached_tts_audio_file(
                        legacy_cache_path,
                        cache_path
                    )
                    if migrated:
                        log(
                            f'Dùng lại cache TTS cũ cho {label}; '
                            'đã chuyển sang cache theo SRT.'
                        )
                    else:
                        log(f'Dùng lại cache TTS cũ cho {label}.')
                return cache_path or legacy_cache_path, cached_audio

        if loose_legacy_cache_enabled and legacy_cache_dir:
            for loose_cache_path in _legacy_tts_cache_candidates(
                legacy_cache_dir,
                provider,
                sub_index
            ):
                if loose_cache_path in (cache_path, legacy_cache_path):
                    continue
                cached_audio = get_valid_cached_tts_audio(
                    loose_cache_path,
                    text=spoken_text,
                    label=f'{label} cùng số dòng cũ',
                    expected_min_ms=expected_min_ms,
                    expected_max_ms=expected_max_ms,
                    log_callback=log
                )
                if cached_audio is None:
                    continue
                if cache_path:
                    migrated = _copy_cached_tts_audio_file(
                        loose_cache_path,
                        cache_path
                    )
                    if migrated:
                        log(
                            f'Dùng lại cache TTS cũ theo dòng {sub_index + 1}; '
                            'đã chuyển sang cache theo SRT.'
                        )
                    else:
                        log(f'Dùng lại cache TTS cũ theo dòng {sub_index + 1}.')
                return cache_path or loose_cache_path, cached_audio

        return cache_path, None

    def get_cached_tts_audio_for_segment(
        sub_index,
        text_content,
        label,
        expected_min_ms=None,
        expected_max_ms=None
    ):
        return get_cached_tts_audio_for_key(
            sub_index,
            tts_cache_text_key(text_content),
            text_content,
            label,
            expected_min_ms=expected_min_ms,
            expected_max_ms=expected_max_ms
        )

    def timeline_max_audio_ms_for_sub(sub_index, safety_gap_ms=12):
        try:
            sub = subs[sub_index]
            start_ms = srt_time_to_ms(sub.start)
            end_ms = srt_time_to_ms(sub.end)
            next_start_ms = None
            for next_sub in subs[sub_index + 1:]:
                candidate_start_ms = srt_time_to_ms(next_sub.start)
                candidate_end_ms = srt_time_to_ms(next_sub.end)
                if candidate_end_ms > candidate_start_ms:
                    next_start_ms = candidate_start_ms
                    break
            slot_end_ms = end_ms
            if next_start_ms is not None and next_start_ms > start_ms:
                slot_end_ms = min(slot_end_ms, next_start_ms)
            return max(1, int(slot_end_ms) - int(start_ms) - int(safety_gap_ms))
        except Exception:
            return None

    def fit_generated_audio_to_sub_slot(sub_index, audio, label):
        if not keep_silence:
            return audio
        try:
            sub = subs[sub_index]
            start_ms = srt_time_to_ms(sub.start)
            end_ms = srt_time_to_ms(sub.end)
            next_start_ms = None
            for next_sub in subs[sub_index + 1:]:
                candidate_start_ms = srt_time_to_ms(next_sub.start)
                candidate_end_ms = srt_time_to_ms(next_sub.end)
                if candidate_end_ms > candidate_start_ms:
                    next_start_ms = candidate_start_ms
                    break
            return fit_tts_audio_to_timeline_slot(
                audio,
                start_ms,
                end_ms,
                next_start_ms=next_start_ms,
                label=label,
                log_callback=log
            )
        except Exception:
            return audio

    def regenerate_single_tts_segment(sub_index, text_content, cache_path, reason):
        log(
            f'Rà soát TTS: đoạn {sub_index + 1} thiếu/lỗi ({reason}), '
            'đang tạo lại riêng...'
        )
        if cache_path and os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except Exception:
                pass

        if provider == 'vieneu':
            text_content = sanitize_vieneu_text(text_content)
            audio = text_to_speech_vieneu(
                text=text_content,
                voice=voice,
                use_gpu=use_gpu,
                batch_size=1,
                log_callback=log,
                max_retries=4
            )
        elif provider == 'omnivoice':
            omni_voice = parse_omnivoice_voice_config(voice)
            audio = text_to_speech_omnivoice(
                text=text_content,
                instruct=omni_voice.get('instruct', ''),
                use_gpu=use_gpu,
                ref_audio=omni_voice.get('ref_audio', ''),
                ref_text=omni_voice.get('ref_text', ''),
                log_callback=log
            )
            audio = polish_omnivoice_segment(audio)
        elif provider == 'gtts':
            audio = text_to_speech_gTTS(text_content, lang=voice)
        elif provider == 'fpt':
            key = keys[sub_index % len(keys)] if keys else ''
            audio = text_to_speech_fpt(text_content, voice, key)
        elif provider == 'zalo':
            key = keys[sub_index % len(keys)] if keys else ''
            audio = text_to_speech_zalo(text_content, voice, key)
        elif provider == 'vbee':
            key = keys[sub_index % len(keys)] if keys else ''
            audio = text_to_speech_vbee(
                text=sanitize_vbee_text(text_content),
                voice_id=voice,
                access_token=key,
                app_id=get_env_var('VBEE_APP_ID', '').strip(),
                speed=1.0
            )
        else:
            raise RuntimeError(f'Không hỗ trợ tạo lại TTS cho provider {provider}.')

        try:
            ensure_valid_tts_audio(
                audio,
                text=text_content,
                label=f'đoạn {sub_index + 1} sau khi tạo lại'
            )
        except Exception as error:
            if not is_usable_tts_audio(audio):
                raise
            log(
                f'Rà soát TTS: đoạn {sub_index + 1} tạo lại vẫn chưa chuẩn '
                f'({error}), nhưng audio còn nghe được nên sẽ dùng và '
                'cho video tự khớp theo audio.'
            )
        audio = apply_audio_speed_pitch(
            audio,
            speed=tts_speed,
            pitch=tts_pitch
        )
        audio = pad_short_tts_audio(
            audio,
            text=text_content,
            label=f'đoạn {sub_index + 1} sau speed/pitch',
            log_callback=log
        )
        if not video_path:
            audio = fit_generated_audio_to_sub_slot(
                sub_index,
                audio,
                f'Đoạn {sub_index + 1}'
            )
        try:
            ensure_valid_tts_audio(
                audio,
                text=text_content,
                label=f'đoạn {sub_index + 1} sau speed/pitch'
            )
        except Exception as error:
            if not is_usable_tts_audio(audio):
                raise
            log(
                f'Rà soát TTS: đoạn {sub_index + 1} sau speed/pitch vẫn bị cảnh báo '
                f'({error}), dùng luôn audio này để video khớp theo độ dài audio.'
            )
        precomputed_audio[sub_index] = audio
        _save_cached_tts_audio(audio, cache_path)
        log(f'Rà soát TTS: tạo lại thành công đoạn {sub_index + 1}.')

    def audit_and_repair_missing_tts_segments():
        if use_existing_audio or continuous_tts_audio is not None:
            return
        if not subs:
            return

        max_rounds = 2
        for round_index in range(1, max_rounds + 1):
            ensure_not_stopped()
            broken_items = []
            for sub_index, sub in enumerate(subs):
                text_content = sub.text.strip().replace('\n', ' ')
                if provider == 'vbee':
                    text_content = sanitize_vbee_text(text_content)
                elif provider == 'vieneu':
                    text_content = sanitize_vieneu_text(text_content)
                if not text_content:
                    continue

                audio = precomputed_audio.get(sub_index)
                bad_reason = validate_tts_audio(
                    audio,
                    text=text_content,
                    label=f'đoạn {sub_index + 1}'
                )
                if bad_reason:
                    broken_items.append((sub_index, text_content, bad_reason))

            if not broken_items:
                if round_index == 1:
                    log('Rà soát TTS: đủ audio cho toàn bộ SRT.')
                else:
                    log('Rà soát TTS: các đoạn thiếu/lỗi đã được sửa xong.')
                return

            log(
                'Rà soát TTS: phát hiện '
                f'{len(broken_items)} đoạn thiếu/lỗi, vòng sửa {round_index}/{max_rounds}.'
            )
            for sub_index, text_content, bad_reason in broken_items:
                cache_path = audio_cache_path_for_segment(sub_index, text_content)
                regenerate_single_tts_segment(
                    sub_index,
                    text_content,
                    cache_path,
                    bad_reason
                )

        remaining = []
        usable_warnings = []
        for sub_index, sub in enumerate(subs):
            text_content = sub.text.strip().replace('\n', ' ')
            audio = precomputed_audio.get(sub_index)
            bad_reason = validate_tts_audio(
                audio,
                text=text_content,
                label=f'đoạn {sub_index + 1}'
            )
            if bad_reason:
                if is_usable_tts_audio(audio):
                    usable_warnings.append((sub_index + 1, bad_reason, text_content[:120]))
                else:
                    remaining.append((sub_index + 1, bad_reason, text_content[:120]))

        if usable_warnings:
            details = '; '.join(
                f'đoạn {idx}: {reason}'
                for idx, reason, _preview in usable_warnings[:5]
            )
            if len(usable_warnings) > 5:
                details += f'; ... và {len(usable_warnings) - 5} đoạn khác'
            log(
                'Rà soát TTS: một số đoạn vẫn bị cảnh báo nhưng còn âm, '
                f'sẽ dùng luôn và kéo/giãn video theo audio. {details}'
            )

        if remaining:
            details = '\n'.join(
                f'Đoạn {idx}: {reason} | text={preview}'
                for idx, reason, preview in remaining[:8]
            )
            if len(remaining) > 8:
                details += f'\n... và {len(remaining) - 8} đoạn khác.'
            raise RuntimeError(
                'Rà soát TTS vẫn còn đoạn thiếu/lỗi sau khi tạo lại:\n'
                + details
            )

    precomputed_audio = {}
    continuous_tts_audio = None
    tts_errors = []
    tts_errors_lock = threading.Lock()
    use_existing_audio = bool(existing_audio_path)
    original_background_music_count = len(background_music_paths or [])
    background_music_paths = filter_existing_media_paths(background_music_paths or [])
    if original_background_music_count and not background_music_paths:
        log('Không có file nhạc nền hợp lệ, bỏ qua chèn nhạc nền.')
    omnivoice_mode = str(omnivoice_mode or '').strip()
    if not omnivoice_mode:
        omnivoice_mode = 'Liền mạch toàn SRT' if omnivoice_continuous else 'Từng dòng'
    if omnivoice_mode == 'Cụm thông minh':
        omnivoice_mode = 'Từng dòng'
    local_gpu_tts = provider in LOCAL_GPU_TTS_PROVIDERS
    omnivoice_smart_chunks = bool(provider == 'omnivoice' and omnivoice_mode == 'Cụm thông minh')
    omnivoice_continuous = bool(
        provider == 'omnivoice'
        and (
            omnivoice_mode == 'Liền mạch toàn SRT'
            or (
                omnivoice_continuous
                and omnivoice_mode not in ('Cụm thông minh', 'Từng dòng')
            )
        )
    )
    cache_dir = None

    ensure_not_stopped()
    if provider == 'omnivoice':
        raise RuntimeError(
            'OmniVoice đã được gỡ khỏi AUTOTTS. '
            'Hãy chọn VieNeu Local GPU hoặc provider TTS khác.'
        )

    if use_existing_audio:
        if not os.path.isfile(existing_audio_path):
            raise Exception(f'Không tìm thấy MP3 đã tạo sẵn:\n{existing_audio_path}')
        log(f'Dùng MP3 đã tạo sẵn, bỏ qua TTS/API: {existing_audio_path}')
        subs = []
        if srt_path:
            log(f'Đọc SRT để chèn phụ đề: {srt_path}')
            try:
                subs = pysrt.open(srt_path, encoding="utf-8")
            except Exception as e:
                raise Exception(f"Lỗi khi đọc file SRT để chèn phụ đề: {e}")
        elif editor_effects and editor_effects.get('subtitle_in_blur'):
            log('Đã bật chèn SRT nhưng chưa chọn file SRT, bỏ qua phần phụ đề.')
    elif provider in ("gtts",) + LOCAL_GPU_TTS_PROVIDERS:
        log(f'Đọc SRT: {srt_path}')
        try:
            subs = pysrt.open(srt_path, encoding="utf-8")
        except Exception as e:
            raise Exception(f"Lỗi khi đọc file SRT: {e}")
        if provider == "gtts":
            keys = ["gtts_dummy_key"] * 10  # Tăng tốc luôn cho gTTS
        else:
            keys = [f"{provider}_local"]
    else:
        log(f'Đọc SRT: {srt_path}')
        try:
            subs = pysrt.open(srt_path, encoding="utf-8")
        except Exception as e:
            raise Exception(f"Lỗi khi đọc file SRT: {e}")
        if not keys:
            raise Exception(
                f"Bạn chưa cấu hình API Key cho nhà cung cấp {provider}!"
            )

    total_subs = len(subs)
    if not use_existing_audio:
        if total_subs <= 0:
            raise Exception('File SRT không có đoạn phụ đề nào để tạo audio.')
        srt_cache_signature = build_srt_cache_signature(subs)
        log(f'Tổng phụ đề: {total_subs} đoạn | Provider: {provider} | Voice: {voice}')
        log(f'Mã cache SRT: {srt_cache_signature}')
        if provider == 'omnivoice':
            omni_voice_for_log = parse_omnivoice_voice_config(voice)
            if omni_voice_for_log.get('ref_audio'):
                log(
                    'OmniVoice clone giọng từ audio mẫu: '
                    f'{omni_voice_for_log.get("ref_audio")}'
                )
                if omni_voice_for_log.get('ref_text'):
                    log('OmniVoice dùng voice clone prompt cache để giữ giọng ổn định hơn.')
                else:
                    log('Gợi ý: nhập Text mẫu khớp audio clone để giọng giống hơn và ổn định hơn.')
            else:
                log(
                    'OmniVoice dùng preset: '
                    f'{omni_voice_for_log.get("instruct") or "Tự động"}'
                )
        elif provider == 'vieneu':
            vieneu_voice_for_log = parse_vieneu_voice_config(voice)
            if vieneu_voice_for_log.get('ref_audio'):
                log(
                    'VieNeu chỉ dùng giọng clone từ audio mẫu: '
                    f'{vieneu_voice_for_log.get("ref_audio")}'
                )
            else:
                raise RuntimeError(
                    'VieNeu hiện chỉ dùng giọng clone. '
                    'Hãy chọn audio mẫu clone trước khi render.'
                )

    if use_existing_audio:
        batch_size = 1
    elif provider == "vbee":
        # Vbee chạy 10 đoạn song song theo yêu cầu; cache từng đoạn
        # giúp chạy lại không mất phần đã tạo nếu API 502 giữa chừng.
        batch_size = 10
    elif local_gpu_tts:
        # Local GPU TTS hỗ trợ batch text trong một lần gọi model.
        # Đây là luồng tương tự API: tạo nhiều dòng/cụm trong một lượt,
        # lưu cache từng file rồi ghép lại theo đúng thứ tự.
        # GTX 1070 8GB: cho phép tối đa 8 theo yêu cầu, giảm nếu thiếu VRAM.
        batch_size = max(1, min(8, int(omnivoice_batch_size or 8)))
    else:
        batch_size = max(10, len(keys))
    if not use_existing_audio:
        log(f'Bắt đầu tạo audio TTS, batch size: {batch_size}')
        cache_dir = _tts_srt_cache_dir(srt_cache_signature)
        legacy_cache_dir = _tts_cache_dir(output_path)
        if not cache_dir:
            cache_dir = legacy_cache_dir
        log(f'Cache audio theo SRT: {cache_dir}')
        try:
            same_cache_dir = (
                os.path.normcase(os.path.abspath(cache_dir))
                == os.path.normcase(os.path.abspath(legacy_cache_dir))
            )
        except Exception:
            same_cache_dir = cache_dir == legacy_cache_dir
        if legacy_cache_dir and not same_cache_dir:
            log(f'Cache audio cũ theo file xuất: {legacy_cache_dir}')
            try:
                srt_mtime = os.path.getmtime(srt_path)
                cache_mtime = os.path.getmtime(legacy_cache_dir)
                output_mtime = (
                    os.path.getmtime(output_path)
                    if output_path and os.path.exists(output_path)
                    else 0
                )
                loose_legacy_cache_enabled = (
                    os.path.isdir(legacy_cache_dir)
                    and srt_mtime <= max(cache_mtime, output_mtime) + 2
                )
            except Exception:
                loose_legacy_cache_enabled = False
            if loose_legacy_cache_enabled:
                log(
                    'Cache cũ: SRT không mới hơn cache/output, '
                    'cho phép dùng lại theo số dòng nếu digest cũ không khớp.'
                )
        if provider == 'omnivoice':
            log(
                'OmniVoice chạy kiểu API local: tạo nhiều dòng/cụm mỗi lượt, '
                'lưu từng file cache rồi ghép tuần tự.'
            )
        elif provider == 'vieneu':
            log(
                'VieNeu chạy GPU kiểu API local: tạo nhiều dòng/lượt, '
                'lưu cache từng file rồi ghép đúng timeline.'
            )

    def process_text_thread(sub_index, text_content, key_to_use):
        try:
            if should_stop():
                return

            if not text_content:
                raise RuntimeError('Nội dung phụ đề trống.')

            cache_path, cached_audio = get_cached_tts_audio_for_segment(
                sub_index,
                text_content,
                label=f'cache đoạn {sub_index + 1}',
            )
            if cached_audio is not None:
                precomputed_audio[sub_index] = cached_audio
                log(f'Dùng cache audio đoạn {sub_index + 1}')
                return

            if provider == "fpt":
                audio = text_to_speech_fpt(
                    text_content,
                    voice,
                    key_to_use
                )

            elif provider == "zalo":
                audio = text_to_speech_zalo(
                    text_content,
                    voice,
                    key_to_use
                )

            elif provider == "vbee":
                vbee_app_id = get_env_var(
                    "VBEE_APP_ID",
                    ""
                ).strip()

                if not vbee_app_id:
                    raise RuntimeError(
                        "Chưa nhập Vbee App ID."
                    )

                text_content = sanitize_vbee_text(text_content)
                if not text_content:
                    raise RuntimeError(
                        'Text không hợp lệ cho Vbee sau khi làm sạch.'
                    )
        
                audio = text_to_speech_vbee(
                    text=text_content,
                    voice_id=voice,
                    access_token=key_to_use,
                    app_id=vbee_app_id,
                    speed=1.0
                )

            elif provider == "omnivoice":
                omni_voice = parse_omnivoice_voice_config(voice)
                audio = text_to_speech_omnivoice(
                    text=text_content,
                    instruct=omni_voice.get('instruct', ''),
                    use_gpu=use_gpu,
                    ref_audio=omni_voice.get('ref_audio', ''),
                    ref_text=omni_voice.get('ref_text', ''),
                    log_callback=log
                )

            else:
                audio = text_to_speech_gTTS(
                    text_content,
                    lang=voice
                )

            audio = apply_audio_speed_pitch(
                audio,
                speed=tts_speed,
                pitch=tts_pitch
            )
            if provider == 'omnivoice':
                ensure_valid_tts_audio(
                    audio,
                    text=text_content,
                    label=f'OmniVoice đoạn {sub_index + 1}'
                )

            precomputed_audio[sub_index] = audio
            _save_cached_tts_audio(audio, cache_path)

        except Exception as e:
            error_text = str(e)
            print(f"Lỗi tạo audio đoạn {sub_index + 1}: {error_text}")
            with tts_errors_lock:
                tts_errors.append(
                    (
                        sub_index + 1,
                        error_text,
                        (text_content or '')[:120]
                    )
                )

    # ==============================
    # TẠO AUDIO TỪ PHỤ ĐỀ
    # ==============================

    if not use_existing_audio and omnivoice_smart_chunks:
        ensure_not_stopped()
        omni_voice = parse_omnivoice_voice_config(voice)
        chunks = build_omnivoice_smart_chunks(
            subs,
            target_seconds=6.0,
            max_gap_seconds=1.2,
            max_text_chars=170
        )
        if not chunks:
            raise RuntimeError('Không tạo được cụm OmniVoice từ SRT.')

        chunk_subs = [item['sub'] for item in chunks]
        log(
            'OmniVoice cụm thông minh: gom '
            f'{total_subs} dòng SRT thành {len(chunks)} cụm.'
        )
        log('OmniVoice cụm thông minh: giới hạn mỗi cụm khoảng 6s / 170 ký tự để tránh đọc thiếu SRT.')
        log('OmniVoice cụm thông minh: mỗi cụm sẽ sync video riêng để giảm khựng và giảm lệch.')

        for i in range(0, len(chunks), batch_size):
            ensure_not_stopped()
            chunk_batch = chunks[i:i + batch_size]
            missing_items = []

            for j, item in enumerate(chunk_batch):
                chunk_idx = i + j
                cache_text = (
                    f'smart|{item["start_ms"]}-{item["end_ms"]}|'
                    f'{item["text"]}|speed={tts_speed:.3f}|'
                    f'pitch={tts_pitch:.3f}'
                )
                cache_path, cached_audio = get_cached_tts_audio_for_key(
                    chunk_idx,
                    cache_text,
                    item["text"],
                    label=f'cache OmniVoice cụm {chunk_idx + 1}',
                )
                if cached_audio is not None:
                    precomputed_audio[chunk_idx] = cached_audio
                    log(f'Dùng cache OmniVoice cụm {chunk_idx + 1}/{len(chunks)}')
                else:
                    missing_items.append((chunk_idx, item, cache_path))

            if missing_items:
                log(
                    'OmniVoice cụm thông minh: tạo '
                    f'{len(missing_items)} cụm '
                    f'({missing_items[0][0] + 1}-'
                    f'{missing_items[-1][0] + 1}/{len(chunks)})'
                )
                log(
                    'OmniVoice batch local: gửi '
                    f'{len(missing_items)} cụm vào GPU trong cùng một lượt.'
                )
                try:
                    generated_segments = text_to_speech_omnivoice_batch(
                        [item['text'] for _idx, item, _cache in missing_items],
                        instruct=omni_voice.get('instruct', ''),
                        use_gpu=use_gpu,
                        ref_audio=omni_voice.get('ref_audio', ''),
                        ref_text=omni_voice.get('ref_text', ''),
                        log_callback=log
                    )

                    for (chunk_idx, item, cache_path), audio in zip(
                        missing_items,
                        generated_segments
                    ):
                        try:
                            ensure_valid_tts_audio(
                                audio,
                                text=item["text"],
                                label=f'OmniVoice cụm {chunk_idx + 1}'
                            )
                        except Exception as first_error:
                            log(
                                f'OmniVoice cụm {chunk_idx + 1} có audio lỗi, '
                                'thử tạo lại riêng cụm này...'
                            )
                            audio = text_to_speech_omnivoice(
                                text=item["text"],
                                instruct=omni_voice.get('instruct', ''),
                                use_gpu=use_gpu,
                                ref_audio=omni_voice.get('ref_audio', ''),
                                ref_text=omni_voice.get('ref_text', ''),
                                log_callback=log
                            )
                            ensure_valid_tts_audio(
                                audio,
                                text=item["text"],
                                label=f'OmniVoice cụm {chunk_idx + 1}'
                            )
                        audio = apply_audio_speed_pitch(
                            audio,
                            speed=tts_speed,
                            pitch=tts_pitch
                        )
                        audio = pad_short_tts_audio(
                            audio,
                            text=item["text"],
                            label=f'OmniVoice cụm {chunk_idx + 1} sau speed/pitch',
                            log_callback=log
                        )
                        audio = smooth_tts_segment(
                            audio,
                            fade_ms=45,
                            pad_ms=20,
                            tail_pad_ms=100
                        )
                        precomputed_audio[chunk_idx] = audio
                        _save_cached_tts_audio(audio, cache_path)

                except Exception as e:
                    error_text = str(e)
                    with tts_errors_lock:
                        for chunk_idx, item, _cache_path in missing_items:
                            tts_errors.append(
                                (
                                    chunk_idx + 1,
                                    error_text,
                                    (item.get('text') or '')[:120]
                                )
                            )

            if tts_errors:
                error_lines = []
                for index, error, text in tts_errors[:6]:
                    preview = f" | text='{text}'" if text else ''
                    error_lines.append(f'Cụm {index}: {error}{preview}')
                raise RuntimeError(
                    'Tạo audio OmniVoice theo cụm bị lỗi nên đã dừng.\n'
                    + '\n'.join(error_lines)
                )

            if progress_callback:
                progress_callback(
                    min(i + batch_size, len(chunks)),
                    len(chunks),
                    'OmniVoice cụm'
                )
            log(
                f'OmniVoice cụm xong '
                f'{min(i + batch_size, len(chunks))}/{len(chunks)} cụm'
            )

        subs = chunk_subs
        total_subs = len(subs)

    elif not use_existing_audio and omnivoice_continuous:
        ensure_not_stopped()
        omni_voice = parse_omnivoice_voice_config(voice)
        log('OmniVoice liền mạch: đang gom nội dung SRT...')
        continuous_text = build_continuous_srt_text(subs)
        if not continuous_text:
            raise RuntimeError('Không có nội dung SRT để tạo OmniVoice liền mạch.')
        estimated_words = len(continuous_text.split())
        log(
            'OmniVoice liền mạch: đã gom '
            f'{total_subs} dòng SRT, khoảng {estimated_words} từ, '
            f'{len(continuous_text)} ký tự.'
        )

        cache_text = (
            f'continuous|{continuous_text}|'
            f'speed={tts_speed:.3f}|pitch={tts_pitch:.3f}'
        )

        continuous_expected_min_ms = max(
            1500,
            min(60000, int(srt_active_duration_seconds(subs) * 1000 * 0.25))
        )
        cache_path, cached_audio = get_cached_tts_audio_for_key(
            0,
            cache_text,
            continuous_text,
            label='cache OmniVoice liền mạch',
            expected_min_ms=continuous_expected_min_ms,
        )
        if cached_audio is not None:
            continuous_tts_audio = cached_audio
            log(
                'Dùng cache OmniVoice liền mạch toàn SRT '
                f'({len(continuous_tts_audio) / 1000:.1f}s).'
            )
        else:
            log(
                'OmniVoice liền mạch: gửi toàn bộ SRT cho model '
                f'({len(continuous_text)} ký tự), không chia đoạn.'
            )
            if omni_voice.get('ref_audio'):
                log('OmniVoice liền mạch: dùng audio mẫu clone.')
                if omni_voice.get('ref_text'):
                    log('OmniVoice liền mạch: có Text mẫu, sẽ tạo/dùng clone prompt cache.')
                else:
                    log('OmniVoice liền mạch: chưa có Text mẫu, clone có thể kém ổn định hơn.')
            else:
                log(
                    'OmniVoice liền mạch: dùng preset '
                    f'{omni_voice.get("instruct") or "Tự động"}.'
                )
            if progress_callback:
                progress_callback(1, 6, 'OmniVoice liền mạch')

            started_generate = time.time()

            def generate_continuous_tts():
                return text_to_speech_omnivoice(
                    text=continuous_text,
                    instruct=omni_voice.get('instruct', ''),
                    use_gpu=use_gpu,
                    ref_audio=omni_voice.get('ref_audio', ''),
                    ref_text=omni_voice.get('ref_text', '')
                )

            continuous_tts_audio = run_with_heartbeat(
                generate_continuous_tts,
                heartbeat_callback=lambda elapsed: log(
                    'OmniVoice liền mạch vẫn đang tạo audio... '
                    f'{elapsed}s'
                ),
                heartbeat_seconds=15
            )
            log(
                'OmniVoice liền mạch: generate xong sau '
                f'{time.time() - started_generate:.1f}s, '
                f'audio dài {len(continuous_tts_audio) / 1000:.1f}s.'
            )
            ensure_valid_tts_audio(
                continuous_tts_audio,
                text=continuous_text,
                label='OmniVoice liền mạch',
                expected_min_ms=continuous_expected_min_ms
            )
            if progress_callback:
                progress_callback(3, 6, 'OmniVoice liền mạch')

            before_fx_ms = len(continuous_tts_audio)
            effective_tts_speed = (
                1.0
                if omnivoice_lock_continuous_audio_speed
                else tts_speed
            )
            if omnivoice_lock_continuous_audio_speed and abs(tts_speed - 1.0) > 0.000001:
                log(
                    'OmniVoice liền mạch: đang khóa speed audio = 1.0 '
                    f'để tránh lệch, bỏ qua speed UI {tts_speed:.2f}.'
                )
            log(
                'OmniVoice liền mạch: đang áp dụng speed/pitch '
                f'(speed={effective_tts_speed:.2f}, pitch={tts_pitch:.2f})...'
            )
            continuous_tts_audio = apply_audio_speed_pitch(
                continuous_tts_audio,
                speed=effective_tts_speed,
                pitch=tts_pitch
            )
            log(
                'OmniVoice liền mạch: audio sau speed/pitch '
                f'{before_fx_ms / 1000:.1f}s -> '
                f'{len(continuous_tts_audio) / 1000:.1f}s.'
            )
            if progress_callback:
                progress_callback(4, 6, 'OmniVoice liền mạch')

            log('OmniVoice liền mạch: đang làm mượt đầu/cuối audio...')
            continuous_tts_audio = smooth_tts_segment(
                continuous_tts_audio,
                fade_ms=60,
                pad_ms=40,
                tail_pad_ms=180
            )
            if progress_callback:
                progress_callback(5, 6, 'OmniVoice liền mạch')

            log('OmniVoice liền mạch: đang lưu cache audio...')
            _save_cached_tts_audio(continuous_tts_audio, cache_path)
            log(
                'OmniVoice liền mạch: đã lưu cache, audio cuối dài '
                f'{len(continuous_tts_audio) / 1000:.1f}s.'
            )

        precomputed_audio = {0: continuous_tts_audio}
        if progress_callback:
            progress_callback(6, 6, 'OmniVoice liền mạch')

    elif not use_existing_audio:
        for i in range(0, total_subs, batch_size):
            ensure_not_stopped()

            batch = subs[i:i + batch_size]
            threads = []

            if local_gpu_tts:
                omni_voice = parse_omnivoice_voice_config(voice)
                missing_items = []
                log(
                    f'{provider} từng dòng: mỗi dòng SRT là một job, '
                    f'tối đa {batch_size} dòng/lượt giống API/Vbee.'
                )

                for j, sub in enumerate(batch):
                    sub_idx = i + j
                    text = sub.text.strip().replace("\n", " ")
                    if provider == 'vieneu':
                        text = sanitize_vieneu_text(text)
                    cache_path, cached_audio = get_cached_tts_audio_for_segment(
                        sub_idx,
                        text,
                        label=f'cache audio đoạn {sub_idx + 1}',
                        expected_max_ms=(
                            timeline_max_audio_ms_for_sub(sub_idx)
                            if not video_path
                            else None
                        )
                    )
                    if cached_audio is not None:
                        precomputed_audio[sub_idx] = cached_audio
                        log(f'Dùng cache audio đoạn {sub_idx + 1}')
                    else:
                        missing_items.append(
                            (sub_idx, text, cache_path)
                        )

                if missing_items:
                    log(
                        f'{provider} batch local tạo '
                        f'{len(missing_items)} đoạn '
                        f'({missing_items[0][0] + 1}-'
                        f'{missing_items[-1][0] + 1})'
                    )
                    try:
                        if provider == 'omnivoice':
                            generated_segments = text_to_speech_omnivoice_batch(
                                [item[1] for item in missing_items],
                                instruct=omni_voice.get('instruct', ''),
                                use_gpu=use_gpu,
                                ref_audio=omni_voice.get('ref_audio', ''),
                                ref_text=omni_voice.get('ref_text', ''),
                                log_callback=log
                            )
                        else:
                            generated_segments = text_to_speech_vieneu_batch(
                                [item[1] for item in missing_items],
                                voice=voice,
                                use_gpu=use_gpu,
                                batch_size=batch_size,
                                log_callback=log
                            )

                        for (sub_idx, text, cache_path), audio in zip(
                            missing_items,
                            generated_segments
                        ):
                            try:
                                try:
                                    ensure_valid_tts_audio(
                                        audio,
                                        text=text,
                                        label=f'{provider} đoạn {sub_idx + 1}'
                                    )
                                except Exception as retry_error:
                                    if not is_usable_tts_audio(audio):
                                        raise
                                    log(
                                        f'{provider} đoạn {sub_idx + 1} tạo lại vẫn bị cảnh báo '
                                        f'({retry_error}), dùng luôn audio này.'
                                    )
                            except Exception:
                                log(
                                    f'{provider} đoạn {sub_idx + 1} có audio lỗi, '
                                    'thử tạo lại riêng đoạn này...'
                                )
                                if provider == 'omnivoice':
                                    audio = text_to_speech_omnivoice(
                                        text=text,
                                        instruct=omni_voice.get('instruct', ''),
                                        use_gpu=use_gpu,
                                        ref_audio=omni_voice.get('ref_audio', ''),
                                        ref_text=omni_voice.get('ref_text', ''),
                                        log_callback=log
                                    )
                                else:
                                    audio = text_to_speech_vieneu(
                                        text=text,
                                        voice=voice,
                                        use_gpu=use_gpu,
                                        batch_size=batch_size,
                                        log_callback=log
                                    )
                                ensure_valid_tts_audio(
                                    audio,
                                    text=text,
                                    label=f'{provider} đoạn {sub_idx + 1}'
                                )
                            if provider == 'omnivoice':
                                audio = polish_omnivoice_segment(audio)
                            audio = apply_audio_speed_pitch(
                                audio,
                                speed=tts_speed,
                                pitch=tts_pitch
                            )
                            audio = pad_short_tts_audio(
                                audio,
                                text=text,
                                label=f'{provider} đoạn {sub_idx + 1} sau speed/pitch',
                                log_callback=log
                            )
                            if not video_path:
                                audio = fit_generated_audio_to_sub_slot(
                                    sub_idx,
                                    audio,
                                    f'Đoạn {sub_idx + 1}'
                                )
                            try:
                                ensure_valid_tts_audio(
                                    audio,
                                    text=text,
                                    label=f'{provider} đoạn {sub_idx + 1} sau speed/pitch'
                                )
                            except Exception as final_error:
                                if not is_usable_tts_audio(audio):
                                    raise
                                log(
                                    f'{provider} đoạn {sub_idx + 1} sau speed/pitch vẫn bị cảnh báo '
                                    f'({final_error}), dùng luôn và để video khớp theo audio.'
                                )
                            precomputed_audio[sub_idx] = audio
                            _save_cached_tts_audio(audio, cache_path)

                    except Exception as e:
                        error_text = str(e)
                        print(
                            f"Lỗi tạo audio {provider} batch "
                            f"{missing_items[0][0] + 1}-"
                            f"{missing_items[-1][0] + 1}: {error_text}"
                        )
                        if provider == 'vieneu':
                            log(
                                'VieNeu batch vẫn lỗi, chuyển sang cứu từng đoạn '
                                'với retry riêng để không mất cả nhóm.'
                            )
                            for sub_idx, text, cache_path in missing_items:
                                try:
                                    ensure_not_stopped()
                                    audio = text_to_speech_vieneu(
                                        text=text,
                                        voice=voice,
                                        use_gpu=use_gpu,
                                        batch_size=1,
                                        log_callback=log,
                                        max_retries=4
                                    )
                                    try:
                                        ensure_valid_tts_audio(
                                            audio,
                                            text=text,
                                            label=f'VieNeu đoạn {sub_idx + 1}'
                                        )
                                    except Exception as retry_error:
                                        if not is_usable_tts_audio(audio):
                                            raise
                                        log(
                                            f'VieNeu đoạn {sub_idx + 1} tạo lại vẫn bị cảnh báo '
                                            f'({retry_error}), dùng luôn audio này.'
                                        )
                                    audio = apply_audio_speed_pitch(
                                        audio,
                                        speed=tts_speed,
                                        pitch=tts_pitch
                                    )
                                    audio = pad_short_tts_audio(
                                        audio,
                                        text=text,
                                        label=f'VieNeu đoạn {sub_idx + 1} sau speed/pitch',
                                        log_callback=log
                                    )
                                    if not video_path:
                                        audio = fit_generated_audio_to_sub_slot(
                                            sub_idx,
                                            audio,
                                            f'Đoạn {sub_idx + 1}'
                                        )
                                    try:
                                        ensure_valid_tts_audio(
                                            audio,
                                            text=text,
                                            label=f'VieNeu đoạn {sub_idx + 1} sau speed/pitch'
                                        )
                                    except Exception as final_error:
                                        if not is_usable_tts_audio(audio):
                                            raise
                                        log(
                                            f'VieNeu đoạn {sub_idx + 1} sau speed/pitch vẫn bị cảnh báo '
                                            f'({final_error}), dùng luôn và để video khớp theo audio.'
                                        )
                                    precomputed_audio[sub_idx] = audio
                                    _save_cached_tts_audio(audio, cache_path)
                                    log(
                                        f'VieNeu cứu thành công đoạn {sub_idx + 1}.'
                                    )
                                except Exception as item_error:
                                    with tts_errors_lock:
                                        tts_errors.append(
                                            (
                                                sub_idx + 1,
                                                (
                                                    'VieNeu đã thử lại nhiều lần '
                                                    f'nhưng vẫn lỗi: {item_error}'
                                                ),
                                                (text or '')[:120]
                                            )
                                        )
                        else:
                            with tts_errors_lock:
                                for sub_idx, text, _cache_path in missing_items:
                                    tts_errors.append(
                                        (
                                            sub_idx + 1,
                                            error_text,
                                            (text or '')[:120]
                                        )
                                    )

                threads = []

            else:

                for j, sub in enumerate(batch):
                    if should_stop():
                        break

                    sub_idx = i + j
                    text = sub.text.strip().replace("\n", " ")
                    if provider == "vbee":
                        text = sanitize_vbee_text(text)
                    elif provider == 'vieneu':
                        text = sanitize_vieneu_text(text)
                    key = keys[j % len(keys)]

                    t = threading.Thread(
                        target=process_text_thread,
                        args=(sub_idx, text, key)
                    )

                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()

            ensure_not_stopped()

            if tts_errors:
                error_lines = []
                for index, error, text in tts_errors[:6]:
                    preview = f" | text='{text}'" if text else ''
                    error_lines.append(
                        f'Đoạn {index}: {error}{preview}'
                    )
                more = ''
                if len(tts_errors) > 6:
                    more = f'\n... và {len(tts_errors) - 6} lỗi khác.'
                raise RuntimeError(
                    'Tạo audio từ SRT bị lỗi nên đã dừng, '
                    'không render tiếp video.\n'
                    + '\n'.join(error_lines)
                    + more
                )

            if progress_callback:
                progress_callback(
                    min(i + batch_size, total_subs),
                    total_subs,
                    "Tải Audio API"
                )
            log(f'TTS xong {min(i + batch_size, total_subs)}/{total_subs} đoạn')

            if provider == "vbee":
                time.sleep(0.8)
            else:
                time.sleep(0.2)

        audit_and_repair_missing_tts_segments()

    # ==============================
    # CHUẨN BỊ VIDEO VÀ AUDIO
    # ==============================

    ensure_not_stopped()

    final_audio = (
        continuous_tts_audio
        if continuous_tts_audio is not None
        else AudioSegment.silent(duration=0)
    )
    video_segments = []
    use_ffmpeg_timeline = bool(
        (fast_render or editor_effects)
        and video_path
        and video_clip is None
    )

    base_clip = video_clip
    opened_base_clip = False

    if base_clip is None and video_path:
        log(f'Mở video: {video_path}')
        base_clip = VideoFileClip(video_path)
        opened_base_clip = True

    base_duration = getattr(base_clip, 'duration', None) if base_clip is not None else None
    continuous_sync_video_speed = 1.0

    if use_existing_audio:
        if os.path.normcase(os.path.abspath(existing_audio_path)) != os.path.normcase(os.path.abspath(output_path)):
            shutil.copyfile(existing_audio_path, output_path)
            log(f'Đã dùng lại MP3 có sẵn: {output_path}')
        else:
            log('MP3 có sẵn trùng với nơi lưu, giữ nguyên file audio.')

        if progress_callback:
            progress_callback(1, 1, 'Dùng MP3 có sẵn')

        if base_clip is not None and video_path and video_clip is None:
            video_output = (
                output_path.rsplit(".", 1)[0]
                + "_synced.mp4"
            )
            try:
                audio_duration = get_audio_duration_seconds(output_path)
            except Exception:
                audio_duration = 0
            existing_audio_sync_speed = 1.0
            srt_timeline_duration = 0.0
            if subs:
                try:
                    srt_timeline_duration = max(
                        srt_time_to_ms(sub.end) / 1000.0
                        for sub in subs
                    )
                except Exception:
                    srt_timeline_duration = 0.0
            sync_source_duration = (
                float(base_duration)
                if keep_silence and base_duration
                else (
                    srt_timeline_duration
                    or (float(base_duration) if base_duration else 0.0)
                    or audio_duration
                )
            )
            if sync_source_duration and audio_duration and audio_duration + 0.05 < sync_source_duration:
                _pad_audio_file_to_duration(
                    output_path,
                    sync_source_duration,
                    log_callback=log
                )
                try:
                    audio_duration = get_audio_duration_seconds(output_path)
                except Exception:
                    pass
            timeline_duration = sync_source_duration or audio_duration
            if not timeline_duration or timeline_duration <= 0:
                timeline_duration = base_duration or audio_duration or 1.0
            if sync_source_duration and audio_duration:
                existing_audio_sync_speed = sync_source_duration / audio_duration
                log(
                    'MP3 có sẵn: giữ nguyên audio, chỉnh tốc độ video '
                    f'x{existing_audio_sync_speed:.4f} để khớp '
                    f'{audio_duration:.2f}s.'
                )
            elif keep_silence and base_duration:
                _pad_audio_file_to_duration(output_path, base_duration, log_callback=log)
            if keep_video_effect_audio and video_path:
                _mix_tts_with_vocal_reduced_video_audio(
                    video_path,
                    output_path,
                    duration_s=timeline_duration,
                    log_callback=log
                )
            if background_music_paths:
                _mix_background_music_into_audio(
                    output_path,
                    background_music_paths,
                    duration_s=timeline_duration,
                    volume_percent=background_music_volume,
                    log_callback=log
                )
            dummy_subs = [_SimpleSub(0, timeline_duration)]
            dummy_audio = {0: AudioSegment.silent(duration=int(timeline_duration * 1000))}
            existing_audio_editor_effects = editor_effects
            if (
                editor_effects
                and editor_effects.get('subtitle_in_blur')
                and not subs
            ):
                existing_audio_editor_effects = copy.deepcopy(editor_effects)
                existing_audio_editor_effects['subtitle_in_blur'] = False
            rendered = render_video_with_ffmpeg_timeline(
                video_path=video_path,
                audio_path=output_path,
                output_video_path=video_output,
                subs=dummy_subs,
                audio_by_index=dummy_audio,
                base_duration=base_duration,
                keep_silence=keep_silence,
                use_gpu=use_gpu,
                fast_render=fast_render,
                video_speed=existing_audio_sync_speed,
                adjust_audio_speed=False,
                editor_effects=existing_audio_editor_effects,
                subtitle_timeline_subs=subs if subs else None,
                progress_callback=progress_callback,
                log_callback=log
            )
            if rendered:
                _force_mux_audio_to_video(video_output, output_path, log_callback=log)
                if opened_base_clip and base_clip is not None:
                    try:
                        base_clip.close()
                    except Exception:
                        pass
                return finalize_video_output(video_output)
            log('Render MP3 có sẵn bằng FFmpeg lỗi, chuyển sang MoviePy.')

        if background_music_paths:
            fallback_duration = base_duration
            if not fallback_duration:
                try:
                    fallback_duration = get_audio_duration_seconds(output_path)
                except Exception:
                    fallback_duration = None
            _mix_background_music_into_audio(
                output_path,
                background_music_paths,
                duration_s=fallback_duration,
                volume_percent=background_music_volume,
                log_callback=log
            )

        if base_clip is not None:
            if progress_callback:
                progress_callback(1, 1, 'Render Video')
            final_video = None
            audio_clip = None
            close_final_video = False
            try:
                final_video = base_clip
                if (
                    existing_audio_sync_speed
                    and abs(existing_audio_sync_speed - 1.0) > 0.000001
                ):
                    final_video = final_video.fx(
                        speedx,
                        existing_audio_sync_speed
                    )
                audio_clip = AudioFileClip(output_path)
                final_video = final_video.set_audio(audio_clip)
                close_final_video = True
                video_output = (
                    output_path.rsplit(".", 1)[0]
                    + "_synced.mp4"
                )
                source_fps = getattr(base_clip, "fps", None) or 30
                write_kwargs = {
                    "audio_codec": "aac",
                    "audio_bitrate": "192k",
                    "threads": max(2, multiprocessing.cpu_count() // 2),
                    "logger": None,
                    "fps": source_fps
                }
                if use_gpu:
                    write_kwargs.update({
                        "codec": "h264_nvenc",
                        "preset": "p4" if not fast_render else "p1",
                        "ffmpeg_params": ["-cq", "21" if fast_render else "18", "-pix_fmt", "yuv420p"]
                    })
                else:
                    write_kwargs.update({
                        "codec": "libx264",
                        "preset": "veryfast" if fast_render else "medium",
                        "ffmpeg_params": ["-crf", "21" if fast_render else "18", "-pix_fmt", "yuv420p"]
                    })
                final_video.write_videofile(video_output, **write_kwargs)
                _force_mux_audio_to_video(video_output, output_path, log_callback=log)
                log(f'Đã render video từ MP3 có sẵn: {video_output}')
                return finalize_video_output(video_output)
            finally:
                if audio_clip is not None:
                    try:
                        audio_clip.close()
                    except Exception:
                        pass
                if close_final_video and final_video is not None:
                    try:
                        final_video.close()
                    except Exception:
                        pass
                if opened_base_clip and base_clip is not None:
                    try:
                        base_clip.close()
                    except Exception:
                        pass

        return output_path

    current_end_ms = 0
    use_continuous_tts_timeline = continuous_tts_audio is not None
    render_audio_by_index = precomputed_audio
    segment_audio_clips = []
    segment_audio_temp_paths = []
    use_segment_attached_audio = bool(
        base_clip is not None
        and not use_ffmpeg_timeline
        and not use_continuous_tts_timeline
        and not keep_video_effect_audio
        and not keep_original_audio_in_silence
        and not background_music_paths
        and abs(float(video_speed or 1.0) - 1.0) <= 0.000001
    )

    def attach_tts_audio_to_segment(video_segment, audio_segment, label):
        if (
            not use_segment_attached_audio
            or video_segment is None
            or audio_segment is None
            or len(audio_segment) <= 0
        ):
            try:
                return video_segment.without_audio()
            except Exception:
                return video_segment

        temp_audio_path = (
            f'_segment_tts_{os.getpid()}_'
            f'{threading.get_ident()}_{label}_{random.randint(1000, 9999)}.wav'
        )
        audio_segment.export(temp_audio_path, format='wav')
        audio_clip = AudioFileClip(temp_audio_path)
        segment_audio_temp_paths.append(temp_audio_path)
        segment_audio_clips.append(audio_clip)
        return video_segment.set_audio(audio_clip)

    use_audio_overlay_timeline = bool(
        keep_silence
        and not use_continuous_tts_timeline
        and not use_ffmpeg_timeline
        and base_clip is None
    )

    if use_audio_overlay_timeline:
        last_sub_end_ms = 0
        try:
            if subs:
                last_sub_end_ms = max(
                    srt_time_to_ms(sub.end)
                    for sub in subs
                )
        except Exception:
            last_sub_end_ms = 0

        timeline_ms = max(
            int((base_duration or 0) * 1000),
            int(last_sub_end_ms)
        )
        final_audio = AudioSegment.silent(
            duration=max(1, timeline_ms)
        )
        log(
            'Ghép audio TTS theo timestamp SRT, '
            'có fade mép đoạn để giảm khựng.'
        )
    elif keep_silence and not use_continuous_tts_timeline and use_ffmpeg_timeline:
        log(
            'Ghép audio TTS tuần tự theo video đã sync tốc độ, '
            'tránh chồng tiếng khi đoạn TTS dài hơn timeline SRT.'
        )
        if provider == 'omnivoice':
            log('OmniVoice: bật cân âm lượng, đệm hơi và nối mềm để giảm hụt hơi.')
    elif keep_silence and not use_continuous_tts_timeline and base_clip is not None:
        log(
            'Ghép audio TTS tuần tự theo timeline video đã co/giãn từng đoạn, '
            'giữ khoảng lặng gốc để tránh lệch tích lũy.'
        )
        if use_segment_attached_audio:
            log(
                'Chế độ ghép đơn giản: gắn TTS trực tiếp vào từng đoạn video '
                'rồi nối các đoạn lại, không mux audio tổng.'
            )
    elif use_continuous_tts_timeline:
        log('Dùng audio OmniVoice liền mạch, bỏ ghép từng dòng SRT để tránh giật/cụt.')
        if base_clip is not None and not use_ffmpeg_timeline:
            if keep_silence:
                video_segments.append(base_clip)
            else:
                for sub in subs:
                    start_ms = srt_time_to_ms(sub.start)
                    end_ms = srt_time_to_ms(sub.end)
                    if end_ms <= start_ms:
                        continue
                    try:
                        video_segments.append(
                            base_clip.subclip(
                                start_ms / 1000.0,
                                end_ms / 1000.0
                            )
                        )
                    except Exception as e:
                        print(f"Lỗi cắt khoảng lặng đoạn liền mạch: {e}")

    # ==============================
    # GHÉP TIMELINE
    # ==============================

    if not use_continuous_tts_timeline:
        render_audio_by_index = {}
        for i, sub in enumerate(subs):

            if progress_callback:
                progress_callback(
                    i + 1,
                    total_subs,
                    "Ghép Timeline"
                )

            start_ms = srt_time_to_ms(sub.start)
            end_ms = srt_time_to_ms(sub.end)

            if start_ms >= end_ms:
                continue

            # Khoảng trống trước subtitle
            if start_ms > current_end_ms and keep_silence:

                gap_duration = start_ms - current_end_ms

                if base_clip is not None and not use_ffmpeg_timeline:
                    try:
                        silent_video = base_clip.subclip(
                            current_end_ms / 1000.0,
                            start_ms / 1000.0
                        )
                        try:
                            silent_video = silent_video.without_audio()
                        except Exception:
                            pass

                        video_segments.append(silent_video)

                    except Exception as e:
                        print(f"Lỗi lấy đoạn video im lặng: {e}")

                if not use_audio_overlay_timeline:
                    final_audio += get_original_audio_segment(
                        current_end_ms,
                        start_ms
                    )

            tts_audio = precomputed_audio.get(
                i,
                AudioSegment.silent(duration=0)
            )
            if provider == 'omnivoice':
                tts_audio = polish_omnivoice_segment(tts_audio)
            elif provider == 'vieneu':
                tts_audio = clarify_vieneu_segment(
                    tts_audio,
                    label=f'VieNeu đoạn {i + 1}',
                    log_callback=log
                )
            else:
                tts_audio = smooth_tts_segment(tts_audio)

            next_start_ms = None
            for next_sub in subs[i + 1:]:
                candidate_start_ms = srt_time_to_ms(next_sub.start)
                candidate_end_ms = srt_time_to_ms(next_sub.end)
                if candidate_end_ms > candidate_start_ms:
                    next_start_ms = candidate_start_ms
                    break
            if keep_silence and base_clip is None and not video_path:
                tts_audio = fit_tts_audio_to_timeline_slot(
                    tts_audio,
                    start_ms,
                    end_ms,
                    next_start_ms=next_start_ms,
                    label=f'Đoạn {i + 1}',
                    log_callback=log
                )
            render_audio_by_index[i] = tts_audio

        # ==============================
        # XỬ LÝ VIDEO CHO ĐOẠN THOẠI
        # ==============================

            if base_clip is not None and not use_ffmpeg_timeline:

                try:
                    seg = base_clip.subclip(
                        start_ms / 1000.0,
                        end_ms / 1000.0
                    )

                    original_dur = seg.duration

                    if len(tts_audio) > 0:
                        target_dur = len(tts_audio) / 1000.0
                    else:
                        target_dur = original_dur

                    if target_dur > 0:
                        speed_factor = original_dur / target_dur
                    else:
                        speed_factor = 1.0

                    if abs(speed_factor - 1.0) > 0.001:
                        seg = seg.fx(speedx, speed_factor)

                    seg = attach_tts_audio_to_segment(
                        seg,
                        tts_audio,
                        f'seg{i + 1}'
                    )
                    video_segments.append(seg)

                except Exception as e:
                    print(f"Lỗi xử lý video đoạn {i}: {e}")

            if use_audio_overlay_timeline:
                final_audio = overlay_audio_extending(
                    final_audio,
                    tts_audio,
                    position=max(0, start_ms - 8)
                )
            else:
                final_audio = append_tts_segment(
                    final_audio,
                    tts_audio,
                    provider=provider
                )
            current_end_ms = end_ms

    # ==============================
    # THÊM PHẦN VIDEO CUỐI
    # ==============================

    if (
        base_clip is not None
        and not use_ffmpeg_timeline
        and keep_silence
        and current_end_ms < base_clip.duration * 1000
    ):
        try:
            tail = base_clip.subclip(
                current_end_ms / 1000.0,
                base_clip.duration
            )
            try:
                tail = tail.without_audio()
            except Exception:
                pass

            video_segments.append(tail)

            tail_duration = int(
                base_clip.duration * 1000 - current_end_ms
            )

            if not use_audio_overlay_timeline:
                final_audio += get_original_audio_segment(
                    current_end_ms,
                    int(base_clip.duration * 1000)
                )

        except Exception as e:
            print(f"Lỗi xử lý đoạn cuối video: {e}")

    # ==============================
    # XUẤT AUDIO
    # ==============================

    if (
        use_ffmpeg_timeline
        and not use_continuous_tts_timeline
        and keep_silence
        and base_duration
        and current_end_ms < base_duration * 1000
    ):
        final_audio += get_original_audio_segment(
            current_end_ms,
            int(base_duration * 1000)
        )

    if use_continuous_tts_timeline and base_duration and len(final_audio) > 0:
        audio_duration_s = len(final_audio) / 1000.0
        sync_source_duration = (
            base_duration
            if keep_silence
            else (srt_active_duration_seconds(subs) or base_duration)
        )
        if audio_duration_s > 0:
            continuous_sync_video_speed = sync_source_duration / audio_duration_s
            log(
                'OmniVoice liền mạch: sẽ chỉnh tốc độ video để khớp audio | '
                f'video dùng để sync={sync_source_duration:.2f}s, '
                f'audio={audio_duration_s:.2f}s, '
                f'tốc độ video x{continuous_sync_video_speed:.4f}.'
            )

    if (
        use_ffmpeg_timeline
        and not use_continuous_tts_timeline
        and len(final_audio) > 0
    ):
        target_audio_s = 0.0
        if keep_silence and base_duration:
            target_audio_s = float(base_duration)
        elif subs:
            try:
                target_audio_s = max(
                    srt_time_to_ms(sub.end) / 1000.0
                    for sub in subs
                )
            except Exception:
                target_audio_s = 0.0
        if target_audio_s > 0:
            target_audio_ms = int(target_audio_s * 1000)
            if len(final_audio) + 50 < target_audio_ms:
                pad_ms = target_audio_ms - len(final_audio)
                final_audio += AudioSegment.silent(duration=pad_ms)
                log(
                    'Đã đệm im lặng cuối audio TTS '
                    f'{pad_ms / 1000.0:.2f}s để MP4 không bị cắt cụt đoạn cuối.'
                )

    final_audio.export(
        output_path,
        format="mp3"
    )
    log(f'Đã xuất audio: {output_path}')
    audio_mix_duration = (
        len(final_audio) / 1000.0
        if len(final_audio) > 0
        else (base_duration if keep_silence else None)
    )
    if keep_video_effect_audio and video_path:
        _mix_tts_with_vocal_reduced_video_audio(
            video_path,
            output_path,
            duration_s=audio_mix_duration,
            log_callback=log
        )
    if background_music_paths:
        _mix_background_music_into_audio(
            output_path,
            background_music_paths,
            duration_s=audio_mix_duration,
            volume_percent=background_music_volume,
            log_callback=log
        )

    if use_ffmpeg_timeline and video_path:
        video_output = (
            output_path.rsplit(".", 1)[0]
            + "_synced.mp4"
        )
        rendered = render_video_with_ffmpeg_timeline(
            video_path=video_path,
            audio_path=output_path,
            output_video_path=video_output,
            subs=(
                (
                    [_SimpleSub(0, base_duration or (len(final_audio) / 1000.0))]
                    if keep_silence
                    else subs
                )
                if use_continuous_tts_timeline
                else subs
            ),
            audio_by_index=(
                {
                    index: (
                        AudioSegment.silent(
                            duration=int(
                                (
                                    base_duration
                                    or (len(final_audio) / 1000.0)
                                ) * 1000
                            )
                        )
                        if keep_silence and index == 0
                        else AudioSegment.silent(
                            duration=max(
                                1,
                                srt_time_to_ms(sub.end) - srt_time_to_ms(sub.start)
                            )
                        )
                    )
                    for index, sub in enumerate(
                        [_SimpleSub(0, base_duration or (len(final_audio) / 1000.0))]
                        if keep_silence
                        else subs
                    )
                }
                if use_continuous_tts_timeline
                else render_audio_by_index
            ),
            base_duration=base_duration,
            keep_silence=keep_silence,
            use_gpu=use_gpu,
            fast_render=fast_render,
            video_speed=continuous_sync_video_speed if use_continuous_tts_timeline else video_speed,
            adjust_audio_speed=not use_continuous_tts_timeline,
            editor_effects=editor_effects,
            subtitle_timeline_subs=(
                subs
                if use_continuous_tts_timeline and keep_silence
                else None
            ),
            progress_callback=progress_callback,
            log_callback=log
        )
        if rendered:
            mux_audio_speed = (
                1.0
                if use_continuous_tts_timeline
                else float(video_speed or 1.0)
            )
            _force_mux_audio_to_video(
                video_output,
                output_path,
                log_callback=log,
                audio_speed=mux_audio_speed
            )
            if opened_base_clip and base_clip is not None:
                try:
                    base_clip.close()
                except Exception:
                    pass
            return finalize_video_output(video_output)
        print('FFmpeg fast render failed; fallback to MoviePy render.')
        log('Chuyển sang fallback MoviePy...')

        if base_clip is not None:
            video_segments = []
            current_end_ms = 0
            if use_continuous_tts_timeline:
                if keep_silence:
                    video_segments.append(base_clip)
                else:
                    for sub in subs:
                        start_ms = srt_time_to_ms(sub.start)
                        end_ms = srt_time_to_ms(sub.end)
                        if end_ms <= start_ms:
                            continue
                        try:
                            video_segments.append(
                                base_clip.subclip(
                                    start_ms / 1000.0,
                                    end_ms / 1000.0
                                )
                            )
                        except Exception as e:
                            print(f"Lỗi cắt khoảng lặng đoạn liền mạch: {e}")
            else:
                for i, sub in enumerate(subs):
                    start_ms = srt_time_to_ms(sub.start)
                    end_ms = srt_time_to_ms(sub.end)
                    if start_ms >= end_ms:
                        continue
                    if start_ms > current_end_ms and keep_silence:
                        try:
                            video_segments.append(base_clip.subclip(current_end_ms / 1000.0, start_ms / 1000.0))
                        except Exception as e:
                            print(f"Lỗi lấy đoạn video im lặng: {e}")
                    try:
                        seg = base_clip.subclip(start_ms / 1000.0, end_ms / 1000.0)
                        original_dur = seg.duration
                        tts_audio = render_audio_by_index.get(
                            i,
                            precomputed_audio.get(i, AudioSegment.silent(duration=0))
                        )
                        target_dur = len(tts_audio) / 1000.0 if len(tts_audio) > 0 else original_dur
                        speed_factor = original_dur / target_dur if target_dur > 0 else 1.0
                        if abs(speed_factor - 1.0) > 0.001:
                            seg = seg.fx(speedx, speed_factor)
                        video_segments.append(seg)
                    except Exception as e:
                        print(f"Lỗi xử lý video đoạn {i}: {e}")
                    current_end_ms = end_ms
                if keep_silence and base_duration and current_end_ms < base_duration * 1000:
                    try:
                        video_segments.append(base_clip.subclip(current_end_ms / 1000.0, base_duration))
                    except Exception as e:
                        print(f"Lỗi xử lý đoạn cuối video: {e}")

    # ==============================
    # RENDER VIDEO
    # ==============================

    if base_clip is not None and video_segments:

        if progress_callback:
            progress_callback(
                total_subs,
                total_subs,
                "Đang Render Video (Chờ chút...)"
            )
        log(f'Bắt đầu render MoviePy, số đoạn video: {len(video_segments)}')

        final_video = None
        audio_clip = None

        try:
            final_video = concatenate_videoclips(
                video_segments,
                method="chain"
            )

            if use_segment_attached_audio:
                log('MoviePy: dùng audio đã gắn sẵn trên từng đoạn video.')
            else:
                audio_clip = AudioFileClip(output_path)
                final_video = final_video.set_audio(audio_clip)

            effective_video_speed = float(video_speed or 1.0)
            if use_continuous_tts_timeline:
                effective_video_speed *= continuous_sync_video_speed

            if effective_video_speed and abs(effective_video_speed - 1.0) > 0.000001:
                final_video = final_video.fx(
                    speedx,
                    effective_video_speed
                )
                if use_continuous_tts_timeline:
                    log(
                        'MoviePy: đã chỉnh tốc độ video liền mạch '
                        f'x{effective_video_speed:.4f} để khớp audio.'
                    )

            video_output = (
                output_path.rsplit(".", 1)[0]
                + "_synced.mp4"
            )
            cpu_count = multiprocessing.cpu_count()

            if fast_render:
                cpu_threads = min(cpu_count, 16)
            else:
                cpu_threads = max(2, cpu_count // 2)

            # Giữ nguyên FPS của video gốc
            source_fps = getattr(base_clip, "fps", None)

            if not source_fps:
                source_fps = getattr(final_video, "fps", None)

            if not source_fps:
                source_fps = 30

            write_kwargs = {
                "audio_codec": "aac",
                "audio_bitrate": "192k",
                "threads": cpu_threads,
                "logger": None,
                "fps": source_fps
            }

            print("===== THÔNG TIN VIDEO XUẤT =====")
            print("Kích thước:", final_video.size)
            print("FPS nguồn:", source_fps)
            print("Dùng GPU:", use_gpu)
            print("Render nhanh:", fast_render)
            print("================================")

            if use_gpu:
                nvenc_preset = "p1" if fast_render else "p4"
                nvenc_cq = "23" if fast_render else "18"
                nvenc_maxrate = "35M" if fast_render else "25M"

                # GTX 1070: xuất bằng NVENC. p1 ưu tiên tốc độ, p4 cân bằng hơn.
                final_video.write_videofile(
                    video_output,
                    codec="h264_nvenc",
                    preset=nvenc_preset,
                    ffmpeg_params=[
                        "-rc", "vbr",
                        "-cq", nvenc_cq,
                        "-b:v", "0",
                        "-maxrate", nvenc_maxrate,
                        "-bufsize", "50M",
                        "-bf", "0",
                        "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart"
                    ],
                    **write_kwargs
                )
                if not use_segment_attached_audio:
                    _force_mux_audio_to_video(
                        video_output,
                        output_path,
                        log_callback=log,
                        audio_speed=effective_video_speed
                    )
                log(f'MoviePy/NVENC hoàn tất: {video_output}')

            else:
                # Xuất bằng CPU libx264
                final_video.write_videofile(
                    video_output,
                    codec="libx264",
                    preset="medium" if fast_render else "slow",
                    ffmpeg_params=[
                        "-crf", "18" if fast_render else "18",
                        "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart"
                    ],
                    **write_kwargs
                )
                if not use_segment_attached_audio:
                    _force_mux_audio_to_video(
                        video_output,
                        output_path,
                        log_callback=log,
                        audio_speed=effective_video_speed
                    )
                log(f'MoviePy/CPU hoàn tất: {video_output}')
            return finalize_video_output(video_output)

        finally:

            if audio_clip is not None:
                try:
                    audio_clip.close()
                except Exception:
                    pass

            if final_video is not None:
                try:
                    final_video.close()
                except Exception:
                    pass

            for clip in segment_audio_clips:
                try:
                    clip.close()
                except Exception:
                    pass

            for temp_path in segment_audio_temp_paths:
                try:
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass

    # ==============================
    # ĐÓNG VIDEO ĐƯỢC MỞ TRONG HÀM
    # ==============================

    if opened_base_clip and base_clip is not None:
        try:
            base_clip.close()
        except Exception:
            pass

    return output_path
class SrtToAudioApp(tb.Frame):
    def __init__(self, root, editor_ref=None, switch_to_editor_cb=None):
        super().__init__(root)
        self.root = root
        self.editor_ref = editor_ref
        self.switch_to_editor_cb = switch_to_editor_cb
        self.srt_file_path = None
        self.output_file_path = None
        self.video_file_path = None
        self.existing_audio_path = None
        self.background_music_paths = []
        self.has_gpu, self.gpu_info, self.gpu_color, self.gpu_enabled = check_gpu_available()
        self.use_gpu = tk.BooleanVar(value=self.gpu_enabled)
        self.video_speed = tk.DoubleVar(value=1.0)
        self.keep_silence = tk.BooleanVar(value=True)
        self.keep_video_effect_audio = tk.BooleanVar(value=False)
        self.keep_original_audio_in_silence = tk.BooleanVar(value=False)
        self.output_quality = tk.StringVar(value='Gốc')
        self.split_video_parts = tk.IntVar(value=1)
        self.tts_speed = tk.DoubleVar(value=1.2)
        self.tts_pitch = tk.DoubleVar(value=1.0)
        self.omnivoice_batch_size = tk.IntVar(value=8)
        self.omnivoice_mode = tk.StringVar(value='Từng dòng')
        self.omnivoice_continuous = tk.BooleanVar(value=False)
        self.omnivoice_lock_continuous_audio_speed = tk.BooleanVar(value=True)
        self.background_music_volume = tk.DoubleVar(value=12.0)
        self.omnivoice_ref_audio_path = None
        self.omnivoice_ref_text = tk.StringVar(value='')
        # ==============================
        # HÀNG CHỜ VIDEO
        # ==============================
        self.job_queue = []
        self.queue_running = False
        self.stop_queue_requested = False
        self.queue_stop_event = threading.Event()
        self.render_stop_event = None
        self.stop_render_requested = False
        self.last_stop_context = None
        self.last_single_fast = False
        self.last_queue_fast = False
        self.last_effects_fast = True
        self.last_render_output_path = None

        # Mặc định không tự tắt máy để tránh tắt nhầm khi thử tool
        self.shutdown_after_queue = tk.BooleanVar(value=False)
        self.shutdown_delay_seconds = tk.IntVar(value=60)
        self.queue_count_var = tk.StringVar(value='Hàng chờ: 0 video')
        self.lang_code_map = {'Tiếng Việt': 'vi', 'Tiếng Anh': 'en', 'Tiếng Nhật': 'ja', 'Tiếng Trung': 'zh-cn'}
        self.tts_providers = {'Google TTS': 'gtts', 'FPT TTS': 'fpt', 'Zalo TTS': 'zalo', 'Vbee TTS': 'vbee', 'VieNeu Local GPU': 'vieneu'}
        self.voice_options = {
    'gtts': self.lang_code_map,

    'fpt': {
        'Ban Mai': 'banmai',
        'Lê Minh': 'leminh',
        'Mỹ An': 'myan',
        'Thu Minh': 'thuminh',
        'Lan Nhi': 'lannhi',
        'Linh San': 'linhsan'
    },

    'zalo': {
        'Nữ miền Bắc': '1',
        'Nam miền Bắc': '2',
        'Nữ miền Nam': '3',
        'Nam miền Nam': '4'
    },

    'vbee': {
        'HN - Ngọc Huyền':
            'hn_female_ngochuyen_full_48k-fhg',

        'HN - Mai Phương':
            'hn_female_maiphuong_vdts_48k-fhg',

        'SG - Lan Trinh':
            'sg_female_lantrinh_vdts_48k-fhg',

        'SG - Thảo Trinh':
            'sg_female_thaotrinh_full_48k-fhg',

        'SG - Tường Vy':
            'sg_female_tuongvy_call_44k-fhg'
    },

    'vieneu': {
        'Clone từ audio mẫu': ''
    }
}
        self.create_widgets()
    def create_widgets(self):
        # ***<module>.SrtToAudioApp.create_widgets: Failure: Compilation Error
        # ==========================================
        # KHUNG CUỘN DỌC CHO TOÀN BỘ TAB TẠO GIỌNG
        # ==========================================
        scroll_host = tb.Frame(self)
        scroll_host.pack(
            fill=BOTH,
            expand=YES
        )

        scroll_canvas = tk.Canvas(
            scroll_host,
            highlightthickness=0,
            borderwidth=0,
            background=COLOR_CANVAS
        )

        page_scrollbar = tb.Scrollbar(
            scroll_host,
            orient='vertical',
            command=scroll_canvas.yview
        )

        scroll_canvas.configure(
            yscrollcommand=page_scrollbar.set
        )

        page_scrollbar.pack(
            side=RIGHT,
            fill=Y
        )

        scroll_canvas.pack(
            side=LEFT,
            fill=BOTH,
            expand=YES
        )

        # Toàn bộ giao diện cũ sẽ nằm trong container này
        container = tb.Frame(
            scroll_canvas,
            padding=(26, 22)
        )

        container_window = scroll_canvas.create_window(
            (0, 0),
            window=container,
            anchor='nw'
        )


        def update_scroll_region(event=None):
            scroll_canvas.configure(
                scrollregion=scroll_canvas.bbox('all')
            )


        def resize_scroll_content(event):
            # Giữ nội dung rộng bằng vùng hiển thị
            scroll_canvas.itemconfigure(
                container_window,
                width=event.width
            )


        def scroll_with_mouse(event):
            if event.delta > 0:
                scroll_canvas.yview_scroll(-3, 'units')
            else:
                scroll_canvas.yview_scroll(3, 'units')


        container.bind(
            '<Configure>',
            update_scroll_region
        )

        scroll_canvas.bind(
            '<Configure>',
            resize_scroll_content
        )

        # Cuộn bằng con lăn chuột
        scroll_canvas.bind_all(
            '<MouseWheel>',
            scroll_with_mouse
        )
        hero = tb.Frame(container, bootstyle='secondary')
        hero.pack(fill=X, pady=(0, 16), ipadx=14, ipady=12)
        tb.Label(hero, text='🎙️ Tạo giọng đọc & đồng bộ video', font=(APP_FONT, 17, 'bold'), bootstyle='inverse-secondary').pack(anchor=W)
        tb.Label(hero, text=f'Chọn SRT, giọng đọc, video và xuất file MP3/MP4 đồng bộ. {APP_BUILD}', font=(APP_FONT, 10), bootstyle='inverse-secondary').pack(anchor=W, pady=(4, 0))
        files_frame = tb.LabelFrame(container, text='📁 Tệp đầu vào')
        files_frame.pack(fill=X, pady=(0, 15), ipadx=10, ipady=10)
        tb.Button(files_frame, text='📄 Chọn SRT', bootstyle='info', command=self.select_srt_file, width=20).grid(row=0, column=0, padx=8, pady=8, sticky='w')
        self.lbl_srt_path = tb.Label(files_frame, text='📄 Chưa chọn file SRT', wraplength=700, font=(APP_FONT, 10))
        self.lbl_srt_path.grid(row=0, column=1, padx=8, pady=8, sticky='w')
        tb.Button(files_frame, text='🎬 Chọn Video', bootstyle='outline-primary', command=self.select_video_file, width=20).grid(row=1, column=0, padx=8, pady=8, sticky='w')
        self.lbl_video_path = tb.Label(files_frame, text='🎬 Chưa chọn file video', wraplength=700, font=(APP_FONT, 10))
        self.lbl_video_path.grid(row=1, column=1, padx=8, pady=8, sticky='w')
        tb.Button(files_frame, text='🎧 Dùng MP3 đã có', bootstyle='outline-success', command=self.select_existing_audio_file, width=20).grid(row=2, column=0, padx=8, pady=8, sticky='w')
        existing_audio_row = tb.Frame(files_frame)
        existing_audio_row.grid(row=2, column=1, padx=8, pady=8, sticky='ew')
        self.lbl_existing_audio_path = tb.Label(existing_audio_row, text='🎧 Chưa chọn MP3 khôi phục', wraplength=620, font=(APP_FONT, 10))
        self.lbl_existing_audio_path.pack(side=LEFT, padx=(0, 8))
        tb.Button(existing_audio_row, text='Bỏ MP3', bootstyle='danger-outline', command=self.clear_existing_audio_file).pack(side=LEFT)
        tts_frame = tb.LabelFrame(container, text='🎙️ Cài đặt giọng đọc TTS')
        tts_frame.pack(fill=X, pady=(0, 15), ipadx=10, ipady=10)
        tb.Label(tts_frame, text='Nguồn TTS:').grid(row=0, column=0, padx=8, pady=8, sticky='e')
        self.provider_combo = tb.Combobox(tts_frame, values=list(self.tts_providers.keys()), state='readonly', bootstyle='success')
        self.provider_combo.grid(row=0, column=1, padx=8, pady=8, sticky='w')
        self.provider_combo.current(0)
        self.provider_combo.bind('<<ComboboxSelected>>', self.on_provider_change)
        tb.Label(tts_frame, text='Chọn giọng:').grid(row=0, column=2, padx=8, pady=8, sticky='e')
        self.voice_combo = tb.Combobox(tts_frame, state='readonly', bootstyle='success')
        self.voice_combo.grid(row=0, column=3, padx=8, pady=8, sticky='w')
        self.update_voice_options('gtts')
        tb.Label(tts_frame, text='Test giọng:').grid(row=1, column=0, padx=8, pady=8, sticky='e')
        self.preview_text = tk.StringVar(value='Xin chào, đây là giọng đọc thử.')
        tb.Entry(tts_frame, textvariable=self.preview_text, width=40).grid(row=1, column=1, columnspan=2, padx=8, pady=8, sticky='ew')
        fx_frame = tb.Frame(tts_frame)
        fx_frame.grid(row=2, column=0, columnspan=4, padx=8, pady=5, sticky='w')
        tb.Label(fx_frame, text='🎧 Tùy chỉnh Giọng đọc (CapCut Style):', font=('Helvetica', 9, 'bold')).pack(side=LEFT, padx=(0, 15))
        tb.Label(fx_frame, text='Tốc độ (Speed):').pack(side=LEFT)
        tb.Spinbox(fx_frame, from_=0.5, to=3.0, increment=0.1, textvariable=self.tts_speed, width=5).pack(side=LEFT, padx=5)
        tb.Label(fx_frame, text='Cao độ (Pitch):').pack(side=LEFT, padx=(15, 0))
        tb.Spinbox(fx_frame, from_=0.5, to=2.0, increment=0.1, textvariable=self.tts_pitch, width=5).pack(side=LEFT, padx=5)
        Tooltip(fx_frame, 'Pitch > 1.0: Tiếng thanh/trẻ con hơn. Pitch < 1.0: Tiếng trầm/đàn ông hơn.')
        clone_frame = tb.Frame(tts_frame)
        clone_frame.grid(row=3, column=0, columnspan=4, padx=8, pady=(4, 8), sticky='ew')
        tb.Button(clone_frame, text='🎙️ Chọn audio mẫu clone', bootstyle='outline-info', command=self.select_omnivoice_ref_audio).pack(side=LEFT, padx=(0, 8))
        self.lbl_omnivoice_ref_audio = tb.Label(clone_frame, text='Chưa chọn audio mẫu clone local', wraplength=360, font=(APP_FONT, 9))
        self.lbl_omnivoice_ref_audio.pack(side=LEFT, padx=(0, 8))
        tb.Button(clone_frame, text='Bỏ mẫu', bootstyle='danger-outline', command=self.clear_omnivoice_ref_audio).pack(side=LEFT, padx=(0, 8))
        tb.Label(clone_frame, text='Text mẫu:').pack(side=LEFT, padx=(8, 4))
        tb.Entry(clone_frame, textvariable=self.omnivoice_ref_text, width=34).pack(side=LEFT, fill=X, expand=YES)
        Tooltip(clone_frame, 'VieNeu sẽ clone theo audio mẫu nếu có chọn. Text mẫu là nội dung nói trong audio mẫu.')
        omni_speed_frame = tb.Frame(tts_frame)
        omni_speed_frame.grid(row=4, column=0, columnspan=4, padx=8, pady=(0, 8), sticky='w')
        tb.Label(omni_speed_frame, text='VieNeu dòng/lượt:').pack(side=LEFT, padx=(0, 6))
        tb.Spinbox(omni_speed_frame, from_=1, to=8, increment=1, textvariable=self.omnivoice_batch_size, width=5).pack(side=LEFT)
        tb.Label(omni_speed_frame, text='đoạn/lần').pack(side=LEFT, padx=(6, 12))
        tb.Label(omni_speed_frame, text='1-8 dòng/lượt, thiếu VRAM thì giảm', font=(APP_FONT, 8, 'italic')).pack(side=LEFT)
        tb.Label(
            omni_speed_frame,
            text='VieNeu luôn ghép theo timeline từng dòng',
            font=(APP_FONT, 8, 'italic')
        ).pack(side=LEFT, padx=(18, 0))
        Tooltip(omni_speed_frame, 'Từng dòng: mỗi dòng SRT là một job như API/Vbee, tạo tối đa 8 dòng/lượt rồi ghép theo timeline.')
        self.btn_preview = tb.Button(tts_frame, text='▶ Nghe thử', bootstyle='warning', command=self.start_preview_thread)
        self.btn_preview.grid(row=1, column=3, padx=8, pady=8, sticky='w')
        opts_frame = tb.LabelFrame(container, text='⚙️ Tùy chọn nâng cao')
        opts_frame.pack(fill=X, pady=(0, 15), ipadx=10, ipady=10)
        tb.Checkbutton(opts_frame, text='Giữ nguyên video + âm gốc trong khoảng im lặng', variable=self.keep_silence, bootstyle='round-toggle').grid(row=0, column=0, padx=8, pady=8, sticky='w', columnspan=2)
        tb.Label(opts_frame, text='Tốc độ video:').grid(row=0, column=2, padx=8, pady=8, sticky='e')
        tb.Entry(opts_frame, textvariable=self.video_speed, width=8).grid(row=0, column=3, padx=8, pady=8, sticky='w')
        tb.Label(opts_frame, text='Chất lượng xuất:').grid(row=0, column=4, padx=8, pady=8, sticky='e')
        self.output_quality_combo = tb.Combobox(
            opts_frame,
            textvariable=self.output_quality,
            values=['Gốc', '720p', '1080p', '2K / 1440p', '4K / 2160p'],
            state='readonly',
            width=13,
            bootstyle='success'
        )
        self.output_quality_combo.grid(row=0, column=5, padx=8, pady=8, sticky='w')
        Tooltip(self.output_quality_combo, 'Chọn độ phân giải video xuất ra. Gốc sẽ giữ kích thước video nguồn.')
        tb.Label(opts_frame, text='Chia sau render:').grid(row=1, column=4, padx=8, pady=(0, 8), sticky='e')
        tb.Spinbox(
            opts_frame,
            from_=1,
            to=99,
            increment=1,
            textvariable=self.split_video_parts,
            width=6,
            bootstyle='info'
        ).grid(row=1, column=5, padx=8, pady=(0, 8), sticky='w')
        Tooltip(opts_frame, '1 = không chia. 2 = cắt đôi, 3 = chia 3 phần, 4 = chia 4 phần... File gốc vẫn được giữ nguyên.')
        presets_frame = tb.Frame(opts_frame)
        presets_frame.grid(row=1, column=2, columnspan=2, padx=8, pady=(0, 8), sticky='w')
        for s in [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]:
            tb.Button(presets_frame, text=f'{s}x', width=4, bootstyle='outline-info', command=lambda v=s: self.video_speed.set(v)).pack(side=tk.LEFT, padx=3)
        gpu_frame = tb.Frame(opts_frame)
        gpu_frame.grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 8), sticky='w')
        self.chk_use_gpu = tb.Checkbutton(gpu_frame, text='Sử dụng GPU (NVENC)', variable=self.use_gpu, bootstyle='round-toggle', state=tk.NORMAL if self.has_gpu and self.gpu_enabled else tk.DISABLED)
        self.chk_use_gpu.pack(side=tk.LEFT)
        tb.Label(gpu_frame, text=f'({self.gpu_info})', font=('', 8, 'italic')).pack(side=tk.LEFT, padx=8)
        music_frame = tb.Frame(opts_frame)
        music_frame.grid(row=3, column=0, columnspan=6, padx=8, pady=(10, 0), sticky='ew')
        tb.Button(music_frame, text='🎵 Thêm nhạc nền', bootstyle='outline-info', command=self.select_background_music_files).pack(side=LEFT, padx=(0, 8))
        tb.Button(music_frame, text='Bỏ nhạc nền', bootstyle='danger-outline', command=self.clear_background_music_files).pack(side=LEFT, padx=(0, 8))
        tb.Label(music_frame, text='Âm lượng:').pack(side=LEFT, padx=(8, 4))
        tb.Spinbox(music_frame, from_=0, to=60, increment=1, textvariable=self.background_music_volume, width=5).pack(side=LEFT)
        tb.Label(music_frame, text='%').pack(side=LEFT, padx=(4, 10))
        self.lbl_background_music = tb.Label(music_frame, text='Chưa chọn nhạc nền', wraplength=520, font=(APP_FONT, 9))
        self.lbl_background_music.pack(side=LEFT, fill=X, expand=YES)
        Tooltip(music_frame, 'Mức đề xuất 8-15%. App tự lặp nếu nhạc ngắn hơn video, cắt nếu dài hơn, và fade/crossfade giữa nhiều bài.')
        api_btn_frame = tb.Frame(opts_frame)
        api_btn_frame.grid(row=4, column=0, columnspan=4, padx=8, pady=(10, 0), sticky='w')
        tb.Button(api_btn_frame, text='🔑 Quản lý API Key / chạy song song', bootstyle='secondary', command=self.open_api_key_dialog).pack(side=tk.LEFT)
        out_frame = tb.Frame(container)
        out_frame.pack(fill=X, pady=(10, 20))
        tb.Button(out_frame, text='💾 Chọn nơi lưu', bootstyle='secondary', command=self.select_output_file, width=20).pack(side=LEFT, padx=8)
        self.lbl_output_path = tb.Label(out_frame, text='💾 Chưa chọn nơi lưu Audio/Video', font=(APP_FONT, 10))
        self.lbl_output_path.pack(side=LEFT, padx=8)
        self.btn_open_output_folder = tb.Button(out_frame, text='📂 Mở thư mục', bootstyle='secondary-outline', width=14, command=self.open_last_output_folder, state=tk.DISABLED)
        self.btn_open_output_folder.pack(side=LEFT, padx=8)
        Tooltip(self.btn_open_output_folder, 'Mở thư mục chứa file vừa render xong.')
        self.btn_fast_convert = tb.Button(out_frame, text='⚡ RENDER NHANH', bootstyle='warning', width=20, command=lambda: self.start_conversion_thread(fast=True))
        self.btn_fast_convert.pack(side=RIGHT, padx=8)
        Tooltip(self.btn_fast_convert,'⚡ Render nhanh, giữ nguyên FPS nguồn. ''GPU dùng CQ 21, CPU dùng CRF 21.')
        self.btn_convert = tb.Button(out_frame, text='🚀 TẠO NGAY', bootstyle='success', width=20, command=lambda: self.start_conversion_thread(fast=False))
        self.btn_convert.pack(side=RIGHT, padx=8)
        Tooltip(self.btn_convert,'🚀 Render chất lượng cao. ''GPU dùng CQ 18, CPU dùng CRF 18 và giữ nguyên FPS nguồn.')
        self.btn_effects_only = tb.Button(out_frame, text='🎬 SUB MỜ (ÂM GỐC)', bootstyle='info', width=24, command=lambda: self.start_effects_only_render_thread(fast=True))
        self.btn_effects_only.pack(side=RIGHT, padx=8)
        Tooltip(self.btn_effects_only, 'Không tạo TTS. Giữ âm thanh gốc của video và chèn SRT vào vùng mờ nếu đã chọn SRT.')
        self.btn_stop_render = tb.Button(out_frame, text='⏹ DỪNG', bootstyle='danger', width=12, command=self.request_stop_render, state=tk.DISABLED)
        self.btn_stop_render.pack(side=RIGHT, padx=8)
        Tooltip(self.btn_stop_render, 'Dừng tác vụ render/TTS đang chạy.')
        self.btn_continue_render = tb.Button(out_frame, text='▶ TIẾP TỤC', bootstyle='success-outline', width=14, command=self.continue_after_stop, state=tk.DISABLED)
        self.btn_continue_render.pack(side=RIGHT, padx=8)
        Tooltip(self.btn_continue_render, 'Chạy tiếp tác vụ vừa dừng. Hàng chờ sẽ bỏ qua video đã hoàn tất.')
        # ==============================
        # GIAO DIỆN HÀNG CHỜ VIDEO
        # ==============================
        queue_frame = tb.LabelFrame(
            container,
            text='📚 Hàng chờ xử lý video'
        )
        queue_frame.pack(
            fill=X,
            pady=(0, 15),
            ipadx=10,
            ipady=10
        )

        queue_columns = (
            'stt',
            'srt',
            'video',
            'output',
            'status'
        )

        self.queue_tree = tb.Treeview(
            queue_frame,
            columns=queue_columns,
            show='headings',
            height=4,
            bootstyle='info'
        )

        self.queue_tree.heading('stt', text='STT')
        self.queue_tree.heading('srt', text='SRT')
        self.queue_tree.heading('video', text='Video')
        self.queue_tree.heading('output', text='Video xuất')
        self.queue_tree.heading('status', text='Trạng thái')

        self.queue_tree.column(
            'stt',
            width=45,
            minwidth=45,
            anchor='center',
            stretch=False
        )

        self.queue_tree.column(
            'srt',
            width=180,
            anchor='w'
        )

        self.queue_tree.column(
            'video',
            width=180,
            anchor='w'
        )

        self.queue_tree.column(
            'output',
            width=180,
            anchor='w'
        )

        self.queue_tree.column(
            'status',
            width=110,
            anchor='center',
            stretch=False
        )

        queue_scroll = tb.Scrollbar(
            queue_frame,
            orient='vertical',
            command=self.queue_tree.yview
        )

        self.queue_tree.configure(
            yscrollcommand=queue_scroll.set
        )

        self.queue_tree.grid(
            row=0,
            column=0,
            columnspan=8,
            padx=(8, 0),
            pady=8,
            sticky='nsew'
        )

        queue_scroll.grid(
            row=0,
            column=8,
            padx=(0, 8),
            pady=8,
            sticky='ns'
        )

        queue_frame.columnconfigure(0, weight=1)

        queue_buttons = tb.Frame(queue_frame)
        queue_buttons.grid(
            row=1,
            column=0,
            columnspan=9,
            padx=8,
            pady=(0, 8),
            sticky='ew'
        )

        self.btn_queue_add = tb.Button(
            queue_buttons,
            text='➕ Thêm tác vụ hiện tại',
            bootstyle='success-outline',
            command=self.add_current_job_to_queue
        )
        self.btn_queue_add.pack(side=LEFT, padx=(0, 5))

        self.btn_queue_remove = tb.Button(
            queue_buttons,
            text='➖ Xóa mục chọn',
            bootstyle='warning-outline',
            command=self.remove_selected_queue_jobs
        )
        self.btn_queue_remove.pack(side=LEFT, padx=5)

        self.btn_queue_clear = tb.Button(
            queue_buttons,
            text='🧹 Xóa tất cả',
            bootstyle='danger-outline',
            command=self.clear_job_queue
        )
        self.btn_queue_clear.pack(side=LEFT, padx=5)

        tb.Label(
            queue_buttons,
            textvariable=self.queue_count_var,
            bootstyle='info'
        ).pack(side=LEFT, padx=15)

        self.btn_queue_stop = tb.Button(
            queue_buttons,
            text='⏹ Dừng sau video hiện tại',
            bootstyle='danger',
            command=self.request_stop_queue,
            state=tk.DISABLED
        )
        self.btn_queue_stop.pack(side=RIGHT, padx=(5, 0))

        self.btn_queue_fast = tb.Button(
            queue_buttons,
            text='⚡ Chạy hàng chờ nhanh',
            bootstyle='warning',
            command=lambda: self.start_queue_thread(fast=True)
        )
        self.btn_queue_fast.pack(side=RIGHT, padx=5)

        self.btn_queue_start = tb.Button(
            queue_buttons,
            text='▶ Chạy hàng chờ',
            bootstyle='success',
            command=lambda: self.start_queue_thread(fast=False)
        )
        self.btn_queue_start.pack(side=RIGHT, padx=5)

        shutdown_frame = tb.Frame(queue_frame)
        shutdown_frame.grid(
            row=2,
            column=0,
            columnspan=9,
            padx=8,
            pady=(0, 8),
            sticky='w'
        )

        tb.Checkbutton(
            shutdown_frame,
            text='Tự động tắt máy khi hoàn tất toàn bộ hàng chờ',
            variable=self.shutdown_after_queue,
            bootstyle='round-toggle-danger'
        ).pack(side=LEFT)

        tb.Label(
            shutdown_frame,
            text='Hẹn tắt sau:'
        ).pack(side=LEFT, padx=(20, 5))

        tb.Spinbox(
            shutdown_frame,
            from_=30,
            to=600,
            increment=30,
            textvariable=self.shutdown_delay_seconds,
            width=6
        ).pack(side=LEFT)

        tb.Label(
            shutdown_frame,
            text='giây'
        ).pack(side=LEFT, padx=(5, 15))

        tb.Button(
            shutdown_frame,
            text='Hủy lệnh tắt máy',
            bootstyle='secondary-outline',
            command=self.cancel_scheduled_shutdown
        ).pack(side=LEFT)
        progress_frame = tb.Frame(container)
        progress_frame.pack(fill=X)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = tb.Progressbar(progress_frame, orient='horizontal', mode='determinate', variable=self.progress_var, bootstyle='success-striped')
        self.progress_bar.pack(fill=X, pady=(0, 10))
        self.lbl_status = tb.Label(progress_frame, text='✅ Sẵn sàng tạo audio/video', font=(APP_FONT, 10, 'bold'), bootstyle='info')
        self.lbl_status.pack(anchor=W)
        log_frame = tb.LabelFrame(container, text='📋 Log render')
        log_frame.pack(fill=X, pady=(10, 0), ipadx=8, ipady=8)
        self.render_log = ScrolledText(log_frame, height=8, padding=6, font=(APP_FONT, 9), bootstyle='dark')
        self.render_log.pack(fill=X)
        self.render_log.text.insert(END, 'Sẵn sàng. Log render sẽ hiển thị ở đây.\n')
        self.render_log.text.config(state=DISABLED)
    def append_render_log(self, message, clear=False):
        timestamp = datetime.now().strftime('%H:%M:%S')

        def write_log():
            try:
                self.render_log.text.config(state=NORMAL)
                if clear:
                    self.render_log.text.delete('1.0', END)
                self.render_log.text.insert(END, f'[{timestamp}] {message}\n')
                self.render_log.text.see(END)
                self.render_log.text.config(state=DISABLED)
            except Exception:
                pass

        try:
            self.root.after(0, write_log)
        except Exception:
            write_log()
    def get_settings_dict(self):
        return {'use_gpu': self.use_gpu.get(), 'video_speed': self.video_speed.get(), 'keep_silence': self.keep_silence.get(), 'keep_video_effect_audio': False, 'keep_original_audio_in_silence': bool(self.keep_silence.get()), 'output_quality': self.output_quality.get(), 'split_video_parts': self.split_video_parts.get(), 'tts_speed': self.tts_speed.get(), 'tts_pitch': self.tts_pitch.get(), 'omnivoice_batch_size': self.omnivoice_batch_size.get(), 'omnivoice_mode': self.omnivoice_mode.get(), 'omnivoice_continuous': self.omnivoice_continuous.get(), 'omnivoice_lock_continuous_audio_speed': self.omnivoice_lock_continuous_audio_speed.get(), 'background_music_paths': self.background_music_paths, 'background_music_volume': self.background_music_volume.get(), 'provider': self.provider_combo.get(), 'voice': self.voice_combo.get(), 'preview_text': self.preview_text.get(), 'omnivoice_ref_audio_path': self.omnivoice_ref_audio_path, 'omnivoice_ref_text': self.omnivoice_ref_text.get()}
    def apply_settings(self, settings):
        if not settings:
            return
        else:
            self.use_gpu.set(settings.get('use_gpu', self.gpu_enabled))
            self.video_speed.set(settings.get('video_speed', 1.0))
            self.keep_silence.set(settings.get('keep_silence', True))
            self.keep_video_effect_audio.set(False)
            self.keep_original_audio_in_silence.set(bool(self.keep_silence.get()))
            self.output_quality.set(settings.get('output_quality', 'Gốc'))
            self.split_video_parts.set(settings.get('split_video_parts', 1))
            self.tts_speed.set(settings.get('tts_speed', 1.2))
            self.tts_pitch.set(settings.get('tts_pitch', 1.0))
            saved_omni_batch = int(settings.get('omnivoice_batch_size', 8) or 8)
            self.omnivoice_batch_size.set(max(1, min(8, saved_omni_batch)))
            saved_mode = settings.get('omnivoice_mode')
            if not saved_mode:
                saved_mode = 'Liền mạch toàn SRT' if settings.get('omnivoice_continuous', False) else 'Từng dòng'
            if saved_mode == 'Cụm thông minh':
                saved_mode = 'Từng dòng'
            self.omnivoice_mode.set(saved_mode)
            self.omnivoice_continuous.set(saved_mode == 'Liền mạch toàn SRT')
            self.omnivoice_lock_continuous_audio_speed.set(settings.get('omnivoice_lock_continuous_audio_speed', True))
            self.background_music_paths = filter_existing_media_paths(
                settings.get('background_music_paths', []) or []
            )
            self.background_music_volume.set(settings.get('background_music_volume', 12.0))
            self.update_background_music_label()
            self.preview_text.set(settings.get('preview_text', 'Xin chào, đây là giọng đọc thử.'))
            self.omnivoice_ref_audio_path = resolve_existing_media_path(
                settings.get('omnivoice_ref_audio_path')
            )
            self.omnivoice_ref_text.set(settings.get('omnivoice_ref_text', ''))
            if hasattr(self, 'lbl_omnivoice_ref_audio'):
                label = (
                    f'Audio mẫu: {nice_path(self.omnivoice_ref_audio_path)}'
                    if self.omnivoice_ref_audio_path
                    else 'Chưa chọn audio mẫu clone local'
                )
                self.lbl_omnivoice_ref_audio.config(text=label)
            prov = settings.get('provider', 'Google TTS')
            if prov in self.tts_providers:
                self.provider_combo.set(prov)
                self.update_voice_options(self.tts_providers[prov])
                voice = settings.get('voice', '')
                if voice in self.voice_combo['values']:
                    self.voice_combo.set(voice)

    def attach_output_quality_effect(self, editor_effects=None):
        effects = copy.deepcopy(editor_effects) if editor_effects else {}
        effects['output_quality'] = self.output_quality.get()
        return effects

    def set_last_render_output(self, path):
        if not path:
            return
        self.last_render_output_path = path
        try:
            self.btn_open_output_folder.config(state=tk.NORMAL)
        except Exception:
            pass

    def open_last_output_folder(self):
        path = self.last_render_output_path or self.output_file_path
        if not path:
            messagebox.showwarning(
                'Chưa có file',
                'Chưa có file render nào để mở thư mục.'
            )
            return

        folder = path if os.path.isdir(path) else os.path.dirname(path)
        if not folder or not os.path.exists(folder):
            messagebox.showerror(
                'Không tìm thấy thư mục',
                f'Không tìm thấy thư mục:\n{folder}'
            )
            return

        try:
            if os.name == 'nt':
                if os.path.isfile(path):
                    subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
                else:
                    subprocess.Popen(['explorer', os.path.normpath(folder)])
            else:
                subprocess.Popen(['xdg-open', folder])
        except Exception as error:
            messagebox.showerror(
                'Không mở được thư mục',
                str(error)
            )

    def select_srt_file(self):
        path = filedialog.askopenfilename(
            filetypes=[('Subtitle file', ('*.srt',))]
        )
        if path:
            self.srt_file_path = path
            self.lbl_srt_path.config(text=f'📄 SRT: {nice_path(path)}')

    def select_video_file(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ('Video files', ('*.mp4', '*.avi', '*.mkv', '*.mov')),
                ('All files', ('*.*',))
            ]
        )
        if path:
            self.video_file_path = path
            self.lbl_video_path.config(text=f'🎬 Video: {nice_path(path)}')
            if self.editor_ref is not None:
                try:
                    self.editor_ref.load_video_from_path(path)
                    if self.switch_to_editor_cb:
                        self.switch_to_editor_cb()
                except Exception:
                    pass

    def select_existing_audio_file(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ('MP3 audio', ('*.mp3',)),
                ('Audio files', ('*.mp3', '*.wav', '*.m4a', '*.aac', '*.flac', '*.ogg')),
                ('All files', ('*.*',))
            ]
        )
        if path:
            self.existing_audio_path = path
            self.lbl_existing_audio_path.config(
                text=f'🎧 MP3 khôi phục: {nice_path(path)}'
            )
            self.lbl_status.config(
                text='✅ Đã chọn MP3 có sẵn. Khi render sẽ bỏ qua TTS/Vbee.'
            )

    def clear_existing_audio_file(self):
        self.existing_audio_path = None
        self.lbl_existing_audio_path.config(
            text='🎧 Chưa chọn MP3 khôi phục'
        )
        self.lbl_status.config(
            text='✅ Đã bỏ MP3 khôi phục. Render sẽ tạo TTS như bình thường.'
        )

    def select_omnivoice_ref_audio(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ('Audio mẫu', ('*.wav', '*.mp3', '*.m4a', '*.aac', '*.flac', '*.ogg')),
                ('All files', ('*.*',))
            ]
        )
        if path:
            self.omnivoice_ref_audio_path = path
            self.lbl_omnivoice_ref_audio.config(
                text=f'Audio mẫu: {nice_path(path)}'
            )
            self.lbl_status.config(
                text='✅ Đã chọn audio mẫu để clone giọng local.'
            )

    def clear_omnivoice_ref_audio(self):
        self.omnivoice_ref_audio_path = None
        self.lbl_omnivoice_ref_audio.config(
            text='Chưa chọn audio mẫu clone local'
        )
        self.lbl_status.config(
            text='✅ Đã bỏ audio mẫu clone. Sẽ dùng preset giọng.'
        )

    def update_background_music_label(self):
        count = len(self.background_music_paths)
        if count <= 0:
            text = 'Chưa chọn nhạc nền'
        elif count == 1:
            text = f'Nhạc nền: {nice_path(self.background_music_paths[0])}'
        else:
            first_name = os.path.basename(self.background_music_paths[0])
            text = f'Nhạc nền: {count} file | bắt đầu: {first_name}'

        try:
            self.lbl_background_music.config(text=text)
        except Exception:
            pass

    def select_background_music_files(self):
        paths = filedialog.askopenfilenames(
            filetypes=[
                ('Audio nền', ('*.mp3', '*.wav', '*.m4a', '*.aac', '*.flac', '*.ogg')),
                ('All files', ('*.*',))
            ]
        )
        if paths:
            self.background_music_paths = list(paths)
            self.update_background_music_label()
            self.lbl_status.config(
                text=(
                    f'✅ Đã chọn {len(self.background_music_paths)} '
                    'file nhạc nền. Mức đề xuất 8-15%.'
                )
            )

    def clear_background_music_files(self):
        self.background_music_paths = []
        self.update_background_music_label()
        self.lbl_status.config(text='✅ Đã bỏ nhạc nền.')

    def select_output_file(self):
        path = filedialog.asksaveasfilename(defaultextension='.mp3', filetypes=[('MP3 file', ('*.mp3',))])
        if path:
            self.output_file_path = path
            self.lbl_output_path.config(text=f'💾 Lưu tại: {nice_path(path)}')
    def on_provider_change(self, event=None):
        selected_provider = self.tts_providers[self.provider_combo.get()]
        self.update_voice_options(selected_provider)
    def update_voice_options(self, provider):
        voices = self.voice_options.get(provider, {})
        self.voice_combo['values'] = list(voices.keys())
        if voices:
            self.voice_combo.current(0)
    def get_selected_voice(self):
        provider = self.tts_providers[self.provider_combo.get()]
        voice = self.voice_options[provider][self.voice_combo.get()]
        if provider == 'omnivoice':
            return build_omnivoice_voice_config(
                instruct=voice,
                ref_audio=self.omnivoice_ref_audio_path or '',
                ref_text=self.omnivoice_ref_text.get()
            )
        if provider == 'vieneu':
            return build_vieneu_voice_config(
                voice=voice,
                ref_audio=self.omnivoice_ref_audio_path or '',
                ref_text=self.omnivoice_ref_text.get()
            )
        return voice
    def open_api_key_dialog(self):
        def on_saved():
            self.lbl_status.config(text='Trạng thái: Đã cập nhật API key')

        ApiKeyDialog(self, on_saved=on_saved)

    def start_preview_thread(self):
        self.btn_preview.config(state=tk.DISABLED, text='Đang phát…')
        threading.Thread(target=self.preview_voice, daemon=True).start()

    def preview_voice(self):

        try:
            provider = self.tts_providers[
                self.provider_combo.get()
            ]

            voice = self.get_selected_voice()

            sample_text = (
                self.preview_text.get().strip()
                or 'Xin chào, đây là giọng đọc thử.'
            )

            keys = []
            vbee_app_id = ''

            if provider == 'fpt':
                keys = get_api_keys_list(
                    'FPT_API_KEY'
                )

            elif provider == 'zalo':
                keys = get_api_keys_list(
                    'ZALO_API_KEY'
                )

            elif provider == 'vbee':
                keys = get_api_keys_list(
                    'VBEE_ACCESS_TOKEN'
                )

                vbee_app_id = get_env_var(
                    'VBEE_APP_ID',
                    ''
                ).strip()

            if provider not in ('gtts',) + LOCAL_GPU_TTS_PROVIDERS and not keys:
                messagebox.showwarning(
                    'Thiếu API key',
                    f'Chưa có API key hoặc token cho {provider}.'
                )
                return

            if provider == 'vbee':
                if not vbee_app_id:
                    messagebox.showwarning(
                        'Thiếu Vbee App ID',
                        'Bạn chưa nhập Vbee App ID.'
                    )
                    return

               

            test_key = keys[0] if keys else None

            self.lbl_status.config(
                text='Đang tạo giọng đọc thử...'
            )

            if provider == 'gtts':
                seg = text_to_speech_gTTS(
                    sample_text,
                    lang=voice
                )

            elif provider == 'fpt':
                seg = text_to_speech_fpt(
                    sample_text,
                    voice,
                    test_key
                )

            elif provider == 'zalo':
                seg = text_to_speech_zalo(
                    sample_text,
                    voice,
                    test_key
                )

            elif provider == 'vbee':
                seg = text_to_speech_vbee(
                    text=sample_text,
                    voice_id=voice,
                    access_token=test_key,
                    app_id=vbee_app_id,
                    speed=1.0
                )

            elif provider == 'omnivoice':
                omni_voice = parse_omnivoice_voice_config(voice)
                seg = text_to_speech_omnivoice(
                    text=sample_text,
                    instruct=omni_voice.get('instruct', ''),
                    use_gpu=self.use_gpu.get() and self.gpu_enabled,
                    ref_audio=omni_voice.get('ref_audio', ''),
                    ref_text=omni_voice.get('ref_text', '')
                )
                seg = polish_omnivoice_segment(seg)

            elif provider == 'vieneu':
                vieneu_voice = parse_vieneu_voice_config(voice)
                ref_audio = vieneu_voice.get('ref_audio', '')
                if not ref_audio:
                    raise RuntimeError(
                        'VieNeu hiện chỉ dùng giọng clone. '
                        'Hãy chọn audio mẫu clone trước khi nghe thử.'
                    )
                if not os.path.isfile(ref_audio):
                    raise RuntimeError(
                        'Không tìm thấy audio mẫu VieNeu:\n'
                        f'{ref_audio}'
                    )
                self.lbl_status.config(
                    text='Đang test giọng clone VieNeu bằng GPU...'
                )
                seg = text_to_speech_vieneu(
                    text=sample_text,
                    voice=voice,
                    use_gpu=self.use_gpu.get() and self.gpu_enabled,
                    batch_size=self.omnivoice_batch_size.get()
                )

            else:
                raise RuntimeError(
                    'Nhà cung cấp TTS không hợp lệ.'
                )

            if seg is None or len(seg) == 0:
                raise RuntimeError(
                    'API không tạo được dữ liệu audio.'
                )

            self.lbl_status.config(
                text='Đang áp dụng hiệu ứng Speed/Pitch...'
            )

            seg = apply_audio_speed_pitch(
                seg,
                speed=self.tts_speed.get(),
                pitch=self.tts_pitch.get()
            )
            if provider == 'vieneu':
                self.lbl_status.config(
                    text='Đang làm dày thân giọng VieNeu...'
                )
                seg = clarify_vieneu_segment(
                    seg,
                    label='VieNeu nghe thử'
                )

            self.lbl_status.config(
                text='Đang phát xem trước...'
            )

            safe_play_audiosegment(seg)

            self.lbl_status.config(
                text='✅ Sẵn sàng'
            )

        except Exception as e:
            self.lbl_status.config(
                text='❌ Lỗi nghe thử'
            )

            messagebox.showerror(
                'Lỗi nghe thử',
                str(e)
            )

        finally:
            self.btn_preview.config(
                state=tk.NORMAL,
                text='▶ Nghe thử'
            )
    def make_unique_queue_output(self, output_path):
        """
        Tránh hai tác vụ trong hàng chờ ghi đè cùng một file.
        """

        output_path = os.path.abspath(output_path)

        used_paths = {
            os.path.normcase(
                os.path.abspath(job['output_path'])
            )
            for job in self.job_queue
        }

        base, extension = os.path.splitext(output_path)

        if not extension:
            extension = '.mp3'

        candidate = base + extension
        number = 2

        while os.path.normcase(candidate) in used_paths:
            candidate = f'{base}_{number}{extension}'
            number += 1

        return candidate


    def add_current_job_to_queue(self):
        if self.queue_running:
            messagebox.showwarning(
                'Hàng chờ đang chạy',
                'Không thể thêm tác vụ trong khi hàng chờ đang xử lý.'
            )
            return

        srt_path = self.srt_file_path

        video_path = (
            getattr(self.editor_ref, 'video_path', None)
            or self.video_file_path
        )

        using_existing_audio = bool(self.existing_audio_path)

        if not srt_path and not using_existing_audio:
            messagebox.showwarning(
                'Thiếu SRT',
                'Bạn chưa chọn file SRT.'
            )
            return

        if not video_path:
            messagebox.showwarning(
                'Thiếu video',
                'Bạn chưa chọn file video.'
            )
            return

        if srt_path and not os.path.isfile(srt_path):
            messagebox.showerror(
                'Lỗi',
                f'Không tìm thấy file SRT:\n{srt_path}'
            )
            return

        if not os.path.isfile(video_path):
            messagebox.showerror(
                'Lỗi',
                f'Không tìm thấy file video:\n{video_path}'
            )
            return

        if self.existing_audio_path and not os.path.isfile(self.existing_audio_path):
            messagebox.showerror(
                'Lỗi',
                f'Không tìm thấy MP3 khôi phục:\n{self.existing_audio_path}'
            )
            return

        # Không thêm trùng cùng một cặp SRT + video
        normalized_srt = (
            os.path.normcase(os.path.abspath(srt_path))
            if srt_path
            else ''
        )

        normalized_video = os.path.normcase(
            os.path.abspath(video_path)
        )

        for job in self.job_queue:
            if (
                os.path.normcase(
                    os.path.abspath(job.get('srt_path') or '')
                ) == normalized_srt
                and
                os.path.normcase(
                    os.path.abspath(job['video_path'])
                ) == normalized_video
            ):
                messagebox.showwarning(
                    'Tác vụ đã tồn tại',
                    'Cặp SRT và video này đã có trong hàng chờ.'
                )
                return

        # Nếu chưa chọn nơi lưu thì tự tạo cạnh video gốc
        output_path = self.output_file_path

        if not output_path:
            video_folder = os.path.dirname(video_path)
            video_name = os.path.splitext(
                os.path.basename(video_path)
            )[0]

            output_path = os.path.join(
                video_folder,
                f'{video_name}_tts.mp3'
            )
            final_video_preview = (
                output_path.rsplit('.', 1)[0]
                + '_synced.mp4'
            )
            if not messagebox.askyesno(
                'Chưa chọn nơi lưu',
                (
                    'Bạn chưa chọn nơi lưu cho tác vụ hàng đợi.\n\n'
                    'Ứng dụng sẽ tự lưu cạnh video gốc:\n'
                    f'{final_video_preview}\n\n'
                    'Bạn có muốn tiếp tục không?'
                )
            ):
                return

        output_path = self.make_unique_queue_output(
            output_path
        )

        provider = self.tts_providers[
            self.provider_combo.get()
        ]

        voice = self.get_selected_voice()
        if provider == 'omnivoice':
            omni_voice = parse_omnivoice_voice_config(voice)
            ref_audio = omni_voice.get('ref_audio', '')
            if ref_audio and not os.path.isfile(ref_audio):
                messagebox.showerror(
                    'Lỗi',
                    f'Không tìm thấy audio mẫu OmniVoice:\n{ref_audio}'
                )
                return
        elif provider == 'vieneu':
            vieneu_voice = parse_vieneu_voice_config(voice)
            ref_audio = vieneu_voice.get('ref_audio', '')
            if not ref_audio:
                messagebox.showwarning(
                    'Thiếu audio mẫu clone',
                    'VieNeu hiện chỉ dùng giọng clone. Hãy chọn audio mẫu clone.'
                )
                return
            if not os.path.isfile(ref_audio):
                messagebox.showerror(
                    'Lỗi',
                    f'Không tìm thấy audio mẫu VieNeu:\n{ref_audio}'
                )
                return
        editor_effects = None
        editor_has_effects = False
        if self.editor_ref:
            if hasattr(self.editor_ref, 'get_ffmpeg_effects_config_for_video'):
                editor_effects = copy.deepcopy(
                    self.editor_ref.get_ffmpeg_effects_config_for_video(
                        video_path
                    )
                )
                if hasattr(self.editor_ref, 'has_active_effects_for_video'):
                    editor_has_effects = bool(
                        self.editor_ref.has_active_effects_for_video(
                            video_path
                        )
                    )
                else:
                    editor_has_effects = bool(editor_effects)
            else:
                try:
                    same_editor_video = (
                        os.path.normcase(os.path.abspath(getattr(self.editor_ref, 'video_path', '') or ''))
                        == os.path.normcase(os.path.abspath(video_path))
                    )
                except Exception:
                    same_editor_video = False
                if (
                    same_editor_video
                    and hasattr(self.editor_ref, 'has_active_effects')
                    and self.editor_ref.has_active_effects()
                ):
                    editor_has_effects = True
                    if hasattr(self.editor_ref, 'get_ffmpeg_effects_config'):
                        editor_effects = copy.deepcopy(
                            self.editor_ref.get_ffmpeg_effects_config()
                        )
        editor_effects = self.attach_output_quality_effect(editor_effects)

        job = {
            'srt_path': os.path.abspath(srt_path) if srt_path else None,
            'video_path': os.path.abspath(video_path),
            'output_path': output_path,
            'existing_audio_path': os.path.abspath(self.existing_audio_path) if self.existing_audio_path else None,

            # Chụp lại cài đặt tại thời điểm thêm vào hàng chờ
            'provider': provider,
            'voice': voice,
            'omnivoice_ref_audio_path': self.omnivoice_ref_audio_path,
            'omnivoice_ref_text': self.omnivoice_ref_text.get(),
            'use_gpu': bool(
                self.use_gpu.get()
                and self.gpu_enabled
            ),
            'keep_silence': bool(
                self.keep_silence.get()
            ),
            'keep_video_effect_audio': False,
            'keep_original_audio_in_silence': bool(
                self.keep_silence.get()
            ),
            'video_speed': float(
                self.video_speed.get()
            ),
            'tts_speed': float(
                self.tts_speed.get()
            ),
            'tts_pitch': float(
                self.tts_pitch.get()
            ),
            'omnivoice_batch_size': int(
                self.omnivoice_batch_size.get()
            ),
            'omnivoice_mode': self.omnivoice_mode.get(),
            'omnivoice_continuous': bool(
                self.omnivoice_mode.get() == 'Liền mạch toàn SRT'
            ),
            'omnivoice_lock_continuous_audio_speed': bool(
                self.omnivoice_lock_continuous_audio_speed.get()
            ),
            'background_music_paths': list(self.background_music_paths),
            'background_music_volume': float(
                self.background_music_volume.get()
            ),
            'output_quality': self.output_quality.get(),
            'split_video_parts': int(self.split_video_parts.get() or 1),
            'editor_effects': copy.deepcopy(editor_effects),
            'editor_has_effects': editor_has_effects,

            'status': 'Chờ',
            'error': ''
        }

        self.job_queue.append(job)
        self.refresh_queue_tree()

        # Tránh tác vụ sau vô tình dùng chung file MP3 đầu ra
        self.output_file_path = None
        self.lbl_output_path.config(
            text='💾 Chưa chọn nơi lưu Audio/Video'
        )

        self.lbl_status.config(
            text=(
                f'✅ Đã thêm tác vụ số '
                f'{len(self.job_queue)} vào hàng chờ'
            )
        )


    def refresh_queue_tree(self):
        for item_id in self.queue_tree.get_children():
            self.queue_tree.delete(item_id)

        for index, job in enumerate(self.job_queue):
            final_video_path = (
                job['output_path'].rsplit('.', 1)[0]
                + '_synced.mp4'
            )

            status = job.get('status', 'Chờ')

            if status == 'Hoàn tất':
                tag = 'success'
            elif status == 'Lỗi':
                tag = 'danger'
            elif status == 'Đang xử lý':
                tag = 'processing'
            else:
                tag = 'waiting'

            self.queue_tree.insert(
                '',
                'end',
                iid=str(index),
                values=(
                    index + 1,
                    os.path.basename(job['srt_path']) if job.get('srt_path') else 'Không dùng SRT',
                    os.path.basename(job['video_path']),
                    os.path.basename(final_video_path),
                    f'{status} | MP3 có sẵn' if job.get('existing_audio_path') else status
                ),
                tags=(tag,)
            )

        self.queue_tree.tag_configure(
            'success',
            foreground='#00d084'
        )

        self.queue_tree.tag_configure(
            'danger',
            foreground='#ff4d6d'
        )

        self.queue_tree.tag_configure(
            'processing',
            foreground='#ffb020'
        )

        self.queue_count_var.set(
            f'Hàng chờ: {len(self.job_queue)} video'
        )


    def remove_selected_queue_jobs(self):
        if self.queue_running:
            messagebox.showwarning(
                'Hàng chờ đang chạy',
                'Không thể xóa tác vụ khi hàng chờ đang xử lý.'
            )
            return

        selected_items = self.queue_tree.selection()

        if not selected_items:
            messagebox.showwarning(
                'Chưa chọn',
                'Hãy chọn tác vụ cần xóa.'
            )
            return

        indexes = sorted(
            (int(item_id) for item_id in selected_items),
            reverse=True
        )

        for index in indexes:
            if 0 <= index < len(self.job_queue):
                self.job_queue.pop(index)

        self.refresh_queue_tree()


    def clear_job_queue(self):
        if self.queue_running:
            messagebox.showwarning(
                'Hàng chờ đang chạy',
                'Không thể xóa hàng chờ khi đang xử lý.'
            )
            return

        if not self.job_queue:
            return

        confirm = messagebox.askyesno(
            'Xóa hàng chờ',
            'Bạn có chắc muốn xóa toàn bộ tác vụ?'
        )

        if not confirm:
            return

        self.job_queue.clear()
        self.refresh_queue_tree()


    def get_keys_for_queue_provider(self, provider):
        if provider == 'gtts':
            return []

        if provider in LOCAL_GPU_TTS_PROVIDERS:
            return [f'{provider}_local']

        if provider == 'fpt':
            keys = get_api_keys_list(
                'FPT_API_KEY'
            )

        elif provider == 'zalo':
            keys = get_api_keys_list(
                'ZALO_API_KEY'
            )

        elif provider == 'vbee':
            keys = get_api_keys_list(
                'VBEE_ACCESS_TOKEN'
            )

            app_id = get_env_var(
                'VBEE_APP_ID',
                ''
            ).strip()

            if not app_id:
                raise RuntimeError(
                    'Bạn chưa nhập Vbee App ID.'
                )

        else:
            raise RuntimeError(
                f'Nhà cung cấp không hợp lệ: {provider}'
            )

        if not keys:
            raise RuntimeError(
                f'Chưa cấu hình API key/token cho {provider}.'
            )

        return keys


    def set_queue_controls_running(self, running):
        normal_state = (
            tk.DISABLED if running else tk.NORMAL
        )

        self.btn_queue_add.config(
            state=normal_state
        )

        self.btn_queue_remove.config(
            state=normal_state
        )

        self.btn_queue_clear.config(
            state=normal_state
        )

        self.btn_queue_start.config(
            state=normal_state
        )

        self.btn_queue_fast.config(
            state=normal_state
        )

        self.btn_queue_stop.config(
            state=tk.NORMAL if running else tk.DISABLED
        )

        # Không cho chạy tác vụ đơn đồng thời với hàng chờ
        self.btn_convert.config(
            state=normal_state
        )

        self.btn_fast_convert.config(
            state=normal_state
        )

        self.btn_effects_only.config(
            state=normal_state
        )


    def request_stop_render(self):
        self.stop_render_requested = True

        if self.render_stop_event:
            self.render_stop_event.set()

        if hasattr(self, 'queue_stop_event'):
            self.queue_stop_event.set()

        for process in list(ACTIVE_FFMPEG_PROCESSES):
            try:
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass

        self.append_render_log(
            'Đã yêu cầu dừng thủ công. Tool sẽ dừng sớm nhất có thể.'
        )
        self.btn_continue_render.config(state=tk.NORMAL)
        self.lbl_status.config(
            text='⏹ Đang dừng tác vụ hiện tại...'
        )


    def continue_after_stop(self):
        if self.queue_running:
            messagebox.showwarning(
                'Đang xử lý',
                'Hàng chờ vẫn đang chạy, chưa thể tiếp tục tác vụ khác.'
            )
            return

        self.stop_render_requested = False
        self.btn_continue_render.config(state=tk.DISABLED)

        if self.last_stop_context == 'queue':
            self.append_render_log('Tiếp tục hàng chờ từ các video chưa hoàn tất.')
            self.start_queue_thread(
                fast=self.last_queue_fast,
                resume=True
            )
            return

        if self.last_stop_context == 'effects':
            self.append_render_log('Chạy lại render hiệu ứng vừa dừng.')
            self.start_effects_only_render_thread(
                fast=self.last_effects_fast
            )
            return

        if self.last_stop_context == 'single':
            self.append_render_log('Chạy lại tác vụ render vừa dừng.')
            self.start_conversion_thread(
                fast=self.last_single_fast
            )
            return

        messagebox.showinfo(
            'Chưa có tác vụ',
            'Chưa có tác vụ vừa dừng để tiếp tục.'
        )


    def request_stop_queue(self):
        if not self.queue_running:
            return

        self.stop_queue_requested = True
        self.last_stop_context = 'queue'
        self.queue_stop_event.set()
        self.request_stop_render()

        self.lbl_status.config(
            text=(
                '⏹ Đã yêu cầu dừng. '
                'Tool sẽ dừng sớm nhất có thể.'
            )
        )


    def start_queue_thread(self, fast=False, resume=False):
        if self.queue_running:
            messagebox.showwarning(
                'Đang xử lý',
                'Hàng chờ đang được xử lý.'
            )
            return

        if not self.job_queue:
            messagebox.showwarning(
                'Hàng chờ trống',
                'Hãy thêm ít nhất một tác vụ vào hàng chờ.'
            )
            return

        pending_jobs = [
            job for job in self.job_queue
            if resume and job.get('status') == 'Hoàn tất'
        ]
        if resume and len(pending_jobs) == len(self.job_queue):
            messagebox.showinfo(
                'Hàng chờ',
                'Tất cả video trong hàng chờ đã hoàn tất.'
            )
            return

        # Đọc trước trên luồng giao diện
        shutdown_when_done = bool(
            self.shutdown_after_queue.get()
        )

        try:
            shutdown_delay = max(
                30,
                int(self.shutdown_delay_seconds.get())
            )
        except Exception:
            shutdown_delay = 60

        for job in self.job_queue:
            if resume and job.get('status') == 'Hoàn tất':
                continue
            job['status'] = 'Chờ'
            job['error'] = ''

        self.refresh_queue_tree()

        self.queue_running = True
        self.stop_queue_requested = False
        self.last_stop_context = 'queue'
        self.last_queue_fast = fast
        self.queue_stop_event.clear()
        self.set_queue_controls_running(True)
        self.btn_continue_render.config(state=tk.DISABLED)
        self.append_render_log(
            f'Bắt đầu hàng chờ: {len(self.job_queue)} video | fast={fast} | resume={resume}',
            clear=True
        )
        self.append_render_log(
            'Tự động tắt máy sau hàng chờ: '
            f'{"BẬT" if shutdown_when_done else "TẮT"}'
            + (f' | sau {shutdown_delay}s' if shutdown_when_done else '')
        )

        threading.Thread(
            target=self.run_job_queue,
            args=(
                fast,
                shutdown_when_done,
                shutdown_delay
            ),
            daemon=True
        ).start()


    def run_job_queue(
        self,
        fast_render,
        shutdown_when_done,
        shutdown_delay
    ):
        total_jobs = len(self.job_queue)
        completed_jobs = 0
        failed_jobs = []

        for job_index, job in enumerate(self.job_queue):
            if self.stop_queue_requested or self.queue_stop_event.is_set():
                break

            if job.get('status') == 'Hoàn tất':
                completed_jobs += 1
                continue

            job['status'] = 'Đang xử lý'

            self.root.after(
                0,
                self.refresh_queue_tree
            )

            def update_progress(
                current,
                total,
                phase,
                current_job_index=job_index
            ):
                local_percent = (
                    current / total * 100
                    if total
                    else 0
                )

                overall_percent = (
                    (
                        current_job_index
                        + local_percent / 100
                    )
                    / total_jobs
                    * 100
                )

                def update_ui():
                    self.progress_var.set(
                        overall_percent
                    )

                    self.lbl_status.config(
                        text=(
                            f'Video {current_job_index + 1}/'
                            f'{total_jobs} — '
                            f'[{phase}] '
                            f'{local_percent:.0f}%'
                        )
                    )

                self.root.after(0, update_ui)

            try:
                self.append_render_log(
                    f'Video {job_index + 1}/{total_jobs}: {os.path.basename(job["video_path"])}'
                )
                if job.get('existing_audio_path'):
                    keys = []
                    self.append_render_log(
                        f'Dùng MP3 có sẵn, bỏ qua TTS/API: {job["existing_audio_path"]}'
                    )
                else:
                    keys = self.get_keys_for_queue_provider(
                        job['provider']
                    )
                edited_clip = None
                editor_effects = copy.deepcopy(job.get('editor_effects'))
                if (
                    job.get('editor_has_effects')
                    and not fast_render
                    and editor_effects is None
                    and self.editor_ref
                    and hasattr(self.editor_ref, 'create_edited_clip')
                ):
                    edited_clip = self.editor_ref.create_edited_clip()
                    editor_effects = None
                editor_effects = copy.deepcopy(editor_effects) if editor_effects else {}
                editor_effects['output_quality'] = job.get('output_quality', 'Gốc')

                rendered_output = process_audio_and_video(
                    srt_path=job['srt_path'],
                    output_path=job['output_path'],
                    provider=job['provider'],
                    voice=job['voice'],
                    keys=keys,

                    # Hàng chờ dùng trực tiếp đường dẫn video
                    video_path=job['video_path'],
                    video_clip=edited_clip,

                    keep_silence=job['keep_silence'],
                    use_gpu=job['use_gpu'],
                    progress_callback=update_progress,
                    video_speed=job['video_speed'],
                    tts_speed=job['tts_speed'],
                    tts_pitch=job['tts_pitch'],
                    fast_render=fast_render,
                    editor_effects=editor_effects,
                    log_callback=self.append_render_log,
                    existing_audio_path=job.get('existing_audio_path'),
                    keep_video_effect_audio=False,
                    keep_original_audio_in_silence=job.get('keep_silence', False),
                    stop_event=self.queue_stop_event,
                    omnivoice_batch_size=job.get('omnivoice_batch_size', 8),
                    omnivoice_continuous=job.get('omnivoice_continuous', True),
                    omnivoice_mode=job.get('omnivoice_mode', 'Từng dòng'),
                    omnivoice_lock_continuous_audio_speed=job.get('omnivoice_lock_continuous_audio_speed', True),
                    background_music_paths=job.get('background_music_paths', []),
                    background_music_volume=job.get('background_music_volume', 12.0),
                    split_video_parts=job.get('split_video_parts', 1)
                )
                self.root.after(
                    0,
                    lambda path=rendered_output: self.set_last_render_output(path)
                )

                job['status'] = 'Hoàn tất'
                self.append_render_log(f'Hoàn tất video {job_index + 1}/{total_jobs}')
                completed_jobs += 1

            except Exception as error:
                if self.stop_queue_requested or self.queue_stop_event.is_set():
                    job['status'] = 'Đã dừng'
                    job['error'] = ''
                    self.append_render_log(
                        f'Đã dừng video {job_index + 1}/{total_jobs}.'
                    )
                    self.root.after(
                        0,
                        self.refresh_queue_tree
                    )
                    break

                job['status'] = 'Lỗi'
                job['error'] = str(error)
                self.append_render_log(f'LỖI video {job_index + 1}: {error}')

                failed_jobs.append(
                    (
                        job_index,
                        str(error)
                    )
                )

                print(
                    f'[QUEUE ERROR] Tác vụ '
                    f'{job_index + 1}: {error}'
                )

            self.root.after(
                0,
                self.refresh_queue_tree
            )

        was_stopped = (
            self.stop_queue_requested
            or self.queue_stop_event.is_set()
        )

        self.queue_running = False

        def finish_queue_ui():
            self.set_queue_controls_running(False)
            self.progress_var.set(0)

            if was_stopped:
                self.btn_continue_render.config(
                    state=tk.NORMAL
                )
                self.lbl_status.config(
                    text=(
                        f'⏹ Đã dừng hàng chờ. '
                        f'Hoàn tất {completed_jobs}/'
                        f'{total_jobs} video.'
                    )
                )

                messagebox.showinfo(
                    'Đã dừng hàng chờ',
                    (
                        f'Đã hoàn tất {completed_jobs}/'
                        f'{total_jobs} video.'
                    )
                )

                return

            if failed_jobs:
                self.btn_continue_render.config(
                    state=tk.DISABLED
                )
                self.lbl_status.config(
                    text=(
                        f'⚠ Hàng chờ hoàn tất với '
                        f'{len(failed_jobs)} lỗi.'
                    )
                )

                error_lines = []

                for index, error in failed_jobs[:5]:
                    error_lines.append(
                        f'- Video {index + 1}: '
                        f'{error[:150]}'
                    )

                error_text = '\n'.join(error_lines)

                messagebox.showerror(
                    'Hàng chờ có lỗi',
                    (
                        f'Hoàn tất: {completed_jobs}/'
                        f'{total_jobs}\n'
                        f'Lỗi: {len(failed_jobs)}\n\n'
                        f'{error_text}\n\n'
                        'Máy tính sẽ không tự tắt '
                        'vì có tác vụ bị lỗi.'
                    )
                )

                return

            self.lbl_status.config(
                text=(
                    f'✅ Đã hoàn tất toàn bộ '
                    f'{total_jobs} video.'
                )
            )
            self.btn_continue_render.config(
                state=tk.DISABLED
            )

            final_shutdown_when_done = bool(
                self.shutdown_after_queue.get()
            )
            try:
                final_shutdown_delay = max(
                    30,
                    int(self.shutdown_delay_seconds.get())
                )
            except Exception:
                final_shutdown_delay = shutdown_delay

            if final_shutdown_when_done:
                self.schedule_windows_shutdown(
                    final_shutdown_delay,
                    show_popup=False
                )

            done_message = f'Đã xử lý thành công {total_jobs} video.'
            if final_shutdown_when_done:
                done_message += (
                    '\n\n'
                    f'Đã lên lịch tắt máy sau {final_shutdown_delay} giây. '
                    'Nhấn “Hủy lệnh tắt máy” nếu cần.'
                )

            messagebox.showinfo(
                'Hoàn tất hàng chờ',
                done_message
            )

        self.root.after(
            0,
            finish_queue_ui
        )


    def schedule_windows_shutdown(self, delay_seconds=60, show_popup=True):
        if os.name != 'nt':
            messagebox.showwarning(
                'Không hỗ trợ',
                'Chức năng tự tắt hiện chỉ được thiết lập cho Windows.'
            )
            return

        try:
            delay_seconds = max(
                30,
                int(delay_seconds)
            )

            subprocess.run(
                [
                    'shutdown',
                    '/a'
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            subprocess.run(
                [
                    'shutdown',
                    '/s',
                    '/t',
                    str(delay_seconds)
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.lbl_status.config(
                text=(
                    f'⏻ Máy tính sẽ tắt sau '
                    f'{delay_seconds} giây.'
                )
            )
            self.append_render_log(
                f'Đã lên lịch tắt máy sau {delay_seconds} giây.'
            )

            if show_popup:
                messagebox.showinfo(
                    'Đã lên lịch tắt máy',
                    (
                        f'Máy tính sẽ tự động tắt sau '
                        f'{delay_seconds} giây.\n\n'
                        'Nhấn “Hủy lệnh tắt máy” nếu cần.'
                    )
                )

        except Exception as error:
            self.append_render_log(
                f'Không thể lên lịch tắt máy: {error}'
            )
            messagebox.showerror(
                'Không thể tắt máy',
                str(error)
            )


    def cancel_scheduled_shutdown(self):
        if os.name != 'nt':
            return

        result = subprocess.run(
            [
                'shutdown',
                '/a'
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        if result.returncode == 0:
            self.lbl_status.config(
                text='✅ Đã hủy lệnh tắt máy.'
            )

            messagebox.showinfo(
                'Đã hủy',
                'Đã hủy lệnh tắt máy.'
            )

        else:
            messagebox.showwarning(
                'Không có lệnh tắt máy',
                'Hiện không có lịch tắt máy nào để hủy.'
            )        
    def start_conversion_thread(self, fast=False):
        if not self.output_file_path:
            messagebox.showwarning('Cảnh báo', 'Vui lòng chọn nơi lưu!')
            return
        if not self.srt_file_path and not self.existing_audio_path:
            messagebox.showwarning('Cảnh báo', 'Vui lòng chọn file SRT hoặc MP3 đã có!')
            return
        else:
            effective_video_path = getattr(self.editor_ref, 'video_path', None) or self.video_file_path
            edited_clip = None
            editor_effects = None
            editor_has_effects = (
                self.editor_ref
                and hasattr(self.editor_ref, 'has_active_effects')
                and self.editor_ref.has_active_effects()
            )
            if effective_video_path and self.editor_ref and editor_has_effects:
                    if hasattr(self.editor_ref, 'get_ffmpeg_effects_config'):
                        editor_effects = copy.deepcopy(
                            self.editor_ref.get_ffmpeg_effects_config()
                        )
                    if editor_effects is None:
                        try:
                            self.lbl_status.config(text='Trạng thái: Đang nạp hiệu ứng Video...')
                            edited_clip = self.editor_ref.create_edited_clip()
                        except Exception as e:
                            messagebox.showerror('Lỗi Render Video', f'Lỗi áp dụng hiệu ứng Editor: {e}')
                            self.lbl_status.config(text='Trạng thái: Lỗi tạo Video')
                            return None
            editor_effects = self.attach_output_quality_effect(editor_effects)
            self.btn_convert.config(state=tk.DISABLED, text='Đang xử lý...')
            self.btn_fast_convert.config(state=tk.DISABLED, text='Đang xử lý...')
            self.render_stop_event = threading.Event()
            self.stop_render_requested = False
            self.last_stop_context = 'single'
            self.last_single_fast = fast
            self.btn_stop_render.config(state=tk.NORMAL)
            self.btn_continue_render.config(state=tk.DISABLED)
            threading.Thread(target=self.run_conversion, args=(effective_video_path, edited_clip, fast, copy.deepcopy(editor_effects), self.render_stop_event), daemon=True).start()

    def _effects_only_output_path(self, video_path):
        if self.output_file_path:
            base, ext = os.path.splitext(self.output_file_path)
            return base + '_effects.mp4'

        folder = os.path.dirname(video_path)
        name = os.path.splitext(os.path.basename(video_path))[0]
        return os.path.join(folder, f'{name}_effects.mp4')

    def start_effects_only_render_thread(self, fast=True):
        effective_video_path = (
            getattr(self.editor_ref, 'video_path', None)
            or self.video_file_path
        )

        if not effective_video_path:
            messagebox.showwarning('Thiếu video', 'Vui lòng chọn video trong tab Chỉnh Video hoặc Tạo giọng & Video.')
            return

        if not os.path.isfile(effective_video_path):
            messagebox.showerror('Lỗi', f'Không tìm thấy video:\n{effective_video_path}')
            return

        if not self.editor_ref or not hasattr(self.editor_ref, 'get_ffmpeg_effects_config'):
            messagebox.showerror('Lỗi', 'Không tìm thấy cấu hình hiệu ứng Editor.')
            return

        has_srt_for_sub_blur = bool(
            self.srt_file_path
            and os.path.isfile(self.srt_file_path)
        )

        if (
            hasattr(self.editor_ref, 'has_active_effects')
            and not self.editor_ref.has_active_effects()
            and not has_srt_for_sub_blur
        ):
            if not messagebox.askyesno(
                'Chưa có hiệu ứng',
                'Bạn chưa bật hiệu ứng nào. Vẫn render lại video không?'
            ):
                return

        editor_effects = copy.deepcopy(
            self.editor_ref.get_ffmpeg_effects_config()
        )
        editor_effects = self.attach_output_quality_effect(editor_effects)
        if has_srt_for_sub_blur:
            editor_effects['subtitle_in_blur'] = True

        subtitle_in_blur = bool(editor_effects.get('subtitle_in_blur'))
        if self.existing_audio_path and not has_srt_for_sub_blur:
            notice = (
                'Nút này chỉ render hiệu ứng và giữ audio gốc, '
                'không tạo/gắn giọng TTS.'
            )
            notice += (
                '\n\nMP3 đã chọn sẽ bị bỏ qua. Muốn dùng MP3/TTS hãy bấm '
                'TẠO NGAY hoặc RENDER NHANH.'
            )
            if not messagebox.askyesno(
                'Render không ghép TTS',
                notice + '\n\nBạn vẫn muốn render không TTS không?'
            ):
                return

        output_video_path = self._effects_only_output_path(effective_video_path)

        self.btn_convert.config(state=tk.DISABLED)
        self.btn_fast_convert.config(state=tk.DISABLED)
        self.btn_effects_only.config(state=tk.DISABLED, text='Đang render...')
        self.render_stop_event = threading.Event()
        self.stop_render_requested = False
        self.last_stop_context = 'effects'
        self.last_effects_fast = fast
        self.btn_stop_render.config(state=tk.NORMAL)
        self.btn_continue_render.config(state=tk.DISABLED)
        threading.Thread(
            target=self.run_effects_only_render,
            args=(
                effective_video_path,
                output_video_path,
                fast,
                copy.deepcopy(editor_effects),
                self.srt_file_path
            ),
            daemon=True
        ).start()

    def run_effects_only_render(self, video_path, output_video_path, fast_render, editor_effects, srt_path=None):
        try:
            use_gpu = self.use_gpu.get() and self.gpu_enabled
            self.append_render_log(
                f'Bắt đầu render hiệu ứng-only | fast={fast_render} | GPU={use_gpu}',
                clear=True
            )
            _render_start = time.time()
            subtitle_timeline_subs = None
            if editor_effects and editor_effects.get('subtitle_in_blur'):
                if srt_path and os.path.isfile(srt_path):
                    self.append_render_log(f'Đọc SRT để chèn phụ đề: {srt_path}')
                    try:
                        subtitle_timeline_subs = pysrt.open(
                            srt_path,
                            encoding="utf-8"
                        )
                    except Exception as error:
                        raise RuntimeError(f'Không đọc được SRT để chèn phụ đề: {error}')
                else:
                    self.append_render_log(
                        'Đã bật chèn SRT nhưng chưa chọn file SRT, '
                        'bỏ qua phần phụ đề.'
                    )

            def update_progress(current, total, phase):
                percent = current / total * 100 if total else 0
                self.progress_var.set(percent)
                elapsed = time.time() - _render_start
                if percent > 2:
                    eta_s = int(elapsed / (percent / 100) - elapsed)
                    eta_txt = f'  ⏱ còn ~{eta_s}s' if eta_s > 1 else '  ✅ Sắp xong!'
                else:
                    eta_txt = ''
                self.lbl_status.config(text=f'[{phase}] {percent:.0f}%{eta_txt}')

            render_video_effects_only(
                video_path=video_path,
                output_video_path=output_video_path,
                use_gpu=use_gpu,
                fast_render=fast_render,
                video_speed=self.video_speed.get(),
                editor_effects=editor_effects,
                subtitle_timeline_subs=subtitle_timeline_subs,
                progress_callback=update_progress,
                log_callback=self.append_render_log
            )
            split_rendered_video_parts(
                output_video_path,
                parts=self.split_video_parts.get(),
                log_callback=self.append_render_log
            )

            elapsed_total = time.time() - _render_start
            elapsed_str = f'{elapsed_total:.0f}s' if elapsed_total < 60 else f'{elapsed_total / 60:.1f}m'
            self.lbl_status.config(text=f'✅ Render sub mờ giữ âm gốc xong! ({elapsed_str})')
            self.append_render_log(f'Hoàn tất render sub mờ giữ âm gốc sau {elapsed_str}: {output_video_path}')
            self.set_last_render_output(output_video_path)
            self.btn_continue_render.config(state=tk.DISABLED)
            messagebox.showinfo('✅ Hoàn Tất!', f'Đã xuất video giữ âm gốc, không TTS:\n{output_video_path}\n\nThời gian: {elapsed_str}')
        except Exception as e:
            self.append_render_log(f'LỖI render hiệu ứng-only: {e}')
            if self.stop_render_requested:
                self.lbl_status.config(text='⏹ Đã dừng render hiệu ứng.')
                self.append_render_log('Đã dừng render hiệu ứng theo yêu cầu.')
            else:
                messagebox.showerror('❌ Lỗi Xuất', f'Đã xảy ra lỗi:\n{str(e)}')
                self.lbl_status.config(text=f'❌ Lỗi: {str(e)[:60]}')
        finally:
            self.btn_convert.config(state=tk.NORMAL, text='🚀 TẠO NGAY')
            self.btn_fast_convert.config(state=tk.NORMAL, text='⚡ RENDER NHANH')
            self.btn_effects_only.config(state=tk.NORMAL, text='🎬 SUB MỜ (ÂM GỐC)')
            self.btn_stop_render.config(state=tk.DISABLED)
            if self.stop_render_requested:
                self.btn_continue_render.config(state=tk.NORMAL)
            self.progress_var.set(0)

    def run_conversion(self, effective_video_path, edited_clip, fast_render, editor_effects=None, stop_event=None):
        try:
            use_gpu = self.use_gpu.get() and self.gpu_enabled
            self.append_render_log(
                (
                    f'{APP_BUILD} | Bắt đầu render 1 video | '
                    f'fast={fast_render} | GPU={use_gpu}'
                ),
                clear=True
            )
            if fast_render:
                self.lbl_status.config(text='Trạng thái: ⚡ Bắt đầu chế độ Render Siêu Tốc...')
            else:
                self.lbl_status.config(text='Trạng thái: Bắt đầu tải âm thanh...')
            _render_start = time.time()
            _render_last_phase = [None]
            def update_progress(current, total, phase):
                percent = current / total * 100 if total else 0
                self.progress_var.set(percent)
                elapsed = time.time() - _render_start
                if percent > 2 and phase!= _render_last_phase[0]:
                        _render_last_phase[0] = phase
                if percent > 2:
                    eta_s = int(elapsed / (percent / 100) - elapsed)
                    eta_txt = f'  ⏱ còn ~{eta_s}s' if eta_s > 1 else '  ✅ Sắp xong!'
                else:
                    eta_txt = ''
                self.lbl_status.config(text=f'[{phase}] {current}/{total}  ({percent:.0f}%){eta_txt}')
            provider = self.tts_providers[self.provider_combo.get()]
            voice = self.get_selected_voice()
            keys = []
            if self.existing_audio_path:
                if not os.path.isfile(self.existing_audio_path):
                    raise Exception(
                        f'Không tìm thấy MP3 khôi phục:\n{self.existing_audio_path}'
                    )
                self.append_render_log(
                    f'Dùng MP3 có sẵn, bỏ qua TTS/API: {self.existing_audio_path}'
                )
            elif provider == 'fpt':
                keys = get_api_keys_list('FPT_API_KEY')
            elif provider == 'vieneu':
                vieneu_voice = parse_vieneu_voice_config(voice)
                ref_audio = vieneu_voice.get('ref_audio', '')
                if not ref_audio:
                    raise Exception(
                        'VieNeu hiện chỉ dùng giọng clone. '
                        'Hãy chọn audio mẫu clone trước khi render.'
                    )
                if not os.path.isfile(ref_audio):
                    raise Exception(
                        f'Không tìm thấy audio mẫu VieNeu:\n{ref_audio}'
                    )
                self.append_render_log(
                    'VieNeu: chỉ dùng giọng clone từ audio mẫu, '
                    'không dùng preset.'
                )
            else:
                if provider == 'zalo':
                    keys = get_api_keys_list('ZALO_API_KEY')
                else:
                    if provider == 'vbee':
                        keys = get_api_keys_list(
                            'VBEE_ACCESS_TOKEN'
                        )

                        vbee_app_id = get_env_var(
                            'VBEE_APP_ID',
                            ''
                        ).strip()

                        if not keys:
                            raise Exception(
                                'Bạn chưa nhập Vbee Access Token.'
                            )

                        if not vbee_app_id:
                            raise Exception(
                                'Bạn chưa nhập Vbee App ID.'
                            )
            rendered_output = process_audio_and_video(
                srt_path=self.srt_file_path,
                output_path=self.output_file_path,
                provider=provider,
                voice=voice,
                keys=keys,
                video_path=effective_video_path,
                video_clip=edited_clip,
                keep_silence=self.keep_silence.get(),
                use_gpu=use_gpu,
                progress_callback=update_progress,
                video_speed=self.video_speed.get(),
                tts_speed=self.tts_speed.get(),
                tts_pitch=self.tts_pitch.get(),
                fast_render=fast_render,
                editor_effects=editor_effects,
                log_callback=self.append_render_log,
                existing_audio_path=self.existing_audio_path,
                keep_video_effect_audio=False,
                keep_original_audio_in_silence=self.keep_silence.get(),
                stop_event=stop_event,
                omnivoice_batch_size=self.omnivoice_batch_size.get(),
                omnivoice_continuous=self.omnivoice_mode.get() == 'Liền mạch toàn SRT',
                omnivoice_mode=self.omnivoice_mode.get(),
                omnivoice_lock_continuous_audio_speed=self.omnivoice_lock_continuous_audio_speed.get(),
                background_music_paths=list(self.background_music_paths),
                background_music_volume=self.background_music_volume.get(),
                split_video_parts=self.split_video_parts.get()
            )
            elapsed_total = time.time() - _render_start
            elapsed_str = f'{elapsed_total:.0f}s' if elapsed_total < 60 else f'{elapsed_total / 60:.1f}m'
            mode_lbl = '⚡ Siêu Tốc' if fast_render else '🚀 Chất Lượng Cao'
            self.set_last_render_output(rendered_output)
            self.btn_continue_render.config(state=tk.DISABLED)
            messagebox.showinfo('✅ Hoàn Tất!', f'Xuất file thành công!\nChế độ: {mode_lbl}\nThời gian: {elapsed_str}\n\nFile kết quả:\n{rendered_output}')
            self.lbl_status.config(text=f'✅ Hoàn tất! ({mode_lbl} | {elapsed_str})')
            self.append_render_log(f'Hoàn tất render 1 video sau {elapsed_str}: {rendered_output}')
        except Exception as e:
            self.append_render_log(f'LỖI render: {e}')
            if stop_event and stop_event.is_set():
                self.lbl_status.config(text='⏹ Đã dừng render theo yêu cầu.')
                self.append_render_log('Đã dừng render theo yêu cầu người dùng.')
            else:
                messagebox.showerror('❌ Lỗi Xuất', f'Đã xảy ra lỗi:\n{str(e)}')
                self.lbl_status.config(text=f'❌ Lỗi: {str(e)[:60]}')
        finally:
            self.btn_convert.config(state=tk.NORMAL, text='🚀 TẠO NGAY')
            self.btn_fast_convert.config(state=tk.NORMAL, text='⚡ RENDER NHANH')
            self.btn_stop_render.config(state=tk.DISABLED)
            if stop_event and stop_event.is_set():
                self.btn_continue_render.config(state=tk.NORMAL)
            self.progress_var.set(0)
def _blur_frame_with_regions(get_frame, t, regions, blur_strength=35):
    print(f"👉 Đang xử lý frame... Có vùng làm mờ không? {bool(regions)}") # Thêm vào đây
    f = get_frame(t)
    out = np.array(f, copy=True, order='C')
    if out.dtype != np.uint8:
        out = np.clip(out, 0, 255).astype(np.uint8)
        
    if not regions:
        return out

    # Kiểm tra xem OpenCV có hỗ trợ CUDA không
    has_cuda = False
    try:
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            has_cuda = True
    except AttributeError:
        pass

    if has_cuda:
        print("✅ Đã kích hoạt CUDA: Đang làm mờ bằng GPU GTX 1070!")
        try:
            # --- XỬ LÝ BẰNG GPU (CUDA) ---
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(out) # Đẩy frame từ RAM lên VRAM

            for x1s, y1s, x2s, y2s in regions:
                if x2s <= x1s or y2s <= y1s:
                    continue
                
                # Cắt viền an toàn
                x1 = max(0, x1s)
                y1 = max(0, y1s)
                x2 = min(out.shape[1], x2s)
                y2 = min(out.shape[0], y2s)
                
                if x2 <= x1 or y2 <= y1:
                    continue

                # Tạo ROI (Region of Interest) trực tiếp trên VRAM
                gpu_roi = cv2.cuda_GpuMat(gpu_frame, (y1, y2), (x1, x2))
                
                h, w = y2 - y1, x2 - x1
                blur_div = _blur_strength_to_preview_div(blur_strength)
                k = max(3, min(h, w) // blur_div * 2 + 1)
                k = min(k, min(h, w) // 2 * 2 + 1)
                k = max(3, k)

                # Tạo bộ lọc Blur của CUDA và áp dụng
                blur_filter = cv2.cuda.createGaussianFilter(gpu_roi.type(), gpu_roi.type(), (k, k), 0)
                gpu_roi_blurred = blur_filter.apply(gpu_roi)
                
                # Ghi đè vùng đã làm mờ ngược lại frame gốc trên GPU
                gpu_roi_blurred.copyTo(gpu_roi)

            # Tải frame đã xử lý từ VRAM về lại RAM cho MoviePy
            return gpu_frame.download()
            
        except Exception as e:
            print(f"Lỗi khi dùng CUDA Blur, chuyển về CPU: {e}")
            # Nếu GPU lỗi giữa chừng, rơi xuống khối CPU bên dưới

    # --- XỬ LÝ BẰNG CPU (Fallback giữ nguyên như code gốc) ---
    for x1s, y1s, x2s, y2s in regions:
        if x2s <= x1s or y2s <= y1s:
            continue
        
        x1 = max(0, x1s)
        y1 = max(0, y1s)
        x2 = min(out.shape[1], x2s)
        y2 = min(out.shape[0], y2s)
        
        roi = out[y1:y2, x1:x2]
        if roi.size == 0:
            continue
            
        h, w = roi.shape[:2]
        if h < 2 or w < 2:
            continue
            
        blur_div = _blur_strength_to_preview_div(blur_strength)
        k = max(3, min(h, w) // blur_div * 2 + 1)
        k = min(k, min(h, w) // 2 * 2 + 1)
        k = max(3, k)
        
        try:
            out[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (k, k), 0)
        except Exception:
            pass
            
    return out
def _add_anti_copyright_lines(get_frame, t, mode, strength='Nhẹ'):
    frame = get_frame(t)
    out = np.array(frame, copy=True, order='C')
    if mode == 'Không có':
        return out
    cfg = _effect_strength_config(strength)
    color = (180, 180, 180) if cfg['line_color'] == 'gray' else (255, 255, 255)
    alpha = cfg['line_alpha']
    step = cfg['line_step']
    random_count = 8 if strength == 'Nhẹ' else 12 if strength == 'Vừa' else 15

    # Kiểm tra xem OpenCV có hỗ trợ CUDA không
    has_cuda = False
    try:
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            has_cuda = True
    except AttributeError:
        pass

    if has_cuda:
        try:
            # --- XỬ LÝ BẰNG GPU (CUDA) ---
            h, w = out.shape[:2]
            overlay = out.copy()
            thickness = 1
            
            # CPU sẽ đảm nhận việc vẽ các nét đứt/lưới (vì tác vụ vẽ này rất nhẹ)
            if mode in ['Kẻ ngang', 'Lưới']:
                for y in range(0, h, max(h // step, 10)):
                    cv2.line(overlay, (0, y), (w, y), color, thickness)
            if mode in ['Kẻ dọc', 'Lưới']:
                for x in range(0, w, max(w // step, 10)):
                    cv2.line(overlay, (x, 0), (x, h), color, thickness)
            if mode == 'Ngẫu nhiên':
                np.random.seed(int(t * 5))
                for _ in range(random_count):
                    x1, y1 = (np.random.randint(0, w), np.random.randint(0, h))
                    x2, y2 = (np.random.randint(0, w), np.random.randint(0, h))
                    cv2.line(overlay, (x1, y1), (x2, y2), color, thickness)
            
            # Đẩy video và lớp viền lên VRAM để GPU thực hiện trộn (blend) đè lên nhau
            gpu_out = cv2.cuda_GpuMat()
            gpu_out.upload(out)
            
            gpu_overlay = cv2.cuda_GpuMat()
            gpu_overlay.upload(overlay)
            
            # GPU tính toán hàm addWeighted siêu tốc
            cv2.cuda.addWeighted(gpu_overlay, alpha, gpu_out, 1 - alpha, 0.0, gpu_out)
            
            # Tải kết quả về RAM cho MoviePy
            return gpu_out.download()
        except Exception:
            pass # Nếu GPU lỗi, âm thầm bỏ qua và chạy xuống khối CPU bên dưới

    # --- XỬ LÝ BẰNG CPU (Fallback - GIỮ NGUYÊN 100% CODE GỐC) ---
    h, w = out.shape[:2]
    overlay = out.copy()
    thickness = 1
    if mode in ['Kẻ ngang', 'Lưới']:
        for y in range(0, h, max(h // step, 10)):
            cv2.line(overlay, (0, y), (w, y), color, thickness)
    if mode in ['Kẻ dọc', 'Lưới']:
        for x in range(0, w, max(w // step, 10)):
            cv2.line(overlay, (x, 0), (x, h), color, thickness)
    if mode == 'Ngẫu nhiên':
        np.random.seed(int(t * 5))
        for _ in range(random_count):
            x1, y1 = (np.random.randint(0, w), np.random.randint(0, h))
            x2, y2 = (np.random.randint(0, w), np.random.randint(0, h))
            cv2.line(overlay, (x1, y1), (x2, y2), color, thickness)
    cv2.addWeighted(overlay, alpha, out, 1 - alpha, 0, out)
    
    return out
def get_vietnamese_font(size):
    font_paths = ['arial.ttf', 'Arial.ttf', 'C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/segoeui.ttf', '/Library/Fonts/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf']
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
        else:
            pass
    return ImageFont.load_default()
def _pad_video_to_ratio_gpu(frame, new_w, new_h):
    h, w = frame.shape[:2]
    if w == new_w and h == new_h:
        return frame

    # --- KIỂM TRA CUDA ---
    has_cuda = False
    try:
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            has_cuda = True
    except AttributeError:
        pass

    if has_cuda:
        try:
            # --- XỬ LÝ BẰNG GPU ---
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(frame)
            
            # Yêu cầu VRAM tạo một mảng đen với kích thước mới
            gpu_bg = cv2.cuda_GpuMat(new_h, new_w, gpu_frame.type(), (0, 0, 0))
            
            # Tính toán vị trí căn giữa
            y_off = (new_h - h) // 2
            x_off = (new_w - w) // 2
            
            # Xác định vùng giữa trên phông đen và copy video gốc vào
            gpu_roi = cv2.cuda_GpuMat(gpu_bg, (y_off, y_off + h), (x_off, x_off + w))
            gpu_frame.copyTo(gpu_roi)
            
            return gpu_bg.download()
        except Exception:
            pass

    # --- XỬ LÝ BẰNG CPU (Fallback Siêu Nhanh thay thế cho MoviePy) ---
    bg = np.zeros((new_h, new_w, frame.shape[2]), dtype=frame.dtype)
    y_off = (new_h - h) // 2
    x_off = (new_w - w) // 2
    bg[y_off:y_off+h, x_off:x_off+w] = frame
    return bg
def _add_review_overlay_pro(frame, top_txt, bot_txt, font_size, top_color, bot_color, bg_color):
    # --- KIỂM TRA CUDA ---
    has_cuda = False
    try:
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            has_cuda = True
    except AttributeError:
        pass

    if has_cuda:
        try:
            # --- XỬ LÝ KẾT HỢP (CPU tạo khung chữ -> GPU cắt ghép) ---
            w, h = frame.shape[1], frame.shape[0]
            font = get_vietnamese_font(font_size)
            char_width_approx = font_size * 0.55
            wrap_width = max(10, int(w * 0.95 / char_width_approx))
            
            def hex_to_rgb(hex_str):
                hex_str = hex_str.lstrip('#')
                try:
                    return tuple((int(hex_str[i:i + 2], 16) for i in [0, 2, 4]))
                except:
                    return (255, 255, 255)
                    
            tc = hex_to_rgb(top_color)
            bc = hex_to_rgb(bot_color)
            bgc = hex_to_rgb(bg_color)

            def calc_layout(text):
                if not text: return 0, [], []
                lines = textwrap.wrap(text, width=wrap_width)
                line_heights = []
                for line in lines:
                    try:
                        bb = font.getbbox(line)
                        line_heights.append(bb[3] - bb[1])
                    except:
                        line_heights.append(font_size)
                padding = int(font_size * 0.4)
                total_h = sum(line_heights) + padding * (len(lines) + 1)
                return total_h, lines, line_heights

            top_h, top_lines, top_lh = calc_layout(top_txt)
            bot_h, bot_lines, bot_lh = calc_layout(bot_txt)

            # 1. Đẩy frame gốc lên VRAM
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(frame)

            # 2. Xử lý phần chữ TRÊN (CPU chỉ vẽ dải chữ nhỏ -> đẩy lên GPU)
            if top_h > 0 and top_h < h:
                top_img = Image.new('RGB', (w, top_h), bgc)
                draw_top = ImageDraw.Draw(top_img)
                padding = int(font_size * 0.4)
                current_y = padding
                for i, line in enumerate(top_lines):
                    try:
                        bb = font.getbbox(line)
                        tw = bb[2] - bb[0]
                    except:
                        tw = len(line) * font_size * 0.5
                    draw_top.text(((w - tw) // 2, current_y), line, font=font, fill=tc)
                    current_y += top_lh[i] + padding
                
                # Dùng GPU dán dải chữ lên trên cùng
                gpu_top = cv2.cuda_GpuMat()
                gpu_top.upload(np.array(top_img))
                gpu_roi_top = cv2.cuda_GpuMat(gpu_frame, (0, top_h), (0, w))
                gpu_top.copyTo(gpu_roi_top)

            # 3. Xử lý phần chữ DƯỚI (CPU chỉ vẽ dải chữ nhỏ -> đẩy lên GPU)
            if bot_h > 0 and bot_h < h:
                bot_img = Image.new('RGB', (w, bot_h), bgc)
                draw_bot = ImageDraw.Draw(bot_img)
                padding = int(font_size * 0.4)
                current_y = padding
                for i, line in enumerate(bot_lines):
                    try:
                        bb = font.getbbox(line)
                        tw = bb[2] - bb[0]
                    except:
                        tw = len(line) * font_size * 0.5
                    draw_bot.text(((w - tw) // 2, current_y), line, font=font, fill=bc)
                    current_y += bot_lh[i] + padding
                
                # Dùng GPU dán dải chữ xuống dưới cùng
                gpu_bot = cv2.cuda_GpuMat()
                gpu_bot.upload(np.array(bot_img))
                gpu_roi_bot = cv2.cuda_GpuMat(gpu_frame, (h - bot_h, h), (0, w))
                gpu_bot.copyTo(gpu_roi_bot)

            # Tải thành quả về RAM
            return gpu_frame.download()

        except Exception:
            pass # Lỗi thì tự động nhảy xuống dùng code CPU cũ bên dưới

    # ==========================================================
    # --- XỬ LÝ BẰNG CPU (Fallback - GIỮ NGUYÊN 100% CODE GỐC) ---
    # ==========================================================
    img_pil = Image.fromarray(frame)
    w, h = img_pil.size
    draw = ImageDraw.Draw(img_pil)
    font = get_vietnamese_font(font_size)
    char_width_approx = font_size * 0.55
    wrap_width = max(10, int(w * 0.95 / char_width_approx))
    
    def hex_to_rgb(hex_str):
        hex_str = hex_str.lstrip('#')
        try:
            return tuple((int(hex_str[i:i + 2], 16) for i in [0, 2, 4]))
        except:
            return (255, 255, 255)
            
    tc = hex_to_rgb(top_color)
    bc = hex_to_rgb(bot_color)
    bgc = hex_to_rgb(bg_color)
    
    def draw_text_block(text, is_top, text_color):
        if not text:
            return
        else:
            lines = textwrap.wrap(text, width=wrap_width)
            line_heights = []
            for line in lines:
                try:
                    bb = font.getbbox(line)
                    line_heights.append(bb[3] - bb[1])
                except:
                    line_heights.append(font_size)
            padding = int(font_size * 0.4)
            total_h = sum(line_heights) + padding * (len(lines) + 1)
            if is_top:
                draw.rectangle([(0, 0), (w, total_h)], fill=bgc)
                current_y = padding
            else:
                draw.rectangle([(0, h - total_h), (w, h)], fill=bgc)
                current_y = h - total_h + padding
            for i, line in enumerate(lines):
                try:
                    bb = font.getbbox(line)
                    tw = bb[2] - bb[0]
                except:
                    tw = len(line) * font_size * 0.5
                draw.text(((w - tw) // 2, current_y), line, font=font, fill=text_color)
                current_y += line_heights[i] + padding
                
    draw_text_block(top_txt, True, tc)
    draw_text_block(bot_txt, False, bc)
    
    return np.array(img_pil)
class VideoEditorApp(tb.Frame):
    PREVIEW_W = 720
    PREVIEW_H = 405
    def __init__(self, parent, linked_mode=True):
        super().__init__(parent)
        self.linked_mode = linked_mode
        self.video_path = None
        self.cap = None
        self.playing = False
        self.frame_id = None
        self.blur_regions = []
        self.video_effect_states = {}
        self.draw_mode = tk.StringVar(value='manual_blur')
        self.logo_path = None
        self._raw_logo_img = None
        self._logo_tk = None
        self.logo_item = None
        self.follow_guide_item = None
        self.follow_guide_visible = tk.BooleanVar(value=False)
        self.vid_image_id = None
        self.dragging_logo = False
        self.logo_height = tk.IntVar(value=80)
        self.logo_opacity = tk.IntVar(value=100)
        self.flip_h = tk.BooleanVar(value=False)
        self.flip_v = tk.BooleanVar(value=False)
        self.line_mode = tk.StringVar(value='Không có')
        self.line_strength = tk.StringVar(value='Nhẹ')
        self.blur_strength = tk.IntVar(value=35)
        self.export_ratio = tk.StringVar(value='Bản Gốc')
        self.output_quality = tk.StringVar(value='Gốc')
        self.review_mode = tk.BooleanVar(value=False)
        self.subtitle_in_blur = tk.BooleanVar(value=False)
        self.top_text = tk.StringVar(value='TÊN PHIM ĐỈNH CAO')
        self.bottom_text = tk.StringVar(value='Tập 1 - Quá Cuốn')
        self.text_font_size = tk.IntVar(value=40)
        self.text_color_top = tk.StringVar(value='#FFFF00')
        self.text_color_bot = tk.StringVar(value='#FFFFFF')
        self.text_bg_color = tk.StringVar(value='#000000')
        self.timeline_var = tk.IntVar(value=0)
        self.timeline_max = 0
        self._suppress_timeline_update = False
        self.create_widgets()
    def create_widgets(self):
        # ***<module>.VideoEditorApp.create_widgets: Failure: Compilation Error
        main_content = tb.Frame(self)
        main_content.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        ctrl = tb.Frame(main_content)
        ctrl.pack(side=tk.TOP, fill='x', pady=5)
        btn_load = tb.Button(ctrl, text='Mở video', bootstyle='info', command=self.load_video)
        btn_play = tb.Button(ctrl, text='▶ Phát', bootstyle='success', command=self.play_video)
        btn_pause = tb.Button(ctrl, text='⏸ Tạm dừng', bootstyle='warning', command=self.pause_video)
        btn_logo = tb.Button(ctrl, text='Thêm ảnh overlay', bootstyle='info', command=self.add_logo)
        btn_undo = tb.Button(ctrl, text='↩ Hoàn tác', bootstyle='warning', command=self.undo_blur) # [THÊM MỚI]
        btn_clear = tb.Button(ctrl, text='Xoá hết mờ', bootstyle='danger', command=self.clear_blurs) # [SỬA TEXT]
        
        if not self.linked_mode:
            btn_load.pack(side=tk.LEFT, padx=4)
        btn_play.pack(side=tk.LEFT, padx=4)
        btn_pause.pack(side=tk.LEFT, padx=4)
        btn_logo.pack(side=tk.LEFT, padx=4)
        btn_undo.pack(side=tk.LEFT, padx=4) # [THÊM MỚI]
        btn_clear.pack(side=tk.LEFT, padx=4)
        draw_mode_box = tb.Frame(main_content)
        draw_mode_box.pack(side=tk.TOP, fill='x', pady=(0, 5))
        tb.Label(draw_mode_box, text='Chế độ vẽ:').pack(side=tk.LEFT, padx=(5, 8))
        tb.Radiobutton(draw_mode_box, text='Mờ thủ công', variable=self.draw_mode, value='manual_blur', bootstyle='success-toolbutton').pack(side=tk.LEFT, padx=4)
        tb.Label(draw_mode_box, text='Độ mờ vùng:').pack(side=tk.LEFT, padx=(15, 5))
        tb.Scale(draw_mode_box, from_=1, to=100, variable=self.blur_strength, orient='horizontal', length=150, command=lambda e: self.show_frame(), bootstyle='success').pack(side=tk.LEFT, padx=4)
        tb.Label(draw_mode_box, text='Kéo để chỉnh riêng vùng làm mờ', font=(APP_FONT, 9, 'italic'), bootstyle='secondary').pack(side=tk.LEFT, padx=(10, 0))
        logo_box = tb.Frame(main_content)
        logo_box.pack(side=tk.TOP, fill='x', pady=5)
        tb.Label(logo_box, text='Logo Cao (px):').pack(side=tk.LEFT, padx=(5, 5))
        tb.Spinbox(logo_box, from_=24, to=400, increment=4, textvariable=self.logo_height, width=6, bootstyle='info', command=self.update_logo_preview).pack(side=tk.LEFT, padx=5)
        tb.Label(logo_box, text='Độ mờ (%):').pack(side=tk.LEFT, padx=(15, 5))
        tb.Spinbox(logo_box, from_=10, to=100, increment=5, textvariable=self.logo_opacity, width=6, bootstyle='info', command=self.update_logo_preview).pack(side=tk.LEFT, padx=5)
        tb.Button(
            logo_box,
            text='Mốc Follow',
            bootstyle='secondary-outline',
            command=self.toggle_follow_guide
        ).pack(side=tk.LEFT, padx=(15, 5))
        tb.Button(
            logo_box,
            text='Đặt ảnh vào mốc',
            bootstyle='success-outline',
            command=self.place_logo_on_follow_button
        ).pack(side=tk.LEFT, padx=5)
        tb.Button(
            logo_box,
            text='Sọc màn hình trái',
            bootstyle='warning-outline',
            command=self.add_left_screen_stripe_overlay
        ).pack(side=tk.LEFT, padx=5)
        tb.Button(
            logo_box,
            text='Xóa ảnh',
            bootstyle='danger-outline',
            command=self.clear_logo_overlay
        ).pack(side=tk.LEFT, padx=5)
        tb.Label(logo_box, text='Mốc Follow chỉ để căn trên preview, không render ra video.', font=(APP_FONT, 9, 'italic'), bootstyle='secondary').pack(side=tk.LEFT, padx=(10, 0))
        adv_frame = tb.LabelFrame(main_content, text='Định dạng & Review Phim')
        adv_frame.pack(side=tk.TOP, fill='x', pady=5, ipadx=5, ipady=5)
        row1 = tb.Frame(adv_frame)
        row1.pack(fill=X, pady=2)
        tb.Checkbutton(row1, text='Lật ngang', variable=self.flip_h, bootstyle='round-toggle-warning', command=self.show_frame).pack(side=tk.LEFT, padx=(10, 15))
        tb.Checkbutton(row1, text='Lật dọc', variable=self.flip_v, bootstyle='round-toggle-warning', command=self.show_frame).pack(side=tk.LEFT, padx=15)
        tb.Label(row1, text='Kẻ mờ lách BQ:').pack(side=tk.LEFT, padx=(20, 5))
        cb_lines = tb.Combobox(row1, textvariable=self.line_mode, values=['Không có', 'Kẻ ngang', 'Kẻ dọc', 'Lưới', 'Ngẫu nhiên'], state='readonly', width=12, bootstyle='warning')
        cb_lines.pack(side=tk.LEFT, padx=5)
        cb_lines.bind('<<ComboboxSelected>>', lambda e: self.show_frame())
        tb.Label(row1, text='Mức kẻ:').pack(side=tk.LEFT, padx=(15, 5))
        cb_strength = tb.Combobox(row1, textvariable=self.line_strength, values=['Nhẹ', 'Vừa', 'Mạnh'], state='readonly', width=8, bootstyle='info')
        cb_strength.pack(side=tk.LEFT, padx=5)
        cb_strength.bind('<<ComboboxSelected>>', lambda e: self.show_frame())
        row2 = tb.Frame(adv_frame)
        row2.pack(fill=X, pady=(5, 2))
        tb.Label(row2, text='Tỉ lệ Video:').pack(side=tk.LEFT, padx=(10, 5))
        cb_ratio = tb.Combobox(row2, textvariable=self.export_ratio, values=['Bản Gốc', '16:9 (YouTube)', '9:16 (TikTok)', '1:1 (Vuông)'], state='readonly', width=15)
        cb_ratio.pack(side=tk.LEFT, padx=5)
        cb_ratio.bind('<<ComboboxSelected>>', lambda e: self.show_frame())
        tb.Label(row2, text='Chất lượng:').pack(side=tk.LEFT, padx=(15, 5))
        cb_quality = tb.Combobox(row2, textvariable=self.output_quality, values=['Gốc', '720p', '1080p', '2K / 1440p', '4K / 2160p'], state='readonly', width=13, bootstyle='success')
        cb_quality.pack(side=tk.LEFT, padx=5)
        tb.Checkbutton(row2, text='Bật Phông Review', variable=self.review_mode, bootstyle='round-toggle-success', command=self.show_frame).pack(side=tk.LEFT, padx=(20, 10))
        tb.Checkbutton(
            row2,
            text='Chèn SRT vào vùng mờ',
            variable=self.subtitle_in_blur,
            bootstyle='round-toggle-info',
            command=lambda: (
                self._remember_current_video_effect_state(),
                self.show_frame()
            )
        ).pack(side=tk.LEFT, padx=(10, 10))
        tb.Label(row2, text='Chữ Trên:').pack(side=tk.LEFT, padx=5)
        e_top = tb.Entry(row2, textvariable=self.top_text, width=20)
        e_top.pack(side=tk.LEFT, padx=5)
        e_top.bind('<KeyRelease>', lambda e: self.show_frame())
        tb.Label(row2, text='Chữ Dưới:').pack(side=tk.LEFT, padx=(10, 5))
        e_bot = tb.Entry(row2, textvariable=self.bottom_text, width=20)
        e_bot.pack(side=tk.LEFT, padx=5)
        e_bot.bind('<KeyRelease>', lambda e: self.show_frame())
        row3 = tb.Frame(adv_frame)
        row3.pack(fill=X, pady=(5, 2))
        tb.Label(row3, text='Size chữ (px):').pack(side=tk.LEFT, padx=(10, 5))
        sp_font = tb.Spinbox(row3, from_=10, to=150, increment=2, textvariable=self.text_font_size, width=5, command=self.show_frame)
        sp_font.pack(side=tk.LEFT, padx=5)
        sp_font.bind('<KeyRelease>', lambda e: self.show_frame())
        def pick_color(var_name):
            color = askcolor(color=getattr(self, var_name).get())[1]
            if color:
                getattr(self, var_name).set(color)
                self.show_frame()
        tb.Button(row3, text='🎨 Màu Chữ Trên', bootstyle='outline-light',
                  command=lambda: pick_color('text_color_top')).pack(side=tk.LEFT, padx=(15, 5))

        tb.Button(row3, text='🎨 Màu Chữ Dưới', bootstyle='outline-light',
                  command=lambda: pick_color('text_color_bot')).pack(side=tk.LEFT, padx=5)

        tb.Button(row3, text='🎨 Màu Phông Nền', bootstyle='outline-dark',
                  command=lambda: pick_color('text_bg_color')).pack(side=tk.LEFT, padx=5)
        preview_area = tb.Frame(main_content)
        preview_area.pack(fill='both', expand=True, pady=(6, 0))
        video_panel = tb.Frame(preview_area)
        video_panel.pack(side=tk.LEFT, fill='both', expand=True)
        self.canvas = tk.Canvas(video_panel, width=self.PREVIEW_W, height=self.PREVIEW_H, bg=COLOR_CANVAS, cursor='tcross', highlightthickness=2, highlightbackground=COLOR_ACCENT)
        self.canvas.pack(pady=(0, 6))
        self.canvas.bind('<ButtonPress-1>', self.start_draw)
        self.canvas.bind('<B1-Motion>', self.draw_rect)
        self.canvas.bind('<ButtonRelease-1>', self.end_draw)
        self.canvas.bind('<ButtonPress-3>', self.undo_blur) # [THÊM MỚI] Click chuột phải
        tl = tb.Frame(video_panel)
        tl.pack(fill='x', pady=(0, 5))
        tb.Label(tl, text='Timeline:').pack(side=tk.LEFT)
        self.timeline = tk.Scale(tl, from_=0, to=100, orient='horizontal', variable=self.timeline_var, showvalue=False, command=self.seek_video, bg=COLOR_CANVAS, troughcolor=COLOR_ACCENT, highlightthickness=0)
        self.timeline.pack(side=tk.LEFT, fill='x', expand=True, padx=10)
        self.lbl_frame = tb.Label(tl, text='0', bootstyle='inverse-dark')
        self.lbl_frame.pack(side=tk.LEFT, ipadx=5, ipady=5)
    def get_settings_dict(self):
        self._remember_current_video_effect_state()
        return {
            'logo_height': self.logo_height.get(),
            'logo_opacity': self.logo_opacity.get(),
            'flip_h': self.flip_h.get(),
            'flip_v': self.flip_v.get(),
            'line_mode': self.line_mode.get(),
            'line_strength': self.line_strength.get(),
            'blur_strength': self.blur_strength.get(),
            'export_ratio': self.export_ratio.get(),
            'output_quality': self.output_quality.get(),
            'review_mode': self.review_mode.get(),
            'subtitle_in_blur': self.subtitle_in_blur.get(),
            'draw_mode': self.draw_mode.get(),
            'top_text': self.top_text.get(),
            'bottom_text': self.bottom_text.get(),
            'text_font_size': self.text_font_size.get(),
            'text_color_top': self.text_color_top.get(),
            'text_color_bot': self.text_color_bot.get(),
            'text_bg_color': self.text_bg_color.get(),
            'video_effect_states': copy.deepcopy(self.video_effect_states),
        }
    def apply_settings(self, settings):
        if not settings:
            return
        else:
            self.logo_height.set(settings.get('logo_height', 80))
            self.logo_opacity.set(settings.get('logo_opacity', 100))
            self.flip_h.set(settings.get('flip_h', False))
            self.flip_v.set(settings.get('flip_v', False))
            self.line_mode.set(settings.get('line_mode', 'Không có'))
            self.line_strength.set(settings.get('line_strength', settings.get('effect_strength', 'Nhẹ')))
            self.blur_strength.set(settings.get('blur_strength', 35))
            self.export_ratio.set(settings.get('export_ratio', 'Bản Gốc'))
            self.output_quality.set(settings.get('output_quality', 'Gốc'))
            self.review_mode.set(settings.get('review_mode', False))
            self.subtitle_in_blur.set(settings.get('subtitle_in_blur', False))
            self.draw_mode.set(settings.get('draw_mode', 'manual_blur'))
            self.top_text.set(settings.get('top_text', 'TÊN PHIM ĐỈNH CAO'))
            self.bottom_text.set(settings.get('bottom_text', 'Tập 1 - Quá Cuốn'))
            self.text_font_size.set(settings.get('text_font_size', 40))
            self.text_color_top.set(settings.get('text_color_top', '#FFFF00'))
            self.text_color_bot.set(settings.get('text_color_bot', '#FFFFFF'))
            self.text_bg_color.set(settings.get('text_bg_color', '#000000'))
            raw_video_states = settings.get('video_effect_states', {})
            if isinstance(raw_video_states, dict):
                self.video_effect_states = {
                    self._video_effect_key(path): copy.deepcopy(state)
                    for path, state in raw_video_states.items()
                    if isinstance(state, dict) and self._video_effect_key(path)
                }

    def _video_effect_key(self, path=None):
        path = path or self.video_path
        if not path:
            return None
        try:
            return os.path.normcase(os.path.abspath(path))
        except Exception:
            return os.path.normcase(str(path))

    def _capture_video_effect_state(self):
        logo_coords = None
        if self.logo_path and self.logo_item is not None:
            try:
                coords = self.canvas.coords(self.logo_item)
                if coords:
                    logo_coords = tuple(coords)
            except Exception:
                logo_coords = None
        return {
            'blur_regions': copy.deepcopy(self.blur_regions),
            'subtitle_in_blur': bool(self.subtitle_in_blur.get()),
            'draw_mode': self.draw_mode.get(),
            'blur_strength': int(self.blur_strength.get()),
            'flip_h': bool(self.flip_h.get()),
            'flip_v': bool(self.flip_v.get()),
            'line_mode': self.line_mode.get(),
            'line_strength': self.line_strength.get(),
            'export_ratio': self.export_ratio.get(),
            'output_quality': self.output_quality.get(),
            'review_mode': bool(self.review_mode.get()),
            'top_text': self.top_text.get(),
            'bottom_text': self.bottom_text.get(),
            'text_font_size': int(self.text_font_size.get()),
            'text_color_top': self.text_color_top.get(),
            'text_color_bot': self.text_color_bot.get(),
            'text_bg_color': self.text_bg_color.get(),
            'logo_path': self.logo_path,
            'logo_coords': logo_coords,
            'logo_height': int(self.logo_height.get()),
            'logo_opacity': int(self.logo_opacity.get()),
        }

    def _remember_current_video_effect_state(self):
        key = self._video_effect_key()
        if not key:
            return
        self.video_effect_states[key] = self._capture_video_effect_state()

    def _state_has_active_effects(self, state):
        if not state:
            return False
        line_mode = state.get('line_mode', 'Không có')
        export_ratio = state.get('export_ratio', 'Bản Gốc')
        output_quality = state.get('output_quality', 'Gốc')
        no_line_modes = ('Kh\u00f4ng c\u00f3', 'Kh\xc3\xb4ng c\xc3\xb3', 'Không có')
        original_ratios = ('B\u1ea3n G\u1ed1c', 'B\u00e1\u00ba\u00a3n G\u00e1\u00bb\u2018c', 'Bản Gốc')
        return bool(
            state.get('flip_h')
            or state.get('flip_v')
            or state.get('review_mode')
            or state.get('subtitle_in_blur')
            or line_mode not in no_line_modes
            or export_ratio not in original_ratios
            or output_quality != 'Gốc'
            or state.get('blur_regions')
            or (state.get('logo_path') and state.get('logo_coords'))
        )

    def _redraw_blur_rectangles(self):
        self.canvas.delete('blur_rect')
        for x1, y1, x2, y2 in self.blur_regions:
            self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline='#00bc8c',
                width=3,
                dash=(4, 4),
                tags='blur_rect'
            )

    def _apply_video_effect_state(self, state):
        if not state:
            self.blur_regions = []
            self._redraw_blur_rectangles()
            return
        self.blur_regions = [
            tuple(region)
            for region in copy.deepcopy(state.get('blur_regions', []))
        ]
        self.subtitle_in_blur.set(bool(state.get('subtitle_in_blur', False)))
        self.draw_mode.set(state.get('draw_mode', 'manual_blur'))
        self.blur_strength.set(int(state.get('blur_strength', 35)))
        self.flip_h.set(bool(state.get('flip_h', False)))
        self.flip_v.set(bool(state.get('flip_v', False)))
        self.line_mode.set(state.get('line_mode', 'Không có'))
        self.line_strength.set(state.get('line_strength', 'Nhẹ'))
        self.export_ratio.set(state.get('export_ratio', 'Bản Gốc'))
        self.output_quality.set(state.get('output_quality', 'Gốc'))
        self.review_mode.set(bool(state.get('review_mode', False)))
        self.top_text.set(state.get('top_text', 'TÊN PHIM ĐỈNH CAO'))
        self.bottom_text.set(state.get('bottom_text', 'Tập 1 - Quá Cuốn'))
        self.text_font_size.set(int(state.get('text_font_size', 40)))
        self.text_color_top.set(state.get('text_color_top', '#FFFF00'))
        self.text_color_bot.set(state.get('text_color_bot', '#FFFFFF'))
        self.text_bg_color.set(state.get('text_bg_color', '#000000'))
        self.logo_height.set(int(state.get('logo_height', 80)))
        self.logo_opacity.set(int(state.get('logo_opacity', 100)))
        self._redraw_blur_rectangles()

    def _scale_preview_regions_for_video(self, preview_regions, video_path):
        video_width, video_height = _probe_video_dimensions(video_path)
        if video_width <= 0 or video_height <= 0:
            return []
        sx = video_width / self.PREVIEW_W
        sy = video_height / self.PREVIEW_H
        regions = []
        for x1, y1, x2, y2 in preview_regions or []:
            left, right = sorted((float(x1), float(x2)))
            top, bottom = sorted((float(y1), float(y2)))
            x1s = int(left * sx)
            y1s = int(top * sy)
            x2s = int(right * sx)
            y2s = int(bottom * sy)
            if x2s > x1s and y2s > y1s:
                regions.append((x1s, y1s, x2s, y2s))
        return regions

    def _ffmpeg_effects_config_from_state(self, state, video_path):
        state = state or {}
        video_width, video_height = _probe_video_dimensions(video_path)
        sx = video_width / self.PREVIEW_W if video_width > 0 else 1.0
        sy = video_height / self.PREVIEW_H if video_height > 0 else 1.0
        blur_regions = self._scale_preview_regions_for_video(
            state.get('blur_regions', []),
            video_path
        )
        subtitle_region = blur_regions[0] if state.get('subtitle_in_blur') and blur_regions else None
        logo_pos = None
        logo_coords = state.get('logo_coords')
        if state.get('logo_path') and logo_coords:
            try:
                logo_pos = (int(float(logo_coords[0]) * sx), int(float(logo_coords[1]) * sy))
            except Exception:
                logo_pos = None
        return {
            'flip_h': bool(state.get('flip_h', False)),
            'flip_v': bool(state.get('flip_v', False)),
            'line_mode': state.get('line_mode', 'Không có'),
            'line_strength': state.get('line_strength', 'Nhẹ'),
            'blur_strength': int(state.get('blur_strength', 35)),
            'export_ratio': state.get('export_ratio', 'Bản Gốc'),
            'output_quality': state.get('output_quality', 'Gốc'),
            'blur_regions': blur_regions,
            'subtitle_region': subtitle_region,
            'logo_path': state.get('logo_path'),
            'logo_pos': logo_pos,
            'logo_height': int(int(state.get('logo_height', 80)) * sy),
            'logo_opacity': int(state.get('logo_opacity', 100)) / 100.0,
            'review_mode': bool(state.get('review_mode', False)),
            'subtitle_in_blur': bool(state.get('subtitle_in_blur', False)),
            'top_text': state.get('top_text', 'TÊN PHIM ĐỈNH CAO'),
            'bottom_text': state.get('bottom_text', 'Tập 1 - Quá Cuốn'),
            'text_font_size': int(state.get('text_font_size', 40)),
            'text_color_top': state.get('text_color_top', '#FFFF00'),
            'text_color_bot': state.get('text_color_bot', '#FFFFFF'),
            'text_bg_color': state.get('text_bg_color', '#000000'),
        }

    def has_active_effects_for_video(self, video_path=None):
        key = self._video_effect_key(video_path)
        current_key = self._video_effect_key()
        if key and current_key and key == current_key:
            return self.has_active_effects()
        return self._state_has_active_effects(
            self.video_effect_states.get(key)
        )

    def get_ffmpeg_effects_config_for_video(self, video_path=None):
        self._remember_current_video_effect_state()
        key = self._video_effect_key(video_path)
        current_key = self._video_effect_key()
        if key and current_key and key == current_key:
            return self.get_ffmpeg_effects_config()
        state = self.video_effect_states.get(key)
        if not state:
            return None
        return self._ffmpeg_effects_config_from_state(state, video_path)

    def get_source_blur_regions(self):
        return self.scale_preview_regions_to_source(self.blur_regions)

    def scale_preview_regions_to_source(self, preview_regions, account_flips=False):
        if not self.cap:
            return []
        src_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or self.PREVIEW_W)
        src_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or self.PREVIEW_H)
        sx = src_w / self.PREVIEW_W
        sy = src_h / self.PREVIEW_H
        regions = []
        for x1, y1, x2, y2 in preview_regions:
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            x1s, y1s, x2s, y2s = (int(left * sx), int(top * sy), int(right * sx), int(bottom * sy))
            if account_flips and self.flip_h.get():
                x1s, x2s = src_w - x2s, src_w - x1s
            if account_flips and self.flip_v.get():
                y1s, y2s = src_h - y2s, src_h - y1s
            regions.append((x1s, y1s, x2s, y2s))
        return regions
    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[('Video files', ('*.mp4', '*.avi', '*.mkv', '*.mov'))])
        if path:
            self.load_video_from_path(path)
    def load_video_from_path(self, path: str):
        if not path:
            return
        else:
            is_new_video = os.path.abspath(path) != os.path.abspath(self.video_path) if self.video_path else True
            if is_new_video:
                self._remember_current_video_effect_state()
            self.video_path = path
            if self.cap:
                self.cap.release()
            self.cap = cv2.VideoCapture(path)
            if not self.cap or not self.cap.isOpened():
                return None
            else:
                if is_new_video:
                    state = self.video_effect_states.get(
                        self._video_effect_key(path)
                    )
                    if state:
                        self._apply_video_effect_state(state)
                    else:
                        self.blur_regions.clear()
                        self._redraw_blur_rectangles()
                total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
                self.timeline.configure(from_=0, to=total_frames - 1)
                self.timeline_max = total_frames - 1
                self._suppress_timeline_update = False
                self.timeline_var.set(0)
                self.lbl_frame.config(text='0')
                self.playing = False
                self.show_frame()
    def read_frame(self, index=None):
        if not self.cap:
            return
        else:
            if index is not None:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(self.timeline_max, index)))
            ret, frame = self.cap.read()
            return frame if ret else None
    def show_frame(self, event=None):
        if not self.cap:
            return
        else:
            frame = self.read_frame()
            if frame is None:
                self.playing = False
                return
            else:
                cur = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                if not self._suppress_timeline_update:
                    self._suppress_timeline_update = True
                    self.timeline_var.set(cur)
                    self.lbl_frame.config(text=str(cur))
                    self._suppress_timeline_update = False
                if self.flip_h.get():
                    frame = cv2.flip(frame, 1)
                if self.flip_v.get():
                    frame = cv2.flip(frame, 0)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if self.review_mode.get():
                    frame_rgb = _add_review_overlay_pro(frame_rgb, self.top_text.get(), self.bottom_text.get(), self.text_font_size.get(), self.text_color_top.get(), self.text_color_bot.get(), self.text_bg_color.get())
                frame_rgb = cv2.resize(frame_rgb, (self.PREVIEW_W, self.PREVIEW_H))
                mode = self.line_mode.get()
                if mode!= 'Không có':
                    strength_cfg = _effect_strength_config(self.line_strength.get())
                    overlay = frame_rgb.copy()
                    h, w = frame_rgb.shape[:2]
                    alpha = strength_cfg['line_alpha']
                    line_step = strength_cfg['line_step']
                    line_color = (180, 180, 180) if strength_cfg['line_color'] == 'gray' else (255, 255, 255)
                    if mode in ['Kẻ ngang', 'Lưới']:
                        for y in range(0, h, max(h // line_step, 10)):
                            cv2.line(overlay, (0, y), (w, y), line_color, 1)
                    if mode in ['Kẻ dọc', 'Lưới']:
                        for x in range(0, w, max(w // line_step, 10)):
                            cv2.line(overlay, (x, 0), (x, h), line_color, 1)
                    if mode == 'Ngẫu nhiên':
                        np.random.seed(int(cur))
                        for _ in range(8 if self.line_strength.get() == 'Nhẹ' else 12 if self.line_strength.get() == 'Vừa' else 15):
                            cv2.line(overlay, (np.random.randint(0, w), np.random.randint(0, h)), (np.random.randint(0, w), np.random.randint(0, h)), line_color, 1)
                    cv2.addWeighted(overlay, alpha, frame_rgb, 1 - alpha, 0, frame_rgb)
                for x1, y1, x2, y2 in self.blur_regions:
                    x1i, y1i, x2i, y2i = (max(0, int(x1)), max(0, int(y1)), min(self.PREVIEW_W, int(x2)), min(self.PREVIEW_H, int(y2)))
                    if x2i > x1i and y2i > y1i:
                            roi = frame_rgb[y1i:y2i, x1i:x2i]
                            if roi.size > 0:
                                blur_div = _blur_strength_to_preview_div(self.blur_strength.get())
                                k = max(3, min(roi.shape[0], roi.shape[1]) // blur_div * 2 + 1)
                                frame_rgb[y1i:y2i, x1i:x2i] = cv2.GaussianBlur(roi, (k, k), 0)
                img = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
                if self.vid_image_id is None:
                    self.vid_image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=img)
                    self.canvas.tag_lower(self.vid_image_id)
                else:
                    self.canvas.itemconfig(self.vid_image_id, image=img)
                self.canvas.image = img
                self.draw_follow_guide()
                if self.logo_item is not None:
                    self.canvas.tag_raise(self.logo_item)
                if self.playing:
                    self.frame_id = self.after(33, self.show_frame)
    def play_video(self):
        if not self.cap:
            return
        else:
            self.playing = True
            self.show_frame()
    def pause_video(self):
        self.playing = False
        if self.frame_id:
            try:
                self.after_cancel(self.frame_id)
            except Exception:
                pass
            self.frame_id = None
    def cleanup(self):
        self.playing = False
        if self.frame_id:
            try:
                self.after_cancel(self.frame_id)
            except Exception:
                pass
            self.frame_id = None
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
    def seek_video(self, val):
        if not self.cap:
            return
        else:
            self._suppress_timeline_update = True
            self.read_frame(index=int(float(val)))
            self.after_idle(self.show_frame)
            self._suppress_timeline_update = False

    def clear_logo_overlay(self):
        self.logo_path = None
        self._raw_logo_img = None
        self._logo_tk = None
        if self.logo_item is not None:
            try:
                self.canvas.delete(self.logo_item)
            except Exception:
                pass
        self.logo_item = None
        self.show_frame()

    def add_logo(self):
        path = filedialog.askopenfilename(filetypes=[('Ảnh', ('*.png', '*.jpg', '*.jpeg'))])
        if path:
            self.logo_path = path
            try:
                self._raw_logo_img = Image.open(path).convert('RGBA')
                self.update_logo_preview()
                self.canvas.tag_raise(self.logo_item)
            except Exception as e:
                messagebox.showerror('Lỗi', f'Không thể mở ảnh: {e}')

    def ensure_left_screen_stripe_overlay_image(self):
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        path = os.path.join(assets_dir, 'left_screen_stripe_overlay.png')

        width = 96
        height = 900
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img, 'RGBA')
        center_x = width // 2

        # Sọc chính phải thẳng dọc như lỗi panel LCD, không uốn cong như sợi tóc.
        for offset, color, alpha, line_width in [
            (-12, (0, 0, 0), 32, 3),
            (-8, (60, 210, 255), 42, 1),
            (-4, (180, 245, 255), 72, 2),
            (0, (245, 255, 255), 155, 3),
            (4, (110, 220, 255), 58, 2),
            (9, (255, 255, 255), 30, 1),
            (16, (0, 0, 0), 20, 2),
        ]:
            x = center_x + offset
            draw.line((x, 0, x, height), fill=(*color, alpha), width=line_width)

        # Quầng sáng hẹp hai bên giúp sọc hòa vào video, giống màn hình bị cháy đường cột.
        for offset in range(-22, 23):
            distance = abs(offset)
            if distance in (0, 4, 8, 12, 16):
                continue
            alpha = max(0, int(28 * (1 - distance / 24)))
            if alpha > 0:
                draw.line(
                    (center_x + offset, 0, center_x + offset, height),
                    fill=(170, 235, 255, alpha),
                    width=1
                )

        # Nhiễu ngang mảnh trên chính vùng sọc, tạo cảm giác lỗi tín hiệu/màn hỏng.
        for y in range(12, height, 18):
            alpha = 18 if (y // 18) % 2 else 28
            draw.line(
                (center_x - 26, y, center_x + 24, y),
                fill=(255, 255, 255, alpha),
                width=1
            )
        for y in range(7, height, 53):
            draw.rectangle(
                (center_x - 5, y, center_x + 6, min(height - 1, y + 4)),
                fill=(230, 255, 255, 26)
            )

        img.save(path)
        return path

    def add_left_screen_stripe_overlay(self):
        try:
            self.logo_path = self.ensure_left_screen_stripe_overlay_image()
            self._raw_logo_img = Image.open(self.logo_path).convert('RGBA')
            self.logo_height.set(self.PREVIEW_H)
            self.logo_opacity.set(72)
            self.update_logo_preview()
            if self.logo_item is not None:
                stripe_w = int(self._raw_logo_img.width * (self.PREVIEW_H / max(1, self._raw_logo_img.height)))
                x = max(0, min(self.PREVIEW_W - stripe_w, int(self.PREVIEW_W * 0.055)))
                self.canvas.coords(self.logo_item, x, 0)
                self.canvas.tag_raise(self.logo_item)
            self.show_frame()
        except Exception as e:
            messagebox.showerror('Lỗi', f'Không thể tạo sọc màn hình: {e}')

    def ensure_default_follow_overlay_image(self):
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        path = os.path.join(assets_dir, 'follow_plus_overlay.png')
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path

        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        radius = int(size * 0.38)
        shadow_offset = int(size * 0.025)
        draw.ellipse(
            (
                center - radius + shadow_offset,
                center - radius + shadow_offset,
                center + radius + shadow_offset,
                center + radius + shadow_offset
            ),
            fill=(0, 0, 0, 120)
        )
        draw.ellipse(
            (
                center - radius,
                center - radius,
                center + radius,
                center + radius
            ),
            fill=(255, 48, 88, 235),
            outline=(255, 255, 255, 245),
            width=max(5, size // 32)
        )
        plus_w = int(size * 0.11)
        plus_len = int(size * 0.48)
        draw.rounded_rectangle(
            (
                center - plus_len // 2,
                center - plus_w // 2,
                center + plus_len // 2,
                center + plus_w // 2
            ),
            radius=plus_w // 2,
            fill=(255, 255, 255, 255)
        )
        draw.rounded_rectangle(
            (
                center - plus_w // 2,
                center - plus_len // 2,
                center + plus_w // 2,
                center + plus_len // 2
            ),
            radius=plus_w // 2,
            fill=(255, 255, 255, 255)
        )
        img.save(path)
        return path

    def follow_button_anchor_ratio(self):
        if self.cap:
            real_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or self.PREVIEW_W)
            real_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or self.PREVIEW_H)
        else:
            real_w, real_h = self.PREVIEW_W, self.PREVIEW_H
        aspect = real_w / max(1, real_h)
        if aspect < 0.75:
            return 0.918, 0.505
        if aspect < 1.25:
            return 0.900, 0.455
        return 0.925, 0.480

    def follow_button_preview_center(self):
        rx, ry = self.follow_button_anchor_ratio()
        return self.PREVIEW_W * rx, self.PREVIEW_H * ry

    def draw_follow_guide(self):
        if not self.follow_guide_visible.get():
            self.canvas.delete('follow_guide')
            self.follow_guide_item = None
            return

        cx, cy = self.follow_button_preview_center()
        half_len = max(12, int(self.PREVIEW_H * 0.032))
        gap = max(3, int(half_len * 0.22))
        if self.follow_guide_item is None:
            self.canvas.delete('follow_guide')
            h1 = self.canvas.create_line(
                cx - half_len,
                cy,
                cx - gap,
                cy,
                fill='#00e5ff',
                width=2,
                dash=(5, 4),
                tags='follow_guide'
            )
            self.canvas.create_line(
                cx + gap,
                cy,
                cx + half_len,
                cy,
                fill='#00e5ff',
                width=2,
                dash=(5, 4),
                tags='follow_guide'
            )
            self.canvas.create_line(
                cx,
                cy - half_len,
                cx,
                cy - gap,
                fill='#00e5ff',
                width=2,
                dash=(5, 4),
                tags='follow_guide'
            )
            self.canvas.create_line(
                cx,
                cy + gap,
                cx,
                cy + half_len,
                fill='#00e5ff',
                width=2,
                dash=(5, 4),
                tags='follow_guide'
            )
            self.follow_guide_item = h1
        else:
            self.canvas.delete('follow_guide')
            self.follow_guide_item = None
            self.draw_follow_guide()
            return
        self.canvas.tag_raise('follow_guide')
        if self.logo_item is not None:
            self.canvas.tag_raise(self.logo_item)

    def toggle_follow_guide(self):
        self.follow_guide_visible.set(not self.follow_guide_visible.get())
        self.draw_follow_guide()

    def place_logo_on_follow_button(self):
        if not self._raw_logo_img:
            self.add_logo()
            if not self._raw_logo_img:
                return

        if self.logo_height.get() < 24:
            self.logo_height.set(80)
        self.update_logo_preview()
        if not self.logo_item:
            return

        try:
            logo_h = max(1, int(self.logo_height.get()))
            logo_w = int(self._raw_logo_img.width * (logo_h / max(1, self._raw_logo_img.height)))
        except Exception:
            logo_w = logo_h = max(1, int(self.logo_height.get() or 80))

        center_x, center_y = self.follow_button_preview_center()
        x = max(0, min(self.PREVIEW_W - logo_w, center_x - logo_w / 2))
        y = max(0, min(self.PREVIEW_H - logo_h, center_y - logo_h / 2))
        self.canvas.coords(self.logo_item, x, y)
        self.canvas.tag_raise(self.logo_item)
        if not self.follow_guide_visible.get():
            self.follow_guide_visible.set(True)
        self.draw_follow_guide()
        self.show_frame()
    def update_logo_preview(self):
        if not self._raw_logo_img:
            return
        else:
            h = self.logo_height.get()
            ratio = h / self._raw_logo_img.height
            w = int(self._raw_logo_img.width * ratio)
            if w < 1 or h < 1:
                return None
            else:
                resized = self._raw_logo_img.resize((w, h), Image.Resampling.LANCZOS)
                alpha = int(255 * (self.logo_opacity.get() / 100.0))
                resized.putalpha(resized.getchannel('A').point(lambda i: int(i * alpha / 255.0)))
                self._logo_tk = ImageTk.PhotoImage(resized)
                if self.logo_item is None:
                    self.logo_item = self.canvas.create_image(20, 20, anchor=tk.NW, image=self._logo_tk, tags='logo')
                    self.canvas.tag_bind('logo', '<ButtonPress-1>', self.on_logo_press)
                    self.canvas.tag_bind('logo', '<B1-Motion>', self.on_logo_drag)
                    self.canvas.tag_bind('logo', '<Enter>', lambda e: self.canvas.config(cursor='hand2'))
                    self.canvas.tag_bind('logo', '<Leave>', lambda e: self.canvas.config(cursor='tcross'))
                else:
                    self.canvas.itemconfig(self.logo_item, image=self._logo_tk)
    def on_logo_press(self, e):
        self.dragging_logo = True
        self.drag_start_x = e.x
        self.drag_start_y = e.y
        coords = self.canvas.coords(self.logo_item)
        self.item_start_x = coords[0]
        self.item_start_y = coords[1]
    def on_logo_drag(self, e):
        if self.dragging_logo:
            dx = e.x - self.drag_start_x
            dy = e.y - self.drag_start_y
            self.canvas.coords(self.logo_item, self.item_start_x + dx, self.item_start_y + dy)
    def start_draw(self, e):
        items = self.canvas.find_withtag(tk.CURRENT)
        if items and 'logo' in self.canvas.gettags(items[0]):
            return
        else:
            self.dragging_logo = False
            self.start_x, self.start_y = (e.x, e.y)
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='#00bc8c', width=3, dash=(4, 4), tags='blur_rect')
    def draw_rect(self, e):
        if hasattr(self, 'dragging_logo') and self.dragging_logo:
            return
        else:
            if self.rect:
                self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)
    def end_draw(self, e):
        if hasattr(self, 'dragging_logo') and self.dragging_logo:
            self.dragging_logo = False
            return
        else:
            if not self.rect:
                return
            else:
                self.blur_regions.append(self.canvas.coords(self.rect))
                self.rect = None
                self._remember_current_video_effect_state()
                self.show_frame() # [THÊM MỚI] Cập nhật hình ảnh mờ ngay lập tức
    def clear_blurs(self):
        self.blur_regions.clear()
        self.canvas.delete('blur_rect') # [THÊM MỚI] Xóa khung nét đứt
        self._remember_current_video_effect_state()
        self.show_frame()

    def undo_blur(self, event=None):
        """Xóa vùng làm mờ được vẽ gần nhất (Undo)"""
        if self.blur_regions:
            self.blur_regions.pop()
            rects = self.canvas.find_withtag('blur_rect')
            if rects:
                self.canvas.delete(rects[-1])
            self._remember_current_video_effect_state()
            self.show_frame()
    def has_active_effects(self):
        line_mode = self.line_mode.get()
        export_ratio = self.export_ratio.get()
        output_quality = self.output_quality.get()
        no_line_modes = ('Kh\u00f4ng c\u00f3', 'Kh\xc3\xb4ng c\xc3\xb3', 'Không có')
        original_ratios = ('B\u1ea3n G\u1ed1c', 'B\u00e1\u00ba\u00a3n G\u00e1\u00bb\u2018c', 'Bản Gốc')
        if not (
            self.flip_h.get()
            or self.flip_v.get()
            or self.review_mode.get()
            or self.subtitle_in_blur.get()
            or line_mode not in no_line_modes
            or export_ratio not in original_ratios
            or output_quality != 'Gốc'
            or self.blur_regions
            or (self.logo_path and self.logo_item)
        ):
            return False
        return True
    def get_ffmpeg_effects_config(self):
        vw = self.PREVIEW_W
        vh = self.PREVIEW_H
        if self.cap:
            real_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or vw
            real_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or vh
        else:
            real_w, real_h = vw, vh
        sx, sy = (real_w / self.PREVIEW_W, real_h / self.PREVIEW_H)
        blur_regions = self.scale_preview_regions_to_source(self.blur_regions)
        subtitle_region = blur_regions[0] if self.subtitle_in_blur.get() and blur_regions else None
        logo_pos = None
        if self.logo_path and self.logo_item:
            coords = self.canvas.coords(self.logo_item)
            if coords:
                logo_pos = (int(coords[0] * sx), int(coords[1] * sy))
        return {
            'flip_h': self.flip_h.get(),
            'flip_v': self.flip_v.get(),
            'line_mode': self.line_mode.get(),
            'line_strength': self.line_strength.get(),
            'blur_strength': self.blur_strength.get(),
            'export_ratio': self.export_ratio.get(),
            'output_quality': self.output_quality.get(),
            'blur_regions': blur_regions,
            'subtitle_region': subtitle_region,
            'logo_path': self.logo_path,
            'logo_pos': logo_pos,
            'logo_height': int(self.logo_height.get() * sy),
            'logo_opacity': self.logo_opacity.get() / 100.0,
            'review_mode': self.review_mode.get(),
            'subtitle_in_blur': self.subtitle_in_blur.get(),
            'top_text': self.top_text.get(),
            'bottom_text': self.bottom_text.get(),
            'text_font_size': self.text_font_size.get(),
            'text_color_top': self.text_color_top.get(),
            'text_color_bot': self.text_color_bot.get(),
            'text_bg_color': self.text_bg_color.get(),
        }
    def create_edited_clip(self):
        if not self.video_path:
            raise RuntimeError('Chưa có video trong Video Editor.')
        else:
            clip = mp.VideoFileClip(self.video_path)
            flip_h_val = self.flip_h.get()
            flip_v_val = self.flip_v.get()
            review_val = self.review_mode.get()
            t_top = self.top_text.get()
            t_bot = self.bottom_text.get()
            f_size = self.text_font_size.get()
            c_top = self.text_color_top.get()
            c_bot = self.text_color_bot.get()
            c_bg = self.text_bg_color.get()
            line_val = self.line_mode.get()
            line_strength_val = self.line_strength.get()
            blur_strength_val = self.blur_strength.get()
            ratio_val = self.export_ratio.get()
            output_quality_val = self.output_quality.get()
            logo_h = self.logo_height.get()
            logo_op = self.logo_opacity.get() / 100.0
            logo_cords = self.canvas.coords(self.logo_item) if self.logo_path and self.logo_item else None
            copied_blurs = list(self.blur_regions)
            if flip_h_val:
                clip = mirror_x(clip)
            if flip_v_val:
                clip = mirror_y(clip)
            if review_val:
                clip = clip.fl(lambda gf, t: _add_review_overlay_pro(gf(t), t_top, t_bot, f_size, c_top, c_bot, c_bg))
            vw, vh = clip.size
            sx, sy = (vw / self.PREVIEW_W, vh / self.PREVIEW_H)
            scaled_blurs = []
            for x1, y1, x2, y2 in copied_blurs:
                x1s, y1s, x2s, y2s = (int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy))
                if x2s > x1s and y2s > y1s:
                        scaled_blurs.append((x1s, y1s, x2s, y2s))
            if scaled_blurs:
                clip = clip.fl(lambda gf, t: _blur_frame_with_regions(gf, t, scaled_blurs, blur_strength_val))
            if line_val!= 'Không có':
                clip = clip.fl(lambda gf, t: _add_anti_copyright_lines(gf, t, line_val, line_strength_val))
            if self.logo_path and logo_cords:
                    x_prev, y_prev = (logo_cords[0], logo_cords[1])
                    x_vid, y_vid = (int(x_prev * sx), int(y_prev * sy))
                    logo = mp.ImageClip(self.logo_path).set_duration(clip.duration).resize(height=max(16, int(logo_h * sy))).set_opacity(logo_op).set_position((x_vid, y_vid))
                    clip = mp.CompositeVideoClip([clip, logo])
            if ratio_val!= 'Bản Gốc':
                w, h = clip.size
                tr = 1.7777777777777777 if '16:9' in ratio_val else 0.5625 if '9:16' in ratio_val else 1.0
                cr = w / h
                if abs(cr - tr) > 0.01:
                  if cr > tr:
                    new_w = int(w)
                    new_h = int(round(w / tr))
                else:
                    new_w = int(round(h * tr))
                    new_h = int(h)

                # H.264/NVENC hoạt động ổn định hơn với kích thước số chẵn
                if new_w % 2 != 0:
                    new_w += 1

                if new_h % 2 != 0:
                    new_h += 1
                  #  bg = mp.ColorClip(size=(new_w, new_h), color=(0, 0, 0)).set_duration(clip.duration)
                  #  clip = mp.CompositeVideoClip([bg, clip.set_position('center')])
                    clip = clip.fl_image(lambda f: _pad_video_to_ratio_gpu(f, new_w, new_h))
            quality_h = _output_quality_height(output_quality_val)
            if quality_h:
                clip = clip.resize(height=quality_h)
            return clip
class MainApp:
    def __init__(self, root):
        # ***<module>.MainApp.__init__: Failure: Compilation Error
        self.root = root
        header = tb.Frame(self.root, bootstyle='secondary')
        header.pack(fill=X, padx=0, pady=0)
        title_box = tb.Frame(header, bootstyle='secondary')
        title_box.pack(side=LEFT, padx=24, pady=10)
        tb.Label(title_box, text='🎬 AUTOTTS PRO', font=(APP_FONT, 20, 'bold'), bootstyle='inverse-secondary').pack(anchor=W)
        tb.Label(title_box, text='Studio tạo giọng đọc, đồng bộ video & render nhanh', font=(APP_FONT, 10), bootstyle='inverse-secondary').pack(anchor=W, pady=(2, 0))
        badge_frame = tb.Frame(header, bootstyle='secondary')
        badge_frame.pack(side=RIGHT, padx=24, pady=10)
        tb.Label(badge_frame, text='⚡ Render Engine v2', font=(APP_FONT, 9, 'bold'), bootstyle='warning').pack(side=LEFT, padx=6)
        tb.Label(badge_frame, text='🎙 TTS Multi API', font=(APP_FONT, 9, 'bold'), bootstyle='info').pack(side=LEFT, padx=6)
        tb.Label(badge_frame, text=f'v2.5 | {APP_BUILD}', font=(APP_FONT, 9, 'bold'), bootstyle='success').pack(side=LEFT, padx=6)
        tb.Separator(self.root, orient='horizontal').pack(fill=X)
        main_frame = tb.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=YES, padx=8, pady=5)
        nb = tb.Notebook(main_frame, bootstyle='info')
        nb.pack(fill=BOTH, expand=YES)
        self.tab_editor = VideoEditorApp(nb, linked_mode=True)
        self.tab_tts = SrtToAudioApp(nb, editor_ref=self.tab_editor, switch_to_editor_cb=lambda: nb.select(self.tab_editor))
        nb.add(self.tab_tts, text='  🎙️ Tạo giọng & Video  ')
        nb.add(self.tab_editor, text='  🎬 Chỉnh Video  ')
        saved_settings = load_app_settings()
        self.tab_tts.apply_settings(saved_settings.get('srt_tab', {}))
        self.tab_editor.apply_settings(saved_settings.get('editor_tab', {}))
        tb.Separator(self.root, orient='horizontal').pack(fill=X, side=BOTTOM)
        footer_frame = tb.Frame(self.root, bootstyle='secondary')
        footer_frame.pack(side=BOTTOM, fill=X)
        btn_save = tb.Button(footer_frame, text='💾 Lưu Cấu Hình', bootstyle='success-outline', command=self.save_all_settings)
        btn_save.pack(side=LEFT, padx=14)
        try:
            import psutil as _ps
            _ram_gb = round(_ps.virtual_memory().total / 1073741824, 1)
            _ram_used = _ps.virtual_memory().percent
            _cpu_n = _ps.cpu_count(logical=True)
            _sys_txt = f'🖥 CPU {_cpu_n} cores  |  RAM {_ram_gb}GB ({_ram_used}%)  |  {APP_BUILD}'
        except Exception:
            _sys_txt = APP_BUILD
        self.lbl_sys = tb.Label(footer_frame, text=_sys_txt, font=(APP_FONT, 9, 'italic'), bootstyle='inverse-dark')
        self.lbl_sys.pack(side=RIGHT, padx=14, pady=4)
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        self._schedule_sys_refresh()
    def _schedule_sys_refresh(self):
        """Cập nhật thông tin máy ở footer realtime."""
        try:
            import psutil as _ps
            _ram_used = _ps.virtual_memory().percent
            _cpu_pct = _ps.cpu_percent(interval=None)
            self.lbl_sys.config(text=f'🖥 CPU {_cpu_pct:.0f}%  |  RAM {_ps.virtual_memory().total // 1073741824}GB ({_ram_used}%)  |  {APP_BUILD}')
        except Exception:
            pass
        self.root.after(5000, self._schedule_sys_refresh)
    def show_update_popup(self):
        UpdatePopup(self.root)
    def save_all_settings(self, show_msg=True):
        data = {'srt_tab': self.tab_tts.get_settings_dict(), 'editor_tab': self.tab_editor.get_settings_dict()}
        save_app_settings(data)
        if show_msg:
            messagebox.showinfo('Thành công', 'Đã lưu cài đặt. Lần sau mở lại tool sẽ tự động khôi phục cấu hình này!')
    def on_closing(self):
        self.save_all_settings(show_msg=False)
        try:
            self.tab_editor.cleanup()
        except Exception:
            pass
        for process in list(ACTIVE_FFMPEG_PROCESSES):
            try:
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass
        self.root.destroy()
def launch_app():
    """Khởi động cửa sổ chính của app (được gọi sau khi qua cổng license)."""
    root = tb.Window(title=APP_TITLE, themename=APP_THEME, size=(1320, 900))
    apply_modern_style(root)
    root.minsize(1120, 700)
    app = MainApp(root)
    root.mainloop()
if __name__ == '__main__':
    launch_app()





