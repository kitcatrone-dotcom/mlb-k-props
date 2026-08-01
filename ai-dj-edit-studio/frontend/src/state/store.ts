import { create } from "zustand";
import type {
  AnalysisResult,
  EditStyle,
  GenerateResult,
  ImportResult,
  JobProgress,
  LengthTarget,
  SeparationResult,
} from "../types";

export type Stage = "import" | "analyzing" | "analyzed" | "separating" | "ready" | "generating" | "generated";

interface StudioState {
  stage: Stage;
  error: string | null;

  importResult: ImportResult | null;
  analysis: AnalysisResult | null;
  separation: SeparationResult | null;
  generateResult: GenerateResult | null;

  activeJob: JobProgress | null;

  // Remix controls
  style: EditStyle;
  targetBpm: number | null;
  intensity: number;
  energy: number;
  lengthTarget: LengthTarget;

  setStage: (stage: Stage) => void;
  setError: (error: string | null) => void;
  setImportResult: (r: ImportResult) => void;
  setAnalysis: (a: AnalysisResult) => void;
  setSeparation: (s: SeparationResult) => void;
  setGenerateResult: (r: GenerateResult) => void;
  setActiveJob: (j: JobProgress | null) => void;
  setStyle: (s: EditStyle) => void;
  setTargetBpm: (bpm: number | null) => void;
  setIntensity: (v: number) => void;
  setEnergy: (v: number) => void;
  setLengthTarget: (v: LengthTarget) => void;
  reset: () => void;
}

const initial = {
  stage: "import" as Stage,
  error: null,
  importResult: null,
  analysis: null,
  separation: null,
  generateResult: null,
  activeJob: null,
  style: "house" as EditStyle,
  targetBpm: null,
  intensity: 0.6,
  energy: 0.7,
  lengthTarget: "club" as LengthTarget,
};

export const useStudioStore = create<StudioState>((set) => ({
  ...initial,

  setStage: (stage) => set({ stage }),
  setError: (error) => set({ error }),
  setImportResult: (importResult) => set({ importResult, stage: "analyzing" }),
  setAnalysis: (analysis) => set({ analysis, stage: "analyzed" }),
  setSeparation: (separation) => set({ separation, stage: "ready" }),
  setGenerateResult: (generateResult) => set({ generateResult, stage: "generated" }),
  setActiveJob: (activeJob) => set({ activeJob }),
  setStyle: (style) => set({ style }),
  setTargetBpm: (targetBpm) => set({ targetBpm }),
  setIntensity: (intensity) => set({ intensity }),
  setEnergy: (energy) => set({ energy }),
  setLengthTarget: (lengthTarget) => set({ lengthTarget }),
  reset: () => set({ ...initial }),
}));
