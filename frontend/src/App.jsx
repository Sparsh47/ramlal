import { useState, useEffect } from 'react'
import axios from 'axios'
import { ExternalLink, CheckCircle, Clock, Building2, Search, BrainCircuit, RotateCcw } from 'lucide-react'
import './App.css'

function App() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all') // all, ready, manual, applied

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

  const filteredJobs = jobs.filter(job => {
    if (filter === 'applied') return job.applied
    if (filter === 'ready') return job.auto_apply_ready && !job.applied
    if (filter === 'manual') return !job.auto_apply_ready && !job.applied
    return !job.applied // 'all' unapplied
  })

  if (loading) {
    return (
      <div className="loader">
        <div className="spinner"></div>
        Loading AI Job Matches...
      </div>
    )
  }

  return (
    <div className="container">
      <header>
        <h1>Job Agent AI</h1>
        <p className="subtitle">Found {jobs.length} high-quality matches based on your profile.</p>
      </header>

      <div className="tabs">
        <button className={`tab-btn ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>
          Pending ({jobs.filter(j => !j.applied).length})
        </button>
        <button className={`tab-btn ${filter === 'ready' ? 'active' : ''}`} onClick={() => setFilter('ready')}>
          Auto-Apply Ready ({jobs.filter(j => j.auto_apply_ready && !j.applied).length})
        </button>
        <button className={`tab-btn ${filter === 'manual' ? 'active' : ''}`} onClick={() => setFilter('manual')}>
          Manual Review ({jobs.filter(j => !j.auto_apply_ready && !j.applied).length})
        </button>
        <button className={`tab-btn ${filter === 'applied' ? 'active' : ''}`} onClick={() => setFilter('applied')}>
          Applied ({jobs.filter(j => j.applied).length})
        </button>
      </div>

      <div className="jobs-grid">
        {filteredJobs.map(job => (
          <div key={job.id} className={`job-card ${job.applied ? 'is-applied' : ''}`}>
            
            <div className="applied-overlay">
              <div className="applied-badge">
                <CheckCircle size={24} />
                Applied
              </div>
              <button className="unapply-btn" onClick={() => toggleApply(job.id)}>
                <RotateCcw size={16} /> Undo
              </button>
            </div>

            <div className="job-content">
              <div className="job-header">
                <div>
                  <h2 className="job-title">{job.title}</h2>
                  <div className="job-company">
                    <Building2 size={16} /> {job.company}
                  </div>
                </div>
                <div className={`score-badge ${job.score >= 9 ? 'high' : job.score >= 8 ? 'medium' : 'low'}`}>
                  {job.score.toFixed(1)}
                </div>
              </div>

              <div className="job-meta">
                {job.auto_apply_ready ? (
                  <span className="meta-tag ready"><BrainCircuit size={14}/> Full JD Parsed</span>
                ) : (
                  <span className="meta-tag"><Search size={14}/> Snippet Only</span>
                )}
                <span className="meta-tag"><Clock size={14}/> {new Date(job.date_found).toLocaleDateString()}</span>
              </div>

              <p className="job-reasons">"{job.reasons}"</p>

              <div className="job-actions">
                <a href={job.url} target="_blank" rel="noopener noreferrer" className="btn btn-outline">
                  View Job <ExternalLink size={16} />
                </a>
                <button 
                  className={`btn ${job.auto_apply_ready ? 'btn-success' : 'btn-primary'}`}
                  onClick={() => toggleApply(job.id)}
                >
                  <CheckCircle size={18} /> Mark Applied
                </button>
              </div>
            </div>

          </div>
        ))}

        {filteredJobs.length === 0 && (
          <div style={{gridColumn: '1 / -1', textAlign: 'center', padding: '4rem', color: 'var(--text-muted)'}}>
            <h3>No jobs found in this category.</h3>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
