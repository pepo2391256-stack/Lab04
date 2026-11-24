# AGENTS.md — Lab 04 BJT Amplifier Simulator

## 基本原则สำหรับ AI/ผู้ช่วย
1. รักษา `dc_bias.py` และผล Lab 3 ทั้งสามโหมดไว้ ห้ามลบหรือเขียนทับโดยไม่ได้รับอนุมัติ
2. ห้ามแต่งตัวเลข DC/gain/fL/fH/waveform ขึ้นเอง และห้ามเปลี่ยน error เป็น success
3. ค่าที่กรอกต้อง validate ก่อนสร้าง netlist: เป็นตัวเลข, มีหน่วย, ช่วงบวก, RE ต้องมากกว่า 0
4. เรียก ngspice ด้วย `subprocess.run([...])` แบบ argument list เท่านั้น ห้าม `shell=True`, ต้องมี `timeout` และ `cwd` แยกต่อรอบ
5. ใช้ BJT model จาก Starter Kit ของอาจารย์เท่านั้น ถ้า `models/bjt.model` ยังเป็นแม่แบบ (`INSTRUCTOR_MODEL_REQUIRED`) ต้องแจ้ง error
6. แยกป้ายผลให้ชัด: `dc_bias.py` = analytical reference, `spice_engine.py`/ngspice = simulation result
7. ถ้า ngspice ไม่พบ, exit code ไม่เป็นศูนย์, timeout หรือ raw ว่าง ต้องคืน error state และไม่แสดงกราฟเก่า
8. เปลี่ยน UI ได้เฉพาะหลัง critique/polish ที่ผู้เรียนอนุมัติ ห้ามแตะสูตร น netlist หรือ parser เพื่อความสวยงาม
9. บันทึก B1–B8 ใน `docs/validation.md` ด้วย PASS/FAIL/NOT RUN ตามสิ่งที่ tool ทำจริงเท่านั้น
10. เซิร์ฟที่ `http://127.0.0.1:5000/` ตาม Lab 3; ถ้าพอร์ตถูก process อื่นครอง ให้หยุด process นั้นก่อนรัน Flask
