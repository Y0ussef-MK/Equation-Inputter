# Math OCR to Word

A desktop app that extracts text and mathematical equations from images and formats equations as LaTeX for direct pasting into Microsoft Word.

## Features

- Upload PNG, JPG, and JPEG images
- Preserve normal text as closely as possible to the original wording
- Convert formulas into LaTeX using `$...$` for inline math and `$$...$$` for block math
- Modern dark UI built with CustomTkinter
- Threaded OCR so the interface stays responsive while processing images
- Copy extracted text directly to the clipboard
- Better cleanup logic for noisy OCR output and equation formatting

## Project structure

- `main.py` — app entry point
- `src/ui.py` — interface and event handling
- `src/ocr_engine.py` — OCR preprocessing, extraction, and formula cleanup
- `requirements.txt` — dependency list
- `install.bat` — one-click Windows installer
- `run_app.bat` — one-click launch script

## Requirements

- Python 3.10+
- Windows 10/11 recommended for the included batch scripts

## One-click setup on Windows

1. Open the project folder.
2. Double-click `install.bat`.
3. After installation finishes, double-click `run_app.bat` to start the program.

## Manual setup

```powershell
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Why this version is faster and more stable

- Images are resized before OCR to reduce latency.
- The OCR pipeline uses the actual `pix2text` page structure instead of guessing at the returned object.
- Output is cleaned to reduce gibberish spacing artifacts from OCR noise.
- Deprecated or unstable dependency combinations were avoided by pinning a safe NumPy range.

## Troubleshooting

If OCR returns poor results:

- Use a clear, high-contrast image
- Ensure the text is not too small or skewed
- Try a higher-quality image without heavy shadows or glare

If the app fails to start:

```powershell
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

