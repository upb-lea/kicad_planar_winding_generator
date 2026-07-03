# 🧭 Winding Generator — KiCad Action Plugin

This KiCad **pcbnew Action Plugin** generates **planar magnetic windings** (rectangular spiral inductors/transformers) directly in the PCB editor.

This tool allows the user to generate windings with customizable geometry, corner styles and mirroring options.

---

## ✨ Features

- **Flexible Geometry**: Generate windings around a rectangular core window.
- **Corner Styles**: Choose between **Rounded Corners** (using arcs) or **Sharp Corners** (using filled polygons)
- **Adjustable parameters**:
  - Core Width & Core Height (Core leg)
  - Corner Radius
  - Track Width
  - Track Spacing (Turn-Turn)
  - Inner Spacing (Turn-Core)
  - Number of Turns
  - Start position: **Left-Top / Left-Center / Left-Bottom**
  - Mirroring: Easily mirror the winding vertically **Mirror X** or horizontally **Mirror Y**
- Pick center using the **mouse** on the canvas (Currently not available)
- Works with **KiCad 7 / 8 / 9**
- Toolbar **icon** included
- Simple **installer** script

---

## 📦 Repository Structure
winding-generator/
1) planar_winding_plugin # Main folder containing python files for the Plugin (Python), icon.png (Toolbar icon), parameter_sketch.png (simple visualization for the winding)
2) install_to_kicad_plugin.py # One-click installer (asks for plugin folder)
 
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
  - `planar_winding_plugin` folder
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
   - Set the **Turn-Core (clearance), Track Width, Turn-Turn (spacing)**.
   - Set the **Width, Height, Turns**
   - Choose **Winding Corner Type** (Rounded Corner / Right-angled Corner)
   - Set the **Radius** for Rounded Corner 
   - Choose **Start position** (Left-Top / Left-Center / Left-Bottom).
   - Select the **Layer** (e.g., F.Cu).
   - Choose the **Mirror** option (Mirror X / Mirror Y)
4. Click **OK**.

The spiral is drawn as TRACKs and 90° ARCs on the chosen layer or as filled polygon for sharp corner winding.

## Example
This example shows the usage of the plugin.
The core dimensions are based on ELP 22/6/16 core. 

| Gui dialog box                                                | Generated Winding                                             |
|---------------------------------------------------------------|---------------------------------------------------------------|
| ![Gui dialog box](/images/gui_dialog_box_rounded_example.png) | ![Gui dialog box](/images/planar_winding_rounded_example.png) |
| ![Gui dialog box](/images/gui_dialog_box_sharp_example.png)   | ![Gui dialog box](/images/planar_winding_sharp_example.png)   |


---
## GUI Parameters
The dialog box is divided into several sections. Here is a guide to each parameter:
### Center Coordinates
- **Center X / Center Y**: The absolute X and Y coordinated for the center of the winding and the core leg.
### Physical Parameters
- **Turn-Core (mm)**: The clearance (gap) between the inner winding and the core leg.
- **Width (mm)**: The width of the copper track.
- **Turn-Turn (mm)**: The spacing between adjacent turns of the winding.
### Properties
- **Turns**: The total number of winding turns.
- **Width <w> (mm)**: The inner width of the rectangular core window.
- **Height <h> (mm)**: The inner height of the rectangular core window.
### Winding Configuration
- **Winding Corner Type**:
  - **Rounded Corner**: Creates smooth arcs at the corners. Requires a **Radius** value.
  - **Right Angled**: Creates sharp 90 degrees corners using filled polygons. The radius field will be disabled.
- **Radius (mm)**: The fillet radius for rounded corners. Only active if **Rounded Corner** is selected.
- **Layer**: The copper layer (e.g., **F.Cu**, **B.Cu**) where the winding will be placed.
### Start Position
Choose where the winding begins:
- **Left Top**: Starts at the top-left inner corner.
- **Left Center**: Starts at the middle of the left side.
- **Left Bottom**: Starts at the bottom-left inner corner.
### Mirror Options
- **Mirror X** Flips the winding vertically (top becomes bottom)
- **Mirror Y**: Flips the winding horizontally (left becomes right)
### Parameter Diagram
A visual reference showing the parameters (w, h, Turn-Turn, Turn-Core) relate to the final winding shape.

## 🔧 Parameters (Quick Reference)

| Field                   | Meaning                                               |
|-------------------------|-------------------------------------------------------|
| **Center X/Y (mm)**     | Spiral center. Enter X and Y position in mm.          |
| **Width (mm)**          | Width of the core leg (Diameter for round core leg).  |
| **Height (mm)**         | Height of the core leg (Diameter for round core leg). |
| **Turn-Core (mm)**      | Inner clearance from the core to the first turn.      |
| **Width (mm)**          | Track width (copper trace width).                     |
| **Turn-Turn (mm)**      | Track-to-track spacing between adjacent turns.        |
| **Turns**               | Number of spiral turns.                               |
| **Winding Corner Type** | Rounded Corner / Right Angled Corner (sharp)          |
| **Radius (mm)**         | Corner radius.                                        |
| **Start Position**      | Left-Top / Left-Center / Left-Bottom path start.      |
| **Layer**               | Target copper layer (F.Cu, B.Cu, In1.Cu, …).          |
| **Mirror**              | Mirror X / Mirror Y.                                  |

---

## 🛠️ Installer Script (Details)

You can re-run the installer any time, but do not forget to update the plugin in KiCad. 

## Troubleshooting
- **Plugin not showing up**: Ensure you restarted KiCad after installation. Check that the **planar_winding_plugin** folder is inside the **scripting/plugins** directory.
- **Geometry Errors** If you see an error about "Corner radius too Large", it means the core window is too small for the selected radius and track width. Reduce the radius or the track width or increase the Turn-core clearance.


---

## 📄 License

**MIT License**.

---

## 👤 Author

Developed by **Othman Abujazar**  
University of Paderborn — Planar Winding Generator for KiCad.

---


