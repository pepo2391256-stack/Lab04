"""Pipeline smoke test for spice_engine.py using a SOURCED fallback model.

This is NOT a submission result. It proves that validate -> netlist ->
subprocess.run([...]) -> RAW parse -> summary works with real ngspice.
The model below is copied verbatim from the official ngspice 47 distribution:
    Spice64/examples/tclspice/tcl-testbench1/PN2222.mod
It is not an instructor-verified Starter Kit model. Replace models/bjt.model
with the instructor model before using /simulate for graded results.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

import spice_engine  # noqa: E402

SMOKE_DIR = BASE_DIR / "smoke_runs"
MODEL_TEXT = """.model PN2222 NPN(Is=14.34f Xti=3 Eg=1.11 Vaf=74.03 Bf=255.9 Ne=1.307
+ Ise=14.34f Ikf=.2847 Xtb=1.5 Br=6.092 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=7.306p Mjc=.3416 Vjc=.75 Fc=.5 Cje=22.01p Mje=.377 Vje=.75
+ Tr=46.91n Tf=411.1p Itf=.6 Vtf=1.7 Xtf=3 Rb=10)
"""

PARAMS = {
    "vcc": 12,
    "r1": 100,
    "r2": 22,
    "rc": 2.2,
    "re": 1,
    "rl": 10,
    "cin_uf": 10,
    "cout_uf": 10,
    "amp_mv": 10,
    "freq_hz": 1000,
}


def main() -> int:
    SMOKE_DIR.mkdir(exist_ok=True)
    model_path = SMOKE_DIR / "bjt.model"
    model_path.write_text(
        "* FALLBACK_MODEL_NOT_INSTRUCTOR\n"
        "* Source: ngspice-47 official examples/tclspice/tcl-testbench1/PN2222.mod\n"
        + MODEL_TEXT,
        encoding="utf-8",
    )
    spice_engine.MODEL_PATH = model_path
    spice_engine.RUNS_DIR = SMOKE_DIR

    ok, version = spice_engine.check_ngspice()
    print(f"SMOKE TEST (not submission) — ngspice available={ok}: {version}")
    if not ok:
        return 1

    params = spice_engine.validate_params(PARAMS)
    for mode in ("dc", "ac", "tran"):
        print(f"\n--- {mode} ---")
        try:
            raw = spice_engine.run_ngspice(params, mode, "PN2222")
            summary = spice_engine.summarize(raw, params)
        except spice_engine.SimulationError as exc:
            print(f"FAIL: {exc}")
            return 1
        for item in summary["values"]:
            unit = f" {item['unit']}" if item["unit"] else ""
            print(f"  {item['label']}: {item['value']}{unit}")
        print(f"  exit={raw['meta']['exit_code']} run_id={raw['run_id']}")
        (SMOKE_DIR / f"summary-{mode}.json").write_text(
            json.dumps(
                {
                    "note": "SMOKE TEST with sourced fallback model, not instructor kit",
                    "run_id": raw["run_id"],
                    "values": summary["values"],
                    "provenance": summary["provenance"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    print("\nAll three analyses parsed real ngspice RAW output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
