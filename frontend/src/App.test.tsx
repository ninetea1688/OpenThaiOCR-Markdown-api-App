// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import App, { MarkdownPreview } from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("OCR results", () => {
  it("preserves merged cells and removes active HTML and remote images", () => {
    const { container } = render(
      <MarkdownPreview>
        {
          '<table><tr><td rowspan="2" colspan="3">ข้อความ</td></tr></table><script>alert(1)</script><img src="https://outside.example/track.png" onerror="alert(1)"><iframe src="https://outside.example"></iframe><a href="javascript:alert(1)">unsafe</a>'
        }
      </MarkdownPreview>,
    );
    expect(container.querySelector("td")?.getAttribute("rowspan")).toBe("2");
    expect(container.querySelector("td")?.getAttribute("colspan")).toBe("3");
    expect(
      container.querySelector("script, iframe, img, [onerror]"),
    ).toBeNull();
    expect(
      container.querySelector("a")?.getAttribute("href") ?? "",
    ).not.toContain("javascript:");
  });
  it("submits the chosen range, shows partial failures, and switches to JSON", async () => {
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:preview"),
      revokeObjectURL: vi.fn(),
    });
    const fetcher = vi.fn(
      async (path: string, _options?: RequestInit) =>
        new Response(
          JSON.stringify(
            path === "/v1/info"
              ? {
                  model_state: "ready",
                  model_error: null,
                  device: "cpu",
                  max_file_mb: 50,
                  max_pages: 20,
                }
              : {
                  filename: "scan.png",
                  page_count: 2,
                  total_pages: 2,
                  elapsed_ms: 2000,
                  markdown: "# ผลลัพธ์",
                  pages: [
                    {
                      page: 1,
                      markdown: "# ผลลัพธ์",
                      error: null,
                      warnings: [],
                      elapsed_ms: 1000,
                    },
                    {
                      page: 2,
                      markdown: "",
                      error: "cut off",
                      warnings: [],
                      elapsed_ms: 1000,
                    },
                  ],
                },
          ),
          { status: 200 },
        ),
    );
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await screen.findByText("พร้อมใช้งาน");
    fireEvent.change(screen.getByLabelText("เลือกเอกสาร"), {
      target: {
        files: [new File(["image"], "scan.png", { type: "image/png" })],
      },
    });
    fireEvent.change(screen.getByLabelText("จำนวนหน้า"), {
      target: { value: "2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "เริ่มอ่านเอกสาร" }));
    await screen.findByRole("heading", { name: "ผลลัพธ์" });
    expect(screen.getByText("หน้า 2: cut off")).toBeTruthy();
    const options = fetcher.mock.calls.find((call) => call[0] === "/v1/ocr");
    const body = options?.[1]?.body as FormData;
    expect(body.get("max_pages")).toBe("2");
    fireEvent.click(screen.getByRole("tab", { name: "JSON" }));
    expect(screen.getByRole("tabpanel").textContent).toContain(
      '"total_pages": 2',
    );
    fireEvent.change(screen.getByLabelText("เลือกหน้าผลลัพธ์"), {
      target: { value: "2" },
    });
    expect(screen.getByRole("tabpanel").textContent).toContain('"page": 2');
  });
  it("rejects unsupported files before sending them", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              model_state: "ready",
              max_file_mb: 50,
              max_pages: 20,
            }),
          ),
      ),
    );
    render(<App />);
    await screen.findByText("พร้อมใช้งาน");
    fireEvent.change(screen.getByLabelText("เลือกเอกสาร"), {
      target: { files: [new File(["bad"], "scan.exe")] },
    });
    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain("กรุณาเลือกไฟล์"),
    );
  });
});
