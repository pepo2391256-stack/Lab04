"""ngspice adapter for the Lab 04 CE voltage-divider simulator.

Responsibilities:
    validate form values -> build a netlist -> run ngspice as an external
    process -> parse the RAW output -> return values with units and charts.

No simulated result is ever invented here. If ngspice, the model file or
the RAW output is missing/invalid, SimulationError is raised.
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "bjt.model"
RUNS_DIR = BASE_DIR / "runs"
MODEL_PLACEHOLDER = "INSTRUCTOR_MODEL_REQUIRED"
MODEL_FALLBACK_MARKER = "FALLBACK_MODEL_NOT_INSTRUCTOR"
ANALYSIS_MODES = {"dc", "ac", "tran"}
TIMEOUT_SECONDS = 60


class SimulationError(Exception):
    """Raised for any invalid input, missing tool, failed run or bad output."""


def _fmt(value: float, digits: int = 6) -> str:
    return f"{float(value):.{digits}g}"


def _tail(text: str, lines: int = 12) -> str:
    parts = (text or "").splitlines()
    return "\n".join(parts[-lines:]) if parts else "(log ว่าง)"


def ngspice_executable() -> str | None:
    """Resolve ngspice, allowing NGSPICE_PATH for a local portable install."""
    override = os.environ.get("NGSPICE_PATH", "").strip().strip('"')
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return str(candidate.resolve())
        found = shutil.which(override)
        return found
    return shutil.which("ngspice")


@lru_cache(maxsize=1)
def check_ngspice() -> tuple[bool, str]:
    """Return (available, version_or_reason). Never raises.

    Some portable Windows builds never answer --version and block until the
    subprocess timeout. Probe once with a short timeout and cache the result so
    every page render does not pay that cost; batch runs are the real check.
    """
    executable = ngspice_executable()
    if not executable:
        return False, "ไม่พบ ngspice ใน PATH (หรือยังไม่ได้ตั้ง NGSPICE_PATH)"
    try:
        completed = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=1,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        first_line = next((line.strip() for line in output.splitlines() if line.strip()), "")
        if first_line:
            return True, first_line
    except (OSError, subprocess.TimeoutExpired):
        pass
    return True, f"พบ executable: {executable} (อ่าน version ไม่ได้จาก build นี้)"


def is_fallback_model() -> bool:
    """True when the active model is sourced from ngspice examples, not the kit."""
    if not MODEL_PATH.exists():
        return False
    return "FALLBACK_MODEL_NOT_INSTRUCTOR" in MODEL_PATH.read_text(
        encoding="utf-8", errors="replace"
    )


def check_model() -> tuple[bool, str | None, str]:
    """Return (available, model_name, message). Refuses the placeholder file."""
    if not MODEL_PATH.exists():
        return False, None, (
            f"ไม่พบไฟล์โมเดล {MODEL_PATH} — ให้คัดลอก models/bjt.model.example "
            "เป็น bjt.model แล้วใส่โมเดลที่อาจารย์แจกใน Starter Kit"
        )
    text = MODEL_PATH.read_text(encoding="utf-8", errors="replace")
    if MODEL_PLACEHOLDER in text:
        return False, None, (
            "models/bjt.model ยังเป็นแม่แบบ (INSTRUCTOR_MODEL_REQUIRED) — "
            "ห้ามใช้จำลองผลจริง ให้แทนที่ด้วยโมเดลจากอาจารย์ก่อนรัน"
        )
    match = re.search(r"(?im)^\s*\.model\s+(\S+)\s+NPN\b", text)
    if not match:
        return False, None, "ไม่พบคำสั่ง .model ... NPN ในไฟล์โมเดล"
    return True, match.group(1), f"ใช้ BJT model: {match.group(1)}"


def _number(name: str, value, low: float, high: float, unit: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SimulationError(f"{name} ต้องเป็นตัวเลข") from exc
    if not math.isfinite(number) or number < low or number > high:
        raise SimulationError(
            f"{name} ต้องอยู่ในช่วง {_fmt(low)}–{_fmt(high)} {unit} (ได้รับ {value!r})"
        )
    return number


def validate_params(raw: dict) -> dict:
    """Validate all form values before they ever reach a netlist."""
    return {
        "vcc": _number("VCC", raw.get("vcc"), 1, 100, "V"),
        "r1": _number("R1", raw.get("r1"), 0.01, 10000, "kΩ"),
        "r2": _number("R2", raw.get("r2"), 0.01, 10000, "kΩ"),
        "rc": _number("RC", raw.get("rc"), 0.01, 10000, "kΩ"),
        "re": _number("RE", raw.get("re"), 1e-6, 10000, "kΩ (ต้องมากกว่า 0)"),
        "rl": _number("RL", raw.get("rl"), 0.01, 10000, "kΩ"),
        "cin_uf": _number("Cin", raw.get("cin_uf"), 1e-4, 10000, "µF"),
        "cout_uf": _number("Cout", raw.get("cout_uf"), 1e-4, 10000, "µF"),
        "amp_mv": _number("Amplitude", raw.get("amp_mv"), 1e-3, 5000, "mV peak"),
        "freq_hz": _number("Frequency", raw.get("freq_hz"), 1, 1e8, "Hz"),
    }


def build_netlist(
    p: dict, mode: str, model_name: str, run_id: str, include_path: str | None = None
) -> str:
    """Create the CE voltage-divider netlist for one analysis mode."""
    if mode not in ANALYSIS_MODES:
        raise SimulationError(f"ไม่รู้จัก analysis mode: {mode!r}")

    ac_amp = p["amp_mv"] / 1000.0
    tstep = 1.0 / (p["freq_hz"] * 200.0)
    tstop = 5.0 / p["freq_hz"]
    analysis = {
        "dc": ".op",
        "ac": ".ac dec 20 1 10MEG",
        "tran": f".tran {_fmt(tstep, 9)} {_fmt(tstop, 9)}",
    }[mode]

    include_path = (include_path or str(MODEL_PATH.resolve())).replace("\\", "/")
    lines = [
        f"* Lab04 CE voltage-divider amplifier — run {run_id}",
        "* Vin = node in (ก่อน CIN); Vout = node out (บน RL หลัง COUT)",
        "* Netlist นี้สร้างจากค่าที่ validate แล้ว ห้ามแก้ด้วยมือก่อนตรวจ provenance",
        f"VCC vcc 0 DC {_fmt(p['vcc'])}",
        f"VIN in 0 DC 0 AC {_fmt(ac_amp, 9)} SIN(0 {_fmt(ac_amp, 9)} {_fmt(p['freq_hz'], 9)})",
        f"CIN in base {_fmt(p['cin_uf'])}u",
        f"R1 vcc base {_fmt(p['r1'])}k",
        f"R2 base 0 {_fmt(p['r2'])}k",
        f"RC vcc collector {_fmt(p['rc'])}k",
        "Q1 collector base emitter " + model_name,
        f"RE emitter 0 {_fmt(p['re'])}k",
        f"COUT collector out {_fmt(p['cout_uf'])}u",
        f"RL out 0 {_fmt(p['rl'])}k",
        f'.include "{include_path}"',
        ".save all",
        analysis,
        ".end",
        "",
    ]
    return "\n".join(lines)


def parse_raw(text: str) -> dict:
    """Parse an ngspice ASCII RAW file into variables and numeric rows."""
    lines = text.splitlines()
    try:
        values_index = next(
            i for i, line in enumerate(lines) if line.strip().lower() == "values:"
        )
    except StopIteration as exc:
        raise SimulationError(
            "RAW file ไม่มีส่วน 'Values:' — อาจเป็น binary หรือไฟล์ไม่สมบูรณ์"
        ) from exc

    header = lines[:values_index]
    flags_line = next(
        (line for line in header if line.strip().lower().startswith("flags:")), ""
    )
    flags = flags_line.lower()
    if "binary" in flags:
        raise SimulationError(
            "RAW file อยู่ในรูปแบบ binary — ต้องตั้งค่าให้เป็น ascii ก่อนอ่านผล"
        )
    is_complex = "complex" in flags

    variables_index = next(
        (i for i, line in enumerate(header) if line.strip().lower().startswith("variables:")),
        None,
    )
    if variables_index is None:
        raise SimulationError("RAW file ไม่มีส่วน 'Variables:'")

    variables = []
    for line in header[variables_index + 1 :]:
        match = re.match(r"^\s*(\d+)\s+(\S+)\s+(\S+)(?:\s+.*)?$", line)
        if match:
            variables.append(
                {"index": int(match.group(1)), "name": match.group(2), "type": match.group(3)}
            )
    if not variables:
        raise SimulationError("RAW file ไม่มีตัวแปรที่อ่านได้")

    def to_value(token: str):
        try:
            if is_complex:
                if "," in token:
                    real_text, imag_text = token.split(",", 1)
                    return complex(float(real_text), float(imag_text))
                return complex(float(token), 0.0)
            return float(token)
        except ValueError as exc:
            raise SimulationError(f"อ่านค่า RAW ไม่สำเร็จ: {token!r}") from exc

    # ngspice ASCII RAW writes the point index on the first line of a point and
    # then one value per line. Some tools put index + all values on one line.
    rows = []
    pending: list = []
    for line in lines[values_index + 1 :]:
        parts = line.split()
        if not parts:
            continue
        if parts[0].isdigit():
            inline = len(parts) >= len(variables) + 1
            if inline:
                if pending:
                    raise SimulationError("RAW file มีค่าค้างก่อนจุดข้อมูลถัดไป")
                parts = parts[1 : len(variables) + 1]
            elif not pending:
                # Leading point index (ngspice style), values follow on next lines.
                parts = parts[1:]
        for token in parts:
            pending.append(to_value(token))
            if len(pending) == len(variables):
                rows.append(pending)
                pending = []
    if pending:
        raise SimulationError("RAW file มีข้อมูลจุดสุดท้ายไม่ครบตามจำนวนตัวแปร")

    if not rows:
        raise SimulationError("RAW file ไม่มีข้อมูลค่าตัวเลข")
    return {"variables": variables, "rows": rows, "complex": is_complex}


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _var_index(variables: list[dict], name: str) -> int | None:
    wanted = _normalize(name)
    for index, variable in enumerate(variables):
        if _normalize(variable["name"]) == wanted:
            return index
    return None


def _var_index_contains(variables: list[dict], *parts: str) -> int | None:
    for index, variable in enumerate(variables):
        lowered = variable["name"].lower()
        if all(part.lower() in lowered for part in parts):
            return index
    return None


def _real(value) -> float:
    return float(value.real) if isinstance(value, complex) else float(value)


def _series(parsed: dict, name: str) -> list:
    index = _var_index(parsed["variables"], name)
    if index is None:
        available = ", ".join(v["name"] for v in parsed["variables"][:12])
        raise SimulationError(f"RAW ไม่มีตัวแปร {name} (มี: {available})")
    return [row[index] for row in parsed["rows"]]


def _op_value(parsed: dict, name: str) -> float:
    values = _series(parsed, name)
    return _real(values[0])


def extract_dc(parsed: dict, p: dict) -> dict:
    """Read the operating point from ngspice RAW output."""
    vcc = _op_value(parsed, "v(vcc)")
    vb = _op_value(parsed, "v(base)")
    ve = _op_value(parsed, "v(emitter)")
    vc = _op_value(parsed, "v(collector)")

    current_index = _var_index_contains(parsed["variables"], "q1", "ic")
    if current_index is not None:
        ic_ma = _real(parsed["rows"][0][current_index]) * 1000.0
        ic_note = f"Q1 current from ngspice ({parsed['variables'][current_index]['name']})"
        ic_direct = True
    else:
        ic_ma = (vcc - vc) / p["rc"]
        ic_note = "คำนวณจาก (VCC−VC)/RC ด้วย node voltage ที่ ngspice ออกมา"
        ic_direct = False

    return {
        "vcc": vcc,
        "vb": vb,
        "ve": ve,
        "vc": vc,
        "vce": vc - ve,
        "ic_ma": ic_ma,
        "ic_note": ic_note,
        "ic_direct": ic_direct,
    }


def extract_ac(parsed: dict) -> dict:
    """Compute gain and phase from a complex AC RAW sweep."""
    frequency = [_real(value) for value in _series(parsed, "frequency")]
    vin = _series(parsed, "v(in)")
    vout = _series(parsed, "v(out)")

    gain = []
    phase = []
    for input_value, output_value in zip(vin, vout):
        denominator = input_value if isinstance(input_value, complex) else complex(input_value, 0)
        numerator = output_value if isinstance(output_value, complex) else complex(output_value, 0)
        if abs(denominator) < 1e-15:
            gain.append(0.0)
            phase.append(0.0)
            continue
        ratio = numerator / denominator
        gain.append(abs(ratio))
        phase.append(math.degrees(math.atan2(ratio.imag, ratio.real)))
    return {"frequency": frequency, "gain": gain, "phase": phase}


def extract_tran(parsed: dict) -> dict:
    """Read time-domain waveforms and convert to display units."""
    time_s = [_real(value) for value in _series(parsed, "time")]
    vin_v = [_real(value) for value in _series(parsed, "v(in)")]
    vout_v = [_real(value) for value in _series(parsed, "v(out)")]
    return {
        "time_ms": [value * 1000.0 for value in time_s],
        "vin_mv": [value * 1000.0 for value in vin_v],
        "vout_v": vout_v,
    }


def find_cutoff(frequency: list[float], gain: list[float]) -> tuple[float | None, float | None]:
    """Find -3 dB points relative to the in-band maximum; None if absent."""
    if not frequency or not gain:
        return None, None
    peak = max(gain)
    if peak <= 0:
        return None, None
    target = peak / math.sqrt(2.0)
    peak_index = gain.index(peak)

    low = None
    for i in range(peak_index, 0, -1):
        if gain[i] <= target < gain[i - 1]:
            low = frequency[i]
            break

    high = None
    for i in range(peak_index + 1, len(gain)):
        if gain[i] <= target < gain[i - 1]:
            high = frequency[i]
            break
    return low, high


def _downsample_indices(length: int, maximum: int = 350) -> list[int]:
    if length <= maximum:
        return list(range(length))
    step = math.ceil(length / maximum)
    indices = list(range(0, length, step))
    if indices and indices[-1] != length - 1:
        indices.append(length - 1)
    return indices


def _tick_label(value: float, logx: bool) -> str:
    if logx:
        return f"10^{value:.1f}"
    if abs(value) >= 1000 or (0 < abs(value) < 0.01):
        return f"{value:.2e}"
    return f"{value:.3g}"


def line_chart(
    title: str,
    x_values: list[float],
    series: list[dict],
    x_label: str,
    y_label: str,
    *,
    logx: bool = False,
) -> str:
    """Build a small SVG chart directly from simulation arrays (no mock data)."""
    if not x_values or not series:
        return ""
    escape = html.escape
    indices = _downsample_indices(len(x_values))

    transformed_x = []
    for index in indices:
        value = x_values[index]
        if not math.isfinite(value):
            continue
        transformed_x.append(math.log10(max(value, 1e-12)) if logx else float(value))

    plotted = []
    for item in series:
        pairs = []
        for position, index in enumerate(indices):
            if position >= len(transformed_x):
                break
            raw_y = item["values"][index] if index < len(item["values"]) else None
            if raw_y is None or not math.isfinite(float(raw_y)):
                continue
            pairs.append((transformed_x[position], float(raw_y)))
        plotted.append((item, pairs))

    all_y = [point[1] for _, pairs in plotted for point in pairs]
    if not transformed_x or not all_y:
        return ""

    xmin, xmax = min(transformed_x), max(transformed_x)
    ymin, ymax = min(all_y), max(all_y)
    x_pad = (xmax - xmin) * 0.02 if xmax > xmin else 0.5
    y_pad = (ymax - ymin) * 0.08 if ymax > ymin else max(abs(ymax) * 0.1, 0.5)
    xmin, xmax = xmin - x_pad, xmax + x_pad
    ymin, ymax = ymin - y_pad, ymax + y_pad

    left, right, top, bottom = 64, 664, 58, 236

    def sx(value: float) -> float:
        return left + (value - xmin) / (xmax - xmin) * (right - left)

    def sy(value: float) -> float:
        return bottom - (value - ymin) / (ymax - ymin) * (bottom - top)

    parts = [
        '<svg viewBox="0 0 680 290" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{escape(title)}">',
        f"<title>{escape(title)}</title>",
        '<rect width="680" height="290" rx="8" fill="#ffffff" stroke="#dce7ee"/>',
        f'<text x="16" y="24" font-size="14" font-weight="700" fill="#103658">{escape(title)}</text>',
    ]

    for tick in range(5):
        y_value = ymin + (ymax - ymin) * tick / 4
        y_pixel = sy(y_value)
        parts.append(
            f'<line x1="{left}" y1="{y_pixel:.1f}" x2="{right}" y2="{y_pixel:.1f}" '
            'stroke="#e8eff4" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y_pixel + 4:.1f}" text-anchor="end" '
            f'font-size="10" fill="#547084">{escape(_tick_label(y_value, False))}</text>'
        )
        x_value = xmin + (xmax - xmin) * tick / 4
        x_pixel = sx(x_value)
        parts.append(
            f'<line x1="{x_pixel:.1f}" y1="{top}" x2="{x_pixel:.1f}" y2="{bottom}" '
            'stroke="#f0f5f8" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x_pixel:.1f}" y="{bottom + 17}" text-anchor="middle" '
            f'font-size="10" fill="#547084">{escape(_tick_label(x_value, logx))}</text>'
        )

    parts.append(
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#9cb2c2" stroke-width="1.4"/>'
    )
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#9cb2c2" stroke-width="1.4"/>'
    )
    parts.append(
        f'<text x="{(left + right) / 2:.1f}" y="272" text-anchor="middle" '
        f'font-size="11" fill="#486275">{escape(x_label)}</text>'
    )
    parts.append(
        f'<text x="16" y="{(top + bottom) / 2:.1f}" transform="rotate(-90 16 {(top + bottom) / 2:.1f})" '
        f'text-anchor="middle" font-size="11" fill="#486275">{escape(y_label)}</text>'
    )

    legend_x = 70
    for item, pairs in plotted:
        points = " ".join(f"{sx(px):.1f},{sy(py):.1f}" for px, py in pairs)
        color = item.get("color", "#07766e")
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.2" '
            f'stroke-linejoin="round" points="{points}"/>'
        )
        parts.append(
            f'<line x1="{legend_x}" y1="43" x2="{legend_x + 16}" y2="43" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        parts.append(
            f'<text x="{legend_x + 22}" y="47" font-size="10.5" fill="#486275">'
            f"{escape(item['name'])}</text>"
        )
        legend_x += 36 + len(item["name"]) * 7

    parts.append("</svg>")
    return "".join(parts)


def run_ngspice(p: dict, mode: str, model_name: str) -> dict:
    """Execute ngspice in a fresh directory and return parsed output."""
    if mode not in ANALYSIS_MODES:
        raise SimulationError(f"ไม่รู้จัก analysis mode: {mode!r}")

    available, version = check_ngspice()
    if not available:
        raise SimulationError(f"ngspice ไม่พร้อม: {version}")

    executable = ngspice_executable()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]

    # Evidence lives in the project (RUNS_DIR), but ngspice on Windows can hang
    # when -o/-r paths contain spaces. Run in a space-free temp directory and
    # copy the artifacts back for the /artifact route.
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.gettempdir()) / "lab04-ngspice-runs" / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    model_copy = work_dir / "bjt.model"
    model_copy.write_text(
        MODEL_PATH.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
    )
    netlist = build_netlist(p, mode, model_name, run_id, str(model_copy))
    netlist_path = work_dir / "netlist.cir"
    log_path = work_dir / "run.log"
    raw_path = work_dir / "run.raw"
    netlist_path.write_text(netlist, encoding="utf-8")

    command = [
        executable,
        "-b",
        "-o",
        str(log_path),
        "-r",
        str(raw_path),
        str(netlist_path),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(work_dir),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise SimulationError(
            f"ngspice timeout หลัง {TIMEOUT_SECONDS} วินาที (run_id={run_id})"
        ) from exc
    except OSError as exc:
        raise SimulationError(f"เรียก ngspice ไม่สำเร็จ: {exc}") from exc

    def archive() -> None:
        for name in ("netlist.cir", "run.log", "run.raw"):
            source = work_dir / name
            if source.exists():
                shutil.copy2(source, run_dir / name)

    if completed.returncode != 0:
        log_tail = _tail(log_path.read_text(encoding="utf-8", errors="replace")) if log_path.exists() else ""
        archive()
        raise SimulationError(
            f"ngspice exit code {completed.returncode}\n{log_tail or _tail(completed.stdout + completed.stderr)}"
        )
    if not raw_path.exists() or raw_path.stat().st_size == 0:
        archive()
        raise SimulationError(f"RAW file ว่างหรือไม่มี (run_id={run_id})")

    raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_raw(raw_text)
    meta = {
        "run_id": run_id,
        "analysis": mode,
        "ngspice_version": version,
        "bjt_model": model_name,
        "params": p,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "exit_code": completed.returncode,
        "work_dir": str(work_dir),
        "evidence_dir": str(run_dir),
    }
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    archive()
    return {
        "run_id": run_id,
        "mode": mode,
        "version": version,
        "model_name": model_name,
        "parsed": parsed,
        "meta": meta,
        "netlist": netlist,
        "paths": {
            "netlist": str(run_dir / "netlist.cir"),
            "log": str(run_dir / "run.log"),
            "raw": str(run_dir / "run.raw"),
        },
    }


def summarize(result: dict, p: dict) -> dict:
    """Convert parsed ngspice data into display values, units and SVG charts."""
    mode = result["mode"]
    parsed = result["parsed"]
    run_id = result["run_id"]
    warnings = [
        "ผลจาก ngspice ขึ้นกับ BJT model ที่เลือก — อย่ารวมกับค่าจาก dc_bias.py โดยไม่บอกสมมติฐาน"
    ]
    if is_fallback_model():
        warnings.insert(
            0,
            "โมเดล PN2222 มาจากตัวอย่างของ ngspice (FALLBACK_MODEL_NOT_INSTRUCTOR) "
            "ไม่ใช่ Starter Kit ของอาจารย์ — ผลนี้ใช้ตรวจ pipeline เท่านั้น "
            "ต้องแทนที่ models/bjt.model ก่อนส่งงานจริง",
        )

    values: list[dict] = []
    charts: list[dict] = []
    analysis_label = {"dc": "DC / .op", "ac": "AC / .ac", "tran": "Transient / .tran"}[mode]

    if mode == "dc":
        dc = extract_dc(parsed, p)
        values = [
            {"label": "VCC", "value": _fmt(dc["vcc"], 4), "unit": "V", "note": "node vcc"},
            {"label": "VB", "value": _fmt(dc["vb"], 4), "unit": "V", "note": "node base"},
            {"label": "VE", "value": _fmt(dc["ve"], 4), "unit": "V", "note": "node emitter"},
            {"label": "VC", "value": _fmt(dc["vc"], 4), "unit": "V", "note": "node collector"},
            {"label": "VCE", "value": _fmt(dc["vce"], 4), "unit": "V", "note": "VC − VE"},
            {
                "label": "IC",
                "value": _fmt(dc["ic_ma"], 4),
                "unit": "mA",
                "note": dc["ic_note"],
            },
        ]
    elif mode == "ac":
        ac = extract_ac(parsed)
        low, high = find_cutoff(ac["frequency"], ac["gain"])
        peak = max(ac["gain"]) if ac["gain"] else 0.0
        values = [
            {
                "label": "Peak |Vout/Vin|",
                "value": _fmt(peak, 4),
                "unit": "",
                "note": "Vin = node in (ก่อน CIN), Vout = node out (บน RL)",
            },
            {
                "label": "fL (-3 dB)",
                "value": _fmt(low, 4) if low is not None else "not determined in sweep range",
                "unit": "Hz" if low is not None else "",
                "note": "เทียบกับ gain สูงสุดในช่วง sweep",
            },
            {
                "label": "fH (-3 dB)",
                "value": _fmt(high, 4) if high is not None else "not determined in sweep range",
                "unit": "Hz" if high is not None else "",
                "note": "เทียบกับ gain สูงสุดในช่วง sweep",
            },
            {
                "label": "Sweep",
                "value": f"{_fmt(min(ac['frequency']))} – {_fmt(max(ac['frequency']))}",
                "unit": "Hz",
                "note": ".ac dec 20 1 10MEG",
            },
        ]
        if low is None or high is None:
            warnings.append("ไม่พบจุดตัด -3 dB ครบทั้งสองด้านในช่วง sweep ที่กำหนด")
        charts = [
            {
                "title": "Gain magnitude |Vout/Vin| vs frequency",
                "svg": line_chart(
                    "Gain magnitude |Vout/Vin| vs frequency",
                    ac["frequency"],
                    [{"name": "|gain|", "values": ac["gain"], "color": "#167e93"}],
                    "Frequency (Hz, log scale)",
                    "|Vout/Vin|",
                    logx=True,
                ),
            },
            {
                "title": "Phase vs frequency",
                "svg": line_chart(
                    "Phase of Vout/Vin vs frequency",
                    ac["frequency"],
                    [{"name": "phase", "values": ac["phase"], "color": "#a65a2c"}],
                    "Frequency (Hz, log scale)",
                    "Phase (°)",
                    logx=True,
                ),
            },
        ]
    else:
        tran = extract_tran(parsed)
        vin_mv = tran["vin_mv"]
        vout_v = tran["vout_v"]
        peak_output_index = vout_v.index(max(vout_v)) if vout_v else 0
        mean_input = sum(vin_mv) / len(vin_mv) if vin_mv else 0.0
        if vin_mv and vin_mv[peak_output_index] < mean_input:
            phase_note = "Vout สูงสุดเมื่อ Vin ต่ำ → กลับเฟส (สอดคล้องกับ CE)"
        else:
            phase_note = "Vout สูงสุดเมื่อ Vin สูง → ตรวจจุดวัด/การต่อวงจร"
        values = [
            {
                "label": "Vin (peak)",
                "value": _fmt(max(vin_mv), 4) if vin_mv else "—",
                "unit": "mV",
                "note": "node in, วัดจาก transient จริง",
            },
            {
                "label": "Vout (p-p)",
                "value": _fmt(max(vout_v) - min(vout_v), 4) if vout_v else "—",
                "unit": "V",
                "note": "node out บน RL",
            },
            {
                "label": "Time span",
                "value": _fmt(max(tran["time_ms"]), 4) if tran["time_ms"] else "—",
                "unit": "ms",
                "note": "5 cycles ที่ความถี่ที่กรอก",
            },
            {"label": "Phase direction", "value": phase_note, "unit": "", "note": ""},
        ]
        if vout_v and (max(vout_v) > p["vcc"] - 0.2 or min(vout_v) < 0.2):
            warnings.append("Vout ใกล้ rail อาจเกิด clipping — ลด amplitude หรือปรับ bias")
        charts = [
            {
                "title": "Vin and Vout vs time",
                "svg": line_chart(
                    "Vin and Vout vs time (ngspice .tran)",
                    tran["time_ms"],
                    [
                        {"name": "Vin (mV)", "values": vin_mv, "color": "#0c8e83"},
                        {"name": "Vout (V)", "values": vout_v, "color": "#c77a35"},
                    ],
                    "Time (ms)",
                    "Vin (mV) / Vout (V)",
                ),
            }
        ]

    provenance = [
        {"label": "Engine", "value": f"ngspice — {result['version']}"},
        {"label": "Run status", "value": "success (exit code 0)"},
        {
            "label": "BJT model",
            "value": result["model_name"]
            + (" (fallback จากตัวอย่าง ngspice — ยังไม่ใช่ Starter Kit)" if is_fallback_model() else ""),
        },
        {"label": "Analysis", "value": analysis_label},
        {"label": "Run ID", "value": run_id},
    ]
    links = [
        {"label": "netlist.cir", "url": f"/artifact/{run_id}/netlist.cir"},
        {"label": "run.log", "url": f"/artifact/{run_id}/run.log"},
        {"label": "run.raw", "url": f"/artifact/{run_id}/run.raw"},
        {"label": "meta.json", "url": f"/artifact/{run_id}/meta.json"},
    ]
    return {
        "kind": "spice",
        "title": f"SPICE result — {analysis_label}",
        "status": "success",
        "values": values,
        "warnings": warnings,
        "assumptions": [
            "Vin = node in (ก่อน CIN); Vout = node out (บน RL หลัง COUT)",
            "DC: coupling capacitors เปิดวงจร · AC/Transient: Cin/Cout ทำงาน",
            "Baseline ไม่มี emitter bypass capacitor",
        ],
        "charts": charts,
        "provenance": provenance,
        "links": links,
        "analysis": mode,
    }
