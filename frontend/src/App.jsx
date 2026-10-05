import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  CircleDashed,
  Clock3,
  Download,
  Filter,
  LayoutDashboard,
  MapPin,
  Menu,
  PanelLeftClose,
  RotateCcw,
  Search,
  Send,
  Settings2,
  Sparkles,
  Trash2,
  Upload,
  UserRound,
  X,
  Zap,
} from "lucide-react";
import "./App.css";

const STATUSES = ["New", "Saved", "Applied", "Interview", "Rejected", "Offer", "Agent Applied", "Agent Failed"];
const STATUS_META = {
  New: { color: "#8b817a", soft: "#f1ede9", icon: CircleDashed },
  Saved: { color: "#a1603f", soft: "#f8eee9", icon: CheckCircle2 },
  Applied: { color: "#8c4c32", soft: "#f6e8e1", icon: Send },
  Interview: { color: "#b06c35", soft: "#fbf0df", icon: Calendar },
  Rejected: { color: "#b9574d", soft: "#fbedeb", icon: X },
  Offer: { color: "#4d8061", soft: "#eaf4ed", icon: Sparkles },
  "Agent Applied": { color: "#4b7f7d", soft: "#e8f3f2", icon: Zap },
  "Agent Failed": { color: "#b5683f", soft: "#fbefe8", icon: X },
};
const API_URL = import.meta.env.VITE_API_URL;

function RamlalMark({ size = 18 }) {
  return (
    <svg
      aria-hidden="true"
      className="ramlal-mark"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
    >
      <path
        d="M7 18V6.5C7 5.67 7.67 5 8.5 5h3.1a4.4 4.4 0 0 1 0 8.8H7"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="m12 13.8 4.8 5.2"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="M17.3 5.3c1.1.9 1.7 2.2 1.7 3.7 0 1.1-.3 2.1-.9 2.9"
        stroke="#f6c4a8"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

function StatusMenu({ status, onChange }) {
  const [open, setOpen] = useState(false);
  const meta = STATUS_META[status] || STATUS_META.New;
  const StatusIcon = meta.icon;

  useEffect(() => {
    if (!open) return undefined;

    const closeMenu = (event) => {
      if (!event.target.closest(".status-menu")) setOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("mousedown", closeMenu);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeMenu);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  const selectStatus = (nextStatus) => {
    setOpen(false);
    if (nextStatus !== status) onChange(nextStatus);
  };

  return (
    <div className="status-menu" style={{ "--status-color": meta.color }}>
      <button
        className={`status-trigger ${open ? "open" : ""}`}
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Current status: ${status}`}
      >
        <span className="status-trigger-icon" style={{ background: meta.soft }}>
          <StatusIcon size={12} />
        </span>
        <span className="status-trigger-label">{status}</span>
        <ChevronDown size={12} className="status-trigger-chevron" />
      </button>
      {open && (
        <div className="status-menu-list" role="menu">
          <div className="status-menu-heading">Move to</div>
          {STATUSES.map((option) => {
            const OptionIcon = STATUS_META[option].icon;
            const optionMeta = STATUS_META[option];
            return (
              <button
                key={option}
                className={`status-option ${option === status ? "selected" : ""}`}
                onClick={() => selectStatus(option)}
                role="menuitem"
              >
                <span className="status-option-icon" style={{ color: optionMeta.color, background: optionMeta.soft }}>
                  <OptionIcon size={12} />
                </span>
                <span>{option}</span>
                {option === status && <CheckCircle2 size={13} className="status-option-check" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StatusFilterMenu({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const selected = value || "All statuses";
  const meta = value ? STATUS_META[value] : { color: "#8b817a", soft: "#f1ede9", icon: Filter };
  const StatusIcon = meta.icon;

  useEffect(() => {
    if (!open) return undefined;
    const closeMenu = (event) => {
      if (!event.target.closest(".status-filter-menu")) setOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", closeMenu);
    document.addEventListener("touchstart", closeMenu);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeMenu);
      document.removeEventListener("touchstart", closeMenu);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="status-filter-menu">
      <button
        type="button"
        className={`status-filter-trigger ${open ? "open" : ""} ${value ? "has-value" : ""}`}
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Status filter: ${selected}`}
      >
        <span className="status-filter-icon" style={{ color: meta.color, background: meta.soft }}>
          <StatusIcon size={12} />
        </span>
        <span>{selected}</span>
        <ChevronDown size={12} className="status-filter-chevron" />
      </button>
      {open && (
        <div className="status-filter-list" role="listbox">
          <div className="status-menu-heading">Filter by status</div>
          {["", ...STATUSES].map((option) => {
            const optionMeta = option ? STATUS_META[option] : { color: "#8b817a", soft: "#f1ede9", icon: Filter };
            const OptionIcon = optionMeta.icon;
            const isSelected = option === value;
            return (
              <button
                type="button"
                key={option || "all"}
                className={`status-option ${isSelected ? "selected" : ""}`}
                onClick={() => {
                  onChange(option);
                  setOpen(false);
                }}
                role="option"
                aria-selected={isSelected}
              >
                <span className="status-option-icon" style={{ color: optionMeta.color, background: optionMeta.soft }}>
                  <OptionIcon size={12} />
                </span>
                <span>{option || "All statuses"}</span>
                {isSelected && <CheckCircle2 size={13} className="status-option-check" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

const SCORE_OPTIONS = [
  { value: 0, label: "Any match score", desc: "All scored roles", badge: "All" },
  { value: 7, label: "Score 7.0+", desc: "Good fit & above", badge: "7.0+" },
  { value: 8, label: "Score 8.0+", desc: "Strong fit & above", badge: "8.0+" },
  { value: 9, label: "Score 9.0+", desc: "Top tier matches", badge: "9.0+" },
];

function ScoreDropdown({ value, onChange }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return undefined;
    const closeDropdown = (event) => {
      if (!event.target.closest(".score-dropdown")) setOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", closeDropdown);
    document.addEventListener("touchstart", closeDropdown);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeDropdown);
      document.removeEventListener("touchstart", closeDropdown);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  const currentOption = SCORE_OPTIONS.find((opt) => opt.value === value) || SCORE_OPTIONS[0];
  const hasFilter = value > 0;

  return (
    <div className="score-dropdown">
      <button
        type="button"
        className={`score-dropdown-trigger ${open ? "open" : ""} ${hasFilter ? "has-value" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Match score filter: ${currentOption.label}`}
      >
        <Zap size={13} className="score-trigger-icon" />
        <span className="score-trigger-label">{currentOption.label}</span>
        {hasFilter ? (
          <span
            className="score-trigger-clear"
            role="button"
            tabIndex={0}
            title="Clear score filter"
            onClick={(e) => {
              e.stopPropagation();
              onChange(0);
            }}
            aria-label="Clear score filter"
          >
            <X size={12} />
          </span>
        ) : (
          <ChevronDown size={12} className="score-trigger-chevron" />
        )}
      </button>

      {open && (
        <div className="score-dropdown-menu" role="listbox">
          <div className="score-menu-heading">Minimum score</div>
          {SCORE_OPTIONS.map((opt) => {
            const isSelected = opt.value === value;
            return (
              <button
                key={opt.value}
                type="button"
                className={`score-option ${isSelected ? "selected" : ""}`}
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
                role="option"
                aria-selected={isSelected}
              >
                <span className={`score-option-badge score-badge-${opt.value}`}>
                  {opt.badge}
                </span>
                <div className="score-option-text">
                  <strong>{opt.label}</strong>
                  <small>{opt.desc}</small>
                </div>
                {isSelected && <Check size={13} className="score-option-check" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const WEEKDAY_NAMES = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

const PRESETS = [
  { key: "all", label: "All time" },
  { key: "today", label: "Today" },
  { key: "yesterday", label: "Yesterday" },
  { key: "last7", label: "Last 7 days" },
  { key: "last14", label: "Last 14 days" },
  { key: "last30", label: "Last 30 days" },
  { key: "thisMonth", label: "This month" },
  { key: "lastMonth", label: "Last month" },
  { key: "last90", label: "Last 3 months" },
];

const toIsoDate = (date) => {
  if (!date) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const parseIsoDate = (str) => {
  if (!str) return null;
  const parts = str.split("-");
  if (parts.length !== 3) return null;
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1;
  const day = parseInt(parts[2], 10);
  return new Date(year, month, day);
};

const formatShortDate = (isoStr) => {
  if (!isoStr) return "";
  const d = parseIsoDate(isoStr);
  if (!d) return "";
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric"
  });
};

const formatTriggerText = (dateFrom, dateTo) => {
  if (!dateFrom && !dateTo) return "Any date";
  if (dateFrom && !dateTo) return `From ${formatShortDate(dateFrom)}`;
  if (dateFrom && dateTo) {
    if (dateFrom === dateTo) {
      return formatShortDate(dateFrom);
    }
    const d1 = parseIsoDate(dateFrom);
    const d2 = parseIsoDate(dateTo);
    if (!d1 || !d2) return `${dateFrom} – ${dateTo}`;
    if (d1.getFullYear() === d2.getFullYear()) {
      if (d1.getMonth() === d2.getMonth()) {
        const month = d1.toLocaleDateString("en-US", { month: "short" });
        return `${month} ${d1.getDate()} – ${d2.getDate()}, ${d1.getFullYear()}`;
      }
      const m1 = d1.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      const m2 = d2.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      return `${m1} – ${m2}, ${d1.getFullYear()}`;
    }
    const s1 = d1.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    const s2 = d2.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    return `${s1} – ${s2}`;
  }
  return "Any date";
};

const getPresetRange = (key) => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  switch (key) {
    case "today": {
      const iso = toIsoDate(today);
      return { from: iso, to: iso };
    }
    case "yesterday": {
      const d = new Date(today);
      d.setDate(d.getDate() - 1);
      const iso = toIsoDate(d);
      return { from: iso, to: iso };
    }
    case "last7": {
      const start = new Date(today);
      start.setDate(start.getDate() - 6);
      return { from: toIsoDate(start), to: toIsoDate(today) };
    }
    case "last14": {
      const start = new Date(today);
      start.setDate(start.getDate() - 13);
      return { from: toIsoDate(start), to: toIsoDate(today) };
    }
    case "last30": {
      const start = new Date(today);
      start.setDate(start.getDate() - 29);
      return { from: toIsoDate(start), to: toIsoDate(today) };
    }
    case "thisMonth": {
      const start = new Date(today.getFullYear(), today.getMonth(), 1);
      const end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      return { from: toIsoDate(start), to: toIsoDate(end) };
    }
    case "lastMonth": {
      const start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const end = new Date(today.getFullYear(), today.getMonth(), 0);
      return { from: toIsoDate(start), to: toIsoDate(end) };
    }
    case "last90": {
      const start = new Date(today);
      start.setDate(start.getDate() - 89);
      return { from: toIsoDate(start), to: toIsoDate(today) };
    }
    case "all":
    default:
      return { from: "", to: "" };
  }
};

function DateRangePicker({ dateFrom, dateTo, onChange }) {
  const [open, setOpen] = useState(false);
  const [stagedFrom, setStagedFrom] = useState(dateFrom);
  const [stagedTo, setStagedTo] = useState(dateTo);
  const [hoverDate, setHoverDate] = useState(null);

  const [visibleMonth, setVisibleMonth] = useState(() => {
    if (dateFrom) {
      const d = parseIsoDate(dateFrom);
      if (d) return new Date(d.getFullYear(), d.getMonth(), 1);
    }
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

  useEffect(() => {
    // Keep the draft calendar selection aligned after external filter changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStagedFrom(dateFrom);
    setStagedTo(dateTo);
    if (open && dateFrom) {
      const d = parseIsoDate(dateFrom);
      if (d) setVisibleMonth(new Date(d.getFullYear(), d.getMonth(), 1));
    }
  }, [dateFrom, dateTo, open]);

  useEffect(() => {
    if (!open) return undefined;
    const closePicker = (event) => {
      if (!event.target.closest(".date-range-picker")) {
        setOpen(false);
        setHoverDate(null);
      }
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setOpen(false);
        setHoverDate(null);
      }
    };
    document.addEventListener("mousedown", closePicker);
    document.addEventListener("touchstart", closePicker);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closePicker);
      document.removeEventListener("touchstart", closePicker);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  const year = visibleMonth.getFullYear();
  const month = visibleMonth.getMonth();

  const prevMonth = () => setVisibleMonth(new Date(year, month - 1, 1));
  const nextMonth = () => setVisibleMonth(new Date(year, month + 1, 1));
  const prevYear = () => setVisibleMonth(new Date(year - 1, month, 1));
  const nextYear = () => setVisibleMonth(new Date(year + 1, month, 1));
  const jumpToday = () => {
    const now = new Date();
    setVisibleMonth(new Date(now.getFullYear(), now.getMonth(), 1));
  };

  const calendarDays = useMemo(() => {
    const todayIso = toIsoDate(new Date());
    const firstDay = new Date(year, month, 1).getDay();
    const daysInCurrent = new Date(year, month + 1, 0).getDate();
    const daysInPrev = new Date(year, month, 0).getDate();
    const matrix = [];

    for (let i = firstDay - 1; i >= 0; i--) {
      const d = new Date(year, month - 1, daysInPrev - i);
      matrix.push({
        date: d,
        iso: toIsoDate(d),
        dayNumber: d.getDate(),
        isCurrentMonth: false,
        isToday: toIsoDate(d) === todayIso,
      });
    }

    for (let d = 1; d <= daysInCurrent; d++) {
      const date = new Date(year, month, d);
      matrix.push({
        date,
        iso: toIsoDate(date),
        dayNumber: d,
        isCurrentMonth: true,
        isToday: toIsoDate(date) === todayIso,
      });
    }

    let nextDay = 1;
    while (matrix.length < 42) {
      const d = new Date(year, month + 1, nextDay++);
      matrix.push({
        date: d,
        iso: toIsoDate(d),
        dayNumber: d.getDate(),
        isCurrentMonth: false,
        isToday: toIsoDate(d) === todayIso,
      });
    }

    return matrix;
  }, [year, month]);

  const activePresetKey = useMemo(() => {
    if (!dateFrom && !dateTo) return "all";
    for (const preset of PRESETS) {
      if (preset.key === "all") continue;
      const range = getPresetRange(preset.key);
      if (range.from === dateFrom && range.to === dateTo) {
        return preset.key;
      }
    }
    return null;
  }, [dateFrom, dateTo]);

  const handleSelectPreset = (key) => {
    const range = getPresetRange(key);
    setStagedFrom(range.from);
    setStagedTo(range.to);
    setHoverDate(null);
    onChange(range.from, range.to);
    if (range.from) {
      const target = parseIsoDate(range.to || range.from);
      if (target) setVisibleMonth(new Date(target.getFullYear(), target.getMonth(), 1));
    }
  };

  const handleDayClick = (day) => {
    const val = day.iso;
    if (!day.isCurrentMonth) {
      setVisibleMonth(new Date(day.date.getFullYear(), day.date.getMonth(), 1));
    }

    if (!stagedFrom || (stagedFrom && stagedTo)) {
      setStagedFrom(val);
      setStagedTo("");
      setHoverDate(null);
      onChange(val, "");
      return;
    }

    if (val === stagedFrom) {
      setStagedTo(val);
      setHoverDate(null);
      onChange(stagedFrom, val);
    } else if (val < stagedFrom) {
      setStagedFrom(val);
      setStagedTo(stagedFrom);
      setHoverDate(null);
      onChange(val, stagedFrom);
    } else {
      setStagedTo(val);
      setHoverDate(null);
      onChange(stagedFrom, val);
    }
  };

  const handleClear = () => {
    setStagedFrom("");
    setStagedTo("");
    setHoverDate(null);
    onChange("", "");
  };

  const hasFilter = Boolean(dateFrom || dateTo);

  const summaryText = useMemo(() => {
    if (stagedFrom && stagedTo) {
      if (stagedFrom === stagedTo) {
        return `${formatShortDate(stagedFrom)} • Single day`;
      }
      const d1 = parseIsoDate(stagedFrom);
      const d2 = parseIsoDate(stagedTo);
      if (d1 && d2) {
        const daysCount = Math.round((d2 - d1) / (1000 * 60 * 60 * 24)) + 1;
        return `${formatShortDate(stagedFrom)} – ${formatShortDate(stagedTo)} • ${daysCount} days`;
      }
      return `${stagedFrom} – ${stagedTo}`;
    }
    if (stagedFrom && !stagedTo) {
      return "Select an end date (or click start date again for single day)";
    }
    return "Click a start date to begin";
  }, [stagedFrom, stagedTo]);

  const yearOptions = [2024, 2025, 2026, 2027];

  return (
    <div className="date-range-picker">
      <button
        type="button"
        className={`date-range-trigger ${open ? "open" : ""} ${hasFilter ? "has-value" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        title={hasFilter ? "Filter applied. Click to change range." : "Filter by date found"}
      >
        <Calendar size={14} className="date-trigger-icon" />
        <span className="date-trigger-label">{formatTriggerText(dateFrom, dateTo)}</span>
        {hasFilter ? (
          <span
            className="date-trigger-clear"
            title="Clear date filter"
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              handleClear();
            }}
            aria-label="Clear date filter"
          >
            <X size={12} />
          </span>
        ) : (
          <ChevronDown size={13} className="date-trigger-chevron" />
        )}
      </button>

      {open && (
        <div className="calendar-popover-wrap">
          <div className="calendar-backdrop" onClick={() => setOpen(false)} />

          <div className="calendar-popover" role="dialog" aria-label="Choose date range">
            <aside className="calendar-presets">
              <div className="calendar-presets-header">
                <Clock3 size={13} />
                <span>Presets</span>
              </div>
              <div className="calendar-presets-list">
                {PRESETS.map((preset) => {
                  const isActive = activePresetKey === preset.key;
                  return (
                    <button
                      key={preset.key}
                      type="button"
                      className={`preset-btn ${isActive ? "active" : ""}`}
                      onClick={() => handleSelectPreset(preset.key)}
                    >
                      <span>{preset.label}</span>
                      {isActive && <Check size={12} className="preset-check" />}
                    </button>
                  );
                })}
              </div>
            </aside>

            <div className="calendar-main">
              <div className="calendar-selection-row">
                <div className={`date-input-pill ${stagedFrom && !stagedTo ? "active-focus" : ""}`}>
                  <small>Start</small>
                  <span>{stagedFrom ? formatShortDate(stagedFrom) : "Select date"}</span>
                </div>
                <span className="date-input-arrow">→</span>
                <div className={`date-input-pill ${stagedFrom && !stagedTo ? "awaiting-focus" : ""}`}>
                  <small>End</small>
                  <span>{stagedTo ? formatShortDate(stagedTo) : (stagedFrom ? "Select date" : "Select date")}</span>
                </div>
                <button
                  type="button"
                  className="jump-today-btn"
                  onClick={jumpToday}
                  title="Jump to current month"
                >
                  Today
                </button>
              </div>

              <div className="calendar-header">
                <div className="calendar-nav-group">
                  <button
                    type="button"
                    className="calendar-nav"
                    onClick={prevYear}
                    aria-label="Previous year"
                    title="Previous year"
                  >
                    <ChevronsLeft size={14} />
                  </button>
                  <button
                    type="button"
                    className="calendar-nav"
                    onClick={prevMonth}
                    aria-label="Previous month"
                    title="Previous month"
                  >
                    <ChevronLeft size={14} />
                  </button>
                </div>

                <div className="calendar-selectors">
                  <select
                    className="calendar-select month-select"
                    value={month}
                    onChange={(e) => setVisibleMonth(new Date(year, Number(e.target.value), 1))}
                    aria-label="Select month"
                  >
                    {MONTH_NAMES.map((name, idx) => (
                      <option key={name} value={idx}>{name}</option>
                    ))}
                  </select>
                  <select
                    className="calendar-select year-select"
                    value={year}
                    onChange={(e) => setVisibleMonth(new Date(Number(e.target.value), month, 1))}
                    aria-label="Select year"
                  >
                    {yearOptions.map((y) => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </div>

                <div className="calendar-nav-group">
                  <button
                    type="button"
                    className="calendar-nav"
                    onClick={nextMonth}
                    aria-label="Next month"
                    title="Next month"
                  >
                    <ChevronRight size={14} />
                  </button>
                  <button
                    type="button"
                    className="calendar-nav"
                    onClick={nextYear}
                    aria-label="Next year"
                    title="Next year"
                  >
                    <ChevronsRight size={14} />
                  </button>
                </div>
              </div>

              <div className="calendar-weekdays">
                {WEEKDAY_NAMES.map((day) => (
                  <span key={day}>{day}</span>
                ))}
              </div>

              <div
                className="calendar-grid"
                onMouseLeave={() => setHoverDate(null)}
              >
                {calendarDays.map((item) => {
                  const { iso, dayNumber, isCurrentMonth, isToday } = item;

                  const isRangeStart = Boolean(stagedFrom && iso === stagedFrom);
                  const isRangeEnd = Boolean(stagedTo && iso === stagedTo);
                  const isSingleDay = Boolean(stagedFrom && stagedTo && stagedFrom === stagedTo && iso === stagedFrom);
                  const isInRange = Boolean(stagedFrom && stagedTo && iso > stagedFrom && iso < stagedTo);

                  let isHoverInRange = false;
                  let isHoverStart = false;
                  let isHoverEnd = false;
                  if (stagedFrom && !stagedTo && hoverDate && hoverDate !== stagedFrom) {
                    const pStart = stagedFrom < hoverDate ? stagedFrom : hoverDate;
                    const pEnd = stagedFrom < hoverDate ? hoverDate : stagedFrom;
                    isHoverInRange = iso >= pStart && iso <= pEnd;
                    isHoverStart = iso === pStart;
                    isHoverEnd = iso === pEnd;
                  }

                  let dayClasses = "calendar-day";
                  if (!isCurrentMonth) dayClasses += " other-month";
                  if (isToday) dayClasses += " is-today";
                  if (isSingleDay) {
                    dayClasses += " single-selected";
                  } else {
                    if (isRangeStart) dayClasses += " range-start";
                    if (isRangeEnd) dayClasses += " range-end";
                    if (isInRange) dayClasses += " in-range";
                  }
                  if (isHoverInRange && !isInRange && !isRangeStart && !isRangeEnd) {
                    dayClasses += " hover-in-range";
                    if (isHoverStart) dayClasses += " hover-start";
                    if (isHoverEnd) dayClasses += " hover-end";
                  }

                  return (
                    <button
                      key={iso}
                      type="button"
                      className={dayClasses}
                      onClick={() => handleDayClick(item)}
                      onMouseEnter={() => {
                        if (stagedFrom && !stagedTo) {
                          setHoverDate(iso);
                        }
                      }}
                      aria-label={`${iso}${isToday ? " (Today)" : ""}`}
                    >
                      <span className="day-number">{dayNumber}</span>
                      {isToday && <span className="today-dot" />}
                    </button>
                  );
                })}
              </div>

              <div className="calendar-footer">
                <div className="calendar-summary">
                  <span className="summary-text">{summaryText}</span>
                </div>
                <div className="calendar-actions">
                  {(dateFrom || dateTo || stagedFrom || stagedTo) && (
                    <button
                      type="button"
                      className="calendar-btn-clear"
                      onClick={handleClear}
                    >
                      <RotateCcw size={12} />
                      <span>Clear</span>
                    </button>
                  )}
                  <button
                    type="button"
                    className="calendar-btn-apply"
                    onClick={() => {
                      setOpen(false);
                      setHoverDate(null);
                    }}
                  >
                    Done
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activePage, setActivePage] = useState("overview");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [confirmDiscardId, setConfirmDiscardId] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [compactView, setCompactView] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [uploadingResume, setUploadingResume] = useState(false);
  const [resumeMessage, setResumeMessage] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const resumeInputRef = useRef(null);
  const PAGE_SIZE = 9;

  async function fetchJobs(showLoading = true) {
    if (showLoading) setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/jobs`);
      setJobs(response.data);
      setLastRefresh(new Date());
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchJobs();
  }, []);

  const updateStatus = async (id, status) => {
    try {
      const response = await axios.put(`${API_URL}/api/jobs/${id}/status`, { status });
      setJobs((current) => current.map((job) => job.id === id ? { ...job, ...response.data } : job));
    } catch (error) {
      console.error("Failed to update status:", error);
    }
  };

  const discardJob = async (id) => {
    try {
      await axios.delete(`${API_URL}/api/jobs/${id}`);
      setJobs((current) => current.filter((job) => job.id !== id));
    } catch (error) {
      console.error("Failed to discard job:", error);
    } finally {
      setConfirmDiscardId(null);
    }
  };

  const filteredJobs = useMemo(() => jobs.filter((job) => {
    const query = search.toLowerCase();
    const matchesSearch = !query || job.title?.toLowerCase().includes(query) || job.company?.toLowerCase().includes(query);
    const matchesStatus = !statusFilter || (job.status || "New") === statusFilter;
    const matchesScore = (job.score || 0) >= minScore;
    const found = job.date_found ? new Date(job.date_found) : null;
    const matchesFrom = !dateFrom || !found || found >= new Date(`${dateFrom}T00:00:00`);
    const matchesTo = !dateTo || !found || found <= new Date(`${dateTo}T23:59:59`);
    return matchesSearch && matchesStatus && matchesScore && matchesFrom && matchesTo;
  }), [dateFrom, dateTo, jobs, minScore, search, statusFilter]);

  useEffect(() => {
    setCurrentPage(1);
  }, [activePage, dateFrom, dateTo, jobs.length, minScore, search, statusFilter]);

  const counts = useMemo(() => STATUSES.reduce((result, status) => {
    result[status] = jobs.filter((job) => (job.status || "New") === status).length;
    return result;
  }, {}), [jobs]);
  const recommendedJobs = jobs.filter((job) => job.auto_apply_ready || job.score >= 8);
  const applicationJobs = jobs.filter((job) => ["Applied", "Interview", "Offer", "Agent Applied", "Agent Failed"].includes(job.status));
  const activeJobs = jobs.filter((job) => ["Applied", "Interview", "Offer", "Agent Applied"].includes(job.status)).length;
  const averageScore = jobs.length ? (jobs.reduce((total, job) => total + (job.score || 0), 0) / jobs.length).toFixed(1) : "0.0";

  const goTo = (page, nextStatus = "") => {
    setActivePage(page);
    setStatusFilter(nextStatus);
    setMobileMenuOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const downloadResume = () => window.open(`${API_URL}/api/resume`, "_blank");

  const uploadResume = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.type !== "application/pdf") {
      setResumeMessage("Please choose a PDF resume.");
      return;
    }

    setUploadingResume(true);
    setResumeMessage("Parsing resume and refreshing job ratings…");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await axios.post(`${API_URL}/api/resume`, formData);
      setJobs(response.data.jobs || []);
      setLastRefresh(new Date());
      setResumeMessage(
        `${response.data.updated_count} job ratings updated from ${file.name}.`,
      );
    } catch (error) {
      const detail = error.response?.data?.detail || "Resume upload failed.";
      setResumeMessage(detail);
    } finally {
      setUploadingResume(false);
    }
  };

  if (loading) {
    return <div className="loader"><div className="loader-mark"><RamlalMark size={25} /></div><strong>Preparing your workspace</strong><span>Finding your best opportunities…</span></div>;
  }

  const JobCard = ({ job }) => {
    const status = job.status || "New";
    return (
      <article className={`job-card ${compactView ? "compact" : ""}`}>
        <div className="job-card-heading">
          <div className="company-avatar">{(job.company || "?").slice(0, 1).toUpperCase()}</div>
          <div className="job-company"><strong>{job.company || "Unknown company"}</strong><small><MapPin size={11} /> Remote / Flexible</small></div>
        </div>
        <div className="job-card-body">
          <div className="job-title-row"><h3>{job.title || "Untitled role"}</h3><span className={`score-badge ${job.score >= 8 ? "score-high" : ""}`}>{Number(job.score || 0).toFixed(1)}</span></div>
          <p className="job-reason">{job.reasons || "A promising match for your profile."}</p>
          <div className="job-tags"><span>Full-time</span>{job.auto_apply_ready && <span className="ready-tag"><Zap size={11} /> Auto-apply ready</span>}</div>
        </div>
        {job.applied_at && <div className="applied-date"><Clock3 size={12} /> Updated {new Date(job.applied_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</div>}
        <div className="job-card-footer">
          <a href={job.url} target="_blank" rel="noopener noreferrer" className="view-link">View role <ArrowUpRight size={13} /></a>
          <div className="card-controls">
            <StatusMenu status={status} onChange={(nextStatus) => updateStatus(job.id, nextStatus)} />
            {confirmDiscardId === job.id ? <div className="discard-confirm"><button className="confirm-delete" onClick={() => discardJob(job.id)}>Delete</button><button className="icon-button" onClick={() => setConfirmDiscardId(null)} aria-label="Cancel delete"><X size={13} /></button></div> : <button className="icon-button delete-button" onClick={() => setConfirmDiscardId(job.id)} aria-label={`Discard ${job.title}`}><Trash2 size={13} /></button>}
          </div>
        </div>
      </article>
    );
  };

  const renderFilterBar = () => (
    <div className="filter-panel">
      <div className="search-box"><Search size={16} /><input type="search" placeholder="Search roles or companies" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
      <StatusFilterMenu value={statusFilter} onChange={setStatusFilter} />
      <ScoreDropdown value={minScore} onChange={setMinScore} />
      <DateRangePicker dateFrom={dateFrom} dateTo={dateTo} onChange={(from, to) => { setDateFrom(from); setDateTo(to); }} />
      {(search || statusFilter || minScore || dateFrom || dateTo) && <button className="clear-filter" onClick={() => { setSearch(""); setStatusFilter(""); setMinScore(0); setDateFrom(""); setDateTo(""); }}><X size={14} /> Clear</button>}
    </div>
  );

  const EmptyState = ({ title, text }) => <div className="page-empty"><div className="empty-icon"><Sparkles size={22} /></div><h3>{title}</h3><p>{text}</p><button className="primary-button" onClick={() => goTo("all")}>Browse all opportunities</button></div>;

  const renderOverview = () => (
    <>
      <section className="welcome-section"><div><p className="eyebrow">Monday, October 5, 2026</p><h1>Your next great role starts here.</h1><p className="welcome-copy">Stay focused, keep momentum, and let your best opportunities rise to the top.</p></div><div className="welcome-actions"><button className="secondary-button" onClick={downloadResume}><Download size={15} /> Resume</button><button className="primary-button" onClick={() => fetchJobs(false)}><Sparkles size={15} /> Refresh matches</button></div></section>
      <Metrics />
      <section className="overview-grid"><div className="content-panel"><div className="panel-heading"><div><h2>Recommended for you</h2><p>High-confidence matches based on your resume.</p></div><button className="text-button" onClick={() => goTo("recommended")}>View all <ArrowUpRight size={14} /></button></div><div className="mini-job-list">{recommendedJobs.slice(0, 4).map((job) => <JobCard key={job.id} job={job} />)}</div>{!recommendedJobs.length && <EmptyState title="No recommendations yet" text="Refresh your matches to discover new roles." />}</div><PipelineSummary /></section>
    </>
  );

  const Metrics = () => <section className="metric-grid"><Metric icon={BriefcaseBusiness} tone="terracotta" label="Total opportunities" value={jobs.length} note="All saved roles" /><Metric icon={Send} tone="blue" label="In progress" value={activeJobs} note="Across your pipeline" /><Metric icon={Sparkles} tone="green" label="Auto-apply ready" value={recommendedJobs.length} note="Strong profile matches" /><Metric icon={Zap} tone="orange" label="Average match" value={<>{averageScore}<em>/10</em></>} note="Based on all roles" /></section>;
  const Metric = ({ icon: Icon, tone, label, value, note }) => <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={17} /></div><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></div>;
  const PipelineSummary = () => <div className="content-panel"><div className="panel-heading"><div><h2>Pipeline snapshot</h2><p>Where your applications stand today.</p></div><button className="text-button" onClick={() => goTo("applications")}>Open pipeline <ArrowUpRight size={14} /></button></div><div className="pipeline-list">{["New", "Saved", "Applied", "Interview", "Offer"].map((status) => { const meta = STATUS_META[status]; const Icon = meta.icon; return <button className="pipeline-row" key={status} onClick={() => goTo("applications", status)}><span className="pipeline-icon" style={{ color: meta.color, background: meta.soft }}><Icon size={14} /></span><span>{status}</span><strong>{counts[status]}</strong><span className="pipeline-bar"><i style={{ width: `${jobs.length ? Math.min(100, (counts[status] / jobs.length) * 100) : 0}%`, background: meta.color }} /></span><ArrowUpRight size={14} /></button>; })}</div></div>;

  const renderListingPage = (type) => {
    const isRecommended = type === "recommended";
    const isApplications = type === "applications";
    const baseSource = isRecommended ? recommendedJobs : isApplications ? applicationJobs : filteredJobs;
    const source = baseSource.filter((job) => {
      const query = search.toLowerCase();
      const found = job.date_found ? new Date(job.date_found) : null;
      return (!query || job.title?.toLowerCase().includes(query) || job.company?.toLowerCase().includes(query))
        && (!statusFilter || (job.status || "New") === statusFilter)
        && (!minScore || (job.score || 0) >= minScore)
        && (!dateFrom || !found || found >= new Date(`${dateFrom}T00:00:00`))
        && (!dateTo || !found || found <= new Date(`${dateTo}T23:59:59`));
    });
    const pageCount = Math.ceil(source.length / PAGE_SIZE);
    const visibleJobs = source.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
    const firstVisible = source.length ? (currentPage - 1) * PAGE_SIZE + 1 : 0;
    const lastVisible = Math.min(currentPage * PAGE_SIZE, source.length);
    return <><section className="page-intro"><div><p className="eyebrow">{isRecommended ? "Curated matches" : isApplications ? "Your progress" : "Opportunity library"}</p><h1>{isRecommended ? "Recommended roles" : isApplications ? "Application pipeline" : "All opportunities"}</h1><p className="welcome-copy">{isRecommended ? "Roles with the strongest fit and the clearest next step." : isApplications ? "Track every role you have moved beyond the discovery stage." : "Every role discovered, scored, and ready for your review."}</p></div><button className="primary-button" onClick={() => fetchJobs(false)}><Sparkles size={15} /> Refresh data</button></section><div className="listing-toolbar">{renderFilterBar()}<button className={`view-toggle ${compactView ? "active" : ""}`} onClick={() => setCompactView((value) => !value)}><Settings2 size={15} /> {compactView ? "Comfortable view" : "Compact view"}</button></div><div className="listing-meta"><strong>{source.length}</strong> roles in this view {source.length > 0 && <span>Showing {firstVisible}–{lastVisible}</span>} {lastRefresh && <span>Last refreshed {lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>}</div>{source.length ? <><div className={`job-grid ${compactView ? "compact-grid" : ""}`}>{visibleJobs.map((job) => <JobCard key={job.id} job={job} />)}</div>{pageCount > 1 && <div className="pagination" aria-label="Job pagination"><button type="button" className="pagination-button" onClick={() => setCurrentPage(1)} disabled={currentPage === 1} aria-label="First page"><ChevronsLeft size={14} /></button><button type="button" className="pagination-button" onClick={() => setCurrentPage((page) => Math.max(1, page - 1))} disabled={currentPage === 1} aria-label="Previous page"><ChevronLeft size={14} /></button><div className="pagination-pages">{Array.from({ length: pageCount }, (_, index) => index + 1).map((page) => <button type="button" key={page} className={`pagination-page ${page === currentPage ? "active" : ""}`} onClick={() => setCurrentPage(page)} aria-current={page === currentPage ? "page" : undefined}>{page}</button>)}</div><button type="button" className="pagination-button" onClick={() => setCurrentPage((page) => Math.min(pageCount, page + 1))} disabled={currentPage === pageCount} aria-label="Next page"><ChevronRight size={14} /></button><button type="button" className="pagination-button" onClick={() => setCurrentPage(pageCount)} disabled={currentPage === pageCount} aria-label="Last page"><ChevronsRight size={14} /></button></div>}</> : <EmptyState title="Nothing matches these filters" text="Try clearing a filter or browse a different workspace view." />}</>;
  };

  const renderProfile = () => <><section className="page-intro"><div><p className="eyebrow">Your foundation</p><h1>Profile & resume</h1><p className="welcome-copy">Keep your application materials close and ready for the next opportunity.</p></div><button className="primary-button" onClick={() => resumeInputRef.current?.click()} disabled={uploadingResume}><Upload size={15} /> {uploadingResume ? "Updating ratings…" : "Upload latest resume"}</button></section><input ref={resumeInputRef} className="visually-hidden" type="file" accept="application/pdf,.pdf" onChange={uploadResume} /><div className="profile-grid"><div className="profile-card profile-hero"><div className="large-avatar">S</div><div><h2>Sparsh</h2><p>Candidate profile</p><span className="profile-status"><i /> Resume available</span></div></div><div className="profile-card"><div className="profile-card-title"><UserRound size={16} /><h3>Profile readiness</h3></div><div className="readiness-track"><i style={{ width: "86%" }} /></div><strong className="readiness-value">86%</strong><p className="card-note">Your resume is being used to score every opportunity.</p></div><div className="profile-card profile-details"><div className="profile-card-title"><BriefcaseBusiness size={16} /><h3>Workspace details</h3></div><div className="detail-row"><span>Roles tracked</span><strong>{jobs.length}</strong></div><div className="detail-row"><span>Average match</span><strong>{averageScore}/10</strong></div><div className="detail-row"><span>Ready to apply</span><strong>{recommendedJobs.length}</strong></div></div><div className="profile-card resume-card"><div className="resume-illustration"><FileIcon /></div><div><h3>Resume.pdf</h3><p>Upload a newer PDF to refresh this profile and recalculate every job score.</p><div className="resume-actions"><button className="secondary-button" onClick={downloadResume}><Download size={14} /> Open resume</button><button className="secondary-button" onClick={() => resumeInputRef.current?.click()} disabled={uploadingResume}><Upload size={14} /> Replace</button></div>{resumeMessage && <span className="resume-message">{resumeMessage}</span>}</div></div></div></>;
  const FileIcon = () => <div className="file-icon"><span>PDF</span></div>;

  const navItems = [{ id: "overview", label: "Overview", icon: LayoutDashboard }, { id: "all", label: "All opportunities", icon: BriefcaseBusiness, count: jobs.length }, { id: "recommended", label: "Recommended", icon: Sparkles, count: recommendedJobs.length }, { id: "applications", label: "Applications", icon: Send, count: applicationJobs.length }];
  const pageTitle = activePage === "overview" ? "Overview" : activePage === "all" ? "All opportunities" : activePage === "recommended" ? "Recommended" : activePage === "applications" ? "Applications" : "Profile & resume";

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""} ${mobileMenuOpen ? "open" : ""}`}>
      <div className="brand">
        {sidebarCollapsed ? (
          <button className="brand-mark brand-mark-toggle" onClick={() => setSidebarCollapsed(false)} aria-label="Expand sidebar" title="Expand sidebar">
            <RamlalMark size={20} />
          </button>
        ) : (
          <>
            <div className="brand-mark"><RamlalMark size={20} /></div>
            <div className="brand-copy"><strong>Ramlal</strong><span>career workspace</span></div>
            <button className="collapse-button icon-button" onClick={() => setSidebarCollapsed(true)} aria-label="Collapse sidebar">
              <PanelLeftClose size={17} />
            </button>
          </>
        )}
      </div>
      <nav className="primary-nav">
        <span className="nav-label">Workspace</span>
        {navItems.map(({ id, label, icon: Icon, count }) => (
          <button key={id} className={`nav-item ${activePage === id ? "active" : ""}`} onClick={() => goTo(id)} title={sidebarCollapsed ? label : undefined}>
            <Icon size={16} /><span className="nav-text">{label}</span>{count !== undefined && <b>{count}</b>}
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <button className="profile-mini" onClick={() => goTo("profile")} title={sidebarCollapsed ? "My profile" : undefined}>
          <div className="profile-avatar">S</div>
          <div className="profile-copy"><strong>My profile</strong><span>Resume is ready</span></div>
          <ChevronDown className="profile-chevron" size={14} />
        </button>
        <button className="resume-button" onClick={downloadResume}><Download size={15} /><span className="nav-text">Download resume</span></button>
      </div>
    </aside>
    <main className="main-content">
      <header className="topbar">
        <div className="breadcrumb">
          <button className="mobile-menu-button icon-button" onClick={() => setMobileMenuOpen(true)} aria-label="Open navigation menu">
            <Menu size={19} />
          </button>
          <span>Workspace</span><span>/</span><strong>{pageTitle}</strong>
        </div>
        <div className="topbar-actions">
          <button className="topbar-user" onClick={() => goTo("profile")}><div className="profile-avatar small">S</div><span>Sparsh</span><ChevronDown size={13} /></button>
        </div>
      </header>
      <div className="page-content">{activePage === "overview" && renderOverview()}{["all", "recommended", "applications"].includes(activePage) && renderListingPage(activePage)}{activePage === "profile" && renderProfile()}</div>
    </main>
    {/* Mobile bottom navigation */}
    <nav className="bottom-nav" aria-label="Mobile navigation">
      <button className={`bottom-nav-item ${activePage === "overview" ? "active" : ""}`} onClick={() => goTo("overview")}>
        <LayoutDashboard size={20} /><span>Overview</span>
      </button>
      <button className={`bottom-nav-item ${activePage === "all" ? "active" : ""}`} onClick={() => goTo("all")}>
        <BriefcaseBusiness size={20} /><span>Jobs</span>
      </button>
      <button className={`bottom-nav-item ${activePage === "recommended" ? "active" : ""}`} onClick={() => goTo("recommended")}>
        <Sparkles size={20} /><span>Matches</span>
      </button>
      <button className={`bottom-nav-item ${activePage === "applications" ? "active" : ""}`} onClick={() => goTo("applications")}>
        <Send size={20} /><span>Applied</span>
      </button>
      <button className={`bottom-nav-item ${activePage === "profile" ? "active" : ""}`} onClick={() => goTo("profile")}>
        <UserRound size={20} /><span>Profile</span>
      </button>
    </nav>
  </div>;
}

export default App;
