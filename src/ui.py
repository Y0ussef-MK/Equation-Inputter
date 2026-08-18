from __future__ import annotations

import threading
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageTk
import pyperclip

from .ocr_engine import extract_math_ocr


class MathOCRApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Math OCR to Word")
        self.geometry("1120x760")
        self.minsize(980, 620)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.image_path: str | None = None
        self.image_preview = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkLabel(
            self,
            text="Math OCR to Word",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#e2e8f0",
        )
        header.grid(row=0, column=0, padx=22, pady=(24, 12), sticky="w")

        toolbar = ctk.CTkFrame(self, corner_radius=18, border_width=1)
        toolbar.grid(row=1, column=0, padx=22, pady=(0, 14), sticky="ew")
        toolbar.grid_columnconfigure(1, weight=1)

        upload_button = ctk.CTkButton(
            toolbar,
            text="Upload Image",
            command=self.open_image_dialog,
            width=180,
            height=42,
            fg_color="#3b82f6",
            hover_color="#2563eb",
        )
        upload_button.grid(row=0, column=0, padx=18, pady=16, sticky="w")

        self.status_label = ctk.CTkLabel(
            toolbar,
            text="No image selected",
            font=ctk.CTkFont(size=14),
            text_color="#dbeafe",
        )
        self.status_label.grid(row=0, column=1, padx=(0, 18), pady=16, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(
            toolbar,
            orientation="horizontal",
            mode="indeterminate",
            width=260,
            height=10,
        )
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=18, pady=(0, 16), sticky="ew")
        self.progress_bar.configure(progress_color="#22c55e")
        self.progress_bar.stop()

        content = ctk.CTkFrame(self, corner_radius=20, border_width=1)
        content.grid(row=2, column=0, padx=22, pady=(0, 22), sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=3)
        content.grid_rowconfigure(0, weight=1)

        preview_frame = ctk.CTkFrame(content, corner_radius=18, border_width=1)
        preview_frame.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)

        preview_title = ctk.CTkLabel(
            preview_frame,
            text="Image Preview",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e2e8f0",
        )
        preview_title.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")

        self.preview_label = ctk.CTkLabel(
            preview_frame,
            text="No preview",
            width=260,
            height=200,
            compound="top",
            anchor="center",
            text_color="#cbd5e1",
        )
        self.preview_label.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

        output_panel = ctk.CTkFrame(content, corner_radius=18, border_width=1)
        output_panel.grid(row=0, column=1, padx=(0, 18), pady=18, sticky="nsew")
        output_panel.grid_columnconfigure(0, weight=1)
        output_panel.grid_rowconfigure(1, weight=1)

        output_header = ctk.CTkLabel(
            output_panel,
            text="Extracted Text",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e2e8f0",
        )
        output_header.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")

        self.output_box = ctk.CTkTextbox(
            output_panel,
            wrap="word",
            font=ctk.CTkFont(size=15),
            height=20,
            fg_color="#0f172a",
            text_color="#f8fafc",
            border_color="#334155",
            border_width=1,
            scrollbar_button_color="#475569",
        )
        self.output_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

        self.copy_button = ctk.CTkButton(
            output_panel,
            text="Copy to Clipboard",
            command=self.copy_result,
            width=200,
            height=42,
            fg_color="#16a34a",
            hover_color="#15803d",
        )
        self.copy_button.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="e")

    def open_image_dialog(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")],
        )
        if not file_path:
            return

        self.image_path = file_path
        self.status_label.configure(text="Processing image...")
        self.progress_bar.start()
        self.output_box.delete("0.0", "end")
        self.output_box.insert("0.0", "")
        self._show_image_preview(file_path)

        thread = threading.Thread(target=self._run_ocr, args=(file_path,), daemon=True)
        thread.start()

    def _show_image_preview(self, file_path: str) -> None:
        try:
            image = Image.open(file_path)
            image = image.convert("RGB")
            image.thumbnail((320, 220))
            photo = ImageTk.PhotoImage(image)
            self.image_preview = photo
            self.preview_label.configure(image=photo, text="")
            self.preview_label.image = photo
        except Exception:
            self.preview_label.configure(text="Preview unavailable")

    def _run_ocr(self, file_path: str) -> None:
        try:
            result = extract_math_ocr(file_path)
            self.after(0, lambda: self._show_result(result))
        except Exception as exc:  # pragma: no cover - UI error path
            self.after(0, lambda: self._show_error(str(exc)))

    def _show_result(self, result: str) -> None:
        self.output_box.delete("0.0", "end")
        self.output_box.insert("0.0", result)
        self.status_label.configure(text="OCR complete")
        self.progress_bar.stop()

    def _show_error(self, message: str) -> None:
        self.output_box.delete("0.0", "end")
        self.output_box.insert("0.0", f"Error: {message}")
        self.status_label.configure(text="Processing failed")
        self.progress_bar.stop()

    def copy_result(self) -> None:
        text = self.output_box.get("0.0", "end").strip()
        if not text:
            self.status_label.configure(text="Nothing to copy")
            return

        try:
            pyperclip.copy(text)
            self.status_label.configure(text="Copied to clipboard")
        except Exception:
            self.status_label.configure(text="Clipboard access unavailable")


if __name__ == "__main__":
    app = MathOCRApp()
    app.mainloop()
