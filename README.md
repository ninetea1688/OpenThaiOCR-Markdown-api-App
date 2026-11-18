# OCR Markdown API

API บนเครื่องสำหรับอ่านเอกสารภาษาไทย (PDF หรือรูปภาพ) ออกมาเป็น Markdown โดยตารางออกมาเป็น HTML ที่คง `rowspan` / `colspan` ไว้ ใช้โมเดลเปิด [iapp/OpenThai2.1-OCR-Markdown-20261118](https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118) ของ iApp Technology ซึ่งปรับจาก NVIDIA Nemotron 3.5 Parse

ทำเป็นบริการแยก เพื่อให้หลายโปรเจกต์ เช่น GovHR หรือเครื่องมือจัดการเอกสาร เรียกใช้ร่วมกันผ่าน HTTP ได้ **เอกสารทั้งหมดประมวลผลบนเครื่องนี้ ไม่ส่งออกไปข้างนอก** การควบคุมสิทธิ์เข้าถึงและการดูแลข้อมูลยังเป็นหน้าที่ของผู้ติดตั้ง (ใช้อินเทอร์เน็ตตอนติดตั้ง/ดาวน์โหลดโมเดล และตั้งโหมดออฟไลน์ได้หลัง cache ครบ)

มีบริการคู่กันคือ [OCR Text API](../ocr-text-api/README.md) ที่พอร์ต 8091 สำหรับอ่านข้อความล้วนแบบเร็วบน CPU

อัปเดตโมเดลและเอกสารวันที่ 18 พ.ย. 2569 · API v0.2.0

---

## หน้า GUI และ Docker Compose

มีหน้าเว็บ **OCR Workspace** (React + TypeScript + Vite) สำหรับอัปโหลด PDF/รูปภาพ เลือกช่วงหน้า ดูต้นฉบับเทียบผล OCR สลับ Preview / Markdown / JSON และดาวน์โหลดผล โดย Preview รองรับตารางรวมเซลล์

```bash
docker compose up -d --build
```

เปิด [หน้าใช้งาน](http://localhost:8090) รอโมเดลขึ้นพร้อมใช้งานในครั้งแรก ค่าเริ่มต้นใช้ CPU และเก็บโมเดลใน named volume; สำหรับ Linux NVIDIA มี `compose.gpu.yaml` เพิ่มให้

ดูขั้นตอนติดตั้ง ตั้งค่า LAN, GPU, offline และวิธีพัฒนาหน้าเว็บใน [DEPLOYMENT.md](DEPLOYMENT.md) บน Mac ถ้าต้องการใช้ Apple GPU ให้รัน API บน macOS โดยตรงแล้ว build หน้าเว็บตามคู่มือ

---

## รุ่นโมเดลที่ใช้และสิ่งที่เปลี่ยน

- โมเดล: **OpenThai 2.1 OCR Markdown** — `iapp/OpenThai2.1-OCR-Markdown-20261118`
- Snapshot: `c974dc7d18a4511a21988f4a1d12fad07ac16625` ตรวจจาก release **v2.2.0** ของต้นทางเมื่อ 18 พ.ย. 2569
- Runtime: **nemotron-parse 3.5.0.post8** ติดตั้งจาก snapshot เดียวกับโมเดล ไม่ใช่แพ็กเกจชื่อเดียวกันบน PyPI
- Release v2.2.0 ใช้ weights ของ 2.1 และเพิ่มตัวเลือก dewarping; โปรเจกต์นี้ปิด dewarping ตามคำแนะนำต้นทาง และใช้ Transformers เหมือนเดิม ไม่ได้เปลี่ยนไปใช้ GGUF/llama.cpp

ผลลัพธ์แบบใหม่: สูตรใช้ LaTeX `$$...$$`; หัว/ท้ายกระดาษยังอยู่ใน `blocks` แต่ไม่อยู่ใน Markdown รวม; หน้าว่างคืนข้อความว่าง; “ำ” ใน Markdown และ `blocks[].content` เป็น U+0E33; ตารางไม่ใส่ `rowspan="1"` / `colspan="1"` แต่ยังเก็บเซลล์รวมจริงไว้ ค่า `blocks[].text` และ `raw` ยังเป็นผลทำนายดิบ จึงอาจต่างจากข้อความที่จัดรูปแบบแล้ว GUI แสดงสูตรเป็น source LaTeX

ตรวจรุ่นที่รันจริงได้จาก `/health` หรือ `/v1/info`: `model`, `revision` และ `runtime_version` ส่วน `version` เป็นรุ่น API wrapper แยกจากรุ่นโมเดล ชื่อ repository เก่าที่ redirect มาหน้าใหม่ไม่ได้ทำให้ snapshot ที่ล็อกไว้เปลี่ยนตาม

## ความสามารถของระบบ

- อ่านไฟล์ PDF และรูปภาพ (JPEG, PNG, WebP, TIFF หลายหน้า, BMP) ผ่าน HTTP บนเครื่องนี้
- คืนค่าเป็น Markdown ตามลำดับการอ่าน ตารางเป็น HTML ที่คงการรวมเซลล์ (`rowspan` / `colspan`)
- แยกบล็อกในหน้า เช่น หัวเรื่อง (`Title`), ข้อความ (`Text`), ตาราง (`Table`), รูป (`Picture`) พร้อมกรอบตำแหน่งทั้งแบบ normalized และเป็นพิกเซล
- เลือกช่วงหน้าได้ด้วย `start_page` และ `max_pages` ถ้าหน้าใดอ่านไม่สำเร็จ จะบันทึกข้อผิดพลาดของหน้านั้นแล้วอ่านหน้าถัดไปต่อ
- มีหน้าตรวจสถานะ (`/health`), ข้อมูลระบบ (`/v1/info`) และเอกสารลองเรียกใช้แบบ Swagger ที่ `/docs`
- โหลดโมเดลตอนเปิดเซิร์ฟเวอร์ในเบื้องหลัง หลังจากโหลดครั้งแรกแล้วตั้ง `OCR_LOCAL_FILES_ONLY=true` เพื่อทำงานออฟไลน์ได้ทั้งตัว
- รับคำขอจากเบราว์เซอร์บน `localhost` เท่านั้น (CORS) และฟังที่ `127.0.0.1` เป็นค่าเริ่มต้น จึงไม่เปิดให้เครื่องอื่นเรียกจนกว่าจะตั้งค่าเอง
- ประมวลผลทีละหน้า เพื่อไม่ให้หน่วยความจำเต็ม คำขอที่เข้าพร้อมกันจะเข้าคิว

## สรุปสั้น ๆ

| | |
|---|---|
| โฟลเดอร์ | `/Users/ninetea/Projects/nhso/ocr-markdown-api` |
| ที่อยู่ API | `http://127.0.0.1:8090` |
| เอกสาร API (Swagger) | `http://127.0.0.1:8090/docs` |
| ไฟล์ที่รับ | PDF, JPEG, PNG, WebP, TIFF (หลายหน้าได้), BMP |
| ขีดจำกัดเริ่มต้น | ไฟล์ไม่เกิน 50 MB, ไม่เกิน 20 หน้าต่อคำขอ |
| โมเดล | `iapp/OpenThai2.1-OCR-Markdown-20261118` รุ่น `c974dc7d18a4511a21988f4a1d12fad07ac16625` (ล็อกรุ่นไว้) ประมาณ 2.5 GB เก็บใน `~/.cache/huggingface` ไม่อยู่ในโฟลเดอร์โปรเจกต์ |
| ความเร็ว | ขึ้นกับอุปกรณ์และเอกสาร ผลวัด 49–69 วินาทีบน MPS และ 271.5 วินาทีบน Docker CPU ด้านล่างเป็นผลของรุ่น 2.0; ไม่ใช่ benchmark ของ 2.1 |

## เมื่อไหร่ควรใช้ตัวนี้

| | **ocr-markdown-api** (โปรเจกต์นี้) | **ocr-text-api** |
|---|---|---|
| พอร์ต | `8090` | `8091` |
| โมเดล | OpenThai 2.1 OCR Markdown (ประมาณ 2.5 GB) | OpenThai2.0-OCR-Text (ประมาณ 4 MB) |
| ผลลัพธ์ | Markdown ที่มีตารางเป็น HTML คงเซลล์รวมไว้ พร้อมบล็อกและกรอบ | ข้อความล้วนตามลำดับการอ่าน พร้อมกรอบและค่าความมั่นใจของทุกบรรทัด |
| ความเร็วบนเครื่องนี้ | ค่าทดสอบเดิมรุ่น 2.0: 50–70 วินาที/หน้า บน Apple MPS; รุ่นใหม่ต้องวัดกับงานจริง | ไม่ถึงหนึ่งวินาทีต่อหน้า ใช้ CPU อย่างเดียว |
| เหมาะกับ | งานที่ต้องคงรูปแบบหน้า โดยเฉพาะตาราง | ค้นหาข้อความ ดึงข้อความจากสแกน ส่งต่อให้แชตบอต หรืออ่านเอกสารจำนวนมาก |

รูปแบบการเรียกคล้ายกัน (`POST /v1/ocr` แบบ multipart ฟิลด์ `file`, `start_page`, `max_pages`) จึงสลับกันได้ง่าย

## บน Mac ใช้ Transformers ไม่ใช่ vLLM

ต้นทางมีทั้งทางเลือก vLLM สำหรับ NVIDIA และ GGUF/llama.cpp สำหรับ Mac/CPU แต่โปรเจกต์นี้ใช้ **PyTorch + Transformers** ทั้งบน CPU, Apple MPS และ CUDA โดยอิง[คู่มือทางการ](https://iapp.co.th/blog/openthai2p0-ocr-how-to-run) คือรันผ่าน PyTorch + Transformers บน GPU ของชิป Apple (`mps`)

- **ตัวเลขอ้างอิงเดิมของรุ่น 2.0:** H100 ใช้ประมาณ 1.6 วินาทีต่อหน้า ส่วน iApp วัดบน MacBook Pro M3 Max ได้ 15–27 วินาทีต่อหน้า บน MacBook Air M1 (RAM 16 GB) เครื่องนี้เคยวัดรุ่น 2.0 ได้ตามหมายเหตุประวัติด้านล่าง โปรเซสใช้ RAM ราว 0.8 GB (ไม่รวมหน่วยความจำฝั่ง GPU ที่ macOS นับแยก ระหว่างทดสอบเครื่องยังว่าง 65%) หน้าที่มีตัวหนังสือแน่นจะช้ากว่านี้
- **ผลลัพธ์และความเร็วอาจต่างจากคะแนนบนการ์ดโมเดล** เพราะใช้ backend และอุปกรณ์ต่างกัน
- **อ่านทีละหน้า:** API ล็อกให้ประมวลผลได้ครั้งละหนึ่งหน้า คำขอที่เข้ามาพร้อมกันจะรอคิว เพื่อไม่ให้หน่วยความจำเต็ม
- ถ้าต่อไปมีเครื่องที่มี GPU ของ NVIDIA ค่อยย้ายไปใช้ vLLM ได้ โดยรูปแบบ API ฝั่งผู้เรียกไม่ต้องเปลี่ยน

## ติดตั้ง (ทำครั้งเดียว)

ต้องมี Python 3.10 ขึ้นไป (เครื่องนี้ใช้ 3.13 ผ่าน `uv` ไม่ใช้ Python 3.15 ของระบบ เพราะบางแพ็กเกจยังไม่มีไฟล์ติดตั้ง) และแนะนำให้มี [uv](https://docs.astral.sh/uv/) ที่เครื่องนี้มีอยู่แล้ว เผื่อพื้นที่ว่างอย่างน้อย 5 GB

```bash
cd /Users/ninetea/Projects/nhso/ocr-markdown-api
scripts/install.sh
```

สคริปต์จะทำตามคู่มือของ iApp ดังนี้

1. สร้าง virtualenv ที่ `.venv` ในโฟลเดอร์โปรเจกต์ ไม่ยุ่งกับ Python ของระบบ และไม่ยุ่งกับ venv ของ ocr-text-api
2. โหลดโมเดลรุ่นที่ล็อกไว้ลง Hugging Face cache โดยข้ามไฟล์ที่ไม่ได้ใช้บน Mac คือ `dflash2/` (ตัวช่วยของ vLLM), `reference/` และ `assets/`
3. ติดตั้งแพ็กเกจ `nemotron-parse` ของโมเดลเอง ซึ่งจะติดตั้ง PyTorch, Transformers และเวอร์ชันที่ NVIDIA/iApp กำหนด ตามด้วยไลบรารีของ API (`requirements.txt`)

เวอร์ชันที่ติดตั้งจริงบนเครื่องนี้บันทึกไว้ใน `requirements.lock.txt` เมื่อเปลี่ยน revision ต้องติดตั้ง runtime ใหม่ด้วย โดยรันสคริปต์เดิมอีกครั้ง สคริปต์อ่าน model ID/revision จาก `app/config.py`, `.env` และ environment ให้ตรงกับ API

## เปิดและปิดเซิร์ฟเวอร์

### เปิดแบบเห็นในเทอร์มินัล

```bash
cd /Users/ninetea/Projects/nhso/ocr-markdown-api
scripts/run.sh
```

เซิร์ฟเวอร์เปิดทันทีที่ `http://127.0.0.1:8090` แล้วโหลดโมเดลต่อในเบื้องหลัง ระยะเวลาขึ้นกับอุปกรณ์และ cache ระหว่างนี้ `GET /health` จะตอบ `"model_state": "loading"` เมื่อพร้อมแล้วจะเป็น `"ready"` ถ้าส่งไฟล์เข้ามาระหว่างที่โมเดลยังโหลดไม่เสร็จ คำขอจะรอจนโหลดเสร็จแล้วค่อยทำงาน

หยุดด้วยการกด `Ctrl+C` ในเทอร์มินัลนั้น

### เปิดไว้เบื้องหลัง (ปิดหน้าต่างเทอร์มินัลได้)

```bash
cd /Users/ninetea/Projects/nhso/ocr-markdown-api
mkdir -p logs
OCR_LOCAL_FILES_ONLY=true nohup scripts/run.sh > logs/server.log 2>&1 &
```

`OCR_LOCAL_FILES_ONLY=true` ทำให้ไม่ต่อเน็ตหลังจากมีโมเดลในเครื่องแล้ว บันทึกการทำงานอยู่ที่ `logs/server.log`

### ตรวจสถานะ

```bash
# โมเดลพร้อมเมื่อมี "ready" ในผลลัพธ์
curl http://127.0.0.1:8090/health

# มีโปรเซสฟังพอร์ต 8090 อยู่หรือไม่
lsof -nP -iTCP:8090 -sTCP:LISTEN
```

รอจนพร้อมแล้วค่อยส่งไฟล์

```bash
until curl -sf http://127.0.0.1:8090/health | grep -q '"ready"'; do sleep 2; done
echo ready
```

ลองเรียกใช้แบบมีหน้าจอได้ที่ [http://127.0.0.1:8090/docs](http://127.0.0.1:8090/docs)

### ปิดเซิร์ฟเวอร์

ถ้ารันด้วย Docker ให้ใช้ `docker compose stop ocr` คำสั่ง `kill` ด้านล่างใช้เฉพาะเซิร์ฟเวอร์ Python ที่รันแบบ native

- ถ้าเปิดแบบเห็นในเทอร์มินัล: กด `Ctrl+C`
- ถ้าเปิดไว้เบื้องหลัง หรือไม่แน่ใจว่าเปิดจากหน้าต่างไหน:

```bash
kill $(lsof -ti tcp:8090)
```

ตรวจว่าปิดแล้วด้วย `curl http://127.0.0.1:8090/health` ซึ่งจะเชื่อมต่อไม่ได้ คำสั่งนี้ปิดเฉพาะพอร์ต 8090 ไม่กระทบ OCR Text API ที่พอร์ต 8091

## คู่มือการใช้งาน

1. เปิดเซิร์ฟเวอร์ตามด้านบน และรอจน `/health` เป็น `ready`
2. ส่งไฟล์เข้า `POST /v1/ocr` ด้วยวิธีใดวิธีหนึ่งด้านล่าง
3. ฝั่งผู้เรียกควรตั้ง timeout ให้ยาว (เช่น 1 ชั่วโมง) เพราะการอ่านบน CPU อาจใช้เวลาหลายนาทีต่อหน้า เอกสารหลายหน้าควรส่งเป็นงานเบื้องหลัง หรือแบ่งช่วงด้วย `start_page` / `max_pages`
4. ผลอยู่ในฟิลด์ `markdown` (ทุกหน้าต่อกัน คั่นด้วยบรรทัดว่าง) และ `pages[]` (รายหน้า พร้อมบล็อกและตาราง)

### ลองจากเบราว์เซอร์

เปิด [http://127.0.0.1:8090/docs](http://127.0.0.1:8090/docs) เลือก `POST /v1/ocr` กด Try it out อัปโหลดไฟล์ แล้วกด Execute

### curl

```bash
curl -X POST http://127.0.0.1:8090/v1/ocr \
  -F "file=@/path/to/document.pdf" \
  -F "max_pages=5" \
  --max-time 3600 -o result.json
```

หรือใช้สคริปต์ตัวอย่าง ซึ่งจะบันทึกผลเป็น `document.pdf.ocr.json` แล้วพิมพ์ Markdown ออกมา

```bash
examples/curl.sh document.pdf 1 5
```

### Python

ดูฉบับเต็มที่ `examples/client.py`

```python
import httpx

with open("document.pdf", "rb") as f:
    r = httpx.post(
        "http://127.0.0.1:8090/v1/ocr",
        files={"file": ("document.pdf", f, "application/pdf")},
        data={"max_pages": 5},
        timeout=3600,
    )
r.raise_for_status()
print(r.json()["markdown"])
```

### Node / TypeScript (เช่น backend ของ GovHR)

```ts
const form = new FormData();
form.append("file", new Blob([buffer]), "document.pdf");
form.append("max_pages", "5");
const res = await fetch("http://127.0.0.1:8090/v1/ocr", { method: "POST", body: form });
const { markdown, pages } = await res.json();
```

## API

### `GET /health`

บอกว่าเซิร์ฟเวอร์ทำงานอยู่ไหม โมเดลโหลดเสร็จหรือยัง (`model_state`: `not_loaded` / `loading` / `ready` / `error`) ใช้อุปกรณ์อะไร (`cuda` / `mps` / `cpu`) รวมถึงชื่อและรุ่นของโมเดล

### `GET /v1/info`

ข้อมูลแบบเดียวกับ `/health` และเพิ่มชนิดไฟล์ที่รับ ขีดจำกัด และเวลาที่ใช้โหลดโมเดล

### `POST /v1/ocr`

ส่งไฟล์แบบ `multipart/form-data`

| ฟิลด์ | จำเป็น | ความหมาย |
|---|---|---|
| `file` | ใช่ | PDF หรือรูปภาพ |
| `start_page` | ไม่ | หน้าแรกที่จะอ่าน นับจาก 1 (ค่าเริ่มต้น 1) |
| `max_pages` | ไม่ | จำนวนหน้าที่จะอ่านนับจาก `start_page` (ไม่เกิน `OCR_MAX_PAGES`) |
| `include_raw` | ไม่ | `true` เพื่อแนบผลดิบของโมเดลมาด้วยในแต่ละหน้า |

ตัวอย่างโครงสร้างผลลัพธ์ (ค่าประกอบคำอธิบาย ไม่ใช่ผล benchmark)

```json
{
  "model": "iapp/OpenThai2.1-OCR-Markdown-20261118",
  "revision": "c974dc7d18a4511a21988f4a1d12fad07ac16625",
  "runtime_version": "3.5.0.post8",
  "device": "mps",
  "filename": "memo.pdf",
  "file_type": "pdf",
  "total_pages": 3,
  "page_count": 1,
  "pages": [
    {
      "page": 1, "width": 1654, "height": 2339,
      "markdown": "# บันทึกข้อความ\n\n<table>...</table>",
      "blocks": [
        {"class": "Title", "box": [0.40, 0.05, 0.60, 0.08], "box_pixels": [662, 117, 992, 187],
         "content": "# บันทึกข้อความ", "text": "# บันทึกข้อความ"}
      ],
      "warnings": [], "error": null, "elapsed_ms": 41234
    }
  ],
  "markdown": "Markdown ของทุกหน้าต่อกัน คั่นด้วยบรรทัดว่าง",
  "elapsed_ms": 41234
}
```

- `blocks` เรียงตามลำดับการอ่าน แต่ละบล็อกมี `class` (เช่น `Title`, `Text`, `Table`, `Picture`), `box` (พิกัดแบบ normalized ของโมเดล), `box_pixels` (พิกัดเป็นพิกเซลบนภาพของหน้านั้น) และ `content`
- **ถ้าหน้าใดอ่านไม่สำเร็จ** เช่น โมเดลเขียนยาวจนชนขีดจำกัด token (`GenerationError`) หน้านั้นจะมี `error` บอกสาเหตุ แล้วระบบจะอ่านหน้าถัดไปต่อ ไม่ทำให้ทั้งเอกสารล้ม ส่วน `markdown` รวมจะใส่ `<!-- page N could not be read: … -->` แทนหน้านั้น
- ถ้าผู้เรียกตัดการเชื่อมต่อระหว่างทาง ระบบจะหยุดหลังหน้าปัจจุบัน ไม่ทำหน้าที่เหลือ
- รหัสข้อผิดพลาด: `413` ไฟล์ใหญ่เกิน, `415` ไม่ใช่ PDF หรือรูปภาพที่รองรับ (หรือ PDF ติดรหัสผ่าน), `400` `start_page` เกินจำนวนหน้า, `503` โหลดโมเดลไม่สำเร็จ

## ตั้งค่า

เปลี่ยนค่าได้โดย `cp .env.example .env` แล้วแก้ไฟล์ `.env` (ไม่มีรหัสลับใด ๆ) หรือส่งตัวแปร `OCR_*` ตอนเปิดเซิร์ฟเวอร์

| ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `OCR_HOST` | `127.0.0.1` | เปิดรับเฉพาะเครื่องนี้ ถ้าจะให้เครื่องอื่นในวงแลนเรียก ให้ตั้งเป็น `0.0.0.0` (API ไม่มีระบบล็อกอิน ควรใช้ในเครือข่ายที่ไว้ใจได้เท่านั้น) |
| `OCR_PORT` | `8090` | พอร์ต |
| `OCR_DEVICE` | `auto` | `auto` จะเลือก `cuda` → `mps` → `cpu` ตามลำดับ |
| `OCR_PRELOAD` | `true` | โหลดโมเดลทันทีที่เปิดเซิร์ฟเวอร์ ถ้าตั้งเป็น `false` จะโหลดตอนมีคำขอแรก |
| `OCR_LOCAL_FILES_ONLY` | `false` | ตั้งเป็น `true` เพื่อไม่ให้ต่อเน็ตเลย หลังจากโหลดโมเดลเสร็จแล้ว |
| `OCR_MAX_FILE_MB` | `50` | ขนาดไฟล์สูงสุด |
| `OCR_MAX_PAGES` | `20` | จำนวนหน้าสูงสุดต่อคำขอ |
| `OCR_PDF_DPI` | `200` | ความละเอียดตอนแปลง PDF เป็นภาพ (ตามคู่มือ iApp) |
| `OCR_MAX_NEW_TOKENS` | `8744` | จำนวน token สูงสุดต่อหน้า ตามค่าต้นทาง |
| `OCR_MODEL_ID` | `iapp/OpenThai2.1-OCR-Markdown-20261118` | repository ของโมเดล |
| `OCR_MODEL_REVISION` | `c974dc7d…` | snapshot ที่ล็อกไว้; เปลี่ยนแล้วต้องติดตั้ง runtime ใหม่และ rebuild image |

## ผลตรวจอัปเกรด 2.1 (18 พ.ย. 2569)

- API v0.2.0, โมเดล `iapp/OpenThai2.1-OCR-Markdown-20261118` ที่ revision `c974dc7d18a4511a21988f4a1d12fad07ac16625`, runtime `3.5.0.post8` โหลดใน Docker แบบออฟไลน์สำเร็จ
- ตรวจ SHA-256 ของ weights ตรงกับข้อมูลจาก Hugging Face ก่อนใช้งาน
- ทดสอบ Python 19 รายการผ่านทั้ง native environment และภายใน image; frontend 3 รายการผ่าน รวมถึงตรวจหน้า GUI บน desktop/mobile และ Swagger UI ใน Chromium
- ส่งหน้าว่างเข้า API จริง: คืน Markdown/blocks ว่างโดยไม่มีข้อผิดพลาด ใช้เวลารวม 436 ms
- อ่าน `samples/thai_table.png` จริงสำเร็จหนึ่งหน้าใน 275.5 วินาทีบน Docker CPU (4 vCPU / RAM ประมาณ 5.8 GiB) ตรวจพบตารางและยืนยันการ normalize “ำ” / ตัด unit spans ผลเก็บใน `outputs/upgrade_2.1_table.json` และ `.md` ซึ่งไม่อยู่ใน git
- ตัวเลขเป็นเอกสารตัวอย่างหนึ่งหน้า ไม่ใช่ benchmark ความเร็วหรือความแม่นยำทั่วไป ยังไม่ได้ทดสอบ CUDA/NVIDIA หรือวัดความเร็ว MPS ของ snapshot ใหม่

## ผลทดสอบเดิมของรุ่น 2.0 (12 พ.ย. 2569)

- ทดสอบกับ `samples/thai_table.png` ใช้เวลา 69.0 วินาที ได้หัวเรื่อง ย่อหน้า และตาราง 5×4 ครบทุกเซลล์ เลขไทยคงไว้ และกับ `samples/thai_table.pdf` ใช้เวลา 49.4 วินาที โครงสร้างเดียวกัน ยืนยันว่าการแยกหน้า PDF ทำงาน ผลเก็บไว้ที่ `outputs/smoke_png.json` และ `outputs/smoke_pdf.json` (โฟลเดอร์นี้ไม่อยู่ใน git)
- ภาพตัวอย่างที่สร้างด้วย `scripts/make_sample.py` วาดด้วย Pillow ซึ่งบน Mac ไม่มี libraqm จึงวาดวรรณยุกต์ที่ซ้อนบนสระบนหาย (เช่น «เรื่อง» กลายเป็น «เรือง» ตั้งแต่ในภาพ) ผลที่ขาดวรรณยุกต์ตรงนั้นจึงมาจากภาพตัวอย่าง ไม่ใช่จากโมเดล ควรทดสอบความแม่นด้วยเอกสารจริง
- ในผลลัพธ์ **รุ่น 2.0** ตัวอักษร «ำ» อาจถูกเขียนเป็นสองตัว (`ํ` + `า`) เช่น «ประจำ» กลายเป็น «ประจํา» สำคัญถ้าโปรเจกต์อื่นจะค้นข้อความ

## ข้อจำกัดของโมเดล 2.1 / runtime v2.2.0

- ภาพถ่ายเอกสารเต็มหน้าได้รับการปรับปรุง แต่ภาพหรือรูปประกอบที่ไม่มีข้อความยังอาจได้ข้อความที่โมเดลสร้างขึ้น การข้ามหน้าว่างไม่ใช่การรับประกันความถูกต้องของภาพทุกประเภท
- สูตรคณิตศาสตร์ยังเป็นจุดอ่อน ต้องตรวจสอบกับต้นฉบับ และ GUI ยังแสดงเป็น LaTeX source
- Dewarping ยังไม่เปิดใช้ และต้นทางยังไม่แนะนำให้เปิดสำหรับโมเดล Markdown รุ่นนี้


- **ลายมือ** อ่านได้เฉพาะระดับบรรทัด ไม่รองรับหน้าที่เขียนด้วยลายมือทั้งหน้า
- **ตัวหนังสือแนวตั้ง** เช่น หัวตารางที่หมุนตั้ง อาจอ่านผิด
- **ภาพถ่ายคำสั้น ๆ หรือภาพที่ครอปเล็ก ๆ** อ่านได้แย่กว่าทั้งหน้า ควรส่งเป็นหน้าเอกสารเต็มหน้า
- **ตัวพิมพ์ดอตแมทริกซ์** เช่น สมุดบัญชีธนาคาร อาจอ่านได้ด้อยกว่าตัวอย่างสังเคราะห์ของต้นทาง ต้องทดสอบกับเอกสารจริง
- เลขไทยบางครั้งออกมาเป็นเลขอารบิก
- ตารางที่หน้าตาไม่เหมือนเอกสารราชการไทย บางตารางอาจมีแถวหายหรือ rowspan ผิด
- เป้าหมายคือหน้าเอกสารภาษาไทย/อังกฤษ ไม่ใช่ข้อความในฉากทั่วไปหรือเอกสารภาษาจีน
- รองรับภาษาไทยและอังกฤษ

## แก้ปัญหาเบื้องต้น

| อาการ | สิ่งที่ควรทำ |
|---|---|
| เชื่อมต่อไม่ได้ / เหมือนเซิร์ฟเวอร์ลง | เปิดด้วย `scripts/run.sh` แล้วตรวจด้วย `curl http://127.0.0.1:8090/health` |
| `/health` ตอบ `"loading"` นาน | ครั้งแรกต้องดาวน์โหลดโมเดลใหม่ประมาณ 2.5 GB ตรวจ `logs/server.log` หรือ `docker compose logs -f ocr` |
| ได้รหัส `503` หรือ `"model_state": "error"` | ดูฟิลด์ `model_error` ใน `/health` และบันทึกในล็อก ถ้าโมเดลไม่ครบให้รัน `scripts/install.sh` อีกครั้ง (ต้องมีเน็ตถ้ายังไม่เคยโหลด) |
| แต่ละหน้าช้ามาก | CPU อาจใช้เวลาหลายนาทีต่อหน้า ตั้ง timeout ให้ยาว และอย่าส่งหลายไฟล์พร้อมกันโดยไม่ตั้งใจ เพราะจะเข้าคิว |
| แจ้งว่าพอร์ตถูกใช้แล้ว | มีเซิร์ฟเวอร์เปิดอยู่แล้ว ใช้ได้เลย หรือปิดด้วย `kill $(lsof -ti tcp:8090)` แล้วเปิดใหม่ |
| ผลจากไฟล์ตัวอย่างขาดวรรณยุกต์ | เป็นข้อจำกัดของการวาดภาพตัวอย่าง ไม่ใช่โมเดล ให้ลองกับเอกสารจริง |
| พื้นที่ดิสก์ไม่พอ | น้ำหนักโมเดลประมาณ 2.5 GB ควรมีพื้นที่ว่างอย่างน้อย 5 GB ตอนติดตั้ง |

## ทดสอบ

```bash
cd /Users/ninetea/Projects/nhso/ocr-markdown-api

# ทดสอบ API โดยใช้โมเดลจำลอง ไม่ต้องโหลดโมเดลจริง
.venv/bin/python -m pytest -q

# ทดสอบกับโมเดลจริง: สร้างหน้าเอกสารไทยตัวอย่างที่มีตาราง แล้วส่งเข้า API ที่เปิดไว้
.venv/bin/python scripts/make_sample.py
examples/curl.sh samples/thai_table.png 1 1
```

## อัปเกรดจากรุ่น 2.0

แก้ `OCR_MODEL_ID` และ `OCR_MODEL_REVISION` ใน `.env` เดิมให้ตรงกับ `.env.example` ก่อน หากเปิดโหมดออฟไลน์อยู่ให้ตั้ง `OCR_LOCAL_FILES_ONLY=false` จนกว่า snapshot ใหม่จะโหลดครบ

- Docker: `docker compose up -d --build` — ต้อง rebuild เพื่อติดตั้ง runtime ใหม่ด้วย
- Native: `scripts/install.sh` แล้วเปิด `scripts/run.sh` ใหม่
- ตรวจ `/health`: `model` เป็น `iapp/OpenThai2.1-OCR-Markdown-20261118`, `revision` เป็น `c974dc7d…`, `runtime_version` เป็น `3.5.0.post8`, `version` เป็น `0.2.0` และ `model_state` เป็น `ready`
- Cache รุ่นเดิมเก็บไว้ได้ แต่ใช้แทน weights รุ่น 2.1 ไม่ได้ รายละเอียดและผลทดสอบดู [DEPLOYMENT.md](DEPLOYMENT.md)

## โครงสร้างโปรเจกต์

```
app/main.py       FastAPI: /health, /v1/info, /v1/ocr
app/engine.py     โหลดโมเดลและอ่านทีละหน้า ตามคู่มือ iApp (Transformers + DocumentParser, box mode, mode="single")
app/pages.py      แยก PDF เป็นภาพทีละหน้าด้วย pypdfium2 (ไม่ต้องติดตั้ง poppler) และเปิดไฟล์รูปภาพ
app/config.py     ค่าตั้งจากตัวแปร OCR_* หรือไฟล์ .env
app/schemas.py    รูปแบบ JSON ของผลลัพธ์
scripts/          install.sh, run.sh, make_sample.py
examples/         curl.sh, client.py
tests/            ทดสอบ API ด้วยโมเดลจำลอง
samples/          หน้าเอกสารตัวอย่างที่สร้างขึ้นเอง ไม่มีข้อมูลส่วนบุคคล
```

## คำขอบคุณผู้พัฒนาและ Base Model

ขอขอบคุณ **NVIDIA** ผู้พัฒนา **[Nemotron 3.5 Parse](https://huggingface.co/nvidia/Nemotron-3.5-Parse)** ซึ่งเป็น Base Model ของระบบนี้ รวมถึง tokenizer, โครงสร้างบล็อก/ตาราง และ parsing runtime ที่เป็นรากฐานของงานอ่านเอกสาร

ขอขอบคุณ **iApp Technology / ทีม OpenThai** ผู้พัฒนาและเผยแพร่ **[OpenThai 2.1 OCR Markdown](https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118)** สำหรับภาษาไทย/อังกฤษ ตลอดจนการปรับปรุงข้อมูลฝึก การประมวลผลผลลัพธ์ และคู่มือการใช้งาน และขอขอบคุณผู้มีส่วนร่วมด้านข้อมูล เครื่องมือ และการทดสอบตามที่ต้นทางระบุไว้ใน model card

โปรเจกต์นี้พัฒนา API, GUI และชุด deploy สำหรับเรียกใช้ผลงานต้นทาง ไม่ได้พัฒนาหรือฝึก Base Model/weights เหล่านี้เอง การกล่าวถึงผู้พัฒนาไม่ได้หมายถึงการรับรองโปรเจกต์นี้โดยผู้พัฒนาต้นทาง

## References

1. [iApp/OpenThai — Model card ของ snapshot ที่ใช้](https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118/blob/c974dc7d18a4511a21988f4a1d12fad07ac16625/README.md): รุ่นโมเดล วิธีใช้ รูปแบบ Markdown ข้อจำกัด และ dewarping
2. [NVIDIA — Nemotron 3.5 Parse Base Model](https://huggingface.co/nvidia/Nemotron-3.5-Parse): สถาปัตยกรรม การใช้งาน และเอกสารโมเดลต้นแบบ
3. [iApp — ประกาศ OpenThai 2.1 OCR](https://iapp.co.th/blog/openthai2p1-ocr-release): การเปลี่ยนแปลงจากรุ่น 2.0
4. [iApp — คู่มือติดตั้ง Linux, Windows และ Mac](https://iapp.co.th/en/blog/openthai2p0-ocr-how-to-run)
5. [LICENSE ของโมเดลที่ใช้](https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118/blob/c974dc7d18a4511a21988f4a1d12fad07ac16625/LICENSE), [Third-party notices](https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118/blob/c974dc7d18a4511a21988f4a1d12fad07ac16625/THIRD_PARTY_NOTICES.md) และ [Tokenizer attribution](https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118/blob/c974dc7d18a4511a21988f4a1d12fad07ac16625/TOKENIZER_ATTRIBUTION.md)

## สัญญาอนุญาต

- โค้ดของ API ในโฟลเดอร์นี้ใช้สัญญาอนุญาต MIT (ไฟล์ `LICENSE`)
- **โมเดลไม่ได้เป็นผลงานของโปรเจกต์นี้** ผู้พัฒนาคือ iApp Technology ซึ่งปรับมาจาก NVIDIA Nemotron 3.5 Parse ใช้สัญญาอนุญาต OpenMDW-1.1 ส่วน tokenizer ใช้ MIT รายละเอียดและลิงก์ไปยังไฟล์สัญญาอนุญาตต้นฉบับอยู่ใน `THIRD_PARTY_NOTICES.md`
- ถ้าจะแจกจ่ายตัวโมเดลต่อ เช่น ใส่ไว้ใน Docker image ต้องแนบ `LICENSE`, `THIRD_PARTY_NOTICES.md` และ `TOKENIZER_ATTRIBUTION.md` ของโมเดลไปด้วยโดยไม่แก้ไข
