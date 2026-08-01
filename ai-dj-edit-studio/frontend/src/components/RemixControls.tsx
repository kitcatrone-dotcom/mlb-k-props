import { useState } from "react";
import { startGenerate, subscribeJob } from "../api/client";
import { LENGTH_TARGETS } from "../types";
import type { GenerateResult } from "../types";
import { useStudioStore } from "../state/store";

export function RemixControls() {
  const {
    analysis,
    style,
    targetBpm,
    intensity,
    energy,
    lengthTarget,
    setTargetBpm,
    setIntensity,
    setEnergy,
    setLengthTarget,
    setActiveJob,
    setGenerateResult,
    setError,
    setStage,
    importResult,
  } = useStudioStore();

  const [generating, setGenerating] = useState(false);

  if (!analysis || !importResult) return null;

  const handleGenerate = async () => {
    setError(null);
    setGenerating(true);
    setStage("generating");
    try {
      const { job_id } = await startGenerate({
        session_id: importResult.session_id,
        style,
        target_bpm: targetBpm,
        intensity,
        energy,
        length_target: lengthTarget,
      });

      await new Promise<void>((resolve, reject) => {
        const unsubscribe = subscribeJob(job_id, (progress) => {
          setActiveJob(progress);
          if (progress.status === "done") {
            unsubscribe();
            setGenerateResult(progress.result as unknown as GenerateResult);
            resolve();
          } else if (progress.status === "error") {
            unsubscribe();
            reject(new Error(progress.error ?? "Edit generation failed"));
          }
        });
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStage("ready");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="remix-controls">
      <label className="control">
        <span>Target BPM</span>
        <div className="control__row">
          <input
            type="range"
            min={60}
            max={190}
            step={1}
            value={targetBpm ?? analysis.tempo.bpm}
            onChange={(e) => setTargetBpm(Number(e.target.value))}
          />
          <span className="control__value">
            {(targetBpm ?? analysis.tempo.bpm).toFixed(0)}
            {targetBpm === null && " (original)"}
          </span>
        </div>
        <button className="link-button" onClick={() => setTargetBpm(null)}>
          Reset to detected BPM
        </button>
      </label>

      <label className="control">
        <span>Remix intensity</span>
        <div className="control__row">
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={intensity}
            onChange={(e) => setIntensity(Number(e.target.value))}
          />
          <span className="control__value">{Math.round(intensity * 100)}%</span>
        </div>
      </label>

      <label className="control">
        <span>Energy level</span>
        <div className="control__row">
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={energy}
            onChange={(e) => setEnergy(Number(e.target.value))}
          />
          <span className="control__value">{Math.round(energy * 100)}%</span>
        </div>
      </label>

      <label className="control">
        <span>Song length</span>
        <select value={lengthTarget} onChange={(e) => setLengthTarget(e.target.value as typeof lengthTarget)}>
          {LENGTH_TARGETS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>

      <button className="primary-button" onClick={() => void handleGenerate()} disabled={generating}>
        {generating ? "Generating edit…" : "Generate Edit"}
      </button>
    </div>
  );
}
