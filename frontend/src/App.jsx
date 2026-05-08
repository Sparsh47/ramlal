import { useState, useEffect } from "react";
import axios from "axios";
import {
  ExternalLink,
  Zap,
  Search,
  LayoutTemplate,
  Download,
  Calendar,
  Filter,
  X,
  Trash2,
} from "lucide-react";
import "./App.css";

const STATUSES = ["New", "Saved", "Applied", "Interview", "Rejected", "Offer"];
const STATUS_COLORS = {
  New: "#6b7280",
  Saved: "#3b82f6",
  Applied: "#8b5cf6",
  Interview: "#f59e0b",
  Rejected: "#ef4444",
  Offer: "#10b981",
};

const STATUS_ICONS = {
  New: <Search size={15} />,
  Saved: <Download size={15} />,
  Applied: <ExternalLink size={15} />,
  Interview: <Calendar size={15} />,
  Rejected: <X size={15} />,
  Offer: <Zap size={15} />,
};

function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedMonth, setSelectedMonth] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    fetchJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchJobs() {
    try {
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/api/jobs`,
      );
      setJobs(response.data);
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    } finally {
      setLoading(false);
    }
  }

  const updateStatus = async (id, newStatus) => {
    try {
      const response = await axios.put(
        `${import.meta.env.VITE_API_URL}/api/jobs/${id}/status`,
        { status: newStatus },
      );
      setJobs((prev) =>
        prev.map((job) =>
          job.id === id
            ? {
                ...job,
                status: newStatus,
                ...(newStatus === "Applied" && response.data.applied_at
                  ? { applied_at: response.data.applied_at }
                  : {}),
              }
            : job,
        ),
      );
    } catch (error) {
      console.error("Failed to update status:", error);
    }
  };

  const [confirmDiscardId, setConfirmDiscardId] = useState(null);

  const discardJob = async (id) => {
    try {
      await axios.delete(`${import.meta.env.VITE_API_URL}/api/jobs/${id}`);
      setJobs((prev) => prev.filter((job) => job.id !== id));
    } catch (error) {
      console.error("Failed to discard job:", error);
    } finally {
      setConfirmDiscardId(null);
    }
  };

  const clearFilters = () => {
    setSearchQuery("");
    setMinScore(0);
    setDateFrom("");
    setDateTo("");
    setSelectedMonth("");
    setStatusFilter("");
  };

  const hasActiveFilters =
    searchQuery ||
    minScore > 0 ||
    dateFrom ||
    dateTo ||
    selectedMonth ||
    statusFilter;

  const handleDownloadResume = () => {
    window.open(`${import.meta.env.VITE_API_URL}/api/resume`, "_blank");
  };

  // ── Client-side filtering ──────────────────────────────────────────────────
  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.company?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesScore = (job.score || 0) >= minScore;

    const matchesStatus = !statusFilter || job.status === statusFilter;

    let matchesDate = true;
    if (dateFrom || dateTo || selectedMonth) {
      const jobDate = job.date_found ? new Date(job.date_found) : null;
      if (jobDate) {
        if (selectedMonth) {
          const [y, m] = selectedMonth.split("-");
          matchesDate =
            jobDate.getFullYear() === parseInt(y) &&
            jobDate.getMonth() + 1 === parseInt(m);
        } else {
          if (dateFrom)
            matchesDate = matchesDate && jobDate >= new Date(dateFrom);
          if (dateTo)
            matchesDate =
              matchesDate && jobDate <= new Date(dateTo + "T23:59:59");
        }
      }
    }

    return matchesSearch && matchesScore && matchesStatus && matchesDate;
  });

  // ── Stats ──────────────────────────────────────────────────────────────────
  const statCounts = STATUSES.reduce((acc, s) => {
    acc[s] = filteredJobs.filter((j) => (j.status || "New") === s).length;
    return acc;
  }, {});

  // ── Loading state ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="loader">
        <LayoutTemplate size={32} />
        <p>Loading Ramlal Workspace…</p>
      </div>
    );
  }

  // ── Job Card ───────────────────────────────────────────────────────────────
  const JobCard = ({ job }) => {
    const status = job.status || "New";
    const showAppliedAt =
      job.applied_at &&
      ["Applied", "Interview", "Rejected", "Offer"].includes(status);

    return (
      <div className="job-card">
        <div className="card-top">
          <span className="company-name">{job.company}</span>
          <div className="card-top-right">
            {job.auto_apply_ready && (
              <span className="auto-ready-badge" title="Auto-apply ready">
                ⚡ Auto-ready
              </span>
            )}
            <span
              className={`score-dot ${
                job.score >= 9 ? "high" : job.score >= 8 ? "medium" : "low"
              }`}
            >
              {(job.score || 0).toFixed(1)}
            </span>
          </div>
        </div>

        <h3 className="job-title">{job.title}</h3>
        <p className="job-reason">{job.reasons}</p>

        {showAppliedAt && (
          <p className="applied-at">
            <Calendar size={11} />
            {new Date(job.applied_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </p>
        )}

        <div className="card-actions">
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn"
          >
            <ExternalLink size={14} /> View
          </a>
          <select
            value={status}
            onChange={(e) => updateStatus(job.id, e.target.value)}
            className="status-select"
            style={{ color: STATUS_COLORS[status] }}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          {confirmDiscardId === job.id ? (
            <div className="discard-confirm">
              <button
                className="btn btn-confirm-discard"
                onClick={() => discardJob(job.id)}
                title="Yes, permanently delete"
              >
                <Trash2 size={13} /> Sure?
              </button>
              <button
                className="btn btn-cancel-discard"
                onClick={() => setConfirmDiscardId(null)}
                title="Cancel"
              >
                <X size={13} />
              </button>
            </div>
          ) : (
            <button
              className="btn btn-discard"
              onClick={() => setConfirmDiscardId(job.id)}
              title="Discard this job"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>
    );
  };

  // ── Main render ────────────────────────────────────────────────────────────
  return (
    <div className="app-container">
      <header>
        <div className="brand">
          <LayoutTemplate size={24} color="var(--text-main)" />
          <h1>Ramlal</h1>
        </div>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={handleDownloadResume}>
            <Download size={14} /> My Resume
          </button>
        </div>
      </header>

      {/* ── Toolbar ── */}
      <div className="toolbar">
        {/* Search */}
        <div className="search-box">
          <Search size={16} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search by title or company…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Score filter */}
        <div className="filter-box">
          <select
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
          >
            <option value={0}>All Scores</option>
            <option value={7}>Score 7.0+</option>
            <option value={8}>Score 8.0+</option>
            <option value={9}>Score 9.0+</option>
          </select>
        </div>

        {/* Date range */}
        <div className="filter-box date-range">
          <Calendar size={14} color="var(--text-muted)" />
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="filter-input"
            title="From date"
          />
          <span className="date-sep">–</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="filter-input"
            title="To date"
          />
        </div>

        {/* Month filter */}
        <div className="filter-box">
          <input
            type="month"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="filter-input"
            title="Filter by month"
          />
        </div>

        {/* Status filter */}
        <div className="filter-box">
          <Filter size={14} color="var(--text-muted)" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">All Statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Clear filters */}
        {hasActiveFilters && (
          <button
            className="btn btn-clear"
            onClick={clearFilters}
            title="Clear all filters"
          >
            <X size={14} /> Clear
          </button>
        )}
      </div>

      {/* ── Stats bar ── */}
      <div className="stats-bar">
        <span className="stat-total">{filteredJobs.length} jobs</span>
        {STATUSES.filter((s) => statCounts[s] > 0).map((s) => (
          <span
            key={s}
            className="stat-chip"
            style={{ "--chip-color": STATUS_COLORS[s] }}
          >
            {statCounts[s]} {s}
          </span>
        ))}
      </div>

      {/* ── Kanban board ── */}
      <div className="kanban-board">
        {STATUSES.map((status) => {
          const colJobs = filteredJobs.filter(
            (j) => (j.status || "New") === status,
          );
          const colClass = `col-${status.toLowerCase()}`;
          return (
            <div key={status} className={`kanban-col ${colClass}`}>
              <div className="col-header">
                <div className="col-title">
                  {STATUS_ICONS[status]}
                  {status}
                </div>
                <span className="col-count">{colJobs.length}</span>
              </div>
              <div className="col-content">
                {colJobs.map((job) => (
                  <JobCard key={job.id} job={job} />
                ))}
                {colJobs.length === 0 && (
                  <div className="empty-state">
                    No {status.toLowerCase()} jobs
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default App;
