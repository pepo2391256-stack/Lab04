"""Analytical DC bias calculations carried over from Lab 3.

Units used throughout this module:
    voltage: V
    resistance: kOhm
    current: mA (ib_ua is microampere)

This module is intentionally independent from the SPICE path so the three
Lab 3 bias modes remain available as a reference.
"""

from __future__ import annotations

from math import isfinite


def _positive(name: str, value, *, maximum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} ต้องเป็นตัวเลข") from exc
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{name} ต้องมากกว่า 0")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} ต้องไม่เกิน {maximum:g}")
    return number


def _format_result(mode, vb, ve, vc, beta, ib_ma, ic_ma, vcc, rc, re):
    """Build a common result dictionary and add region warnings."""
    vce = vc - ve
    warnings = []

    if ic_ma <= 0 or ib_ma <= 0:
        region = "cutoff"
        warnings.append("กระแสเบสเป็นศูนย์หรือติดลบจากสมการประมาณ → อยู่ในสภาวะตัด (cutoff)")
    elif vce < 0.2 or vc <= vb:
        region = "saturation (suspected)"
        warnings.append("VCE ต่ำหรือ VC ไม่สูงกว่า VB → อาจเข้าสู่ภาวะอิ่มตัว สมการ active-region ไม่เหมาะสม")
    else:
        region = "active"

    assumptions = [
        f"VBE คงที่ = 0.7 V (ที่ผู้ใช้ปรับได้), β คงที่ = {beta:g}",
        "ไม่Include Early effect และไม่ใช้ BJT model จาก SPICE",
    ]

    return {
        "mode": mode,
        "vb": vb,
        "ve": ve,
        "vc": vc,
        "vce": vce,
        "ib_ua": ib_ma * 1000.0,
        "ic_ma": ic_ma,
        "ie_ma": ib_ma + ic_ma,
        "region": region,
        "warnings": warnings,
        "assumptions": assumptions,
        "fixture": {"vcc": vcc, "rc": rc, "re": re},
    }


def solve_fixed(vcc, rb, rc, beta, vbe=0.7):
    """Fixed bias: base resistor from VCC to base, emitter grounded."""
    vcc = _positive("VCC", vcc, maximum=200)
    rb = _positive("RB", rb, maximum=10000)
    rc = _positive("RC", rc, maximum=10000)
    beta = _positive("β", beta, maximum=5000)
    vbe = _positive("VBE", vbe, maximum=2)

    if vbe >= vcc:
        raise ValueError("VBE ต้องน้อยกว่า VCC สำหรับ fixed bias")

    ib_ma = (vcc - vbe) / rb
    ic_ma = beta * ib_ma
    vb = vbe
    ve = 0.0
    vc = vcc - ic_ma * rc
    return _format_result("fixed", vb, ve, vc, beta, ib_ma, ic_ma, vcc, rc, 0.0)


def solve_emitter(vcc, rb, rc, re, beta, vbe=0.7):
    """Emitter bias with base resistor and unbypassed emitter resistor."""
    vcc = _positive("VCC", vcc, maximum=200)
    rb = _positive("RB", rb, maximum=10000)
    rc = _positive("RC", rc, maximum=10000)
    re = _positive("RE", re, maximum=10000)
    beta = _positive("β", beta, maximum=5000)
    vbe = _positive("VBE", vbe, maximum=2)

    if vbe >= vcc:
        raise ValueError("VBE ต้องน้อยกว่า VCC สำหรับ emitter bias")

    ib_ma = (vcc - vbe) / (rb + (beta + 1) * re)
    ic_ma = beta * ib_ma
    ve = (beta + 1) * ib_ma * re
    vb = ve + vbe
    vc = vcc - ic_ma * rc
    return _format_result("emitter", vb, ve, vc, beta, ib_ma, ic_ma, vcc, rc, re)


def solve_divider(vcc, r1, r2, rc, re, beta, vbe=0.7):
    """Voltage-divider bias using the Thevenin equivalent of R1/R2."""
    vcc = _positive("VCC", vcc, maximum=200)
    r1 = _positive("R1", r1, maximum=10000)
    r2 = _positive("R2", r2, maximum=10000)
    rc = _positive("RC", rc, maximum=10000)
    re = _positive("RE", re, maximum=10000)
    beta = _positive("β", beta, maximum=5000)
    vbe = _positive("VBE", vbe, maximum=2)

    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)

    if vth <= vbe:
        ib_ma = 0.0
        ic_ma = 0.0
        ve = 0.0
        vb = vth
        vc = vcc
        result = _format_result("divider", vb, ve, vc, beta, ib_ma, ic_ma, vcc, rc, re)
        result["warnings"].append("VTH ต่ำกว่า VBE → แขนง divider ไม่เพียงพอ อยู่ในสภาวะตัด")
        return result

    ib_ma = (vth - vbe) / (rth + (beta + 1) * re)
    ic_ma = beta * ib_ma
    ve = (beta + 1) * ib_ma * re
    vb = ve + vbe
    vc = vcc - ic_ma * rc
    return _format_result("divider", vb, ve, vc, beta, ib_ma, ic_ma, vcc, rc, re)


def compute(mode: str, params: dict) -> dict:
    """Dispatch to one of the three Lab 3 analytical modes."""
    mode = (mode or "").strip().lower()
    if mode == "fixed":
        return solve_fixed(params["vcc"], params["rb"], params["rc"], params["beta"], params["vbe"])
    if mode == "emitter":
        return solve_emitter(params["vcc"], params["rb"], params["rc"], params["re"], params["beta"], params["vbe"])
    if mode == "divider":
        return solve_divider(params["vcc"], params["r1"], params["r2"], params["rc"], params["re"], params["beta"], params["vbe"])
    raise ValueError(f"ไม่รู้จัก bias mode: {mode!r}")
