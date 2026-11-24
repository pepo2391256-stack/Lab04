# UI Preview Test Log — เฉพาะหน้าฟอร์ม

ไฟล์ที่เทส: `ui-preview.html` (ผ่าน Browser tool)
**ไม่ใช่ผล ngspice / ไม่ใช่ผลคำนวณจริง** — ปุ่มในหน้านี้เพียง echo ค่าที่กรอก
สาเหตุที่ไม่รันแอปจริง: ไม่พบ Python/ngspice ใน environment และพอร์ต 5000 ถูก PID 4 (System/HTTP.sys) ครองอยู่

| # | Test | ค่าที่ใส่ | ผลที่เห็น | Screenshot |
|---|---|---|---|---|
| 1 | SPICE fixture เริ่มต้น | analysis=tran, VCC 12 V, R1 100k, R2 22k, RC 2.2k, RE 1k, RL 10k, Cin/Cout 10µF, 10 mV @ 1 kHz | echo แสดงครบทุกค่าตาม fixture | `captures/test1-default-spice.jpeg` |
| 2 | เปลี่ยน source และ RE | analysis=ac, RE 1.5k, amplitude 20 mV, frequency 2 kHz | echo แสดงค่าใหม่ทั้ง 3 จุด | `captures/test2-changed-source.jpeg` |
| 3 | Invalid input | analysis=dc, RE = 0 | echo แจ้ง “RE ต้องมากกว่า 0 — engine จะปฏิเสธก่อนสร้าง netlist” | `captures/test3-invalid-re0.jpeg` |
| 4 | Analytical panel | bias=divider, VCC 12 V, β 100, VBE 0.7 V, R1 100k, R2 22k, RC 2.2k, RE 1k | echo แสดงชุดค่า Lab 3 | `captures/test4-analytical-divider.jpeg` |

## สถานะจริงตามใบงาน
B1–B8 ยังเป็น `NOT RUN` ใน `docs/validation.md` เพราะยังไม่ได้รัน Flask + ngspice + Playwright MCP กับแอปจริง
หน้า UI preview นี้ใช้เพื่อตรวจเฉพาะการกรอกข้อมูลและการสลับ panel เท่านั้น
