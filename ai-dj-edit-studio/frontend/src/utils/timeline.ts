import type { Section, SectionLabel, TimelineClip } from "../types";

const ROLE_TO_LABEL: Record<string, SectionLabel> = {
  intro_drums_only: "intro",
  verse_arranged: "verse",
  build: "build",
  build_synth: "build",
  drop_full: "drop",
  breakdown_filtered: "breakdown",
  bridge: "bridge",
  outro_drums_only: "outro",
};

/** Adapts a generated edit's timeline (arrangement roles like
 * "drop_full"/"breakdown_filtered") into the same `Section[]` shape
 * `StructureTimeline` uses for the original song's detected structure, so
 * the two can share one visualization component. */
export function timelineClipsToSections(clips: TimelineClip[]): Section[] {
  return clips.map((clip) => ({
    label: ROLE_TO_LABEL[clip.style_role] ?? "verse",
    start: clip.start_sec,
    end: clip.end_sec,
    bar_start: 0,
    bar_count: 0,
    energy: 0.6,
  }));
}
