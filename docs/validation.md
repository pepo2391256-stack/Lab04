# Lab 04 Validation Record (ผลรันจริง)

URL ที่ใช้เทส: **http://127.0.0.1:5000/** (ตรงตาม Lab 3 ทุกประการ)  
รันเซิร์ฟเวอร์ด้วย `NGSPICE_PATH` ชี้ไปยัง ngspice 47 portable และ `PYTHONIOENCODING=utf-8`

## สภาพแวดล้อมที่ทำให้รันได้

- Python 3.12.10 + Flask 3.1.3
- ngspice 47 portable (`ngspice-47_64.7z`) ตั้งผ่าน `NGSPICE_PATH`
- แก้บั๊กจริง: `stdin=DEVNULL` (ngspice ค้าง), path ไม่มีช่องว่างตอนรัน + also copy กลับ, RAW parser รองรับ complex และบรรทัดค่าต่อเนื่อง
- `check_ngspice()` ถูก cache และลด timeout เหลือ 1 วินาที → GET หน้าแรกเร็วขึ้น (วัดจริง ~1.04 s)
- **BJT model ที่ใช้เทสคือ `models/bjt.fallback.model` → `models/bjt.model`** (PN2222 จาก official example ของ ngspice 47) **ไม่ใช่ Starter Kit ของอาจารย์** หน้าเว็บแสดง badge เตือนและทุกผล `/simulate` มี warning ทุกครั้ง

## ผล B1–B8 (รันซ้ำหลัง Impeccable polish ที่พอร์ต 5000)

| Case | Method | Input | ผลที่เห็นจริง | Evidence | Status |
|---|---|---|---|---|---|
| B1 Regression | Browser `/analytical` 3 mode | Divider 12 V, β100, VBE 0.7, 100k/22k/2.2k/1k · Fixed RB470k · Emitter RB470k | Divider VB 1.9422 V, VE 1.2422 V, VC 9.2943 V, IC 1.2299 mA · Fixed IC 2.4043 mA · Emitter IC 1.9790 mA; card/field แต่ละโหมดสลับถูกต้อง | `captures/final-B1-divider.jpeg`, `final-B1-fixed.jpeg`, `final-B1-emitter.jpeg` | **PASS** |
| B2 DC SPICE | Browser `/simulate` mode dc | R1 100k, R2 22k, RC 2.2k, RE 1k, RL 10k | VB 2.016 V, VE 1.364 V, VC 9.017 V, VCE 7.653 V, IC 1.356 mA จาก RAW จริง; run id `20261124T054735Z-dbf7bc`, exit 0 | `captures/final-B2-dc.jpeg`, `runs/20261124T054735Z-dbf7bc/` | **PASS** |
| B3 Change RE | เปลี่ยน RE 1k→1.5k แล้ว dc ซ้ำ | RE เดียว | IC 1.356 → 0.9388 mA, VCE 7.653 → 8.518 V (อ่านจาก RAW รอบใหม่ run id `20261124T054737Z-64570b`) | `captures/final-B3-re.jpeg`, `runs/20261124T054737Z-64570b/` | **PASS** |
| B4 AC | Browser `/simulate` mode ac | `.ac dec 20 1 10MEG`, 10 mV | gain peak 1.758; กราฟ Frequency (Hz, log) + gain + phase (°); fL/fH = `not determined in sweep range`; run id `20261124T054738Z-c85f75` | `captures/final-B4-ac.jpeg`, `runs/20261124T054738Z-c85f75/` | **PASS** |
| B5 Transient | Browser `/simulate` mode tran | 10 mV peak @ 1 kHz | Vin peak 10 mV, Vout p-p 0.03515 V, span 5 ms, กลับเฟสตาม CE; run id `20261124T054740Z-cf19ce` | `captures/final-B5-tran.jpeg`, `runs/20261124T054740Z-cf19ce/` | **PASS** |
| B6 Change Source | เปลี่ยน 10 mV/1 kHz → 20 mV/2 kHz แล้ว tran ซ้ำ | amplitude + frequency | Vin 10→20 mV, Vout p-p 0.03515→0.07031 V, span 5→2.5 ms; run id `20261124T054741Z-b5a8ca` | `captures/final-B6-source.jpeg`, `runs/20261124T054741Z-b5a8ca/` | **PASS** |
| B7 Invalid / Fail | ใส่ RE=0 ใน `/simulate` | RE = 0 | error `RE ต้องอยู่ในช่วง 1e-06–10000 kΩ (ต้องมากกว่า 0) (ได้รับ '0')`; ไม่มี result, ไม่มี svg | `captures/final-B7-invalid.jpeg` | **PASS** |
| B8 UI | Browser 1440×900 + Puppeteer 390×844 + Impeccable detector | หน้า `/` และผลทุก state | แกน/หน่วย/ป้ายที่มา/analysis mode/link evidence อ่านได้; ไม่มี horizontal overflow; detector `[]` ทั้ง desktop และ phone; Lighthouse accessibility 1.00, best practices 1.00, SEO 1.00; console error 0 | `captures/impeccable-after/1440x900.png`, `390x844.png`, `captures/final-B4-ac.jpeg`, `docs/impeccable-audit.md` | **PASS (desktop + mobile)** |

## Impeccable workflow

1. `impeccable context --target templates/index.html` → `SCOPED_EXISTING_ALLOWED` (ปรับของเดิมได้)
2. Critique แบบ dual-agent (Assessment A + B) → 21/40; snapshot ต้นฉบับอยู่ที่ `.impeccable/critique/2026-11-24T05-42-31Z__templates-index-html.md` และสำเนาใน `docs/impeccable-critique.md` (ปิดแล้วหลังแก้ครบ)
3. Polish จริง: cache ngspice probe, fieldset แยก DC/coupling/source, `type=number` + `min/step/required`, plan diagram, `aria-live`, loading state, result-ready/run id, ลบ side-tab/straggler
4. Detector หลังแก้: `[]` ที่ 1440×900 และ 390×844; `captures/impeccable-after/` มีภาพก่อน/หลัง
5. Audit → 18/20 Excellent; report อยู่ที่ `docs/impeccable-audit.md` และ `.impeccable/audit/`

## ภาพสำหรับ Microsoft Word

เพื่อให้ส่งอาจารย์ได้สะดวก มีชุดภาพ **element-only** (ไม่ใช่ full-page ยาว ๆ) อยู่ใน `captures/word/`
ขนาดแต่ละภาพโดยประมาณ **1296 × 290–636 px** → ใส่ใน Word ได้พอดี:

- `word-B1-divider.png`, `word-B1-fixed.png`, `word-B1-emitter.png`
- `word-B2-dc.png`, `word-B3-re.png`
- `word-B4-ac-values.png`, **`word-B4-gain.png`**, **`word-B4-phase.png`**
- `word-B5-tran-values.png`, **`word-B5-waveform.png`**
- `word-B6-source-values.png`, **`word-B6-waveform.png`**
- `word-B7-invalid.png`

สำเนาบน Desktop: `C:\Users\B6822149\Desktop\Lab04_Screenshots\` และ ZIP `Lab04_Word_Images.zip`

## หมายเหตุความตรงไปตรงมา

- ทุกตัวเลขอ่านจากหน้าเว็บที่รัน ngspice จริง ไม่ได้ hard-code; `netlist.cir`, `run.log`, `run.raw`, `meta.json` อยู่ใน `runs/<run_id>/` ทุกครั้ง
- ผล DC ของ ngspice ไม่เท่ากันทุกหลักกับ analytical ตามที่ใบงานระบุ (model คนละสมมติฐาน)
- โมเดลยังเป็น fallback จาก example ของ ngspice → **ยังใช้ส่งงานไม่ได้จนกว่าแทนที่ด้วย Starter Kit ของอาจารย์แล้วรัน B1–B8 ซ้ำ**
- Git: ชุด commit `c2b42b6`, `0babfd5`, `9ed99a4`; mirror ท้องถิ่น `lab04-git-remote.git` ใช้เป็น evidence ชั่วคราว; **ยัง push GitHub ไม่ได้เพราะยังไม่มี credential/repo ของผู้ใช้**
- ตรวจเพิ่มเติม: `python -m unittest discover -s tests -t .` → 8 tests OK; `python tools/smoke_test.py` → `.op/.ac/.tran` อ่าน RAW จริงครบ
