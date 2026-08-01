import { fileUrl } from "./api/client";
import { AnalysisSummary } from "./components/AnalysisSummary";
import { DropZone } from "./components/DropZone";
import { ExportPanel } from "./components/ExportPanel";
import { GenreSelector } from "./components/GenreSelector";
import { JobProgress } from "./components/JobProgress";
import { RemixControls } from "./components/RemixControls";
import { StemMixer } from "./components/StemMixer";
import { StructureTimeline } from "./components/StructureTimeline";
import { WaveformPlayer } from "./components/WaveformPlayer";
import { useStudioStore } from "./state/store";
import { timelineClipsToSections } from "./utils/timeline";

export default function App() {
  const { importResult, analysis, generateResult, error, reset } = useStudioStore();

  return (
    <div className="app">
      <header className="app__header">
        <h1>AI DJ Edit Studio</h1>
        {importResult && (
          <button className="link-button" onClick={reset}>
            Start over
          </button>
        )}
      </header>

      {error && <div className="error-banner">{error}</div>}

      <main className="app__main">
        {!importResult && <DropZone />}

        {importResult && !analysis && (
          <div className="panel">
            <p>Analyzing {importResult.filename}…</p>
          </div>
        )}

        {importResult && analysis && (
          <>
            <section className="panel">
              <h2>{importResult.filename}</h2>
              <AnalysisSummary analysis={analysis} />
              <WaveformPlayer audioUrl={fileUrl(importResult.session_id, "original.wav")} />
              <StructureTimeline sections={analysis.structure.sections} durationSec={analysis.duration_sec} />
            </section>

            <section className="panel">
              <h2>Stems</h2>
              <StemMixer />
            </section>

            <section className="panel">
              <h2>Edit style</h2>
              <GenreSelector />
              <RemixControls />
              <JobProgress />
            </section>

            {generateResult && (
              <section className="panel">
                <h2>Generated edit — {generateResult.resulting_bpm.toFixed(1)} BPM</h2>
                <WaveformPlayer
                  audioUrl={fileUrl(importResult.session_id, generateResult.preview_path)}
                />
                <StructureTimeline
                  sections={timelineClipsToSections(generateResult.timeline)}
                  durationSec={generateResult.duration_sec}
                />
                <ExportPanel />
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
