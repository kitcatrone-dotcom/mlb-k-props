import { EDIT_STYLES } from "../types";
import { useStudioStore } from "../state/store";

export function GenreSelector() {
  const style = useStudioStore((s) => s.style);
  const setStyle = useStudioStore((s) => s.setStyle);

  return (
    <div className="genre-selector">
      {EDIT_STYLES.map((opt) => (
        <button
          key={opt.value}
          className={`genre-chip ${style === opt.value ? "genre-chip--active" : ""}`}
          onClick={() => setStyle(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
