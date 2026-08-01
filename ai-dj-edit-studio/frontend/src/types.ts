// Mirrors backend/app/schemas.py 1:1. Kept as a hand-written twin rather
// than codegen'd since the surface is small and stable.

export interface KeyInfo {
  tonic: string;
  mode: "major" | "minor";
  display: string;
  camelot: string;
  confidence: number;
}

export interface TempoInfo {
  bpm: number;
  confidence: number;
  beat_times: number[];
  downbeat_times: number[];
}

export interface TimeSignatureInfo {
  numerator: number;
  denominator: number;
  confidence: number;
}

export type SectionLabel =
  | "intro"
  | "verse"
  | "pre_chorus"
  | "build"
  | "drop"
  | "breakdown"
  | "bridge"
  | "outro";

export interface Section {
  label: SectionLabel;
  start: number;
  end: number;
  bar_start: number;
  bar_count: number;
  energy: number;
}

export interface StructureInfo {
  sections: Section[];
  bar_length_sec: number;
}

export interface EnergyProfile {
  overall_energy: number;
  danceability: number;
  valence: number;
  curve: number[];
}

export interface GenreGuess {
  label: string;
  confidence: number;
}

export interface AnalysisResult {
  session_id: string;
  duration_sec: number;
  tempo: TempoInfo;
  key: KeyInfo;
  time_signature: TimeSignatureInfo;
  structure: StructureInfo;
  energy: EnergyProfile;
  genre_guesses: GenreGuess[];
}

export interface ImportResult {
  session_id: string;
  filename: string;
  duration_sec: number;
  sample_rate: number;
  channels: number;
}

export interface SeparationResult {
  session_id: string;
  stems: Record<string, string>;
}

export type EditStyle =
  | "house"
  | "tech_house"
  | "drum_and_bass"
  | "afro_house"
  | "melodic_house"
  | "bass_house"
  | "extended_club_edit";

export const EDIT_STYLES: { value: EditStyle; label: string }[] = [
  { value: "house", label: "House" },
  { value: "tech_house", label: "Tech House" },
  { value: "drum_and_bass", label: "Drum & Bass" },
  { value: "afro_house", label: "Afro House" },
  { value: "melodic_house", label: "Melodic House" },
  { value: "bass_house", label: "Bass House" },
  { value: "extended_club_edit", label: "Extended Club Edit" },
];

export type LengthTarget = "original" | "radio" | "club" | "extended";

export const LENGTH_TARGETS: { value: LengthTarget; label: string }[] = [
  { value: "original", label: "Original length" },
  { value: "radio", label: "Radio (~3:30)" },
  { value: "club", label: "Club (~5:30)" },
  { value: "extended", label: "Extended DJ tool (~8:00+)" },
];

export interface GenerateRequest {
  session_id: string;
  style: EditStyle;
  target_bpm: number | null;
  intensity: number;
  energy: number;
  length_target: LengthTarget;
}

export interface TimelineClip {
  section_label: string;
  style_role: string;
  start_sec: number;
  end_sec: number;
  source_section_label: string | null;
}

export interface GenerateResult {
  session_id: string;
  edit_id: string;
  style: EditStyle;
  resulting_bpm: number;
  duration_sec: number;
  timeline: TimelineClip[];
  preview_path: string;
}

export type ExportFormat = "wav" | "mp3" | "stems";

export interface ExportResult {
  session_id: string;
  edit_id: string;
  files: Record<string, string>;
}

export type JobStatus = "queued" | "running" | "done" | "error";

export interface JobProgress {
  job_id: string;
  kind: string;
  status: JobStatus;
  progress: number;
  message: string;
  result: Record<string, unknown> | null;
  error: string | null;
}
