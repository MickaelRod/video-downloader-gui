"""VIDEO DOWNLOADER GUI - Tkinter interface to download a video via yt-dlp or ffmpeg."""

import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import tkinter as tk
import urllib.request
from tkinter import filedialog, messagebox, ttk
from urllib.error import HTTPError, URLError

APP_TITLE = "VIDEO DOWNLOADER GUI"
DEFAULT_FILENAME_STEM = "Video"
WINDOW_WIDTH = 840
DEFAULT_LANGUAGE = "en"

FFMPEG_EXE = shutil.which("ffmpeg")
FFPROBE_EXE = shutil.which("ffprobe")
YTDLP_EXE = shutil.which("yt-dlp")

CURL_CFFI_COMPATIBLE_VERSIONS = ("0.5.10", "0.10.")
CURL_CFFI_RECOMMENDED_VERSION = "0.10.0"

TRANSLATIONS = {
    "en": {
        "app_title": "VIDEO DOWNLOADER GUI",
        "language_label": "Language:",
        "intro_overview_title": "Overview:",
        "intro_message": (
            "This script downloads a video from the Internet "
            "and saves it to the Downloads folder.\n"
            "yt-dlp supports many streaming platforms with format selection; "
            "FFmpeg only works with direct video file links (e.g. a URL ending in .mp4)."
        ),
        "intro_warning_title": "Disclaimer:",
        "intro_warning_message": (
            "Only download videos you own the rights to, that are in the public domain, "
            "or that the copyright holder allows you to download (e.g. under a Creative Commons "
            "license or explicit permission). Respect the terms of service of the platform you "
            "download from. You are solely responsible for how you use this tool."
        ),
        "requirements_title": "System requirements:",
        "requirement_ytdlp": "- yt-dlp installed: ",
        "requirement_ffmpeg": "- FFmpeg installed: ",
        "requirement_curl_cffi": "- curl_cffi installed (needed by some streaming platforms): ",
        "status_ok": "OK",
        "status_missing": "No",
        "status_missing_optional": "Not installed",
        "status_incompatible": "Incompatible version ({version})",
        "button_download_ytdlp": "Download with YT-DLP",
        "button_download_ffmpeg": "Download with FFMPEG",
        "no_library_message": "Neither library is available. Install yt-dlp or ffmpeg then restart the script.",
        "button_close": "Close",
        "step_video_link_title": "Video link",
        "url_label": "Enter the URL of the video to download:",
        "button_continue": "Continue",
        "button_back": "Back",
        "error_no_link": "Video link not provided",
        "error_link_not_found": "Incorrect video link: video not found",
        "error_link_access": "Error accessing the video (code {code})",
        "error_link_unreachable": "Could not access the video: {reason}",
        "step_analyzing_title": "Analyzing video...",
        "analyzing_message": "Retrieving video information, please wait.",
        "error_analyze": "Could not analyze the video: {error}",
        "step_options_title": "Download options",
        "duration_label": "Video duration: {duration}",
        "duration_unknown": "unknown",
        "title_label": "Video title (file name):",
        "video_format_label": "Video format:",
        "audio_format_label": "Audio format:",
        "default_format_label": "Default",
        "button_download": "Download",
        "warning_file_exists": "The video \"{filename}\" already exists. Please choose another name.",
        "step_downloading_title": "Downloading...",
        "downloading_message": "Downloading \"{name}\", please wait.",
        "error_unknown": "Unknown error",
        "step_filename_title": "Video name",
        "filename_label": "Video file name (leave blank for \"{default}\"):",
        "folder_label": "Destination folder:",
        "button_browse": "Browse...",
        "step_summary_title": "Summary",
        "status_success": "Download successful",
        "status_failure": "Download failed",
        "status_cancelled": "Download cancelled",
        "summary_name": "Video name: {name}",
        "summary_size": "Video size: {size}",
        "summary_location": "Location: {location}",
        "summary_duration": "Video duration: {duration}",
        "summary_error": "Error: {error}",
        "summary_error_curl_cffi_hint": (
            "This may be caused by curl_cffi being missing or incompatible with yt-dlp. "
            "Install a compatible version, e.g.: pip install curl_cffi=={version}"
        ),
        "summary_error_bot_check_hint": (
            "This platform requires a bot-check verification (e.g. sign-in confirmation) "
            "that this script cannot pass. Try again later or with another video."
        ),
        "summary_elapsed": "Operation duration: {elapsed}",
        "button_new_video": "New video",
        "button_quit": "Quit",
        "button_cancel": "Cancel",
        "progress_percent": "{percent:.0f}%",
        "progress_unknown": "Downloading...",
        "unit_hour_min_sec": "{hours}h {minutes:02d}min {seconds:02d}s",
        "unit_min_sec": "{minutes}min {seconds:02d}s",
        "unit_sec": "{seconds}s",
    },
    "fr": {
        "app_title": "VIDEO DOWNLOADER GUI",
        "language_label": "Langue :",
        "intro_overview_title": "Présentation :",
        "intro_message": (
            "Ce script permet de télécharger une vidéo depuis Internet "
            "et de l'enregistrer dans le dossier Téléchargements.\n"
            "yt-dlp prend en charge de nombreuses plateformes de streaming avec choix des formats ; "
            "FFmpeg fonctionne uniquement avec des liens directs vers un fichier vidéo (ex. une URL se terminant par .mp4)."
        ),
        "intro_warning_title": "Avertissement :",
        "intro_warning_message": (
            "Ne télécharger que des vidéos dont vous détenez les droits, qui sont dans le domaine "
            "public, ou dont l'ayant droit autorise le téléchargement (par exemple sous licence "
            "Creative Commons ou avec une autorisation explicite). Respecter les conditions "
            "d'utilisation de la plateforme depuis laquelle vous téléchargez. Vous êtes seul "
            "responsable de l'usage que vous faites de cet outil."
        ),
        "requirements_title": "Configuration système requise :",
        "requirement_ytdlp": "- YT-DLP installé : ",
        "requirement_ffmpeg": "- FFmpeg installé : ",
        "requirement_curl_cffi": "- curl_cffi installé (nécessaire pour certaines plateformes de streaming) : ",
        "status_ok": "OK",
        "status_missing": "Non",
        "status_missing_optional": "Non installé",
        "status_incompatible": "Version incompatible ({version})",
        "button_download_ytdlp": "Télécharger avec YT-DLP",
        "button_download_ffmpeg": "Télécharger avec FFMPEG",
        "no_library_message": "Aucune des deux librairies n'est disponible. Installer yt-dlp ou ffmpeg puis relancer le script.",
        "button_close": "Fermer",
        "step_video_link_title": "Lien de la vidéo",
        "url_label": "Indiquer l'URL de la vidéo à télécharger :",
        "button_continue": "Continuer",
        "button_back": "Retour",
        "error_no_link": "Lien vers la vidéo non précisé",
        "error_link_not_found": "Lien vers la vidéo incorrect : vidéo non trouvée",
        "error_link_access": "Erreur lors de l'accès à la vidéo (code {code})",
        "error_link_unreachable": "Impossible d'accéder à la vidéo : {reason}",
        "step_analyzing_title": "Analyse de la vidéo...",
        "analyzing_message": "Récupération des informations de la vidéo, patienter.",
        "error_analyze": "Impossible d'analyser la vidéo : {error}",
        "step_options_title": "Options de téléchargement",
        "duration_label": "Durée de la vidéo : {duration}",
        "duration_unknown": "inconnue",
        "title_label": "Titre de la vidéo (nom du fichier) :",
        "video_format_label": "Format vidéo :",
        "audio_format_label": "Format audio :",
        "default_format_label": "Par défaut",
        "button_download": "Télécharger",
        "warning_file_exists": "La vidéo \"{filename}\" existe déjà. Préciser un autre nom.",
        "step_downloading_title": "Téléchargement en cours...",
        "downloading_message": "Téléchargement de \"{name}\" en cours, patienter.",
        "error_unknown": "Erreur inconnue",
        "step_filename_title": "Nom de la vidéo",
        "filename_label": "Nom du fichier vidéo (laisser vide pour \"{default}\") :",
        "folder_label": "Dossier de destination :",
        "button_browse": "Parcourir...",
        "step_summary_title": "Récapitulatif",
        "status_success": "Téléchargement réussi",
        "status_failure": "Échec du téléchargement",
        "status_cancelled": "Téléchargement annulé",
        "summary_name": "Nom de la vidéo : {name}",
        "summary_size": "Taille de la vidéo : {size}",
        "summary_location": "Emplacement : {location}",
        "summary_duration": "Durée de la vidéo : {duration}",
        "summary_error": "Erreur : {error}",
        "summary_error_curl_cffi_hint": (
            "Cela peut être dû à curl_cffi absent ou incompatible avec yt-dlp. "
            "Installer une version compatible, par exemple : pip install curl_cffi=={version}"
        ),
        "summary_error_bot_check_hint": (
            "Cette plateforme exige une vérification anti-bot (par exemple une confirmation de "
            "connexion) que ce script ne peut pas passer. Réessayer plus tard ou avec une autre vidéo."
        ),
        "summary_elapsed": "Durée de l'opération : {elapsed}",
        "button_new_video": "Nouvelle vidéo",
        "button_quit": "Quitter",
        "button_cancel": "Annuler",
        "progress_percent": "{percent:.0f} %",
        "progress_unknown": "Téléchargement en cours...",
        "unit_hour_min_sec": "{hours}h {minutes:02d}min {seconds:02d}s",
        "unit_min_sec": "{minutes}min {seconds:02d}s",
        "unit_sec": "{seconds}s",
    },
}


def get_downloads_folder() -> str:
    return os.path.join(os.path.expanduser("~"), "Downloads")


def remove_leftover_part_files(destination: str) -> None:
    """Removes stale yt-dlp temp files (.part, .part-Frag*, .ytdl) left by an interrupted download."""
    folder = os.path.dirname(destination)
    basename = os.path.basename(destination)
    for entry in os.listdir(folder):
        if entry.startswith(basename) and (
            entry.endswith(".part") or entry.endswith(".ytdl") or ".part-Frag" in entry
        ):
            try:
                os.remove(os.path.join(folder, entry))
            except OSError:
                pass


def is_ffmpeg_available() -> bool:
    return bool(FFMPEG_EXE) and bool(FFPROBE_EXE)


def is_ytdlp_available() -> bool:
    return bool(YTDLP_EXE)


def get_curl_cffi_status():
    """Returns (installed_version_or_None, is_compatible)."""
    try:
        import curl_cffi
        version = getattr(curl_cffi, "__version__", "")
    except ImportError:
        return None, False

    is_compatible = any(version.startswith(prefix) for prefix in CURL_CFFI_COMPATIBLE_VERSIONS)
    return version, is_compatible


def is_curl_cffi_related_error(error_text: str) -> bool:
    lowered = error_text.lower()
    return "curl_cffi" in lowered or "impersonate" in lowered


def is_bot_check_error(error_text: str) -> bool:
    lowered = error_text.lower()
    return "sign in to confirm" in lowered or "confirm you're not a bot" in lowered


def check_video_url(url: str) -> None:
    """Raises an exception if the URL is empty or does not point to an existing resource."""
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status >= 400:
            raise HTTPError(url, response.status, "Not Found", None, None)


KNOWN_VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv")


def ensure_mp4_extension(filename: str) -> str:
    filename = filename.strip()
    if not filename:
        return DEFAULT_FILENAME_STEM + ".mp4"
    lower_filename = filename.lower()
    for extension in KNOWN_VIDEO_EXTENSIONS:
        if lower_filename.endswith(extension):
            filename = filename[: -len(extension)]
            break
    return filename + ".mp4"


def sanitize_filename(name: str) -> str:
    name = re.sub(r"\s*\|\s*", " - ", name)
    name = re.sub(r'[\\/:*?"<>]', "_", name).strip()
    return name or DEFAULT_FILENAME_STEM


def format_file_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{int(num_bytes)} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} GB"


YTDLP_PROGRESS_RE = re.compile(r"\[download\]\s+(\d{1,3}(?:\.\d+)?)%")
FFMPEG_TIME_RE = re.compile(r"out_time_ms=(\d+)")


def parse_ytdlp_progress_line(line: str):
    match = YTDLP_PROGRESS_RE.search(line)
    return float(match.group(1)) if match else None


def parse_ffmpeg_progress_line(line: str, total_duration):
    """Returns a percentage (0-100) from an ffmpeg `-progress pipe:1` line, or None."""
    if total_duration is None or total_duration <= 0:
        return None
    match = FFMPEG_TIME_RE.match(line)
    if not match:
        return None
    elapsed_seconds = int(match.group(1)) / 1_000_000
    return max(0.0, min(100.0, elapsed_seconds / total_duration * 100))


def get_video_duration(filepath: str):
    try:
        result = subprocess.run(
            [
                FFPROBE_EXE,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return None


VCODEC_LABELS = {
    "avc1": "AVC",
    "av01": "AV1",
    "vp9": "VP9",
    "vp09": "VP9",
    "hev1": "HEVC",
    "hvc1": "HEVC",
}


def codec_short_label(codec: str) -> str:
    prefix = codec.split(".")[0].lower()
    return VCODEC_LABELS.get(prefix, prefix.upper())


def ytdlp_fetch_info(url: str):
    """Returns (title, duration_string, video_formats, audio_formats) via yt-dlp -j.

    video_formats and audio_formats are lists of (format_id, label).
    """
    result = subprocess.run(
        [YTDLP_EXE, "-j", "--skip-download", url],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if not result.stdout.strip():
        error_lines = [line for line in (result.stderr or "").splitlines() if line.strip()]
        raise RuntimeError(error_lines[-1] if error_lines else "yt-dlp returned no data")
    data = json.loads(result.stdout.strip().splitlines()[-1])

    title = data.get("title", "")
    duration_string = data.get("duration_string", "")

    video_formats = []
    audio_formats = []
    for entry in data.get("formats", []):
        if entry.get("ext") == "mhtml" or entry.get("format_note") == "storyboard":
            continue
        vcodec = entry.get("vcodec")
        acodec = entry.get("acodec")
        has_video = vcodec not in (None, "none")
        has_audio = acodec not in (None, "none")
        format_id = entry.get("format_id", "")

        if has_video and not has_audio:
            resolution = entry.get("resolution") or entry.get("format_note") or ""
            extension = entry.get("ext", "").upper()
            codec_label = codec_short_label(vcodec) if vcodec else ""
            bitrate = entry.get("vbr") or entry.get("tbr")
            bitrate_label = f"{round(bitrate)} kbps" if bitrate else ""
            details = " ".join(part for part in (codec_label, bitrate_label) if part)
            label = f"{resolution} - {details} ({extension})" if details else f"{resolution} ({extension})"
            video_formats.append((format_id, label))
        elif has_audio and not has_video:
            quality = (entry.get("format_note") or "").capitalize()
            extension = entry.get("ext", "").upper()
            audio_formats.append((format_id, f"{quality} ({extension})"))

    return title, duration_string, video_formats, audio_formats


class VideosDownloaderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.language = DEFAULT_LANGUAGE
        self.root.title(APP_TITLE)
        self.root.resizable(False, False)

        self.video_url = ""
        self.video_name = DEFAULT_FILENAME_STEM + ".mp4"
        self.download_folder = get_downloads_folder()
        self.use_ytdlp = False
        self.download_process = None
        self.download_cancelled = False

        self.show_intro_step()

    # ---------- Translation helper ----------

    def t(self, key: str, **kwargs) -> str:
        text = TRANSLATIONS[self.language][key]
        return text.format(**kwargs) if kwargs else text

    def format_duration(self, seconds: float) -> str:
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return self.t("unit_hour_min_sec", hours=hours, minutes=minutes, seconds=secs)
        if minutes:
            return self.t("unit_min_sec", minutes=minutes, seconds=secs)
        return self.t("unit_sec", seconds=secs)

    # ---------- UI helpers ----------

    def clear_window(self) -> None:
        for widget in self.root.winfo_children():
            widget.destroy()

    def build_frame(self, title: str) -> tk.Frame:
        self.clear_window()
        frame = tk.Frame(self.root, padx=24, pady=20)
        frame.pack()
        tk.Frame(frame, width=WINDOW_WIDTH - 48, height=1).pack()
        tk.Label(frame, text=title, font=("Segoe UI", 14, "bold")).pack(pady=(0, 12))
        return frame

    def build_folder_picker(self, frame: tk.Frame) -> None:
        """Adds a destination folder label + entry + Browse button to `frame`, bound to self.download_folder."""
        tk.Label(frame, text=self.t("folder_label")).pack(anchor="w")

        folder_row = tk.Frame(frame)
        folder_row.pack(fill="x", pady=(6, 16))

        folder_entry = tk.Entry(folder_row, width=76)
        folder_entry.pack(side="left", fill="x", expand=True)
        folder_entry.insert(0, self.download_folder)

        def on_change(event=None):
            self.download_folder = folder_entry.get().strip() or get_downloads_folder()

        folder_entry.bind("<FocusOut>", on_change)

        def on_browse():
            chosen = filedialog.askdirectory(initialdir=self.download_folder or get_downloads_folder())
            if chosen:
                self.download_folder = chosen
                folder_entry.delete(0, tk.END)
                folder_entry.insert(0, chosen)

        tk.Button(folder_row, text=self.t("button_browse"), command=on_browse).pack(side="left", padx=(8, 0))

    # ---------- Step 1: introduction ----------

    def show_intro_step(self) -> None:
        frame = self.build_frame(self.t("app_title"))

        language_frame = tk.Frame(frame)
        language_frame.pack(anchor="e", pady=(0, 12))
        tk.Label(language_frame, text=self.t("language_label")).pack(side="left", padx=(0, 6))
        language_combo = ttk.Combobox(
            language_frame, values=["English", "Français"], width=12, state="readonly"
        )
        language_combo.pack(side="left")
        language_combo.current(0 if self.language == "en" else 1)

        def on_language_change(event=None):
            self.language = "en" if language_combo.get() == "English" else "fr"
            self.show_intro_step()

        language_combo.bind("<<ComboboxSelected>>", on_language_change)

        overview_frame = tk.Frame(frame)
        overview_frame.pack(fill="x", pady=(0, 16))
        tk.Label(overview_frame, text=self.t("intro_overview_title"), font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(
            overview_frame, text=self.t("intro_message"),
            wraplength=WINDOW_WIDTH - 60, justify="left",
        ).pack(anchor="w")

        warning_frame = tk.Frame(frame)
        warning_frame.pack(fill="x", pady=(0, 16))
        tk.Label(warning_frame, text=self.t("intro_warning_title"), font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(
            warning_frame, text=self.t("intro_warning_message"),
            wraplength=WINDOW_WIDTH - 60, justify="left",
        ).pack(anchor="w")

        ytdlp_ok = is_ytdlp_available()
        ffmpeg_ok = is_ffmpeg_available()

        requirements_frame = tk.Frame(frame)
        requirements_frame.pack(fill="x", pady=(0, 20))
        tk.Label(requirements_frame, text=self.t("requirements_title"), font=("Segoe UI", 10, "bold")).pack(
            anchor="w"
        )

        for label, available in (
            (self.t("requirement_ytdlp"), ytdlp_ok),
            (self.t("requirement_ffmpeg"), ffmpeg_ok),
        ):
            status_text = self.t("status_ok") if available else self.t("status_missing")
            status_color = "green" if available else "red"
            status_line = tk.Frame(requirements_frame)
            status_line.pack(anchor="w", pady=(4, 0))
            tk.Label(status_line, text=label).pack(side="left")
            tk.Label(status_line, text=status_text, fg=status_color, font=("Segoe UI", 10, "bold")).pack(side="left")

        curl_cffi_version, curl_cffi_compatible = get_curl_cffi_status()
        if curl_cffi_version is None:
            curl_cffi_status_text = self.t("status_missing_optional")
            curl_cffi_status_color = "#b8860b"
        elif curl_cffi_compatible:
            curl_cffi_status_text = self.t("status_ok")
            curl_cffi_status_color = "green"
        else:
            curl_cffi_status_text = self.t("status_incompatible", version=curl_cffi_version)
            curl_cffi_status_color = "#b8860b"
        curl_cffi_line = tk.Frame(requirements_frame)
        curl_cffi_line.pack(anchor="w", pady=(4, 0))
        tk.Label(curl_cffi_line, text=self.t("requirement_curl_cffi")).pack(side="left")
        tk.Label(
            curl_cffi_line, text=curl_cffi_status_text, fg=curl_cffi_status_color, font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        if ytdlp_ok or ffmpeg_ok:
            buttons_frame = tk.Frame(frame)
            buttons_frame.pack(pady=(8, 0))
            if ytdlp_ok:
                tk.Button(
                    buttons_frame, text=self.t("button_download_ytdlp"), width=22,
                    command=lambda: self.start_download_flow(True)
                ).pack(side="left", padx=(0, 8) if ffmpeg_ok else 0)
            if ffmpeg_ok:
                tk.Button(
                    buttons_frame, text=self.t("button_download_ffmpeg"), width=22,
                    command=lambda: self.start_download_flow(False)
                ).pack(side="left")
        else:
            tk.Label(
                frame,
                text=self.t("no_library_message"),
                fg="red",
                wraplength=WINDOW_WIDTH - 60,
                justify="left",
            ).pack(pady=(0, 12))
            tk.Button(frame, text=self.t("button_close"), width=24, command=self.root.destroy).pack()

    def start_download_flow(self, use_ytdlp: bool) -> None:
        self.use_ytdlp = use_ytdlp
        self.show_url_step()

    # ---------- Step 2: video URL ----------

    def show_url_step(self) -> None:
        frame = self.build_frame(self.t("step_video_link_title"))

        tk.Label(frame, text=self.t("url_label")).pack(anchor="w")

        url_entry = tk.Entry(frame, width=96)
        url_entry.pack(pady=(6, 16))
        url_entry.insert(0, self.video_url)
        url_entry.focus_set()

        def on_continue(event=None):
            self.video_url = url_entry.get().strip()

            if not self.video_url:
                messagebox.showerror(self.t("app_title"), self.t("error_no_link"))
                return

            self.root.config(cursor="wait")
            self.root.update()
            try:
                check_video_url(self.video_url)
            except HTTPError as error:
                if error.code == 404:
                    messagebox.showerror(self.t("app_title"), self.t("error_link_not_found"))
                else:
                    messagebox.showerror(self.t("app_title"), self.t("error_link_access", code=error.code))
                return
            except URLError as error:
                messagebox.showerror(self.t("app_title"), self.t("error_link_unreachable", reason=error.reason))
                return
            finally:
                self.root.config(cursor="")

            if self.use_ytdlp:
                self.load_ytdlp_info()
            else:
                self.show_filename_step()

        url_entry.bind("<Return>", on_continue)

        buttons_frame = tk.Frame(frame)
        buttons_frame.pack(pady=(4, 0))
        tk.Button(buttons_frame, text=self.t("button_continue"), width=20, command=on_continue).pack(
            side="left", padx=(0, 8)
        )
        tk.Button(buttons_frame, text=self.t("button_back"), width=20, command=self.show_intro_step).pack(side="left")

    # ---------- Step 3a (yt-dlp): fetch info ----------

    def load_ytdlp_info(self) -> None:
        frame = self.build_frame(self.t("step_analyzing_title"))
        tk.Label(frame, text=self.t("analyzing_message"), wraplength=WINDOW_WIDTH - 60, justify="left").pack()
        self.root.update()

        try:
            title, duration_string, video_formats, audio_formats = ytdlp_fetch_info(self.video_url)
        except Exception as error:
            if is_bot_check_error(str(error)):
                messagebox.showerror(self.t("app_title"), self.t("summary_error_bot_check_hint"))
            else:
                messagebox.showerror(self.t("app_title"), self.t("error_analyze", error=error))
            self.show_url_step()
            return

        self.show_ytdlp_options_step(title, duration_string, video_formats, audio_formats)

    # ---------- Step 3b (yt-dlp): download options ----------

    def show_ytdlp_options_step(
        self, title, duration_string, video_formats, audio_formats, warning: str = "",
        selected_title=None, selected_video_index: int = 0, selected_audio_index: int = 0,
    ) -> None:
        frame = self.build_frame(self.t("step_options_title"))

        if warning:
            tk.Label(frame, text=warning, fg="red", wraplength=WINDOW_WIDTH - 60, justify="left").pack(pady=(0, 12))

        self.build_folder_picker(frame)

        tk.Label(frame, text=self.t("duration_label", duration=duration_string or self.t("duration_unknown"))).pack(
            anchor="w", pady=(0, 12)
        )

        tk.Label(frame, text=self.t("title_label")).pack(anchor="w")
        title_entry = tk.Entry(frame, width=96)
        title_entry.pack(pady=(6, 16))
        title_entry.insert(0, selected_title if selected_title is not None else (title or ""))

        default_label = self.t("default_format_label")

        tk.Label(frame, text=self.t("video_format_label")).pack(anchor="w")
        video_values = [default_label] + [label for _, label in video_formats]
        video_combo = ttk.Combobox(frame, values=video_values, width=91, state="readonly")
        video_combo.pack(pady=(6, 16))
        video_combo.current(selected_video_index)

        tk.Label(frame, text=self.t("audio_format_label")).pack(anchor="w")
        audio_values = [default_label] + [label for _, label in audio_formats]
        audio_combo = ttk.Combobox(frame, values=audio_values, width=91, state="readonly")
        audio_combo.pack(pady=(6, 16))
        audio_combo.current(selected_audio_index)

        def on_download():
            chosen_title = title_entry.get().strip() or title or DEFAULT_FILENAME_STEM
            self.video_name = ensure_mp4_extension(sanitize_filename(chosen_title))

            video_index = video_combo.current() - 1
            audio_index = audio_combo.current() - 1
            video_format_id = video_formats[video_index][0] if video_index >= 0 else None
            audio_format_id = audio_formats[audio_index][0] if audio_index >= 0 else None

            destination = os.path.join(self.download_folder, self.video_name)
            if os.path.exists(destination):
                self.show_ytdlp_options_step(
                    title, duration_string, video_formats, audio_formats,
                    warning=self.t("warning_file_exists", filename=self.video_name),
                    selected_title=title_entry.get(),
                    selected_video_index=video_combo.current(),
                    selected_audio_index=audio_combo.current(),
                )
                return

            self.run_ytdlp_download(destination, video_format_id, audio_format_id)

        buttons_frame = tk.Frame(frame)
        buttons_frame.pack(pady=(8, 0))
        tk.Button(buttons_frame, text=self.t("button_download"), width=20, command=on_download).pack(
            side="left", padx=(0, 8)
        )
        tk.Button(buttons_frame, text=self.t("button_back"), width=20, command=self.show_url_step).pack(side="left")

    def run_ytdlp_download(self, destination: str, video_format_id, audio_format_id) -> None:
        remove_leftover_part_files(destination)

        command = [YTDLP_EXE, "-o", destination, "--no-continue", "--newline"]
        if video_format_id and audio_format_id:
            command += ["-f", f"{video_format_id}+{audio_format_id}"]
        elif video_format_id:
            command += ["-f", f"{video_format_id}+bestaudio"]
        elif audio_format_id:
            command += ["-f", f"bestvideo+{audio_format_id}"]
        command += ["--merge-output-format", "mp4", self.video_url]

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        def on_finished(returncode: int, stderr_text: str):
            success = returncode == 0 and os.path.exists(destination)
            error_message = ""
            if not success and not self.download_cancelled:
                error_message = stderr_text.strip().splitlines()[-1] if stderr_text else self.t("error_unknown")
                if is_bot_check_error(stderr_text or ""):
                    error_message += " " + self.t("summary_error_bot_check_hint")
                elif is_curl_cffi_related_error(stderr_text or ""):
                    error_message += " " + self.t(
                        "summary_error_curl_cffi_hint", version=CURL_CFFI_RECOMMENDED_VERSION
                    )
            return success, error_message

        self.run_download_with_progress(process, destination, parse_ytdlp_progress_line, on_finished)

    # ---------- Step 3 (ffmpeg): file name ----------

    def show_filename_step(self, warning: str = "") -> None:
        frame = self.build_frame(self.t("step_filename_title"))

        if warning:
            tk.Label(frame, text=warning, fg="red", wraplength=WINDOW_WIDTH - 60, justify="left").pack(pady=(0, 12))

        self.build_folder_picker(frame)

        default_filename = DEFAULT_FILENAME_STEM + ".mp4"
        tk.Label(frame, text=self.t("filename_label", default=default_filename)).pack(anchor="w")

        name_entry = tk.Entry(frame, width=90)
        name_entry.pack(anchor="w", pady=(6, 16))
        name_entry.focus_set()

        def on_download(event=None):
            filename = ensure_mp4_extension(name_entry.get())
            destination = os.path.join(self.download_folder, filename)

            if os.path.exists(destination):
                self.show_filename_step(
                    warning=self.t("warning_file_exists", filename=filename)
                )
                return

            self.video_name = filename
            self.run_ffmpeg_download(destination)

        name_entry.bind("<Return>", on_download)
        tk.Button(frame, text=self.t("button_download"), width=20, command=on_download).pack()

    def run_ffmpeg_download(self, destination: str) -> None:
        process = subprocess.Popen(
            [FFMPEG_EXE, "-y", "-i", self.video_url, "-c", "copy", "-progress", "pipe:1", "-nostats", destination],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Fetched on a background thread so a slow/unreachable ffprobe never delays showing
        # the downloading screen or blocks the Tkinter main loop.
        total_duration_holder = {"value": None}
        threading.Thread(
            target=lambda: total_duration_holder.__setitem__("value", get_video_duration(self.video_url)),
            daemon=True,
        ).start()

        def parse_progress_line(line: str):
            return parse_ffmpeg_progress_line(line, total_duration_holder["value"])

        def on_finished(returncode: int, stderr_text: str):
            success = returncode == 0
            error_message = ""
            if not success and not self.download_cancelled:
                error_message = stderr_text.strip().splitlines()[-1] if stderr_text else self.t("error_unknown")
            return success, error_message

        self.run_download_with_progress(process, destination, parse_progress_line, on_finished)

    # ---------- Downloading screen with progress bar ----------

    def run_download_with_progress(self, process, destination, parse_progress_line, on_finished) -> None:
        """Drives a download subprocess to completion while updating a progress bar.

        stdout is read on a background thread (subprocess pipes are blocking) and fed into a
        queue so the Tkinter main loop never blocks. `parse_progress_line(line)` must return a
        percentage (0-100) or None. `on_finished(returncode, stderr_text)` is called once the
        process exits and must return (success, error_message).
        """
        frame = self.build_frame(self.t("step_downloading_title"))
        tk.Label(frame, text=self.t("downloading_message", name=self.video_name),
                 wraplength=WINDOW_WIDTH - 60, justify="left").pack(pady=(0, 12))

        progress_bar = ttk.Progressbar(frame, length=WINDOW_WIDTH - 60, mode="determinate", maximum=100)
        progress_bar.pack(pady=(0, 8))

        progress_label = tk.Label(frame, text=self.t("progress_unknown"))
        progress_label.pack(pady=(0, 12))

        self.download_process = process
        self.download_cancelled = False
        start_time = time.time()
        got_percent = False

        line_queue = queue.Queue()
        stderr_lines = []

        def read_stdout():
            for line in iter(process.stdout.readline, ""):
                line_queue.put(line)
            process.stdout.close()

        def read_stderr():
            # Must be drained continuously: on Windows, an unread stderr pipe fills up and
            # blocks the subprocess entirely (including its stdout writes) once ffmpeg/yt-dlp
            # produces enough stderr output (e.g. ffmpeg's HLS warnings).
            for line in iter(process.stderr.readline, ""):
                stderr_lines.append(line)
            process.stderr.close()

        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        def on_cancel():
            self.download_cancelled = True
            cancel_button.config(state="disabled")
            try:
                process.terminate()
            except OSError:
                pass

        cancel_button = tk.Button(frame, text=self.t("button_cancel"), width=20, command=on_cancel)
        cancel_button.pack()

        INDETERMINATE_FALLBACK_MS = 3000

        def switch_to_indeterminate():
            if got_percent or process.poll() is not None:
                return
            progress_bar.config(mode="indeterminate")
            progress_bar.start(15)

        self.root.after(INDETERMINATE_FALLBACK_MS, switch_to_indeterminate)

        def tick():
            nonlocal got_percent
            try:
                while True:
                    line = line_queue.get_nowait()
                    percent = parse_progress_line(line)
                    if percent is not None:
                        if not got_percent:
                            got_percent = True
                            progress_bar.stop()
                            progress_bar.config(mode="determinate")
                        progress_bar["value"] = percent
                        progress_label.config(text=self.t("progress_percent", percent=percent))
            except queue.Empty:
                pass

            if process.poll() is None:
                self.root.after(50, tick)
                return

            progress_bar.stop()

            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
            stderr_text = "".join(stderr_lines)
            self.download_process = None
            elapsed = time.time() - start_time

            if self.download_cancelled:
                remove_leftover_part_files(destination)
                if os.path.exists(destination):
                    try:
                        os.remove(destination)
                    except OSError:
                        pass
                self.show_summary_step(False, destination, elapsed, "", cancelled=True)
                return

            success, error_message = on_finished(process.returncode, stderr_text)
            self.show_summary_step(success, destination, elapsed, error_message)

        tick()

    # ---------- Final step: summary ----------

    def show_summary_step(
        self, success: bool, destination: str, elapsed: float, error_message: str, cancelled: bool = False
    ) -> None:
        frame = self.build_frame(self.t("step_summary_title"))

        if cancelled:
            status_text = self.t("status_cancelled")
            status_color = "#b8860b"
        else:
            status_text = self.t("status_success") if success else self.t("status_failure")
            status_color = "green" if success else "red"
        tk.Label(frame, text=status_text, font=("Segoe UI", 11, "bold"), fg=status_color).pack(pady=(0, 12))

        details = [self.t("summary_name", name=self.video_name)]

        if success:
            file_size = format_file_size(os.path.getsize(destination))
            details.append(self.t("summary_size", size=file_size))
            duration_seconds = get_video_duration(destination) if is_ffmpeg_available() else None
            duration = self.format_duration(duration_seconds) if duration_seconds is not None else self.t(
                "duration_unknown"
            )
            details.append(self.t("summary_location", location=destination))
            details.append(self.t("summary_duration", duration=duration))
        elif not cancelled:
            details.append(self.t("summary_error", error=error_message))

        details.append(self.t("summary_elapsed", elapsed=self.format_duration(elapsed)))

        for line in details:
            tk.Label(frame, text=line, wraplength=WINDOW_WIDTH - 60, justify="left", anchor="w").pack(
                fill="x", pady=2
            )

        buttons_frame = tk.Frame(frame)
        buttons_frame.pack(pady=(16, 0))
        tk.Button(buttons_frame, text=self.t("button_new_video"), width=20, command=self.show_intro_step).pack(
            side="left", padx=(0, 8)
        )
        tk.Button(buttons_frame, text=self.t("button_quit"), width=20, command=self.root.destroy).pack(side="left")


def main() -> None:
    root = tk.Tk()
    VideosDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
