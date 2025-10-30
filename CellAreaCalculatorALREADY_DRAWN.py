import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk


def lade_bild():
    global img, tk_img, mask_img

    filepath = filedialog.askopenfilename(
        title="Please select picture",
        filetypes=[("Bilddateien", "*.png;*.jpg;*.jpeg;*.tif;*.bmp")]
    )
    if not filepath:
        return

    img = cv2.imread(filepath)
    if img is None:
        messagebox.showerror("No correct path choosen.",
                             "picture could not be loaded, no correct path was chosen.")
        return

    # Verarbeitung
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    try:
        lower_h = int(lower_h_entry.get())
        lower_s = int(lower_s_entry.get())
        lower_v = int(lower_v_entry.get())
        upper_h = int(upper_h_entry.get())
        upper_s = int(upper_s_entry.get())
        upper_v = int(upper_v_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Select reasonable color palette.")
        return

    lower_pink = np.array([lower_h, lower_s, lower_v])
    upper_pink = np.array([upper_h, upper_s, upper_v])

    # --- Neue Schritte für schwammige Zellgrenzen ---
    # 1. Glätten, um Rauschen zu reduzieren
    hsv_blur = cv2.GaussianBlur(hsv, (5, 5), 0)

    # 2. Maske erstellen
    mask = cv2.inRange(hsv_blur, lower_pink, upper_pink)

    # 3. Morphologische Operationen (Close → Open)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # --- Konturen finden ---
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    ergebnis_text.delete(1.0, tk.END)

    try:
        pixel_size = float(pixel_size_entry.get())
    except ValueError:
        pixel_size = 1.0
        messagebox.showinfo("Information",
                            "Please select proper pixelsize.")

    if len(contours) == 0:
        ergebnis_text.insert(tk.END, "No Circles been found\n")
    else:
        gesamtgroesse = 0
        gesamtradius = 0
        for i, c in enumerate(contours, start=1):
            area_px = cv2.contourArea(c)
            radius_px = (area_px / np.pi) ** 0.5

            # Reale Werte berechnen
            area_real = area_px * (pixel_size ** 2)
            radius_real = radius_px * pixel_size

            gesamtgroesse += area_px
            gesamtradius += radius_px

            ergebnis_text.insert(tk.END,
                                 f"Cell: {i}:\n"
                                 f"  Area = {area_px:.2f} px² ({area_real:.2f} real²)\n"
                                 f"  Radius ≈ {radius_px:.2f} px ({radius_real:.2f} real)\n\n"
                                 )

        gesamtgroesse_real = gesamtgroesse * (pixel_size ** 2)
        gesamtradius_real = gesamtradius * pixel_size

        ergebnis_text.insert(tk.END,
                             f"Accumlulated Area Area = {gesamtgroesse:.2f} px² ({gesamtgroesse_real:.2f} real²)\n"
                             f"Accumulated Radius ≈ {gesamtradius:.2f} px ({gesamtradius_real:.2f} real)\n"
                             )

    # Ausgabe-Bild mit erkannten Konturen
    output = img.copy()
    cv2.drawContours(output, contours, -1, (255, 0, 0), 2)

    # Anzeige im GUI
    output_rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
    output_pil = Image.fromarray(output_rgb)
    tk_img = ImageTk.PhotoImage(output_pil)

    canvas.delete("all")
    canvas.create_image(0, 0, anchor="nw", image=tk_img)
    canvas.config(scrollregion=canvas.bbox(tk.ALL))


# --- Restliches GUI wie vorher ---
root = tk.Tk()
root.title("Cell Are Calculator with Cells already drawn")

frame = tk.Frame(root)
frame.pack(pady=10)

btn_laden = tk.Button(frame, text="Load picture", command=lade_bild)
btn_laden.pack(side=tk.LEFT, padx=10)

tk.Label(frame, text="Pixelsize (e.g 0.5 µm/px):").pack(side=tk.LEFT)
pixel_size_entry = tk.Entry(frame, width=10)
pixel_size_entry.insert(0, "1.0")
pixel_size_entry.pack(side=tk.LEFT, padx=5)

color_frame = tk.LabelFrame(root, text="HSV-Color-spectrum. Standard is for pink circles.", padx=10, pady=5)
color_frame.pack(pady=10)

tk.Label(color_frame, text="H").grid(row=0, column=1)
tk.Label(color_frame, text="S").grid(row=0, column=2)
tk.Label(color_frame, text="V").grid(row=0, column=3)

tk.Label(color_frame, text="Lower:").grid(row=1, column=0)
lower_h_entry = tk.Entry(color_frame, width=5)
lower_s_entry = tk.Entry(color_frame, width=5)
lower_v_entry = tk.Entry(color_frame, width=5)
lower_h_entry.insert(0, "140")
lower_s_entry.insert(0, "50")
lower_v_entry.insert(0, "50")
lower_h_entry.grid(row=1, column=1)
lower_s_entry.grid(row=1, column=2)
lower_v_entry.grid(row=1, column=3)

tk.Label(color_frame, text="Upper:").grid(row=2, column=0)
upper_h_entry = tk.Entry(color_frame, width=5)
upper_s_entry = tk.Entry(color_frame, width=5)
upper_v_entry = tk.Entry(color_frame, width=5)
upper_h_entry.insert(0, "180")
upper_s_entry.insert(0, "255")
upper_v_entry.insert(0, "255")
upper_h_entry.grid(row=2, column=1)
upper_s_entry.grid(row=2, column=2)
upper_v_entry.grid(row=2, column=3)

text_frame = tk.Frame(root)
text_frame.pack(pady=10, fill=tk.BOTH, expand=True)

ergebnis_text = tk.Text(text_frame, width=80, height=20)
ergebnis_text.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)

info_text = tk.Text(text_frame, width=50, height=20, bg="#f5f5f5", wrap=tk.WORD)
info_text.pack(side=tk.RIGHT, padx=10, fill=tk.BOTH)
info_text.insert(tk.END,
                 """This programm is for cells that already been drawn with a grey scale backround and to calculate their size. 
You need to calculate how big one pixel is by divinding the actual size of e.g. the width by the number of pixels in the pictures width. 
Please enter this value before loading the picture.
You can find a better software to draw those circles and calculate them on my page, this was just a demo version.
                 
H = Hue (Color tone)
    The color (0–179)
    e.g. 0 = red, 60 = yellow, 120 = green, 150–180 = pink

S = Saturation
    How intense is the color? (0–255)

V = Value (Brightness)
    How bright is the color? (0–255)

And then you have a range, i.e., two values,
because in a photo, there’s no way all pixels
have exactly the same HSV value.

Blue circled area = that’s the part that was measured.
                 """)
info_text.config(state="disabled")

canvas_frame = tk.Frame(root)
canvas_frame.pack()

canvas = tk.Canvas(canvas_frame, width=1280, height=720, bg="gray90")
canvas.pack()

root.mainloop()