import pcbnew
import math

def to_mm(v_nm):
    """Converts nm to mm
    :param v_nm: nm to convert
    :type v_nm: str
    """
    return pcbnew.to_mm(v_nm)

def d2r(a):
    """Converts degrees to radians.
    :param a: Degrees to convert to radians
    :type a: float
    """
    return a * math.pi / 180.0

def v2(x, y):
    """Return a KiCad VECTOR2I point from (x, y), casting to ints (nm units).
    :param x: X coordinate
    :type x: float
    :param y: Y coordinate
    :type y: float
    """
    return pcbnew.VECTOR2I(int(x), int(y))

def validate_rounded_corner_core_clearance(r_corner, clearance):
    """
    Validate that the rounded inner winding corner does not intrude into
    the rectangular core corner.

    All arguments are in KiCad internal units.

    :param r_corner: User-defined geometric corner radius.
    :type r_corner: int
    :param clearance: Required clearance from core to winding.
    :type clearance: int
    :return: Tuple ``(ok, message)``. If valid, ``ok`` is True and message is empty.
             If invalid, ``ok`` is False and message contains the error description.
    :rtype: tuple[bool, str]
    """

    if r_corner <= 0:
        return True, ""

    diagonal = math.sqrt(2.0) * float(r_corner)
    allowed = float(r_corner + clearance)

    if diagonal > allowed:
        max_radius = clearance / (math.sqrt(2.0) - 1.0)

        msg = (
            "Rounded corner radius is too large for the selected core clearance.\n\n"
            "The inner copper arc would intrude into the core corner region.\n\n"
            f"Selected radius: {pcbnew.ToMM(r_corner):.3f} mm\n"
            f"Clearance: {pcbnew.ToMM(clearance):.3f} mm\n"
            f"Maximum allowed radius: {pcbnew.ToMM(int(max_radius)):.3f} mm\n\n"
            "Reduce the corner radius or increase the core clearance."
        )

        return False, msg

    return True, ""