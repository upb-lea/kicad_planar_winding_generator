# 🧭 Winding Generator — KiCad Action Plugin

This KiCad **pcbnew Action Plugin** generates **planar magnetic windings** (rectangular spiral inductors/transformers) directly in the PCB editor.

---

## ✨ Features

- Rectangular spiral with rounded corners
- Adjustable parameters:
  - Width & Height (outer window)
  - Corner Radius
  - Track Width
  - Track Spacing (Guard)
  - Inner Gap (first-turn clearance)
  - Number of Turns
  - Start position: **Left-Top / Left-Center / Left-Bottom**
- Pick center using the **mouse** on the canvas
- Works with **KiCad 7 / 8 / 9**
- Toolbar **icon** included
- Simple **installer** script

---

## 📦 Repository Structure
winding-generator/
├─ winding_generator.py # Main KiCad Action Plugin (Python)
├─ install_to_kicad_plugin.py # One-click installer (asks for plugin folder)
├─ icon.png # Toolbar icon (red winding)
└─ README.md # This file

## 🧰 Requirements

- KiCad **7 / 8 / 9**
- Python **3.10+** (for the installer)
- Windows / macOS / Linux

---

## ⚙️ Installation (Recommended)

 1) **Clone the repository**.
 2) Run the installer file, which is "install_to_kicad_plugin.py".
- A folder picker will ask for your **KiCad plugins directory**.  
  If you don’t know it, open KiCad PCB Editor and go to:
  **Tools → External Plugins → Open Plugin Directory**, then copy that path into the picker.
- The installer saves your choice and can guess common locations next time.
- It copies:
  - `winding_generator.py`
  - `icon.png`
  into your KiCad plugins folder.

3) **Refresh in KiCad**
- In **KiCad PCB Editor**: **Tools → External Plugins → Refresh Plugins**
- You should see **“Winding Generator”** in the menu and a red winding **toolbar icon**.

> Tip: If the plugin doesn’t appear immediately, restart KiCad.

---

## 🖥️ How to Use

1. Open your board in **KiCad PCB Editor**.
2. Click the **Winding Generator** toolbar icon (red spiral) or run it from  
   **Tools → External Plugins → Winding Generator**.
3. In the dialog:
   - Click **Use mouse** to pick the center from the canvas (or type X/Y in mm).
   - Set **Width, Height, Radius, Gap, Track Width, Guard (spacing), Turns**.
   - Choose **Start position** (Left-Top / Left-Center / Left-Bottom).
   - Select the **Layer** (e.g., F.Cu).
4. Click **OK**. The spiral is drawn as TRACKs and 90° ARCs on the chosen layer.

---

## 🔧 Parameters (Quick Reference)

| Field              | Meaning                                                                 |
|--------------------|-------------------------------------------------------------------------|
| **Center X/Y (mm)**| Spiral center. Use **Use mouse** to capture from the canvas.           |
| **Width (mm)**     | Outer window width of the rounded rectangle.                            |
| **Height (mm)**    | Outer window height of the rounded rectangle.                           |
| **Radius (mm)**    | Corner radius.                                                          |
| **Gap (mm)**       | Inner clearance from window to first turn.                              |
| **Width (mm)**     | Track width (copper trace width).                                       |
| **Guard (mm)**     | Track-to-track spacing between adjacent turns.                          |
| **Turns**          | Number of spiral turns.                                                 |
| **Start Position** | Left-Top / Left-Center / Left-Bottom path start.                        |
| **Layer**          | Target copper layer (F.Cu, B.Cu, In1.Cu, …).                            |

---

## 🛠️ Installer Script (Details)

You can re-run the installer any time, but do not forget to update the plugin in Kickad. 


---

## 📄 License

**MIT License**.

---

## 👤 Author

Developed by **Othman Abujazar**  
University of Paderborn — Planar Winding Generator for KiCad.

---


