import { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";

interface WaveformPlayerProps {
  audioUrl: string;
  regions?: { start: number; end: number; color: string; label?: string }[];
  height?: number;
}

/** Thin wrapper around wavesurfer.js: renders a waveform for `audioUrl`
 * with play/pause, and optionally colored section regions (used to overlay
 * detected song structure). */
export function WaveformPlayer({ audioUrl, regions, height = 96 }: WaveformPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const isPlayingRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      height,
      waveColor: "#4d4d63",
      progressColor: "#8b5cf6",
      cursorColor: "#f4f4f5",
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      url: audioUrl,
    });
    wavesurferRef.current = ws;

    return () => {
      ws.destroy();
      wavesurferRef.current = null;
    };
  }, [audioUrl, height]);

  const togglePlay = () => {
    const ws = wavesurferRef.current;
    if (!ws) return;
    ws.playPause();
    isPlayingRef.current = !isPlayingRef.current;
  };

  return (
    <div className="waveform">
      <button className="waveform__play" onClick={togglePlay} aria-label="Play/pause">
        ▶ / ⏸
      </button>
      <div className="waveform__track" ref={containerRef} />
      {regions && regions.length > 0 && (
        <div className="waveform__legend">
          {regions.map((r, i) => (
            <span key={i} className="waveform__legend-item">
              <span className="waveform__legend-swatch" style={{ background: r.color }} />
              {r.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
