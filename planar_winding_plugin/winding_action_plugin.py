
import pcbnew
import os
import wx
from .winding_gui import  ParamsDialog
from .winding_functions import make_point, layer_id
from .winding_drawing import add_track
from .rectangular_windings import (create_left_bottom_sharp,
                                  create_left_center_sharp,
                                  create_left_top_sharp)
from .rounded_windings import (create_left_bottom_rounded,
                              create_left_center_rounded,
                              create_left_top_rounded)


# Set True to draw a short line at the chosen center for verification
debug_test = False

MM = pcbnew.FromMM


# ---------------------- Action plugin ----------------------
class PlanarRectSpiralLC(pcbnew.ActionPlugin):
    """Main execution: gather inputs, pick center, convert units, draw."""
    def defaults(self):
        """Initialize plugin metadata and icon for KiCad toolbar
        This method sets the essential properties required by pcbnew.ActionPlugin
        to register the tool with the KiCad interface. It defines:

        - The display name and category in the External Plugin Manager.
        - A short description for user reference.
        - The toolbar button visibility (enabled).
        - The path to the plugin's icon image.

        These settings are called automatically by KiCad when the plugin is loaded.
        """
        self.name = "Winding Generator"
        self.category = "Add tracks"
        self.description = "Generate planar winding (Left-Top / Left-Center / Left-Bottom)"
        # This is needed to show the button toolbar of the winding generator
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "icon.png")

    def Run(self):
        """Main execution method for the plugin
        This method orchestrates the entire lifecycle of the plugin:
        1. Validates that a board is open.
        2. Displays the GUI and retrieves user parameters.
        3. Converts units (mm to nm) and resolves geometry references.
        4. Dispatches the correct winding generation function based on inputs.
        5. Commits the changes to the board within a transaction.

        :return: None"""

        # ---------------------------------------------------------
        # 1. Board Validation
        # ---------------------------------------------------------
        board = pcbnew.GetBoard()
        if not board:
            return

        # ---------------------------------------------------------
        # 2. Get Parameters from GUI
        # ---------------------------------------------------------
        # Instantiate the dialog
        dlg = ParamsDialog(None)
        # Show the dialog and block until the user clicks OK or Cancel
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy(); return # User cancelled; exit without changes
        # Extract the parameter dictionary returned by the dialog
        P = dlg.get()
        dlg.Destroy() # Clean up the dialog window

        # ---------------------------------------------------------
        # 3. Center Point Resolution
        # ---------------------------------------------------------
        # Determine the center of the winding.
        # Priority 1: Use the point captured by the mouse cursor (if available).
        # Priority 2: Use the Center X/Y values entered in the dialog.
        if P["center_nm"] is not None:
            center = P["center_nm"]
        else:
            # Convert from mm (dialog input) to internal units (nm)
            center = make_point(MM(P["cx_mm"]), MM(P["cy_mm"]))

        # ---------------------------------------------------------
        # 4. Parameter Conversion & Validation
        # ---------------------------------------------------------
        # Convert all physical dimensions from mm to KiCad internal units (nm)
        sx = MM(P["sx"]) # Core Width (X)
        sy = MM(P["sy"]) # Core Height (Y)
        r  = MM(P["r"]) # Corner Radius
        cin = MM(P["cin"]) # Core-to-Winding Clearance
        w  = MM(P["w"]) # Track Width
        sp  = MM(P["sp"]) # Turn-to-Turn Spacing

        # Ensure at least 1 turn
        n  = max(1, int(P["n"]))

        # Map integer start codes to readable names (0=LT, 1=LC, 2=LB)
        start = int(P["start"])  # 0=LT, 1=LC, 2=LB

        # Resolve layer name string to KiCad integer ID (e.g., "F.Cu" -> 0)
        layer = layer_id(board, P["layer_name"])

        corner_type = P["corner_type"] # "Rounded Corner" or "Right Angled"
        mirror_x = P.get("mirror_x", False)
        mirror_y = P.get("mirror_y", False)

        # Optional debug tick at center
        # Debug visualization to verify center point location
        if debug_test:
            add_track(board, make_point(center.x - MM(1.0), center.y), make_point(center.x + MM(1.0), center.y), layer, w)

        pcbnew.Refresh() # Update the view before processing

        # ---------------------------------------------------------
        # 5. Geometry Generation (Dispatcher)
        # ---------------------------------------------------------
        # Use a Transaction to allow the entire winding to be undone as one action
        tx = pcbnew.Transaction(board, "Planar Winding") if hasattr(pcbnew, "Transaction") else None
        try:
            if corner_type == "Rounded Corner":
                # Dispatch to rounded generators
                if start == 0:
                    create_left_top_rounded(board, layer, center, sx, sy, r, cin, w, sp, n,
                                     mirror_x=mirror_x, mirror_y=mirror_y)

                elif start == 1:
                    create_left_center_rounded(board, layer, center, sx, sy, r, cin, w, sp, n,
                                       mirror_x=mirror_x, mirror_y=mirror_y)

                elif start == 2:
                    create_left_bottom_rounded(board, layer, center, sx, sy, r, cin, w, sp, n,
                                       mirror_x=mirror_x, mirror_y=mirror_y)

            else:
                # Dispatch to sharp (rectangular) generators
                if start == 0:
                    create_left_top_sharp(board, layer, center, sx, sy, cin, w, sp, n,
                                                  mirror_x=mirror_x, mirror_y=mirror_y)

                elif start == 1:
                    create_left_center_sharp(board, layer, center, sx, sy, cin, w, sp, n,
                                                     mirror_x=mirror_x, mirror_y=mirror_y)

                elif start == 2:
                    create_left_bottom_sharp(board, layer, center, sx, sy, cin, w, sp, n,
                                                    mirror_x=mirror_x, mirror_y=mirror_y)

        finally:
            # Ensure the transaction is committed if a transaction object exists
            if tx: tx.Commit()

        # Refresh the board view to show the new copper
        pcbnew.Refresh()
        # wx.MessageBox("Spiral created.", "Done")


# Register
#PlanarRectSpiralLC().register()
