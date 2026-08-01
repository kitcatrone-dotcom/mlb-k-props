import { useRef, useState } from "react";
import { fileUrl, startSeparation, subscribeJob } from "../api/client";
import type { SeparationResult } from "../types";
import { useStudioStore } from "../state/store";

const STEM_ORDER = ["vocals", "drums", "bass", "other"] as const;
const STEM_LABELS: Record<(typeof STEM_ORDER)[number], string> = {
  vocals: "Vocals",
  drums: "Drums",
  bass: "Bass",
  other: "Melody / Other",
};

export function StemMixer() {
  const { importResult, separation, setSeparation, setActiveJob, setError, setStage } = useStudioStore();
  const [separating, setSeparating] = useState(false);
  const [muted, setMuted] = useState<Record<string, boolean>>({});
  const [playing, setPlaying] = useState(false);
  const audioRefs = useRef<Record<string, HTMLAudioElement | null>>({});

  if (!importResult) return null;

  const handleSeparate = async () => {
    setError(null);
    setSeparating(true);
    setStage("separating");
    try {
      const { job_id } = await startSeparation(importResult.session_id);
      await new Promise<void>((resolve, reject) => {
        const unsubscribe = subscribeJob(job_id, (progress) => {
          setActiveJob(progress);
          if (progress.status === "done") {
            unsubscribe();
            setSeparation(progress.result as unknown as SeparationResult);
            resolve();
          } else if (progress.status === "error") {
            unsubscribe();
            reject(new Error(progress.error ?? "Stem separation failed"));
          }
        });
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStage("analyzed");
    } finally {
      setSeparating(false);
    }
  };

  if (!separation) {
    return (
      <div className="stem-mixer stem-mixer--empty">
        <button className="primary-button" onClick={() => void handleSeparate()} disabled={separating}>
          {separating ? "Separating stems…" : "Separate Stems"}
        </button>
      </div>
    );
  }

  const toggleMute = (stem: string) => {
    setMuted((m) => {
      const next = { ...m, [stem]: !m[stem] };
      const el = audioRefs.current[stem];
      if (el) el.muted = next[stem];
      return next;
    });
  };

  const togglePlayAll = () => {
    const elements = STEM_ORDER.map((s) => audioRefs.current[s]).filter(Boolean) as HTMLAudioElement[];
    if (playing) {
      elements.forEach((el) => el.pause());
    } else {
      const t = elements[0]?.currentTime ?? 0;
      elements.forEach((el) => {
        el.currentTime = t;
        void el.play();
      });
    }
    setPlaying(!playing);
  };

  return (
    <div className="stem-mixer">
      <button className="primary-button" onClick={togglePlayAll}>
        {playing ? "Pause all stems" : "Play all stems"}
      </button>
      <div className="stem-mixer__tracks">
        {STEM_ORDER.map((stem) => {
          const relPath = separation.stems[stem];
          if (!relPath) return null;
          return (
            <div key={stem} className="stem-track">
              <div className="stem-track__header">
                <span>{STEM_LABELS[stem]}</span>
                <button
                  className={`mute-button ${muted[stem] ? "mute-button--active" : ""}`}
                  onClick={() => toggleMute(stem)}
                >
                  {muted[stem] ? "Muted" : "Mute"}
                </button>
              </div>
              <audio
                ref={(el) => {
                  audioRefs.current[stem] = el;
                }}
                src={fileUrl(importResult.session_id, relPath)}
                controls
                onEnded={() => setPlaying(false)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
