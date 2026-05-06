import { useState, useEffect } from 'react'
import axios from 'axios'
import { ExternalLink, Check, Zap, Search, LayoutTemplate } from 'lucide-react'
import './App.css'

function App() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchJobs()
  }, [])

  const fetchJobs = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/jobs')
      setJobs(response.data)
      setLoading(false)
    } catch (error) {
      console.error("Failed to fetch jobs:", error)
      setLoading(false)
    }
  }

  const toggleApply = async (id) => {
    try {
      const response = await axios.put(`http://localhost:8000/api/jobs/${id}/apply`)
      setJobs(jobs.map(job => 
        job.id === id ? { ...job, applied: response.data.applied } : job
      ))
    } catch (error) {
      console.error("Failed to update status:", error)
    }
  }

  const readyJobs = jobs.filter(j => j.auto_apply_ready && !j.applied)
  const manualJobs = jobs.filter(j => !j.auto_apply_ready && !j.applied)
  const appliedJobs = jobs.filter(j => j.applied)

  if (loading) {
    return (
      <div className="loader">
        <LayoutTemplate size={32} />
        <p>Loading Ramlal Workspace...</p>
      </div>
    )
  }

  const JobCard = ({ job, isAppliedCol }) => (
    <div className="job-card">
      <div className="card-top">
        <span className="company-name">{job.company}</span>
        <span className={`score-dot ${job.score >= 9 ? 'high' : job.score >= 8 ? 'medium' : 'low'}`}>
          {job.score.toFixed(1)}
        </span>
      </div>
      <h3 className="job-title">{job.title}</h3>
      <p className="job-reason">{job.reasons}</p>
      
      <div className="card-actions">
        <a href={job.url} target="_blank" rel="noopener noreferrer" className="btn">
          <ExternalLink size={14} /> View
        </a>
        <button 
          className={isAppliedCol ? "btn" : "btn btn-primary"} 
          onClick={() => toggleApply(job.id)}
        >
          <Check size={14} /> {isAppliedCol ? 'Undo' : 'Apply'}
        </button>
      </div>
    </div>
  )

  return (
    <div className="app-container">
      <header>
        <div className="brand">
          <LayoutTemplate size={24} color="var(--text-main)" />
          <h1>Ramlal</h1>
        </div>
        <div className="stats">
          <span>{jobs.length} Total</span>
          <span>{appliedJobs.length} Applied</span>
        </div>
      </header>

      <div className="kanban-board">
        
        {/* Column 1: Ready to Auto Apply */}
        <div className="kanban-col col-ready">
          <div className="col-header">
            <div className="col-title">
              <Zap size={16} /> Auto-Apply Ready
            </div>
            <span className="col-count">{readyJobs.length}</span>
          </div>
          <div className="col-content">
            {readyJobs.map(job => <JobCard key={job.id} job={job} />)}
            {readyJobs.length === 0 && <div className="empty-state">No jobs in queue</div>}
          </div>
        </div>

        {/* Column 2: Manual Review (Snippets) */}
        <div className="kanban-col col-manual">
          <div className="col-header">
            <div className="col-title">
              <Search size={16} /> Manual Review
            </div>
            <span className="col-count">{manualJobs.length}</span>
          </div>
          <div className="col-content">
            {manualJobs.map(job => <JobCard key={job.id} job={job} />)}
            {manualJobs.length === 0 && <div className="empty-state">No manual reviews pending</div>}
          </div>
        </div>

        {/* Column 3: Applied */}
        <div className="kanban-col col-applied">
          <div className="col-header">
            <div className="col-title">
              <Check size={16} /> Applied
            </div>
            <span className="col-count">{appliedJobs.length}</span>
          </div>
          <div className="col-content">
            {appliedJobs.map(job => <JobCard key={job.id} job={job} isAppliedCol={true} />)}
            {appliedJobs.length === 0 && <div className="empty-state">Get applying!</div>}
          </div>
        </div>

      </div>
    </div>
  )
}

export default App
