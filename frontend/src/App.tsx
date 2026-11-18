import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowSquareOut,
  CheckCircle,
  CircleNotch,
  ClipboardText,
  DownloadSimple,
  FileText,
  Files,
  Scan,
  ShieldCheck,
  UploadSimple,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

interface Info {
  model?: string;
  revision?: string;
  model_state: "not_loaded" | "loading" | "ready" | "error";
  model_error: string | null;
  device: string | null;
  max_file_mb: number;
  max_pages: number;
}
interface Page {
  page: number;
  markdown: string;
  error: string | null;
  warnings: unknown[];
  elapsed_ms: number;
}
interface Result {
  filename: string;
  page_count: number;
  total_pages: number;
  elapsed_ms: number;
  markdown: string;
  pages: Page[];
}
type View = "preview" | "markdown" | "json";
const schema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    td: [...(defaultSchema.attributes?.td ?? []), "rowSpan", "colSpan"],
    th: [...(defaultSchema.attributes?.th ?? []), "rowSpan", "colSpan"],
  },
};
const accept = ".pdf,.png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp";

export function MarkdownPreview({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, schema]]}
        components={{
          img: () => <span className="muted">[รูปภาพในผล OCR]</span>,
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

export default function App() {
  const [info, setInfo] = useState<Info | null>(null);
  const [offline, setOffline] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [start, setStart] = useState("1");
  const [count, setCount] = useState("1");
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [view, setView] = useState<View>("preview");
  const [page, setPage] = useState("all");
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const request = useRef<AbortController | null>(null);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController;
    async function poll() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      try {
        const response = await fetch("/v1/info", { signal: controller.signal });
        if (!response.ok) throw new Error();
        const data: Info = await response.json();
        if (!stopped) {
          setInfo(data);
          setOffline(false);
        }
      } catch {
        if (!stopped) setOffline(true);
      } finally {
        clearTimeout(timeout);
        if (!stopped) timer = setTimeout(poll, 5000);
      }
    }
    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller?.abort();
      request.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!file) {
      setUrl("");
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  useEffect(() => {
    if (!busy) return;
    const began = Date.now();
    const timer = setInterval(
      () => setElapsed(Math.floor((Date.now() - began) / 1000)),
      1000,
    );
    return () => clearInterval(timer);
  }, [busy]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  function choose(candidate?: File) {
    if (busy || !candidate) return;
    setError("");
    setNotice("");
    if (!/\.(pdf|png|jpe?g|webp|tiff?|bmp)$/i.test(candidate.name)) {
      setError("กรุณาเลือกไฟล์ PDF, PNG, JPEG, WebP, TIFF หรือ BMP");
      return;
    }
    if (candidate.size > (info?.max_file_mb ?? 50) * 1024 * 1024) {
      setError(`ไฟล์ต้องมีขนาดไม่เกิน ${info?.max_file_mb ?? 50} MB`);
      return;
    }
    if (!candidate.size) {
      setError("ไฟล์นี้ว่าง กรุณาเลือกไฟล์ใหม่");
      return;
    }
    setFile(candidate);
    setResult(null);
    setPage("all");
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!file || busy) return;
    if (
      !Number.isInteger(Number(start)) ||
      Number(start) < 1 ||
      !Number.isInteger(Number(count)) ||
      Number(count) < 1 ||
      Number(count) > (info?.max_pages ?? 20)
    ) {
      setError("กรุณาระบุช่วงหน้าให้ถูกต้อง");
      return;
    }
    setBusy(true);
    setElapsed(0);
    setError("");
    setNotice("");
    setResult(null);
    setPage("all");
    const body = new FormData();
    body.append("file", file);
    body.append("start_page", start);
    body.append("max_pages", count);
    const controller = new AbortController();
    request.current = controller;
    try {
      const response = await fetch("/v1/ocr", {
        method: "POST",
        body,
        signal: controller.signal,
      });
      if (!response.ok) {
        const problem = await response.json().catch(() => null);
        throw new Error(
          typeof problem?.detail === "string"
            ? problem.detail
            : `ประมวลผลไม่สำเร็จ (HTTP ${response.status})`,
        );
      }
      const data: Result = await response.json();
      setResult(data);
    } catch (e) {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "เชื่อมต่อไม่สำเร็จ กรุณาลองใหม่");
    } finally {
      setBusy(false);
      request.current = null;
    }
  }
  const selected = result?.pages.find((item) => String(item.page) === page);
  const markdown = selected ? selected.markdown : (result?.markdown ?? "");
  const json = JSON.stringify(selected ?? result, null, 2);
  const failed = result?.pages.filter((item) => item.error) ?? [];
  const warnings = (selected ? [selected] : (result?.pages ?? [])).filter(
    (item) => item.warnings.length,
  );
  const state = offline ? "offline" : info?.model_state;
  const status = offline
    ? "เชื่อมต่อไม่ได้"
    : !info
      ? "กำลังเชื่อมต่อ"
      : {
          ready: "พร้อมใช้งาน",
          loading: "กำลังโหลดโมเดล",
          not_loaded: "โหลดโมเดลเมื่อเริ่มอ่าน",
          error: "โมเดลมีปัญหา",
        }[info.model_state];
  const pdf = file && /\.pdf$/i.test(file.name);
  const imagePreview = file && /\.(png|jpe?g|webp|bmp)$/i.test(file.name);

  function download(format: "md" | "json") {
    if (!result) return;
    const link = document.createElement("a");
    const objectUrl = URL.createObjectURL(
      new Blob([format === "md" ? markdown : json], {
        type:
          format === "md"
            ? "text/markdown;charset=utf-8"
            : "application/json;charset=utf-8",
      }),
    );
    link.href = objectUrl;
    link.download = `${file?.name.replace(/\.[^.]+$/, "") ?? "ocr"}${selected ? `-page-${selected.page}` : ""}.${format}`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(view === "json" ? json : markdown);
      setNotice("คัดลอกผลลัพธ์แล้ว");
    } catch {
      setNotice(
        "คัดลอกอัตโนมัติไม่ได้ กรุณาเลือกข้อความในแท็บ Markdown หรือ JSON แล้วคัดลอก",
      );
    }
  }
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="OCR Workspace หน้าแรก">
          <span className="brand-icon">
            <Scan size={24} />
          </span>
          <span>
            OCR <strong>Workspace</strong>
            <small>THAI DOCUMENT TO MARKDOWN</small>
          </span>
        </a>
        <div className="header-right">
          <span className={`status ${state ?? ""}`} role="status">
            <span className="status-dot" />
            {status}
          </span>
          <a className="api-link" href="/docs" target="_blank" rel="noreferrer">
            API Docs <ArrowSquareOut size={15} />
          </a>
        </div>
      </header>
      <main>
        <section className="intro">
          <div>
            <p className="eyebrow">เครื่องมืออ่านเอกสารภาษาไทย</p>
            <h1>จากหน้าเอกสาร สู่ข้อความที่ใช้ต่อได้</h1>
            <p className="muted">
              แปลง PDF และรูปภาพเป็น Markdown พร้อมคงโครงสร้างตาราง
            </p>
          </div>
          <div className="privacy">
            <ShieldCheck size={22} />
            <span>
              ประมวลผลบนเซิร์ฟเวอร์นี้
              <small>ไฟล์เอกสารไม่ถูกส่งไปบริการ OCR ภายนอก</small>
            </span>
          </div>
        </section>
        {(error || info?.model_error) && (
          <div className="alert" role="alert">
            <WarningCircle size={21} />
            <span>{error || info?.model_error}</span>
          </div>
        )}
        {offline && (
          <div className="alert" role="alert">
            ติดต่อ API ไม่ได้ กำลังลองเชื่อมต่อใหม่อัตโนมัติ
          </div>
        )}
        <form className="controls" onSubmit={submit}>
          <div className="control-title">
            <Files size={21} />
            <span>
              ตั้งค่าการอ่าน<small>เลือกไฟล์และช่วงหน้าที่ต้องการ</small>
            </span>
          </div>
          <label>
            เริ่มที่หน้า
            <input
              type="number"
              min="1"
              required
              value={start}
              onChange={(e) => setStart(e.target.value)}
              disabled={busy}
            />
          </label>
          <label>
            จำนวนหน้า
            <input
              type="number"
              min="1"
              max={info?.max_pages ?? 20}
              required
              value={count}
              onChange={(e) => setCount(e.target.value)}
              disabled={busy}
            />
          </label>
          <p className="limit">สูงสุด {info?.max_pages ?? 20} หน้า / ครั้ง</p>
          <button
            className="primary"
            type="submit"
            disabled={
              !file ||
              busy ||
              offline ||
              !info ||
              info.model_state === "loading" ||
              info.model_state === "error"
            }
          >
            {busy ? (
              <CircleNotch className="spin" size={20} />
            ) : (
              <Scan size={20} />
            )}{" "}
            {busy ? "กำลังอ่านเอกสาร" : "เริ่มอ่านเอกสาร"}
            {!busy && <ArrowRight size={18} />}
          </button>
        </form>
      <div className={`workspace ${file ? "has-file" : ""}`}>
          <section className="panel source" aria-labelledby="source-title">
            <div className="panel-heading">
              <h2 id="source-title">
                <span className="step">01</span> เอกสารต้นฉบับ
              </h2>
              <button
                type="button"
                className="text-button"
                onClick={() => input.current?.click()}
                disabled={busy}
              >
                {file ? "เปลี่ยนไฟล์" : "เลือกไฟล์"}
                <UploadSimple size={17} />
              </button>
            </div>
            <input
              ref={input}
              type="file"
              accept={accept}
              aria-label="เลือกเอกสาร"
              className="file-input"
              disabled={busy}
              onChange={(e) => {
                choose(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
            {!file ? (
              <div
                className={`dropzone ${dragging ? "dragging" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  choose(e.dataTransfer.files[0]);
                }}
              >
                <div className="upload-icon">
                  <UploadSimple size={34} weight="light" />
                </div>
                <h3>วางเอกสารของคุณที่นี่</h3>
                <p>หรือเลือกไฟล์จากเครื่องเพื่อเริ่มต้น</p>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => input.current?.click()}
                >
                  เลือกเอกสาร <ArrowRight size={16} />
                </button>
                <span className="file-types">
                  PDF · PNG · JPEG · WebP · TIFF · BMP
                </span>
                <span className="muted">
                  ขนาดไม่เกิน {info?.max_file_mb ?? 50} MB
                </span>
              </div>
            ) : (
              <>
                <div className="file-row">
                  <FileText size={23} />
                  <div>
                    <strong>{file.name}</strong>
                    <small>
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                      {pdf ? " · PDF" : " · รูปภาพ"}
                    </small>
                  </div>
                  <button
                    className="icon-button"
                    aria-label="นำไฟล์ออก"
                    disabled={busy}
                    onClick={() => {
                      setFile(null);
                      setResult(null);
                      setError("");
                      setNotice("");
                    }}
                  >
                    <X size={18} />
                  </button>
                </div>
                <div className="document-view">
                  {pdf ? (
                    <iframe
                      key={url}
                      src={`${url}#page=${selected?.page ?? start}`}
                      title="ตัวอย่าง PDF"
                    />
                  ) : imagePreview ? (
                    <img src={url} alt={`เอกสาร ${file.name}`} />
                  ) : (
                    <div className="empty-state">
                      <FileText size={44} weight="light" />
                      <p>ไฟล์ TIFF พร้อมอ่าน</p>
                      <small>เบราว์เซอร์ไม่รองรับการแสดงตัวอย่างชนิดนี้</small>
                    </div>
                  )}
                </div>
              </>
            )}
            <div className="panel-footer">
              <ShieldCheck size={16} />
              <span>รองรับเอกสารภาษาไทยและภาษาอังกฤษ</span>
            </div>
          </section>
          <section
            className="panel output"
            aria-labelledby="output-title"
            aria-busy={busy}
          >
            <div className="panel-heading">
              <h2 id="output-title">
                <span className="step">02</span> ผลการอ่านเอกสาร
              </h2>
              {result && (
                <span className="result-count">
                  {result.page_count} หน้า ·{" "}
                  {(result.elapsed_ms / 1000).toFixed(1)} วินาที
                </span>
              )}
            </div>
            <div className="output-toolbar">
              <div className="tabs" role="tablist" aria-label="รูปแบบผลลัพธ์">
                {(["preview", "markdown", "json"] as View[]).map((item) => (
                  <button
                    key={item}
                    role="tab"
                    aria-selected={view === item}
                    aria-controls="result-content"
                    id={`tab-${item}`}
                    onClick={() => setView(item)}
                    className={view === item ? "active" : ""}
                  >
                    {
                      {
                        preview: "Preview",
                        markdown: "Markdown",
                        json: "JSON",
                      }[item]
                    }
                  </button>
                ))}
              </div>
              {result && (
                <select
                  aria-label="เลือกหน้าผลลัพธ์"
                  value={page}
                  onChange={(e) => setPage(e.target.value)}
                >
                  <option value="all">ทุกหน้า</option>
                  {result.pages.map((item) => (
                    <option key={item.page} value={item.page}>
                      หน้า {item.page}
                      {item.error ? " (มีข้อผิดพลาด)" : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div
              id="result-content"
              role="tabpanel"
              aria-labelledby={`tab-${view}`}
              className={`result-content ${!result ? "is-empty" : ""}`}
            >
              {busy ? (
                <div className="empty-state" role="status">
                  <span className="processing-icon">
                    <Scan size={36} />
                  </span>
                  <h3>กำลังอ่านเอกสารของคุณ</h3>
                  <p>
                    ใช้เวลาแล้ว {Math.floor(elapsed / 60)}:
                    {String(elapsed % 60).padStart(2, "0")} นาที
                  </p>
                  <small>
                    ระบบจะส่งผลเมื่ออ่านครบช่วงหน้าที่เลือก
                    <br />
                    อาจใช้เวลาหลายนาที ขึ้นกับอุปกรณ์และจำนวนหน้า
                    <br />
                    กรุณาเปิดหน้านี้ไว้ระหว่างประมวลผล
                  </small>
                  <span className="indeterminate">
                    <span />
                  </span>
                </div>
              ) : result ? (
                <>
                  {failed.length > 0 && (
                    <div className="inline-warning" role="alert">
                      อ่านไม่สำเร็จ {failed.length} หน้า
                      {failed.map((item) => (
                        <p key={item.page}>
                          หน้า {item.page}: {item.error}
                        </p>
                      ))}
                    </div>
                  )}
                  {warnings.map((item) => (
                    <div className="inline-warning" key={item.page}>
                      ข้อสังเกตหน้า {item.page}:{" "}
                      {item.warnings
                        .map((w) =>
                          typeof w === "string" ? w : JSON.stringify(w),
                        )
                        .join(" · ")}
                    </div>
                  ))}
                  {view === "preview" ? (
                    markdown.trim() ? (
                      <MarkdownPreview>{markdown}</MarkdownPreview>
                    ) : (
                      <p className="muted">ไม่มีข้อความในหน้าที่เลือก</p>
                    )
                  ) : (
                    <pre tabIndex={0}>{view === "json" ? json : markdown}</pre>
                  )}
                </>
              ) : (
                <div className="empty-state">
                  <span className="result-icon">
                    <ClipboardText size={38} weight="light" />
                  </span>
                  <h3>พื้นที่สำหรับผลลัพธ์ของคุณ</h3>
                  <p>เลือกเอกสาร แล้วกด “เริ่มอ่านเอกสาร”</p>
                  <small>ดูตัวอย่าง คัดลอกข้อความ หรือดาวน์โหลดไปใช้ต่อ</small>
                </div>
              )}
            </div>
            <div className="result-actions">
              <button className="text-button" disabled={!result} onClick={copy}>
                <ClipboardText size={17} />
                คัดลอก
              </button>
              <div>
                <button
                  className="text-button"
                  disabled={!result}
                  onClick={() => download("md")}
                >
                  <DownloadSimple size={17} />
                  .md
                </button>
                <button
                  className="text-button"
                  disabled={!result}
                  onClick={() => download("json")}
                >
                  <DownloadSimple size={17} />
                  .json
                </button>
              </div>
            </div>
          </section>
        </div>
        <footer className="page-footer">
          <span>
            <CheckCircle size={16} /> ตารางรองรับการรวมเซลล์ · ส่งออกได้ทั้ง Markdown
            และ JSON
          </span>
          <span>
            {info?.model?.split("/").at(-1) ?? "OpenThai OCR"}
            {info?.device ? ` / ${info.device.toUpperCase()}` : ""}
          </span>
        </footer>
      </main>
      {notice && (
        <div className="toast" role="status">
          {notice}
        </div>
      )}
    </div>
  );
}
