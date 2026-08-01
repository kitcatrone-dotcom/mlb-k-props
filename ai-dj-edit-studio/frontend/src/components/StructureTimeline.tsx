import type { Section, SectionLabel } from "../types";

const LABEL_COLORS: Record<SectionLabel, string> = {
  intro: "#6b7280",
  verse: "#3b82f6",
  pre_chorus: "#06b6d4",
  build: "#f59e0b",
  drop: "#ef4444",
  breakdown: "#8b5cf6",
  bridge: "#10b981",
  outro: "#6b7280",
};

const LABEL_TEXT: Record<SectionLabel, string> = {
  intro: "Intro",
  verse: "Verse",
  pre_chorus: "Pre-chorus",
  build: "Build",
  drop: "Drop",
  breakdown: "Breakdown",
  bridge: "Bridge",
  outro: "Outro",
};

interface StructureTimelineProps {
  sections: Section[];
  durationSec: number;
}

export function StructureTimeline({ sections, durationSec }: StructureTimelineProps) {
  return (
    <div className="structure-timeline">
      <div className="structure-timeline__bar">
        {sections.map((s, i) => {
          const widthPct = ((s.end - s.start) / durationSec) * 100;
          return (
            <div
              key={i}
              className="structure-timeline__segment"
              style={{ width: `${widthPct}%`, background: LABEL_COLORS[s.label] }}
              title={`${LABEL_TEXT[s.label]} · ${s.start.toFixed(1)}s–${s.end.toFixed(1)}s · energy ${(s.energy * 100).toFixed(0)}%`}
            >
              <span className="structure-timeline__label">{LABEL_TEXT[s.label]}</span>
            </div>
          );
        })}
      </div>
      <div className="structure-timeline__legend">
        {Object.entries(LABEL_TEXT).map(([label, text]) => (
          <span key={label} className="structure-timeline__legend-item">
            <span className="structure-timeline__swatch" style={{ background: LABEL_COLORS[label as SectionLabel] }} />
            {text}
          </span>
        ))}
      </div>
    </div>
  );
}
