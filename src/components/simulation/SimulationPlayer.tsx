import React, { useEffect, useMemo } from "react";

interface SimulationPlayerProps {
  startDate: string;
  endDate: string;
  currentDate: string;
  isPlaying: boolean;
  speed: number; // 1, 2, 10, 20
  loop: boolean;
  onTogglePlay: () => void;
  onStepForward: () => void;
  onStepBackward: () => void;
  onSeekDate: (date: string) => void;
  onChangeSpeed: (speed: number) => void;
  onToggleLoop: () => void;
  onClose: () => void;
  onOpenDatePicker?: () => void;
}

export function SimulationPlayer({
  startDate,
  endDate,
  currentDate,
  isPlaying,
  speed,
  loop,
  onTogglePlay,
  onStepForward,
  onStepBackward,
  onSeekDate,
  onChangeSpeed,
  onToggleLoop,
  onClose,
  onOpenDatePicker,
}: SimulationPlayerProps) {
  // Generate all date steps in the range
  const datesInRange = useMemo(() => {
    const list: string[] = [];
    const curr = new Date(startDate);
    const end = new Date(endDate);
    if (isNaN(curr.getTime()) || isNaN(end.getTime()) || curr > end) {
      return [startDate];
    }
    // Allow full multi-year simulation ranges (safety ceiling of 10 years / 3652 days)
    while (curr <= end && list.length < 3652) {
      list.push(curr.toISOString().split("T")[0]);
      curr.setDate(curr.getDate() + 1);
    }
    return list;
  }, [startDate, endDate]);

  const currentIndex = Math.max(0, datesInRange.indexOf(currentDate));
  const progressRatio =
    datesInRange.length > 1
      ? currentIndex / (datesInRange.length - 1)
      : 1;

  // Keyboard shortcut listener for spacebar play/pause
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger if not typing in an input
      if (
        e.code === "Space" &&
        !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)
      ) {
        e.preventDefault();
        onTogglePlay();
      } else if (e.code === "ArrowRight") {
        onStepForward();
      } else if (e.code === "ArrowLeft") {
        onStepBackward();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onTogglePlay, onStepForward, onStepBackward]);

  const formatDateDisplay = (dateStr: string) => {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const mIdx = parseInt(parts[1], 10) - 1;
      return `${parseInt(parts[2], 10)} ${months[mIdx] ?? ""} ${parts[0]}`;
    }
    return dateStr;
  };

  return (
    <div
      className="simulation-player-bar"
      role="region"
      aria-label="Ocean Date Simulation Player"
    >
      {/* Left section: Range metadata & date trigger */}
      <div className="sim-range-info" onClick={onOpenDatePicker} title="Click to adjust simulation dates">
        <div className="sim-pulse-badge">
          <span className={`sim-dot ${isPlaying ? "playing" : ""}`} />
          <span className="sim-label">SIMULATION</span>
        </div>
        <div className="sim-range-text">
          <span>{formatDateDisplay(startDate)}</span>
          <span className="sim-arrow">→</span>
          <span>{formatDateDisplay(endDate)}</span>
        </div>
      </div>

      {/* Center section: Playback Controls & Scrubber */}
      <div className="sim-center-controls">
        {/* Playback Buttons */}
        <div className="sim-btn-cluster">
          {/* Step Back (◄) */}
          <button
            type="button"
            className="sim-ctrl-btn"
            onClick={onStepBackward}
            title="Previous day (Left Arrow)"
            aria-label="Step backward"
            disabled={currentIndex <= 0 && !loop}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <polygon points="19 20 9 12 19 4 19 20" />
              <line x1="5" y1="19" x2="5" y2="5" />
            </svg>
          </button>

          {/* Play / Pause Toggle */}
          <button
            type="button"
            className={`sim-play-btn ${isPlaying ? "playing" : ""}`}
            onClick={onTogglePlay}
            title={isPlaying ? "Pause simulation (Spacebar)" : "Play simulation (Spacebar)"}
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16" rx="1" />
                <rect x="14" y="4" width="4" height="16" rx="1" />
              </svg>
            ) : (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" style={{ marginLeft: "2px" }}>
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            )}
          </button>

          {/* Step Forward (►) */}
          <button
            type="button"
            className="sim-ctrl-btn"
            onClick={onStepForward}
            title="Next day (Right Arrow)"
            aria-label="Step forward"
            disabled={currentIndex >= datesInRange.length - 1 && !loop}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <polygon points="5 4 15 12 5 20 5 4" />
              <line x1="19" y1="5" x2="19" y2="19" />
            </svg>
          </button>
        </div>

        {/* Timeline Track Scrubber */}
        <div className="sim-timeline-wrapper">
          <div className="sim-date-current">
            <strong>{formatDateDisplay(currentDate)}</strong>
            <span className="sim-step-count">
              Day {currentIndex + 1} of {datesInRange.length}
            </span>
          </div>

          <div className="sim-slider-container">
            <input
              type="range"
              className="sim-slider-track"
              min={0}
              max={Math.max(0, datesInRange.length - 1)}
              step={1}
              value={currentIndex}
              onChange={(e) => {
                const idx = parseInt(e.target.value, 10);
                if (datesInRange[idx]) {
                  onSeekDate(datesInRange[idx]);
                }
              }}
              aria-label="Seek simulation date"
              style={{
                background: `linear-gradient(to right, #58A6FF 0%, #2B5AAF ${progressRatio * 100}%, rgba(153, 168, 169, 0.2) ${progressRatio * 100}%, rgba(153, 168, 169, 0.2) 100%)`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Right section: Speed, Loop & Close */}
      <div className="sim-right-options">
        {/* Speed multiplier selector */}
        <div className="sim-speed-selector">
          {[1, 2, 10, 20].map((s) => (
            <button
              key={s}
              type="button"
              className={`sim-speed-btn ${speed === s ? "active" : ""}`}
              onClick={() => onChangeSpeed(s)}
              title={`${s}x speed`}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Loop toggle */}
        <button
          type="button"
          className={`sim-option-btn ${loop ? "active" : ""}`}
          onClick={onToggleLoop}
          title={loop ? "Looping enabled: wraps back to start date" : "Enable looping"}
          aria-label="Toggle loop"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="17 1 21 5 17 9" />
            <path d="M3 11V9a4 4 0 0 1 4-4h14" />
            <polyline points="7 23 3 19 7 15" />
            <path d="M21 13v2a4 4 0 0 1-4 4H3" />
          </svg>
        </button>

        {/* Exit simulation mode */}
        <button
          type="button"
          className="sim-close-btn"
          onClick={onClose}
          title="Exit simulation mode"
          aria-label="Close simulation"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  );
}
