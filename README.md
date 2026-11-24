# ENG29 2121 — Lab 04: BJT Amplifier Simulator v1

ต่อยอด Flask Web App จาก Lab 3 ให้จำลอง **Common-Emitter Voltage Divider Amplifier**
ด้วย **ngspice จริง**: DC operating point (`.op`), AC frequency response (`.ac`)
และ transient waveform (`.tran`) โดยยังคง DC Bias 3 แบบเดิมไว้

URL ที่ใช้เหมือนแลปที่แล้ว: **http://127.0.0.1:5000/**

## ขอบเขต
- คง `dc_bias.py` และเส้นทาง analytical Fixed / Emitter / Voltage Divider เดิม
- เพิ่ม `spice_engine.py` สำหรับสร้าง netlist, เรียก ngspice แบบ batch และอ่าน raw จริง
- วงจรอ้างอิง: CE voltage divider, NPN, **ไม่มี** emitter bypass capacitor ใน baseline
- Vin วัดที่ node `in` (ก่อน CIN), Vout วัดที่ node `out` (บน RL หลัง COUT)
- ผล analytical กับผล SPICE แสดงแยกป้ายที่มาเสมอ

## Prerequisites
- Python 3.x, Git
- Flask (ดู `requirements.txt`)
- ngspice ที่เรียกได้จาก PATH ของ environment เดียวกับที่รัน Flask
- **BJT model จาก Starter Kit ของอาจารย์** (ห้ามเดาพารามิเตอร์เอง)

## Setup
```bat
git status
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m flask --app app run
```

หรือรันโดยตรง:

```bat
python app.py
```

เปิด <http://127.0.0.1:5000/> ถ้าพอร์ต 5000 ถูก process อื่นครอง ให้หยุด process นั้นก่อน
เพราะใบงานต้องการ URL เดิมจาก Lab 3

## ngspice แบบ portable (ถ้าไม่มีใน PATH)
```bat
set NGSPICE_PATH=C:\path\to\ngspice.exe
python -m flask --app app run
```
`spice_engine.py` อ่าน `NGSPICE_PATH` ก่อน แล้วค่อย fallback หา `ngspice` ใน PATH

## เตรียม BJT model
```bat
copy models\bjt.model.example models\bjt.model
```

แล้วแก้ `models/bjt.model` ด้วยโมเดลที่อาจารย์แจกเท่านั้น ต้องลบ marker
`INSTRUCTOR_MODEL_REQUIRED` ออก ถ้ายังเป็นแม่แบบอยู่ แอปจะปฏิเสธการรันและแจ้ง error
(ไม่มีการสร้างผลจำลองขึ้นมาเอง)

**สถานะตอนนี้:** `models/bjt.model` คือ `bjt.fallback.model` (PN2222 จาก example ของ ngspice 47)
ใช้เพื่อตรวจว่า `.op/.ac/.tran` รันจริงเท่านั้น หน้าเว็บมี badge เตือนและทุกผลมี warning
ว่า **ยังไม่ใช่ Starter Kit ของอาจารย์** — ก่อนส่งงานให้แทนที่ด้วยโมเดลจากอาจารย์

## โครงสร้างไฟล์
```text
app.py                     # routes: /, /analytical, /simulate, /artifact/...
dc_bias.py                 # analytical DC bias จาก Lab 3 (ไม่แก้สมการเดิม)
spice_engine.py            # validate -> netlist -> subprocess -> parse -> chart
templates/index.html       # ฟอร์ม 2 เส้นทาง + ผล + กราฟ + provenance
static/style.css           # UI
static/app.js              # สลับ panel/mode เฉพาะ UI
models/bjt.model.example   # แม่แบบโมเดล (ต้องแทนที่ก่อนรันจริง)
runs/<run_id>/             # netlist/log/raw/meta ต่อรอบ (.gitignore แล้ว)
docs/validation.md         # บันทึก B1–B8 (port 5000, หลัง polish)
docs/model-provenance.md   # ที่มาโมเดล + ข้อจำกัด Starter Kit
docs/impeccable-critique.md # ผล critique 21/40 + priority issues
docs/impeccable-audit.md   # ผล audit 18/20 + detector/Lighthouse
docs/ai-contribution.md    # สรุป 3–5 บรรทัด AI ทำอะไร / นักศึกษาตรวจอะไร
captures/final-*.jpeg      # screenshot B1–B8 แบบ full-page รอบสุดท้าย
captures/word/*.png        # ชุดภาพ element-only ขนาดพอดีสำหรับ Microsoft Word
captures/impeccable-after/ # desktop 1440×900 + phone 390×844 หลัง polish
tests/                     # unit checks สำหรับ dc_bias และ parser
ui-preview.html            # หน้าเทสการกรอกค่าแบบไม่มี backend (UI only)
docs/ui-preview-tests.md   # บันทึกผลเทส UI + screenshot
```

## การรันและ error path
- `/analytical` ใช้ `dc_bias.py` ผลเป็น analytical reference
- `/simulate` ตรวจ input → สร้าง netlist → `subprocess.run([...], timeout=60, cwd=runs/<run_id>)`
  → อ่าน `run.log` และ `run.raw` → แสดงค่าพร้อมหน่วยและ SVG ที่สร้างจากข้อมูลจริง
- หาก ngspice ไม่พบ, model ยังเป็นแม่แบบ, exit code ไม่เป็นศูนย์, timeout, raw ว่าง
  หรือ input ผิด (เช่น RE = 0) หน้าจะแสดง error และ **ไม่มีกราฟ/ค่า success ปลอม**
- ไฟล์หลักฐานต่อรอบเปิดได้จากลิงก์ในผล: `netlist.cir`, `run.log`, `run.raw`, `meta.json`

## ตรวจสอบ
```bat
python -m unittest discover -s tests -t .
python tools/smoke_test.py
```
`tools/smoke_test.py` รันทั้ง 3 analysis ด้วยโมเดลสำรองจาก example ของ ngspice
และเขียน `smoke_runs/summary-*.json` — **ไม่ใช่ผลส่งงาน** ใช้พิสูจน์ว่า pipeline ทำงานจริง

จากนั้นรัน B1–B8 ใน browser ที่ <http://127.0.0.1:5000/> และกรอกผลจริงลง
`docs/validation.md` ห้ามเปลี่ยน `NOT RUN` เป็น `PASS` หาก tool ไม่ได้รันจริง

## ผลตรวจล่าสุด

- `python -m unittest discover -s tests -t .` → 8 tests OK
- `python tools/smoke_test.py` → `.op/.ac/.tran` อ่าน RAW จริงครบ
- B1–B8 → **PASS ทั้ง 8 case** (desktop + mobile) ดู `docs/validation.md`
- Impeccable critique → polish → audit → **18/20 Excellent** ดู `docs/impeccable-audit.md`
- Lighthouse: accessibility 1.00, best practices 1.00, SEO 1.00; console error 0
- ยังติดสองอย่างที่ต้องผู้ใช้ช่วย: (1) โมเดล Starter Kit ของอาจารย์ (2) GitHub repo/credential สำหรับ push

## หมายเหตุ
- ngspice เป็นโปรแกรมภายนอก ไม่ใช่ `pip install` แล้วจบ
- ไม่ใช้ `shell=True`; argument เป็น list; มี `timeout`; แยก working directory ต่อรอบ
- อย่า commit `.venv/`, `.env`, token หรือไฟล์ run ชั่วคราว (`runs/` ถูก ignore แล้ว)
