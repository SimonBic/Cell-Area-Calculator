import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
import tempfile
import os

# --- Globale Variablen ---
img = None
tk_img = None
drawing = False
current_path = []
paths = []
output_pil = None
zoom_factor = 1.0
base_image = None
image_width_px = 0
pixel_size = 1.5  # Standardwert 1,5 nm

# --- Zeichnen starten ---
def start_draw(event):
    global drawing, current_path, offset_x, offset_y
    drawing = True
    # transformiere Mausposition auf Originalbild-Koordinaten
    current_path = [( (event.x - offset_x) / zoom_factor, (event.y - offset_y) / zoom_factor )]

# --- Zeichnen ---
def draw(event):
    global drawing, current_path
    if not drawing:
        return
    x = (event.x - offset_x) / zoom_factor
    y = (event.y - offset_y) / zoom_factor
    last_x, last_y = current_path[-1]
    canvas.create_line(offset_x + last_x*zoom_factor, offset_y + last_y*zoom_factor,
                       offset_x + x*zoom_factor, offset_y + y*zoom_factor, fill="red", width=2)
    current_path.append((x, y))

# --- Zeichnen beenden ---
def end_draw(event):
    global drawing, paths, current_path
    if not drawing:
        return
    drawing = False
    if len(current_path) > 2:
        if np.hypot(current_path[0][0] - current_path[-1][0],
                    current_path[0][1] - current_path[-1][1]) < 10:
            current_path.append(current_path[0])
    if len(current_path) > 2:
        paths.append(current_path)
        aktualisiere_canvas()

# --- Fläche berechnen ---
def berechne_flaeche():
    global output_pil, pixel_size
    ergebnis_text.delete(1.0, tk.END)
    if img is None:
        ergebnis_text.insert(tk.END, "First load picture\n")
        return
    if not paths:
        ergebnis_text.insert(tk.END, "You did not draw any cells.\n")
        return

    # --- Pixelgröße dynamisch anpassen ---
    try:
        real_width = float(real_width_entry.get())
        pixel_size = real_width / image_width_px
    except ValueError:
        pixel_size = 1.5  # Standardwert

    output_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw_img = ImageDraw.Draw(output_pil)

    gesamt_px = 0
    gesamt_real = 0
    flaechen = []

    ergebnis_text.insert(tk.END, "Nr.\tArea (px²)\tArea (nm²)\n")

    for i, path in enumerate(paths, start=1):
        pts = np.array(path, dtype=np.int32)
        if len(pts) < 3:
            continue
        area_px = cv2.contourArea(pts)
        area_real = area_px * (pixel_size ** 2)
        flaechen.append(area_real)
        gesamt_px += area_px
        gesamt_real += area_real

        cx, cy = np.mean(pts[:, 0]), np.mean(pts[:, 1])
        draw_img.text((cx, cy), str(i), fill=(0, 0, 255))

        overlay = Image.new('RGBA', output_pil.size, (255, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        draw_overlay.polygon(path, fill=(255, 0, 0, 60))
        output_pil = Image.alpha_composite(output_pil.convert("RGBA"), overlay)

        ergebnis_text.insert(tk.END, f"{i}\t{area_px:.2f}\t{area_real:.5f}\n")

    durchschnitt = np.mean(flaechen) if flaechen else 0
    ergebnis_text.insert(tk.END, f"\naccumulated size {gesamt_px:.2f} px², {gesamt_real:.5f} nm²\n")
    ergebnis_text.insert(tk.END, f"average size: {durchschnitt:.5f} nm²\n")
    aktualisiere_canvas()

# --- Kreis gezielt löschen ---
def loesche_kreis():
    global paths
    try:
        nr = int(delete_entry.get())
        if 1 <= nr <= len(paths):
            paths.pop(nr - 1)
            ergebnis_text.insert(tk.END, f"cell {nr} deleted\n")
            aktualisiere_canvas()
        else:
            messagebox.showwarning("Error", "number does not exist")
    except ValueError:
        messagebox.showwarning("Error", "Enter valid number")

# --- Excel exportieren ---
def export_excel():
    global output_pil
    if not paths:
        messagebox.showerror("Error", "You did not draw any cells.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "cell-areas"
    ws.append(["Nr.", "Area (px²)", f"Fläche (nm²) [Pixelsize ={pixel_size:.5f}]"])
    for i, path in enumerate(paths, start=1):
        pts = np.array(path, dtype=np.int32)
        if len(pts) < 3:
            continue
        area_px = cv2.contourArea(pts)
        area_real = area_px * (pixel_size ** 2)
        ws.append([i, area_px, area_real])

    tmp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    output_pil.convert("RGB").save(tmp_file.name)
    img_excel = XLImage(tmp_file.name)
    img_excel.width = 600
    img_excel.height = 400
    ws.add_image(img_excel, "E2")

    save_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel-Dateien", "*.xlsx")])
    if save_path:
        wb.save(save_path)
        tmp_file.close()
        os.unlink(tmp_file.name)
        messagebox.showinfo("Fertig", f"Saved as Excel in:\n{save_path}")
    else:
        tmp_file.close()
        os.unlink(tmp_file.name)

# --- Bild laden ---
from PIL import Image

def lade_bild():
    global img, tk_img, base_image, zoom_factor, paths, image_width_px, pixel_size, output_pil
    # Alte Daten zurücksetzen
    paths.clear()
    zoom_factor = 1.0
    output_pil = None
    canvas.delete("all")

    filepath = filedialog.askopenfilename(
        title="Select picture",
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.tif;*.bmp")]
    )
    if not filepath:
        return

    # Windows: Backslashes durch Slashes ersetzen
    filepath = filepath.replace("\\", "/")

    try:
        # Bild mit PIL laden (funktioniert bei fast allen Formaten)
        pil_img = Image.open(filepath).convert("RGB")
        base_image = pil_img
        image_width_px = base_image.width

        # Optional: für OpenCV konvertieren
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    except Exception as e:
        messagebox.showerror("Error", f"Could not load picture:\n{filepath}\n\n{e}")
        return

    # Pixelgröße anhand Eingabefeld setzen
    try:
        real_width = float(real_width_entry.get())
        pixel_size = real_width / image_width_px
    except ValueError:
        pixel_size = 1.5  # Standardwert

    # Bild sofort anzeigen (Canvas aktualisieren)
    aktualisiere_canvas()



# globale Offsets für Bildposition
offset_x = 0
offset_y = 0

def aktualisiere_canvas():
    global tk_img, base_image, zoom_factor, output_pil, offset_x, offset_y
    display_img = (output_pil if output_pil is not None else base_image).copy()
    w, h = display_img.size
    new_size = (int(w * zoom_factor), int(h * zoom_factor))
    resized = display_img.resize(new_size, Image.Resampling.LANCZOS)
    tk_img = ImageTk.PhotoImage(resized)
    canvas.delete("all")
    canvas.create_image(offset_x, offset_y, anchor="nw", image=tk_img)

    # Nummern und Pfade anzeigen
    for i, path in enumerate(paths, start=1):
        if len(path) < 2:
            continue
        # transformiere Pfad-Koordinaten auf Canvas
        path_trans = [(offset_x + x*zoom_factor, offset_y + y*zoom_factor) for x,y in path]

        # Linien verbinden
        for j in range(len(path_trans)-1):
            canvas.create_line(path_trans[j][0], path_trans[j][1],
                               path_trans[j+1][0], path_trans[j+1][1], fill="red", width=2)
        # Nummer zentrieren
        cx = np.mean([x for x, y in path_trans])
        cy = np.mean([y for x, y in path_trans])
        canvas.create_text(cx, cy, text=str(i), fill="blue", font=("Arial", 16, "bold"))

# --- Zoom ---
def zoom(event):
    global zoom_factor, offset_x, offset_y
    # Position der Maus relativ zum Bild
    mouse_x = event.x - offset_x
    mouse_y = event.y - offset_y
    rel_x = mouse_x / zoom_factor
    rel_y = mouse_y / zoom_factor

    # Zoom-Faktor ändern
    if event.delta > 0 or getattr(event, 'num', None) == 4:
        zoom_factor *= 1.1
    else:
        zoom_factor /= 1.1
    zoom_factor = max(0.2, min(zoom_factor, 5.0))

    # Offset so anpassen, dass Maus-Punkt stabil bleibt
    offset_x = event.x - rel_x * zoom_factor
    offset_y = event.y - rel_y * zoom_factor

    aktualisiere_canvas()

# --- Undo ---
def undo(event=None):
    global paths
    if paths:
        paths.pop()
        aktualisiere_canvas()

# --- Text kopieren ---
def kopiere_text():
    # Text für Excel aufbereiten
    text = ""
    lines = ergebnis_text.get(1.0, tk.END).strip().split("\n")
    for line in lines:
        # mehrere Leerzeichen durch Tab ersetzen
        line_tab = "\t".join(line.split())
        text += line_tab + "\n"

    # In Zwischenablage kopieren
    root.clipboard_clear()
    root.clipboard_append(text)
    messagebox.showinfo("Copy", "Text copied in Excel format.")

# --- GUI ---
root = tk.Tk()
root.title("Cell-Area-Calculator - Simon Bichler")

frame = tk.Frame(root)
frame.pack(pady=5)

btn_laden = tk.Button(frame, text="Load picture", command=lade_bild)
btn_laden.pack(side=tk.LEFT, padx=5)

tk.Label(frame, text="Width of picture in nm:").pack(side=tk.LEFT)
real_width_entry = tk.Entry(frame, width=7)
real_width_entry.insert(0, "1.5")
real_width_entry.pack(side=tk.LEFT, padx=5)

btn_berechne = tk.Button(frame, text="Calculate Area", command=berechne_flaeche)
btn_berechne.pack(side=tk.LEFT, padx=5)

btn_excel = tk.Button(frame, text="Export as Excel", command=export_excel)
btn_excel.pack(side=tk.LEFT, padx=5)

tk.Label(frame, text="Delete area num.:").pack(side=tk.LEFT)
delete_entry = tk.Entry(frame, width=5)
delete_entry.pack(side=tk.LEFT, padx=2)
btn_delete = tk.Button(frame, text="Delete", command=loesche_kreis)
btn_delete.pack(side=tk.LEFT, padx=5)

text_frame = tk.Frame(root)
text_frame.pack(pady=5, fill=tk.BOTH, expand=True)

# Ergebnisfeld links
ergebnis_text = tk.Text(text_frame, width=60, height=20)
ergebnis_text.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)

# Infotextfeld rechts
info_text = tk.Text(text_frame, width=30, height=20, bg="#f5f5f5", wrap=tk.WORD)
info_text.pack(side=tk.RIGHT, padx=5, fill=tk.BOTH)
info_text.insert(tk.END,
"""
Cell-Area-Calculator - Simon Bichler

Load picture = b
Copy whole text = c
Export as excel = e
Calculate area = f
Undo last area = z
                 
For suggestions or bug reports, please contact: 
bichler.simon18@googlemail.com

This software is free to use. 
If you wish to support its development, you can make a donation via PayPal
                    """)

canvas_frame = tk.Frame(root)
canvas_frame.pack()

canvas = tk.Canvas(canvas_frame, width=1280, height=720, bg="gray90")
canvas.pack()

canvas.bind("<ButtonPress-1>", start_draw)
canvas.bind("<B1-Motion>", draw)
canvas.bind("<ButtonRelease-1>", end_draw)
canvas.bind("<MouseWheel>", zoom)
canvas.bind("<Button-4>", zoom)
canvas.bind("<Button-5>", zoom)

# --- Tastenkürzel ---
root.bind("<Control-z>", undo)          # Strg+Z
root.bind("b", lambda e: lade_bild())   # B: Bild laden
root.bind("f", lambda e: berechne_flaeche()) # F: Flächen berechnen
root.bind("e", lambda e: export_excel())     # E: Excel export
root.bind("z", lambda e: undo())             # Z: letzten Kreis entfernen
root.bind("c", lambda e: kopiere_text())    # C: Text kopieren

root.mainloop()
