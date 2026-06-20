
import pcbnew
import os
import wx
from gui import  ParamsDialog
from geometry import v2
from drawing import add_track
from rectangular_windings import (create_left_bottom_right_angled,
                                  create_left_center_right_angled,
                                  create_left_top_right_angled)
from rounded_windings import (create_left_bottom,
                              create_left_center,
                              create_left_top)


# Set True to draw a short line at the chosen center for verification
debug_test = False

MM = pcbnew.FromMM

def layer_id(board, name):
    """Resolve a human-readable layer name to a KiCad layer ID.

    :param board: Current board instance
    :type: pcbnew.BOARD
    :param name: KiCad layer name (e.g "F.Cu", "B.Cu")
    :type: str
    :return: KiCad layer ID
    :rtype: int
    """

    lid = board.GetLayerID(name)
    return lid if lid != -1 else pcbnew.F_Cu


# ---------------------- Action plugin ----------------------
class PlanarRectSpiralLC(pcbnew.ActionPlugin):
    """Main execution: gather inputs, pick center, convert units, draw."""
    def defaults(self):
        """Initialize plugin metadata and icon for KiCad toolbar"""
        self.name = "Winding Generator"
        self.category = "Add tracks"
        self.description = "Generate planar winding (Left-Top / Left-Center / Left-Bottom)"
        # This is needed to show the button toolbar of the winding generator
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "icon.png")

    def Run(self):
        """Main execution method for the plugin"""
        board = pcbnew.GetBoard()
        if not board:
            return

        # 1) Get parameters
        dlg = ParamsDialog(None)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy(); return
        P = dlg.get(); dlg.Destroy()

        # 2) Center: with mouse capture removed, always use entered mm → nm.
        if P["center_nm"] is not None:
            center = P["center_nm"]
        else:
            center = v2(MM(P["cx_mm"]), MM(P["cy_mm"]))

        # 3) Convert to internal units (nm)
        sx = MM(P["sx"]); sy = MM(P["sy"])
        r  = MM(P["r"]);  cin = MM(P["cin"])
        w  = MM(P["w"]);  sp  = MM(P["sp"])
        n  = max(1, int(P["n"]))
        start = int(P["start"])  # 0=LT, 1=LC, 2=LB
        layer = layer_id(board, P["layer_name"])
        corner_type = P["corner_type"]
        mirror_x = P.get("mirror_x", False)
        mirror_y = P.get("mirror_y", False)

        # Optional debug tick at center
        if debug_test:
            add_track(board, v2(center.x - MM(1.0), center.y), v2(center.x + MM(1.0), center.y), layer, w)
        pcbnew.Refresh()

        # 4) Draw spiral
        tx = pcbnew.Transaction(board, "Planar Winding") if hasattr(pcbnew, "Transaction") else None
        try:
            if corner_type == "Rounded Corner":

                if start == 0:
                    create_left_top(
                        board, layer, center,
                        sx, sy, r, cin, w, sp, n)

                elif start == 1:
                    create_left_center(
                        board, layer, center,
                        sx, sy, r, cin, w, sp, n)

                elif start == 2:
                    create_left_bottom(
                        board, layer, center,
                        sx, sy, r, cin, w, sp, n)

            else:

                if start == 0:
                    create_left_top_right_angled(board, layer, center, sx, sy, cin, w, sp, n,
                                                  mirror_x=mirror_x, mirror_y=mirror_y)

                elif start == 1:
                    create_left_center_right_angled(board, layer, center, sx, sy, cin, w, sp, n,
                                                     mirror_x=mirror_x, mirror_y=mirror_y)

                elif start == 2:
                    create_left_bottom_right_angled(board, layer, center, sx, sy, cin, w, sp, n,
                                                    mirror_x=mirror_x, mirror_y=mirror_y)
            # if start == 0:
            #     create_left_top(board, layer, center, sx, sy, r, cin, w, sp, n)
            # elif start == 2:
            #     create_left_bottom(board, layer, center, sx, sy, r, cin, w, sp, n)
            # else:
            #     create_left_center(board, layer, center, sx, sy, r, cin, w, sp, n)

        finally:
            if tx: tx.Commit()
        pcbnew.Refresh()
        # wx.MessageBox("Spiral created.", "Done")


# Register
PlanarRectSpiralLC().register()
