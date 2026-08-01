import { useCallback, useRef, useState } from "react";
import { getAnalysis, importFile } from "../api/client";
import { useStudioStore } from "../state/store";

const ACCEPTED_EXTENSIONS = [".mp3", ".wav", ".flac", ".aiff", ".aif"];

function hasSupportedExtension(name: string): boolean {
  const lower = name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export function DropZone() {
  const [dragActive, setDragActive] = useState(false);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const setImportResult = useStudioStore((s) => s.setImportResult);
  const setAnalysis = useStudioStore((s) => s.setAnalysis);
  const setError = useStudioStore((s) => s.setError);

  const handleFile = useCallback(
    async (file: File) => {
      if (!hasSupportedExtension(file.name)) {
        setError(`Unsupported file type. Supported: ${ACCEPTED_EXTENSIONS.join(", ")}`);
        return;
      }
      setError(null);
      setBusy(true);
      try {
        const imported = await importFile(file);
        setImportResult(imported);
        const analysis = await getAnalysis(imported.session_id);
        setAnalysis(analysis);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setBusy(false);
      }
    },
    [setAnalysis, setError, setImportResult]
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (file) void handleFile(file);
    },
    [handleFile]
  );

  return (
    <div
      className={`dropzone ${dragActive ? "dropzone--active" : ""} ${busy ? "dropzone--busy" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={onDrop}
      onClick={() => !busy && inputRef.current?.click()}
      role="button"
      tabIndex={0}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
        }}
      />
      {busy ? (
        <>
          <div className="spinner" />
          <p>Importing & analyzing your track…</p>
        </>
      ) : (
        <>
          <p className="dropzone__title">Drag & drop a song here</p>
          <p className="dropzone__subtitle">or click to browse — MP3, WAV, FLAC, AIFF</p>
        </>
      )}
    </div>
  );
}
