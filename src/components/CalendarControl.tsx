import React, { useState, useRef, useEffect, useMemo } from "react";

interface CalendarControlProps {
  date: string; // Format: "YYYY-MM-DD"
  onSelectDate: (date: string) => void;
  minDate?: string;
  maxDate?: string;
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const MONTH_SHORT = [
  "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
];

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

export const CalendarControl: React.FC<CalendarControlProps> = ({
  date,
  onSelectDate,
  minDate = "2020-01-01",
  maxDate = "2026-12-31",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Parse current selected date
  const selectedParts = useMemo(() => {
    const parts = date.split("-").map((p) => parseInt(p, 10));
    if (parts.length === 3 && !isNaN(parts[0]) && !isNaN(parts[1]) && !isNaN(parts[2])) {
      return { year: parts[0], month: parts[1] - 1, day: parts[2] };
    }
    return { year: 2026, month: 7, day: 25 };
  }, [date]);

  // Viewed month/year in popover navigation
  const [viewYear, setViewYear] = useState(selectedParts.year);
  const [viewMonth, setViewMonth] = useState(selectedParts.month);

  // Sync viewed month/year when selected date changes externally
  useEffect(() => {
    setViewYear(selectedParts.year);
    setViewMonth(selectedParts.month);
  }, [selectedParts.year, selectedParts.month]);

  // Click outside listener to close popover
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  // Days in month calculation
  const calendarDays = useMemo(() => {
    const firstDayIndex = new Date(viewYear, viewMonth, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const daysInPrevMonth = new Date(viewYear, viewMonth, 0).getDate();

    const days: Array<{
      day: number;
      monthOffset: number; // -1 = prev, 0 = current, 1 = next
      dateStr: string;
      isDisabled: boolean;
      isSelected: boolean;
    }> = [];

    // Previous month padding
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const d = daysInPrevMonth - i;
      const m = viewMonth === 0 ? 11 : viewMonth - 1;
      const y = viewMonth === 0 ? viewYear - 1 : viewYear;
      const dateStr = `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      days.push({
        day: d,
        monthOffset: -1,
        dateStr,
        isDisabled: dateStr < minDate || dateStr > maxDate,
        isSelected: false,
      });
    }

    // Current month days
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${viewYear}-${String(viewMonth + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      days.push({
        day: d,
        monthOffset: 0,
        dateStr,
        isDisabled: dateStr < minDate || dateStr > maxDate,
        isSelected:
          viewYear === selectedParts.year &&
          viewMonth === selectedParts.month &&
          d === selectedParts.day,
      });
    }

    // Next month padding to fill a complete 6-week or grid
    const remaining = (7 - (days.length % 7)) % 7;
    for (let d = 1; d <= remaining; d++) {
      const m = viewMonth === 11 ? 0 : viewMonth + 1;
      const y = viewMonth === 11 ? viewYear + 1 : viewYear;
      const dateStr = `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      days.push({
        day: d,
        monthOffset: 1,
        dateStr,
        isDisabled: dateStr < minDate || dateStr > maxDate,
        isSelected: false,
      });
    }

    return days;
  }, [viewYear, viewMonth, selectedParts, minDate, maxDate]);

  const handlePrevMonth = () => {
    if (viewMonth === 0) {
      setViewYear(viewYear - 1);
      setViewMonth(11);
    } else {
      setViewMonth(viewMonth - 1);
    }
  };

  const handleNextMonth = () => {
    if (viewMonth === 11) {
      setViewYear(viewYear + 1);
      setViewMonth(0);
    } else {
      setViewMonth(viewMonth + 1);
    }
  };

  const [hasSelected, setHasSelected] = useState(false);

  const handleSelectDay = (dateStr: string, isDisabled: boolean) => {
    if (isDisabled) return;
    onSelectDate(dateStr);
    setHasSelected(true);
    setIsOpen(false);
  };

  const formattedDate = useMemo(() => {
    const day = selectedParts.day;
    const month = MONTH_SHORT[selectedParts.month] ?? "";
    const year = selectedParts.year;
    return `${day} ${month} ${year}`;
  }, [selectedParts]);

  return (
    <div className="floating-calendar-container" ref={containerRef}>
      <button
        type="button"
        className={`floating-calendar-btn ${hasSelected ? "selected-state" : "default-state"} ${isOpen ? "active" : ""}`}
        onClick={() => setIsOpen(!isOpen)}
        title={hasSelected ? formattedDate : "Select date"}
        aria-label="Calendar date picker"
      >
        <svg
          className="calendar-icon"
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="3" y="4" width="18" height="18" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        {hasSelected && (
          <span className="cal-date-text">{formattedDate}</span>
        )}
      </button>

      {isOpen && (
        <div className="calendar-popover">
          {/* Popover Header */}
          <div className="calendar-popover-header">
            <button
              type="button"
              className="cal-nav-btn"
              onClick={handlePrevMonth}
              aria-label="Previous month"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <div className="cal-current-month-year">
              <select
                className="cal-month-select"
                value={viewMonth}
                onChange={(e) => setViewMonth(parseInt(e.target.value, 10))}
                aria-label="Select month"
              >
                {MONTH_NAMES.map((mName, idx) => (
                  <option key={mName} value={idx}>
                    {mName}
                  </option>
                ))}
              </select>

              <select
                className="cal-year-select"
                value={viewYear}
                onChange={(e) => setViewYear(parseInt(e.target.value, 10))}
                aria-label="Select year"
              >
                {Array.from({ length: 11 }, (_, i) => 2020 + i).map((yr) => (
                  <option key={yr} value={yr}>
                    {yr}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="cal-nav-btn"
              onClick={handleNextMonth}
              aria-label="Next month"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </div>

          {/* Weekday headers */}
          <div className="calendar-weekdays">
            {WEEKDAYS.map((wd) => (
              <div key={wd} className="cal-weekday-cell">
                {wd}
              </div>
            ))}
          </div>

          {/* Days Grid */}
          <div className="calendar-days-grid">
            {calendarDays.map((item, idx) => (
              <button
                key={`${item.dateStr}-${idx}`}
                type="button"
                className={`cal-day-cell ${
                  item.isSelected ? "selected" : ""
                } ${item.isDisabled ? "disabled" : ""} ${
                  item.monthOffset !== 0 ? "outside-month" : ""
                }`}
                disabled={item.isDisabled}
                onClick={() => handleSelectDay(item.dateStr, item.isDisabled)}
              >
                {item.day}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
