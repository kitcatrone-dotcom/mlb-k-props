import type { AnalysisResult } from "../types";

export function AnalysisSummary({ analysis }: { analysis: AnalysisResult }) {
  const topGenre = analysis.genre_guesses[0];

  return (
    <div className="analysis-summary">
      <div className="stat">
        <span className="stat__value">{analysis.tempo.bpm.toFixed(1)}</span>
        <span className="stat__label">BPM</span>
      </div>
      <div className="stat">
        <span className="stat__value">{analysis.key.camelot}</span>
        <span className="stat__label">{analysis.key.display}</span>
      </div>
      <div className="stat">
        <span className="stat__value">
          {analysis.time_signature.numerator}/{analysis.time_signature.denominator}
        </span>
        <span className="stat__label">Time signature</span>
      </div>
      <div className="stat">
        <span className="stat__value">{Math.round(analysis.energy.overall_energy * 100)}%</span>
        <span className="stat__label">Energy</span>
      </div>
      <div className="stat">
        <span className="stat__value">{Math.round(analysis.energy.danceability * 100)}%</span>
        <span className="stat__label">Danceability</span>
      </div>
      {topGenre && (
        <div className="stat">
          <span className="stat__value stat__value--text">{topGenre.label}</span>
          <span className="stat__label">Genre guess ({Math.round(topGenre.confidence * 100)}%)</span>
        </div>
      )}
    </div>
  );
}
