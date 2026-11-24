"""Flask routes for the Lab 04 BJT CE amplifier simulator.

Lab 3 analytical DC bias remains available at /analytical.
New SPICE path is /simulate and runs ngspice through spice_engine.py.
Default port is 5000 — the same URL used by the previous lab.
"""

from __future__ import annotations

import math
import re

from flask import Flask, abort, render_template, request, send_from_directory

import dc_bias
import spice_engine

app = Flask(__name__)
# Always reload templates during development so a template fix is visible
# without restarting the server (Jinja's default follows app.debug only).
app.config["TEMPLATES_AUTO_RELOAD"] = True

SPICE_DEFAULTS = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "rl": "10",
    "cin_uf": "10",
    "cout_uf": "10",
    "amp_mv": "10",
    "freq_hz": "1000",
}

ANALYTICAL_DEFAULTS = {
    "vcc": "12",
    "beta": "100",
    "vbe": "0.7",
    "rb": "470",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
}

RUNS_DIR = spice_engine.RUNS_DIR
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
ARTIFACT_NAMES = {"netlist.cir", "run.log", "run.raw", "meta.json"}


def _collect(form, defaults: dict) -> dict:
    """Read the form back with defaults so errors do not erase user input."""
    return {key: form.get(key, default) for key, default in defaults.items()}


def _status() -> dict:
    ok, version = spice_engine.check_ngspice()
    model_ok, model_name, model_message = spice_engine.check_model()
    if not ok:
        message = f"ngspice ไม่พร้อม: {version}"
    elif not model_ok:
        message = model_message
    else:
        message = f"ngspice พร้อม · {model_name}"
    return {
        "ngspice_ok": ok,
        "ngspice": version,
        "model_ok": model_ok,
        "model": model_name or model_message,
        "message": message,
        "fallback": spice_engine.is_fallback_model(),
        "ready": ok and model_ok,
    }


def _render(
    *,
    result=None,
    error=None,
    engine="spice",
    analysis="dc",
    bias_mode="divider",
    spice_values=None,
    analytical_values=None,
):
    return render_template(
        "index.html",
        result=result,
        error=error,
        engine=engine,
        analysis=analysis,
        bias_mode=bias_mode,
        spice_values=spice_values or SPICE_DEFAULTS,
        analytical_values=analytical_values or ANALYTICAL_DEFAULTS,
        status=_status(),
    )


def _form_number(values: dict, key: str, label: str, low: float, high: float, unit: str) -> float:
    raw = values.get(key, "")
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} ต้องเป็นตัวเลข ({unit})") from exc
    if not math.isfinite(number) or number < low or number > high:
        raise ValueError(f"{label} ต้องอยู่ในช่วง {low:g}–{high:g} {unit}")
    return number


def _analytical_params(values: dict, mode: str) -> dict:
    params = {
        "vcc": _form_number(values, "vcc", "VCC", 1, 200, "V"),
        "beta": _form_number(values, "beta", "β", 1, 5000, ""),
        "vbe": _form_number(values, "vbe", "VBE", 0.1, 2, "V"),
        "rc": _form_number(values, "rc", "RC", 0.01, 10000, "kΩ"),
    }
    if mode == "fixed":
        params["rb"] = _form_number(values, "rb", "RB", 0.01, 10000, "kΩ")
    elif mode == "emitter":
        params["rb"] = _form_number(values, "rb", "RB", 0.01, 10000, "kΩ")
        params["re"] = _form_number(values, "re", "RE", 1e-6, 10000, "kΩ")
    elif mode == "divider":
        params["r1"] = _form_number(values, "r1", "R1", 0.01, 10000, "kΩ")
        params["r2"] = _form_number(values, "r2", "R2", 0.01, 10000, "kΩ")
        params["re"] = _form_number(values, "re", "RE", 1e-6, 10000, "kΩ")
    else:
        raise ValueError(f"ไม่รู้จัก bias mode: {mode!r}")
    return params


def _analytical_display(mode: str, solved: dict) -> dict:
    labels = [
        ("VB", "vb", "V"),
        ("VE", "ve", "V"),
        ("VC", "vc", "V"),
        ("VCE", "vce", "V"),
        ("IB", "ib_ua", "µA"),
        ("IC", "ic_ma", "mA"),
        ("IE", "ie_ma", "mA"),
    ]
    values = [
        {"label": label, "value": f"{float(solved[key]):.4f}", "unit": unit, "note": ""}
        for label, key, unit in labels
    ]
    mode_name = {"fixed": "Fixed Bias", "emitter": "Emitter Bias", "divider": "Voltage Divider Bias"}[mode]
    return {
        "kind": "analytical",
        "title": f"Analytical DC Bias — {mode_name}",
        "status": "success",
        "values": values,
        "warnings": solved["warnings"],
        "assumptions": solved["assumptions"],
        "charts": [],
        "provenance": [
            {"label": "แหล่งผล", "value": "dc_bias.py (Lab 3 analytical)"},
            {"label": "โมเดล", "value": "β คงที่ + VBE คงที่"},
            {"label": "หน่วย", "value": "V / kΩ / mA / µA"},
        ],
        "links": [],
        "analysis": "dc",
    }


@app.get("/")
def index():
    return _render()


@app.post("/analytical")
def analytical():
    values = _collect(request.form, ANALYTICAL_DEFAULTS)
    mode = (request.form.get("bias_mode") or "divider").strip().lower()
    result = None
    error = None
    try:
        solved = dc_bias.compute(mode, _analytical_params(values, mode))
        result = _analytical_display(mode, solved)
    except (ValueError, KeyError) as exc:
        error = str(exc)
    return _render(
        result=result,
        error=error,
        engine="analytical",
        bias_mode=mode,
        analytical_values=values,
    )


@app.post("/simulate")
def simulate():
    values = _collect(request.form, SPICE_DEFAULTS)
    mode = (request.form.get("analysis") or "dc").strip().lower()
    result = None
    error = None
    try:
        if mode not in spice_engine.ANALYSIS_MODES:
            raise spice_engine.SimulationError(f"ไม่รู้จัก analysis mode: {mode!r}")
        params = spice_engine.validate_params(values)
        model_ok, model_name, model_message = spice_engine.check_model()
        if not model_ok:
            raise spice_engine.SimulationError(model_message)
        raw = spice_engine.run_ngspice(params, mode, model_name)
        result = spice_engine.summarize(raw, params)
    except spice_engine.SimulationError as exc:
        error = str(exc)
    return _render(
        result=result,
        error=error,
        engine="spice",
        analysis=mode,
        spice_values=values,
    )


@app.get("/artifact/<run_id>/<filename>")
def artifact(run_id: str, filename: str):
    """Serve evidence files from one run. Whitelisted names only."""
    if not SAFE_RUN_ID.fullmatch(run_id) or filename not in ARTIFACT_NAMES:
        abort(404)
    directory = RUNS_DIR / run_id
    if not directory.is_dir():
        abort(404)
    return send_from_directory(directory, filename, as_attachment=False)


if __name__ == "__main__":
    # Same local URL as the previous lab: http://127.0.0.1:5000/
    app.run(host="127.0.0.1", port=5000, debug=False)
