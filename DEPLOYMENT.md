# การติดตั้ง OCR Workspace

หน้าเว็บ React และ API อยู่ใน container เดียว เปิดที่ `/` และเรียก API ผ่าน origin เดียวกัน จึงไม่ต้องตั้ง URL backend ในหน้าเว็บ และไม่ต้องมี Node.js บนเครื่องปลายทางเมื่อ build image แล้ว

## Docker Compose (CPU)

ต้องมี Docker Engine / Docker Desktop และ Compose v2 แนะนำให้จัดสรร RAM อย่างน้อย 8 GB และพื้นที่ว่างอย่างน้อย 10 GB สำหรับ image, ไลบรารี และโมเดล ทั้งนี้ RAM และเวลาประมวลผลจริงขึ้นกับเอกสาร

จากโฟลเดอร์โปรเจกต์:

```bash
docker compose up -d --build
docker compose logs -f ocr
```

เปิด [OCR Workspace](http://localhost:8090) หรือ [API Docs](http://localhost:8090/docs)

ครั้งแรกต้องใช้อินเทอร์เน็ตเพื่อ build image และดาวน์โหลดโมเดลประมาณ 2.5 GB เมื่อเริ่ม container หน้าเว็บจะบอกสถานะกำลังโหลด รอจนขึ้น **พร้อมใช้งาน** ก่อนเริ่มอ่าน โมเดล OpenThai 2.1 + runtime release v2.2.0 ถูกล็อก snapshot `c974dc7d18a4511a21988f4a1d12fad07ac16625` (nemotron-parse 3.5.0.post8) ไม่เปลี่ยนไปใช้รุ่นใหม่โดยอัตโนมัติ

โมเดลเก็บใน named volume `ocr-markdown_model-cache` และใช้ซ้ำเมื่อ restart หรือสร้าง container ใหม่ ตัว image ติดตั้งเฉพาะ runtime ของโมเดล ไม่บรรจุน้ำหนักโมเดล ไฟล์เอกสารและผล OCR ไม่ได้บันทึกเป็นประวัติบนเซิร์ฟเวอร์ ให้ดาวน์โหลดผลก่อนปิดหรือโหลดหน้าเว็บใหม่

```bash
# ตรวจว่า HTTP server ทำงาน และดูสถานะโมเดล
curl http://localhost:8090/health

# ดู container และ health check
docker compose ps

# หยุด โดยเก็บโมเดลไว้
docker compose down

# เปิดใหม่
docker compose up -d
```

Health check ตรวจว่า HTTP server ตอบและโมเดลไม่อยู่ในสถานะ error โดย `loading` และ `not_loaded` ยังถือว่า healthy ดูฟิลด์ `model_state` ใน `/health` เพื่อเช็กความพร้อมอ่านเอกสาร

อย่าใช้ `docker compose down -v` หากต้องการเก็บ cache โมเดล เพราะคำสั่งนี้ลบ named volume ด้วย หาก container ขึ้น unhealthy ให้ดู `docker compose logs --tail=100 ocr` หลังแก้สาเหตุแล้วใช้ `docker compose restart ocr` (restart policy ไม่ได้ restart เพียงเพราะ health check ขึ้น unhealthy)

## การตั้งค่า

ใช้ค่าเริ่มต้นได้โดยไม่ต้องมี `.env` หรือคัดลอกตัวอย่างแล้วปรับ:

```bash
cp .env.example .env
```

| ตัวแปร | ค่าเริ่มต้นใน Compose | ความหมาย |
|---|---|---|
| `OCR_PORT` | `8090` | พอร์ตบนเครื่อง host |
| `OCR_BIND_ADDRESS` | `127.0.0.1` | ที่อยู่บน host ที่เปิดรับ |
| `OCR_DEVICE` | `cpu` | อุปกรณ์ใน container; ใช้ GPU override สำหรับ NVIDIA |
| `OCR_PRELOAD` | `true` | โหลดโมเดลเมื่อเปิดบริการ |
| `OCR_LOCAL_FILES_ONLY` | `false` | `true` ใช้เฉพาะโมเดลที่ cache แล้ว |
| `OCR_MAX_FILE_MB` | `50` | ขนาดไฟล์สูงสุด |
| `OCR_MAX_PAGES` | `20` | จำนวนหน้าสูงสุดต่อคำขอ |
| `OCR_PDF_DPI` | `200` | ความละเอียดการแปลง PDF |
| `OCR_MAX_NEW_TOKENS` | `8744` | ขีดจำกัด token ต่อหน้า |

`OCR_HOST` ใน `.env.example` ใช้กับการรัน Python โดยตรง ส่วน container ฟัง `0.0.0.0:8090` ภายในเสมอและใช้ `OCR_BIND_ADDRESS` ควบคุมการเผยแพร่บน host ค่า model ID/revision ถูกกำหนดตอน build เพื่อให้ Python runtime ตรงกับโมเดล Compose ส่งค่า `OCR_MODEL_ID` และ `OCR_MODEL_REVISION` ไปเป็น build args `MODEL_ID` / `MODEL_REVISION` ให้อัตโนมัติ เปลี่ยนแล้วต้องใช้ `docker compose up -d --build` เพื่อให้ runtime และโมเดลตรงกัน ห้ามเปลี่ยนเฉพาะ environment ของ container ที่ build ด้วย runtime เก่า

หากย้าย cache จากเครื่องอื่น ให้คัดลอกทั้ง `HF_HOME` รวม shared blobs ด้วย ไม่ควรคัดลอกเฉพาะโฟลเดอร์ repository เพราะ Hugging Face บางรุ่นใช้ symlink ไปยัง blobs ที่แชร์ระหว่างโมเดล อีกทางเลือกคือคัดลอกไฟล์โดย dereference symlink ให้ครบก่อนนำเข้า volume

เมื่อโหลดโมเดลสำเร็จแล้ว สามารถตั้ง `OCR_LOCAL_FILES_ONLY=true` ใน `.env` และรัน `docker compose up -d` เพื่อสร้าง container ใหม่โดยใช้ cache เดิม หน้า GUI รวมฟอนต์และไฟล์ JavaScript ใน image และไม่โหลดจาก CDN ส่วน Swagger UI ที่ `/docs` ใช้ CDN ตามค่าเริ่มต้นของ FastAPI จึงต้องมีอินเทอร์เน็ตเพื่อโหลดหน้าคู่มือนั้น การ build ยังต้องใช้อินเทอร์เน็ตเว้นแต่มี image อยู่แล้ว

## Linux + NVIDIA GPU

ต้องมี NVIDIA driver และ [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) ที่ตั้งค่ากับ Docker แล้ว ตาม[แนวทาง GPU ของ Docker Compose](https://docs.docker.com/compose/how-tos/gpu-support/)

```bash
docker compose -f compose.yaml -f compose.gpu.yaml up -d --build
docker compose -f compose.yaml -f compose.gpu.yaml logs -f ocr
```

ไฟล์ override จอง NVIDIA GPU หนึ่งตัว ตั้ง `OCR_DEVICE=cuda` และเปลี่ยน PyTorch wheel index เป็น CUDA 13.0 ต้องใช้ driver ที่รองรับ CUDA รุ่นนี้ หากต้องใช้รุ่น CUDA อื่นให้แก้ `TORCH_INDEX_URL` ให้ตรงกับ wheel ที่ PyTorch รองรับ ต้อง build ใหม่เมื่อสลับ CPU/GPU

ใช้ `-f compose.yaml -f compose.gpu.yaml` กับคำสั่งจัดการ stack นี้ทุกครั้ง ไม่ตั้ง `platform` บังคับไว้ใน Compose เพื่อให้ CPU build รองรับสถาปัตยกรรม host ตาม wheel ที่ upstream มีให้ ส่วน GPU override มีไว้สำหรับเครื่อง NVIDIA ที่รองรับเท่านั้น

## Mac Apple silicon

ชุด Compose นี้ใช้ CPU บน Mac และอาจช้ากว่าการรัน Python บน macOS โดยตรง เพราะ PyTorch ใน Linux container ไม่เข้าถึง Apple MPS ได้ [Docker ระบุการ passthrough GPU แบบนี้สำหรับ Windows WSL2](https://docs.docker.com/desktop/features/gpu/)

หากต้องการใช้ GPU ของ Mac ให้รัน API ตาม README และ build หน้าเว็บครั้งเดียว:

```bash
npm ci --prefix frontend
npm run build --prefix frontend
scripts/run.sh
```

เปิด `http://localhost:8090` ได้เหมือน Docker โดย FastAPI จะเสิร์ฟ `frontend/dist` อัตโนมัติ รีสตาร์ท API หลัง build ครั้งแรกหากเปิด API อยู่ก่อนแล้ว

## เปิดให้เครื่องอื่นใน LAN

ตั้ง `OCR_BIND_ADDRESS=0.0.0.0` ใน `.env` แล้วรัน `docker compose up -d` จากนั้นเข้า `http://<IP-ของเซิร์ฟเวอร์>:8090` จากเครื่องอื่นได้ หน้าเว็บกับ API อยู่ origin เดียวกันจึงไม่ต้องแก้ CORS

ระบบยังไม่มี authentication เหมาะกับเครื่องส่วนตัวหรือ LAN ที่ไว้ใจได้ ถ้าจะเปิดใช้งานผ่านอินเทอร์เน็ตควรอยู่หลัง reverse proxy ที่มี HTTPS และ authentication ตั้ง upload limit อย่างน้อยเท่ากับ `OCR_MAX_FILE_MB` บวก multipart overhead และตั้ง timeout ให้ยาวพอสำหรับเอกสารหลายหน้า API ปัจจุบันคืนผลเมื่ออ่านครบช่วงหน้าที่เลือก หน้าเว็บแสดงเวลารอ ไม่แสดงเปอร์เซ็นต์รายหน้า

## ย้ายไปอีกเครื่อง / ส่งมอบ image

วิธีปกติคือคัดลอก source โปรเจกต์ (ไม่ต้องคัดลอก `.venv`, `node_modules`, เอกสารส่วนตัว หรือ outputs) ไปเครื่องปลายทางแล้วใช้ `docker compose up -d --build` เครื่องปลายทางจะดาวน์โหลดโมเดลลง volume ของตัวเองในครั้งแรก

ถ้าจะส่ง image สำเร็จรูป ให้ build สำหรับสถาปัตยกรรมปลายทาง เช่น Linux x86_64:

```bash
docker buildx build --platform linux/amd64 -t ocr-workspace:0.2.0 --load .
docker save -o ocr-workspace-amd64.tar ocr-workspace:0.2.0
```

เครื่องปลายทาง:

```bash
docker load -i ocr-workspace-amd64.tar
docker volume create ocr-model-cache
docker run -d --name ocr-workspace --restart unless-stopped --init \
  -p 127.0.0.1:8090:8090 \
  -e OCR_DEVICE=cpu \
  -v ocr-model-cache:/home/ocr/.cache/huggingface \
  ocr-workspace:0.2.0
```

ยังต้องเชื่อมต่ออินเทอร์เน็ตครั้งแรกเพื่อโหลดน้ำหนักโมเดล หากเครื่องปลายทางออฟไลน์ ต้องเตรียมและย้าย cache โมเดลลง volume ให้ครบล่วงหน้า และตั้ง `OCR_LOCAL_FILES_ONLY=true` ดูเงื่อนไขใบอนุญาต upstream ใน `THIRD_PARTY_NOTICES.md` ก่อนแจกจ่ายน้ำหนักโมเดลต่อ

## พัฒนาหน้าเว็บ

ใช้ Node.js 22.12+ หรือ 24 และติดตั้ง Python API ตาม README:

```bash
# terminal 1
scripts/run.sh

# terminal 2
npm ci --prefix frontend
npm run dev --prefix frontend
```

เปิด URL ที่ Vite แสดง (ปกติ `http://localhost:5173`) ตัว dev server ส่ง `/v1`, `/health`, `/docs` และ `/openapi.json` ไปที่ `127.0.0.1:8090`

```bash
npm run build --prefix frontend
npm test --prefix frontend
.venv/bin/python -m pytest -q
```

Preview ใช้ Markdown renderer ร่วมกับ HTML sanitizer เพื่อรองรับตารางที่มี `rowspan` / `colspan` โดยกรอง scripts, event handlers, iframe และ URL ที่ไม่ปลอดภัย รูปในผล OCR ไม่ถูกโหลดจาก URL ภายนอก ส่วน JSON และ Markdown ต้นฉบับยังคงไว้สำหรับดาวน์โหลด

## ผลตรวจชุด deploy เดิม (โมเดล 2.0)

ตรวจบน Docker Desktop บน Mac Apple silicon: build image สำเร็จ, API tests 14 รายการผ่านภายใน image, frontend tests 3 รายการผ่าน และตรวจ flow หน้าเว็บบน Chromium ทั้ง desktop/mobile โมเดลโหลดจาก cache ออฟไลน์ได้ และอ่าน `samples/thai_table.png` สำเร็จหนึ่งหน้าเป็น Markdown พร้อม HTML table ใช้เวลารวม 271.5 วินาทีบน CPU ใน container (Docker จัดสรร 4 vCPU / RAM ประมาณ 5.8 GiB) เวลานี้เป็นเอกสารตัวอย่างหนึ่งไฟล์ ไม่ใช่ค่ารับประกันต่อหน้า สำหรับ NVIDIA GPU ตรวจรูปแบบ Compose แล้ว แต่ยังไม่ได้ทดสอบบนฮาร์ดแวร์ NVIDIA จริง

## อัปเกรดจาก OpenThai 2.0

หากมี `.env` เดิม ให้แก้สองค่านี้ด้วย มิฉะนั้น Compose จะใช้ค่าที่ล็อกเดิมจากไฟล์นั้น:

```dotenv
OCR_MODEL_ID=iapp/OpenThai2.1-OCR-Markdown-20261118
OCR_MODEL_REVISION=c974dc7d18a4511a21988f4a1d12fad07ac16625
```

1. ตั้ง `OCR_LOCAL_FILES_ONLY=false` จนกว่าจะโหลด snapshot ใหม่ครบ รุ่นเดิมใน cache ไม่ใช่ weights รุ่น 2.1
2. ใช้ `docker compose up -d --build` เพื่ออัปเดต runtime จาก snapshot เดียวกันและโหลดโมเดลใหม่ลง volume เดิม ไม่ต้องลบ volume
3. ตรวจ `/health` และ `/v1/info`: ต้องเป็น model ID/revision ใหม่, `runtime_version=3.5.0.post8`, `version=0.2.0` และ `model_state=ready`
4. ทดสอบเอกสารจริงและตรวจผล โดยเฉพาะหัว/ท้ายกระดาษที่ไม่รวมใน Markdown, สูตร `$$...$$` และการ normalize “ำ”
5. เมื่อ cache ใหม่ครบแล้วจึงตั้ง `OCR_LOCAL_FILES_ONLY=true` และใช้ `docker compose up -d`

สำหรับ native Mac ใช้ `scripts/install.sh` ใหม่ก่อนเปิด `scripts/run.sh` สคริปต์อ่าน model ID/revision ตาม Settings ของ API และติดตั้ง runtime ใหม่ด้วย ส่วนไฟล์ `requirements.lock.txt` เป็น snapshot ของ native environment ไม่ใช่รายการสำหรับติดตั้งแพ็กเกจโมเดลจาก PyPI

Dewarping ปิดอยู่ตามคำแนะนำต้นทาง ไม่ได้ติดตั้ง ONNX/opencv หรือโหลดโมเดล dewarp เพิ่ม ดู [References และคำขอบคุณใน README](README.md#references) สำหรับเครดิต iApp/OpenThai และ NVIDIA Base Model

## ผลตรวจอัปเกรด OpenThai 2.1 (18 พ.ย. 2569)

Image/API v0.2.0 รันด้วย OpenThai 2.1 weights ที่ snapshot `c974dc7d18a4511a21988f4a1d12fad07ac16625` และ `nemotron-parse 3.5.0.post8` จาก release v2.2.0 โหลด cache ออฟไลน์ได้ `pip check` ผ่าน และ container healthy ทดสอบ Python 19 รายการผ่านใน image และ native environment, frontend 3 รายการผ่าน, ตรวจ GUI desktop/mobile และ Swagger UI ใน Chromium แล้ว

หน้าว่างคืนผลว่างใน 436 ms; `samples/thai_table.png` สำเร็จหนึ่งหน้าใน 275.5 วินาทีบน Docker CPU 4 vCPU / RAM ประมาณ 5.8 GiB พร้อมตรวจตาราง การ normalize “ำ” และการตัด `rowspan="1"` / `colspan="1"` ค่าเหล่านี้เป็นผลของไฟล์ตัวอย่าง ไม่รับประกันเวลางานอื่น ยังไม่ได้ทดสอบบน NVIDIA GPU จริง ดู [ผลตรวจและ References](README.md)
