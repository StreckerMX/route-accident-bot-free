"""Asistente grafico de configuracion inicial."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from .config_state import SETTINGS_FILE, load_config, save_config, write_env_file
from .google_maps_link_parser import GoogleMapsLinkError, parse_google_maps_link


class SetupWizard(ctk.CTk):
    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.config_path = base_dir / SETTINGS_FILE
        self.env_path = base_dir / ".env"
        self.config = load_config(self.config_path)
        self.completed = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Configuracion - Route Accident Bot FREE")
        self.geometry("640x760")
        self.minsize(560, 680)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _build_ui(self) -> None:
        ctk.CTkLabel(self, text="Configuracion inicial", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(16, 4))
        ctk.CTkLabel(self, text="APIs gratuitas - sin tarjeta de credito", text_color="gray70").pack(pady=(0, 12))

        form = ctk.CTkScrollableFrame(self)
        form.pack(fill="both", expand=True, padx=16, pady=8)

        ctk.CTkLabel(form, text="API Key - OpenRouteService").pack(anchor="w", padx=8, pady=(8, 0))
        self.ors_key_entry = ctk.CTkEntry(form, show="*")
        self.ors_key_entry.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(form, text="API Key - TomTom").pack(anchor="w", padx=8, pady=(8, 0))
        self.tomtom_key_entry = ctk.CTkEntry(form, show="*")
        self.tomtom_key_entry.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(form, text="Correo para Nominatim (recomendado)").pack(anchor="w", padx=8, pady=(8, 0))
        self.email_entry = ctk.CTkEntry(form)
        self.email_entry.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(form, text="Enlace de Google Maps").pack(anchor="w", padx=8, pady=(12, 0))
        link_row = ctk.CTkFrame(form, fg_color="transparent")
        link_row.pack(fill="x", padx=8, pady=4)
        link_row.grid_columnconfigure(0, weight=1)
        self.link_entry = ctk.CTkEntry(link_row, placeholder_text="Pega el enlace de tu ruta")
        self.link_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(link_row, text="Pegar", width=80, command=self._paste_link).grid(row=0, column=1)

        ctk.CTkLabel(form, text="Tipo de carretera").pack(anchor="w", padx=8, pady=(12, 0))
        self.road_var = tk.StringVar(value="free")
        road_row = ctk.CTkFrame(form, fg_color="transparent")
        road_row.pack(fill="x", padx=8, pady=4)
        ctk.CTkRadioButton(road_row, text="Libre (sin cuota)", variable=self.road_var, value="free").pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(road_row, text="Cuota", variable=self.road_var, value="toll").pack(side="left")

        self.periodic_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(form, text="Revisar automaticamente cada 45 min", variable=self.periodic_var).pack(anchor="w", padx=8, pady=12)

        self.telegram_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(form, text="Activar Telegram (opcional)", variable=self.telegram_var, command=self._toggle_telegram).pack(anchor="w", padx=8, pady=4)
        self.telegram_frame = ctk.CTkFrame(form, fg_color="transparent")
        self.telegram_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(self.telegram_frame, text="Token").pack(anchor="w")
        self.telegram_token_entry = ctk.CTkEntry(self.telegram_frame, show="*")
        self.telegram_token_entry.pack(fill="x", pady=2)
        ctk.CTkLabel(self.telegram_frame, text="Chat ID").pack(anchor="w")
        self.telegram_chat_entry = ctk.CTkEntry(self.telegram_frame)
        self.telegram_chat_entry.pack(fill="x", pady=2)
        self._toggle_telegram()

        self.status_label = ctk.CTkLabel(self, text="", text_color="orange")
        self.status_label.pack(fill="x", padx=16, pady=4)

        ctk.CTkButton(self, text="Guardar y continuar", command=self._save).pack(fill="x", padx=16, pady=12)

    def _toggle_telegram(self) -> None:
        state = "normal" if self.telegram_var.get() else "disabled"
        for child in self.telegram_frame.winfo_children():
            if isinstance(child, ctk.CTkEntry):
                child.configure(state=state)

    def _paste_link(self) -> None:
        try:
            text = self.clipboard_get().strip()
        except tk.TclError:
            self.status_label.configure(text="No hay texto en el portapapeles.")
            return
        self.link_entry.delete(0, "end")
        self.link_entry.insert(0, text)

    def _save(self) -> None:
        ors_key = self.ors_key_entry.get().strip()
        tomtom_key = self.tomtom_key_entry.get().strip()
        email = self.email_entry.get().strip()
        link = self.link_entry.get().strip()

        if not ors_key or not tomtom_key:
            self.status_label.configure(text="Indica las API Keys de ORS y TomTom.")
            return
        if not link:
            self.status_label.configure(text="Pega el enlace de Google Maps.")
            return

        try:
            parsed = parse_google_maps_link(link)
        except GoogleMapsLinkError as exc:
            self.status_label.configure(text=str(exc))
            return

        telegram_enabled = self.telegram_var.get()
        telegram_token = self.telegram_token_entry.get().strip() if telegram_enabled else ""
        telegram_chat = self.telegram_chat_entry.get().strip() if telegram_enabled else ""
        if telegram_enabled and (not telegram_token or not telegram_chat):
            self.status_label.configure(text="Completa token y chat ID de Telegram.")
            return

        write_env_file(self.env_path, ors_key, tomtom_key, email, telegram_token, telegram_chat)

        self.config.setdefault("route", {})
        self.config.setdefault("monitor", {})
        self.config.setdefault("telegram", {})
        self.config["route"]["maps_link"] = link
        self.config["route"]["origin"] = parsed.origin
        self.config["route"]["destination"] = parsed.destination
        self.config["route"]["road_preference"] = self.road_var.get()
        self.config["monitor"]["periodic_enabled"] = bool(self.periodic_var.get())
        self.config["monitor"]["interval_minutes"] = 45
        self.config["monitor"]["jam_delay_threshold_minutes"] = 13
        self.config["telegram"]["enabled"] = telegram_enabled
        save_config(self.config_path, self.config)

        self.completed = True
        self.destroy()

    def _cancel(self) -> None:
        self.completed = False
        self.destroy()


def run_setup_wizard(base_dir: Path) -> bool:
    wizard = SetupWizard(base_dir)
    wizard.mainloop()
    return wizard.completed