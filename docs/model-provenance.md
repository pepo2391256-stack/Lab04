# BJT model provenance (ที่มาของโมเดล)

## สิ่งที่ตรวจแล้ว
- อ่านใบงาน `Lab04_BJT_Amplifier_Simulator_2-2569.html` บรรทัด 420, 435, 462:
  ผู้สอนระบุว่า Starter Kit **“ถ้าผู้สอนแจก”** และให้ใช้โมเดลที่ Starter Kit ระบุชื่อ/พารามิเตอร์
- ค้นหาไฟล์ `.model`, `.mod`, `.lib`, `.cir` ใน `C:\Users\B6822149\Downloads` และในโฟลเดอร์ผู้ใช้
  (ยกเว้นโฟลเดอร์โปรเจกต์และ ngspice ที่ติดตั้งเอง) — **ไม่พบ Instructor Starter Kit**
- ใน `Downloads` มีเฉพาะไฟล์ติดตั้ง OpenCode / GitHub Desktop และใบงาน HTML

## สิ่งที่ใช้แทนเพื่อตรวจ pipeline (ไม่ใช่ผลส่งงาน)
- ไฟล์: `models/bjt.fallback.model` → คัดลอกเป็น `models/bjt.model`
- ต้นฉบับ: ngspice 47 official distribution  
  `Spice64/examples/tclspice/tcl-testbench1/PN2222.mod`  
  <https://sourceforge.net/projects/ngspice/files/ng-spice-rework/47/>
- คัดลอกพารามิเตอร์จากต้นฉบับ **ไม่ได้เดาค่า**; มีบรรทัด
  `FALLBACK_MODEL_NOT_INSTRUCTOR` อยู่ในไฟล์
- แอปตรวจ marker นี้แล้วแสดง badge เตือนในหน้า `/` และ warning ในทุกผล `/simulate`

## ข้อจำกัดที่ต้องพูดตามตรง
ผล `.op/.ac/.tran` ที่บันทึกใน `docs/validation.md` ใช้ PN2222 จากตัวอย่าง ngspice
**ไม่ใช่โมเดลของอาจารย์** จึงใช้ยืนยันว่า netlist → subprocess → RAW → graph ทำงานจริงเท่านั้น
ก่อนส่งงานจริงต้องแทนที่ `models/bjt.model` ด้วย `.model` จาก Starter Kit แล้วรัน B1–B8 ซ้ำ

## วิธีแทนที่
```bat
copy /Y C:\path\to\instructor\model.mod models\bjt.model
python -m unittest discover -s tests -t .
python -m flask --app app run
```
ถ้าโมเดลอาจารย์ยังมี marker `INSTRUCTOR_MODEL_REQUIRED` อยู่ แอปจะปฏิเสธการรันและแจ้ง error
ตามที่ `AGENTS.md` ข้อ 5 กำหนด
