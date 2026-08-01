import { useState } from "react";
import { exportEdit, fileUrl } from "../api/client";
import type { ExportFormat, ExportResult } from "../types";
import { useStudioStore } from "../state/store";

const FORMAT_OPTIONS: { value: ExportFormat; label: string }[] = [
  { value: "wav", label: "WAV (24-bit)" },
  { value: "mp3", label: "MP3 (320kbps)" },
  { value: "stems", label: "Individual stems (.zip)" },
];

export function ExportPanel() {
  const { generateResult, importResult, setError } = useStudioStore();
  const [selected, setSelected] = useState<ExportFormat[]>(["wav", "mp3"]);
  const [exporting, setExporting] = useState(false);
  const [result, setResult] = useState<ExportResult | null>(null);

  if (!generateResult || !importResult) return null;

  const toggleFormat = (fmt: ExportFormat) => {
    setSelected((prev) => (prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]));
  };

  const handleExport = async () => {
    setError(null);
    setExporting(true);
    try {
      const res = await exportEdit(importResult.session_id, generateResult.edit_id, selected);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="export-panel">
      <h3>Export</h3>
      <div className="export-panel__formats">
        {FORMAT_OPTIONS.map((opt) => (
          <label key={opt.value} className="checkbox">
            <input
              type="checkbox"
              checked={selected.includes(opt.value)}
              onChange={() => toggleFormat(opt.value)}
            />
            {opt.label}
          </label>
        ))}
      </div>
      <button
        className="primary-button"
        onClick={() => void handleExport()}
        disabled={exporting || selected.length === 0}
      >
        {exporting ? "Exporting…" : "One-Click Export"}
      </button>

      {result && (
        <div className="export-panel__links">
          {Object.entries(result.files).map(([fmt, relPath]) => (
            <a
              key={fmt}
              href={fileUrl(importResult.session_id, relPath)}
              download
              className="export-panel__link"
            >
              Download {fmt.toUpperCase()}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
