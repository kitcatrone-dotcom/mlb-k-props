import { useStudioStore } from "../state/store";

export function JobProgress() {
  const activeJob = useStudioStore((s) => s.activeJob);

  if (!activeJob || activeJob.status === "done") return null;

  return (
    <div className="job-progress">
      <div className="job-progress__bar">
        <div
          className="job-progress__fill"
          style={{ width: `${Math.round(activeJob.progress * 100)}%` }}
        />
      </div>
      <span className="job-progress__message">
        {activeJob.status === "error" ? `Error: ${activeJob.error}` : activeJob.message || activeJob.kind}
      </span>
    </div>
  );
}
