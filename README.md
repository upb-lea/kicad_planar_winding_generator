# 🧭 Winding Generator — KiCad Action Plugin

This KiCad **pcbnew Action Plugin** generates **planar magnetic windings** (rectangular spiral inductors/transformers) directly in the PCB editor.

---

## ✨ Features

- Rectangular spiral with rounded corners
- Adjustable parameters:
  - Width & Height (Core leg)
  - Corner Radius
  - Track Width
  - Track Spacing (Turn-Turn)
  - Inner Spacing (Turn-Core)
  - Number of Turns
  - Start position: **Left-Top / Left-Center / Left-Bottom**
- Pick center using the **mouse** on the canvas
- Works with **KiCad 7 / 8 / 9**
- Toolbar **icon** included
- Simple **installer** script

---

## 📦 Repository Structure
winding-generator/
1) winding_generator.py # Main KiCad Action Plugin (Python)
2) install_to_kicad_plugin.py # One-click installer (asks for plugin folder)
3) icon.png # Toolbar icon 
## 🧰 Requirements

- KiCad 
- Python 
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
   - Enter the center point of the winding **Center X, Center Y**.
   - Set the **Radius, Turn-Core (clearance), Track Width, Turn-Turn (spacing)**.
   - Set the **Width, Height, Turns**
   - Choose **Start position** (Left-Top / Left-Center / Left-Bottom).
   - Select the **Layer** (e.g., F.Cu).
4. Click **OK**. The spiral is drawn as TRACKs and 90° ARCs on the chosen layer.

---

## 🔧 Parameters (Quick Reference)

| Field               | Meaning                                                |
|---------------------|--------------------------------------------------------|
| **Center X/Y (mm)** | Spiral center. Enter X and Y position in mm.           |
| **Width (mm)**      | Width of the core leg (Diameter for round core leg).   |
| **Height (mm)**     | Height of the core leg (Diameter for round core leg).  |
| **Radius (mm)**     | Corner radius.                                         |
| **Turn-Core (mm)**  | Inner clearance from the core to the first turn.       |
| **Width (mm)**      | Track width (copper trace width).                      |
| **Turn-Turn (mm)**  | Track-to-track spacing between adjacent turns.         |
| **Turns**           | Number of spiral turns.                                |
| **Start Position**  | Left-Top / Left-Center / Left-Bottom path start.       |
| **Layer**           | Target copper layer (F.Cu, B.Cu, In1.Cu, …).           |

---

## 🛠️ Installer Script (Details)

You can re-run the installer any time, but do not forget to update the plugin in Kickad. 


---

## 📄 License

**MIT License**.

## 🔗 Related Work

Similar planar inductor / spiral generation tools exist for other EDA platforms.
In particular, Altium Designer users may refer to:

- https://github.com/Altium-Designer-addons/scripts-libraries

which contains PCB scripting utilities, including scripts for generating
spiral / planar inductor geometries inside Altium Designer.
---

## 👤 Author

Developed by **Othman Abujazar**  
University of Paderborn — Planar Winding Generator for KiCad.

---


