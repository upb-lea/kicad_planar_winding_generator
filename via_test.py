import math
import pcbnew
import wx

IU_PER_MM = 1_000_000  # KiCad internal units (nm) per mm


def mm_to_iu(val_mm: float) -> int:
    return int(round(val_mm * IU_PER_MM))


def deg_to_rad(deg: float) -> float:
    return math.radians(deg)


def build_line_points(start, end, count):
    sx, sy = start
    ex, ey = end
    if count == 1:
        return [(sx, sy)]
    return [
        (
            sx + (ex - sx) * i / (count - 1),
            sy + (ey - sy) * i / (count - 1),
        )
        for i in range(count)
    ]


def build_arc_points(center, radius, start_deg, stop_deg, count, closed=False):
    cx, cy = center
    if closed:
        # drop the duplicated last angle; use full sweep 0..2π exclusive
        step = 360.0 / count
        angles_deg = [start_deg + i * step for i in range(count)]
    else:
        if count == 1:
            angles_deg = [start_deg]
        else:
            angles_deg = [
                start_deg + i * (stop_deg - start_deg) / (count - 1)
                for i in range(count)
            ]
    points = []
    for ang_deg in angles_deg:
        ang = deg_to_rad(ang_deg)
        x = cx + radius * math.cos(ang)
        y = cy + radius * math.sin(ang)
        points.append((x, y))
    return points


class ViaPatternDialog(wx.Dialog):
    def __init__(self, board):
        super().__init__(None, title="Via Pattern Array")
        self.board = board
        self.panel = wx.Panel(self)
        self.pattern_choice = wx.RadioBox(
            self.panel,
            label="Pattern type",
            choices=["Line", "Full circle", "Arc"],
            majorDimension=1,
            style=wx.RA_SPECIFY_ROWS,
        )
        self.count_spin = wx.SpinCtrl(self.panel, min=1, max=500, initial=5)
        self.dia_ctrl = wx.TextCtrl(self.panel, value="0.3")
        self.drill_ctrl = wx.TextCtrl(self.panel, value="0.2")

        self.line_start = wx.TextCtrl(self.panel, value="0,0")
        self.line_end = wx.TextCtrl(self.panel, value="10,0")

        self.center_ctrl = wx.TextCtrl(self.panel, value="0,0")
        self.radius_ctrl = wx.TextCtrl(self.panel, value="5")
        self.start_angle_ctrl = wx.TextCtrl(self.panel, value="0")
        self.stop_angle_ctrl = wx.TextCtrl(self.panel, value="180")

        net_names = sorted({net.GetNetname() for net in board.GetNetsByNetcode().values()})
        self.net_choice = wx.ComboBox(self.panel, choices=net_names, style=wx.CB_DROPDOWN)
        if net_names:
            self.net_choice.SetSelection(0)

        sizer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(cols=2, hgap=6, vgap=6)
        grid.Add(wx.StaticText(self.panel, label="Via count"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.count_spin, 0, wx.EXPAND)
        grid.Add(wx.StaticText(self.panel, label="Via diameter [mm]"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.dia_ctrl, 0, wx.EXPAND)
        grid.Add(wx.StaticText(self.panel, label="Drill diameter [mm]"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.drill_ctrl, 0, wx.EXPAND)

        grid.Add(wx.StaticText(self.panel, label="Line start (x,y mm)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.line_start, 0, wx.EXPAND)
        grid.Add(wx.StaticText(self.panel, label="Line end (x,y mm)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.line_end, 0, wx.EXPAND)

        grid.Add(wx.StaticText(self.panel, label="Circle center (x,y mm)"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.center_ctrl, 0, wx.EXPAND)
        grid.Add(wx.StaticText(self.panel, label="Radius [mm]"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.radius_ctrl, 0, wx.EXPAND)
        grid.Add(wx.StaticText(self.panel, label="Start angle [deg]"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.start_angle_ctrl, 0, wx.EXPAND)
        grid.Add(wx.StaticText(self.panel, label="End angle [deg]"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.stop_angle_ctrl, 0, wx.EXPAND)

        grid.Add(wx.StaticText(self.panel, label="Net"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.net_choice, 0, wx.EXPAND)

        sizer.Add(self.pattern_choice, 0, wx.ALL | wx.EXPAND, 8)
        sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 8)

        btns = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btns, 0, wx.ALL | wx.EXPAND, 8)

        self.panel.SetSizer(sizer)
        sizer.Fit(self)

    def parse_pair(self, ctrl):
        text = ctrl.GetValue().strip()
        parts = [float(p) for p in text.replace(" ", "").split(",")]
        if len(parts) != 2:
            raise ValueError("Expecting two comma separated values")
        return parts[0], parts[1]

    def get_params(self):
        params = {"pattern": self.pattern_choice.GetStringSelection(),
            "count": self.count_spin.GetValue(),
            "via_dia_mm": float(self.dia_ctrl.GetValue()),
            "drill_mm": float(self.drill_ctrl.GetValue()),
            "net_name": self.net_choice.GetValue().strip(),
        }
        params["line_start"] = self.parse_pair(self.line_start)
        params["line_end"] = self.parse_pair(self.line_end)
        params["center"] = self.parse_pair(self.center_ctrl)
        params["radius"] = float(self.radius_ctrl.GetValue())
        params["angle_start"] = float(self.start_angle_ctrl.GetValue())
        params["angle_stop"] = float(self.stop_angle_ctrl.GetValue())
        return params


class ViaPatternPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Via Pattern Array"
        self.category = "Modify PCB"
        self.description = "Place vias along a line, circle, or arc."

    def Run(self):
        board = pcbnew.GetBoard()
        dlg = ViaPatternDialog(board)
        if dlg.ShowModal() != wx.ID_OK:
            return

        params = dlg.get_params()
        netcode = self._get_netcode(board, params["net_name"])

        if params["pattern"] == "Line":
            pts = build_line_points(params["line_start"], params["line_end"], params["count"])
        elif params["pattern"] == "Full circle":
            pts = build_arc_points(params["center"], params["radius"], params["angle_start"],
                                   params["angle_start"], params["count"], closed=True)
        else:
            pts = build_arc_points(
                params["center"],
                params["radius"],
                params["angle_start"],
                params["angle_stop"],
                params["count"],
                closed=False,
            )

        self._create_vias(board, pts, params["via_dia_mm"], params["drill_mm"], netcode)
        pcbnew.Refresh()

    def _get_netcode(self, board, name):
        for net in board.GetNetsByNetcode().values():
            if net.GetNetname() == name:
                return net.GetNet()
        return 0  # default to no net

    def _create_vias(self, board, pts_mm, via_dia_mm, drill_mm, netcode):
        via_dia = mm_to_iu(via_dia_mm)
        drill = mm_to_iu(drill_mm)
        for x_mm, y_mm in pts_mm:
            via = pcbnew.VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(mm_to_iu(x_mm), mm_to_iu(y_mm)))
            via.SetWidth(via_dia)
            via.SetDrill(drill)
            via.SetViaType(pcbnew.VIA_THROUGH)
            via.SetNetCode(netcode)
            board.Add(via)


ViaPatternPlugin().register()