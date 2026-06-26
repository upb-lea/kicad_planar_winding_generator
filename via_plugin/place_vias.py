# place_via_array.py
# KiCad Action Plugin: Place an array of vias horizontally or vertically
# KiCad 7/8/9 compatible. Units: dialog in mm; pcbnew uses nm (FromMM/ToMM).

import pcbnew
import wx
import os

MM = pcbnew.FromMM

def v2(x, y):
    return pcbnew.VECTOR2I(int(x), int(y))

def get_netcode(board, net_name):
    """Return netcode for net_name (0 if not found)."""
    if not net_name or net_name.strip() == "":
        return 0
    # KiCad API differences guard:
    try:
        return board.GetNetcodeFromNetname(net_name)
    except Exception:
        nets = board.GetNetsByName()
        n = nets.get(net_name)
        return n.GetNet() if n else 0

def all_net_names(board):
    """Sorted list of net names (human-readable)"""
    names = []
    try:
        # KiCad 7+
        m = board.GetNetsByName()
        for k in m.keys():
            names.append(str(k))
    except Exception:
        # Fallback
        for n in board.GetNets():
            names.append(n.GetNetname())
    names = [n for n in names if n and n != "" and n != ""]  # filter empties
    names.sort()
    names.insert(0, "<no net>")
    return names

def add_via(board, pos_nm, drill_mm, dia_mm, netcode=0):
    """Create a through via at pos_nm (VECTOR2I) with given sizes."""
    via = pcbnew.PCB_VIA(board)
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetPosition(pos_nm)
    via.SetDrill(MM(drill_mm))
    via.SetWidth(MM(dia_mm))            # width == diameter in KiCad
    if netcode:
        via.SetNetCode(netcode)
    # through via layer pair covers all coppers by default
    board.Add(via)

class ViaArrayDialog(wx.Dialog):
    def __init__(self, parent, board):
        super().__init__(parent, title="Place Via Array",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.board = board
        self.SetMinSize(wx.Size(480, 360))

        p  = wx.Panel(self)
        s  = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(3, 4, 6, 8)
        grid.AddGrowableCol(1, 1)
        grid.AddGrowableCol(3, 1)

        # Center X / Y
        grid.Add(wx.StaticText(p, label="Center X (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cx = wx.TextCtrl(p, value="0.0", style=wx.TE_RIGHT); grid.Add(self.cx, 1, wx.EXPAND)
        grid.Add(wx.StaticText(p, label="Center Y (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cy = wx.TextCtrl(p, value="0.0", style=wx.TE_RIGHT); grid.Add(self.cy, 1, wx.EXPAND)

        # Count & Pitch
        grid.Add(wx.StaticText(p, label="Count:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.count = wx.TextCtrl(p, value="6", style=wx.TE_RIGHT); grid.Add(self.count, 1, wx.EXPAND)
        grid.Add(wx.StaticText(p, label="Pitch (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.pitch = wx.TextCtrl(p, value="1.00", style=wx.TE_RIGHT); grid.Add(self.pitch, 1, wx.EXPAND)

        # Drill & Diameter
        grid.Add(wx.StaticText(p, label="Drill (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.drill = wx.TextCtrl(p, value="0.30", style=wx.TE_RIGHT); grid.Add(self.drill, 1, wx.EXPAND)
        grid.Add(wx.StaticText(p, label="Diameter (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.diam  = wx.TextCtrl(p, value="0.60", style=wx.TE_RIGHT); grid.Add(self.diam, 1, wx.EXPAND)

        s.Add(grid, 0, wx.EXPAND | wx.ALL, 8)

        # Orientation
        ori_box = wx.StaticBoxSizer(wx.HORIZONTAL, p, "Orientation")
        self.rb_h = wx.RadioButton(p, label="Horizontal (X)", style=wx.RB_GROUP)
        self.rb_v = wx.RadioButton(p, label="Vertical (Y)")
        self.rb_h.SetValue(True)
        ori_box.Add(self.rb_h, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 16)
        ori_box.Add(self.rb_v, 0, wx.ALIGN_CENTER_VERTICAL)
        s.Add(ori_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Net selection
        net_box = wx.BoxSizer(wx.HORIZONTAL)
        net_box.Add(wx.StaticText(p, label="Net:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.net_choice = wx.Choice(p, choices=all_net_names(board))
        self.net_choice.SetSelection(0)
        net_box.Add(self.net_choice, 1, wx.EXPAND)
        s.Add(net_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Info line
        info = wx.StaticText(p, label="Tip: Center is the middle of the array. Pitch is spacing between vias.")
        s.Add(info, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        p.SetSizer(s)

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(p, 1, wx.ALL | wx.EXPAND, 10)
        btns = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(root)

    def get(self):
        """Return dict of user inputs (mm), with types converted."""
        f = lambda t: float(t.GetValue())
        center_x = f(self.cx)
        center_y = f(self.cy)
        count    = max(1, int(float(self.count.GetValue())))
        pitch    = f(self.pitch)
        drill    = f(self.drill)
        dia      = f(self.diam)
        orient   = "H" if self.rb_h.GetValue() else "V"
        net_name = self.net_choice.GetStringSelection()
        if net_name == "<no net>":
            net_name = ""
        return dict(cx=center_x, cy=center_y, count=count, pitch=pitch,
                    drill=drill, dia=dia, orient=orient, net=net_name)

class PlaceViaArray(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Via Array"
        self.category = "Add vias"
        self.description = "Place an array of vias (horizontal/vertical)"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "vias_icon.png")  # optional

    def Run(self):
        board = pcbnew.GetBoard()
        if not board:
            return

        dlg = ViaArrayDialog(None, board)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy(); return
        P = dlg.get(); dlg.Destroy()

        # Convert to internal coords
        cx = MM(P["cx"]); cy = MM(P["cy"])
        pitch_nm = MM(P["pitch"])
        netcode = get_netcode(board, P["net"])

        # Compute first via position so that array is centered on (cx, cy)
        n = P["count"]
        # For even/odd, center around middle: index i = 0..n-1
        # offset_i = (i - (n-1)/2) * pitch
        for i in range(n):
            offset = int(round((i - (n - 1) / 2.0) * pitch_nm))
            if P["orient"] == "H":
                pos = v2(cx + offset, cy)
            else:
                pos = v2(cx, cy + offset)
            add_via(board, pos, P["drill"], P["dia"], netcode)

        pcbnew.Refresh()

# Register plugin in __init__ file

