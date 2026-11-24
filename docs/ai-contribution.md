# AI สร้าง/แก้ส่วนใด และนักศึกษาตรวจอะไรเอง (3–5 บรรทัด)

1. AI สร้างโครง Flask (`app.py`, `dc_bias.py`, `spice_engine.py`, template/CSS/JS) และ adapter
   ที่เรียก ngspice ด้วย `subprocess.run([...])` แบบ argument list, timeout และ cwd แยกต่อรอบ
2. AI แก้บั๊กจริง 3 จุดที่เจอขณะรัน: Jinja `result.values`, ngspice ค้างจาก stdin,
   path มีช่องว่าง + RAW parser แบบ complex; ไม่ได้แก้สมการ `dc_bias.py`
3. AI ใช้ Skill `impeccable` ตรวจ critique → polish → audit และเก็บภาพก่อน/หลังใน `captures/`
4. นักศึกษาตรวจเอง: ค่าที่กรอก/หน่วย/ช่วง, ป้ายแหล่งที่มา analytical vs SPICE,
   ผล B1–B8 ใน `docs/validation.md`, และยืนยันว่าโมเดลที่ใช้ยังไม่ใช่ Starter Kit อาจารย์
5. นักศึกษาต้องแทนที่ `models/bjt.model` ด้วยโมเดลอาจารย์แล้วรันซ้ำก่อนส่ง (ดู `docs/model-provenance.md`)
