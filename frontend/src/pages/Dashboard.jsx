import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getJobs, selectJobs, getDashboardStats } from '../api/jobs'
import { useAuth } from '../contexts/AuthContext'
import client from '../api/client'

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [jobs, setJobs] = useState([])
  const [stats, setStats] = useState(null)
  const [selected, setSelected] = useState(new Set())
  const [resumes, setResumes] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    if (!user?.onboarding_completed && user?.role !== 'admin') {
      navigate('/onboarding')
      return
    }
    loadData()
  }, [])

  async function loadData() {
    try {
      const [jobsData, statsData, resumesData] = await Promise.all([
        getJobs(),
        getDashboardStats(),
        client.get('/resumes/').then(r => r.data),
      ])
      setJobs(jobsData)
      setStats(statsData)
      setResumes(resumesData)
    } catch (err) {
      console.error('Failed to load dashboard data', err)
    } finally {
      setLoading(false)
    }
  }

  function toggleSelect(jobId) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(jobId)) next.delete(jobId)
      else next.add(jobId)
      return next
    })
  }

  async function handleGenerateResumes() {
    if (selected.size === 0) return
    setGenerating(true)
    try {
      await selectJobs([...selected])
      const { data } = await client.post('/resumes/generate', { job_listing_ids: [...selected] })
      alert(data.message + ' Resumes will appear below shortly.')
      setSelected(new Set())
      setTimeout(async () => {
        const r = await client.get('/resumes/')
        setResumes(r.data)
      }, 15000)
    } catch (err) {
      alert('Failed to generate resumes')
    } finally {
      setGenerating(false)
    }
  }

  if (loading) return <div className="text-gray-500">Loading dashboard...</div>

  return (
    <div className="space-y-6">
      {/* Status Panel */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-semibold">{stats?.jobs_scanned_today || 0}</div>
          <div className="text-sm text-gray-500">Jobs Today</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-semibold">{stats?.resumes_generated || 0}</div>
          <div className="text-sm text-gray-500">Resumes Generated</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-semibold capitalize">{stats?.pipeline_status || 'N/A'}</div>
          <div className="text-sm text-gray-500">Pipeline Status</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-semibold">
            {stats?.last_run ? new Date(stats.last_run).toLocaleDateString() : 'Never'}
          </div>
          <div className="text-sm text-gray-500">Last Run</div>
        </div>
      </div>

      {/* Scan Now */}
      <button
        onClick={async () => {
          try {
            await client.post('/settings/trigger-scan')
            alert('Job scan started. Refresh in a minute to see new results.')
          } catch (err) {
            alert(err.response?.data?.detail || 'Failed to trigger scan')
          }
        }}
        className="text-sm text-blue-600 hover:text-blue-800"
      >
        Scan for new jobs now
      </button>

      {/* Google Drive Link */}
      {user?.google_drive_folder_url && (
        <a
          href={user.google_drive_folder_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-sm text-blue-600 hover:text-blue-800"
        >
          Open Google Drive Folder
        </a>
      )}

      {/* Job Feed */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="text-lg font-medium">Today's Jobs</h2>
          <button
            onClick={handleGenerateResumes}
            disabled={selected.size === 0 || generating}
            className="bg-gray-900 text-white px-4 py-1.5 rounded-md text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
          >
            {generating ? 'Generating...' : `Generate Resumes (${selected.size})`}
          </button>
        </div>

        {jobs.length === 0 ? (
          <div className="px-4 py-12 text-center text-gray-500">
            No jobs found yet. Jobs will appear here after the first scan runs.
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {jobs.map((job) => (
              <div key={job.id} className="px-4 py-3 flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={selected.has(job.id)}
                  onChange={() => toggleSelect(job.id)}
                  className="mt-1 h-4 w-4 rounded border-gray-300"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{job.title}</span>
                    {job.is_new && (
                      <span className="bg-green-100 text-green-700 text-xs px-1.5 py-0.5 rounded">New</span>
                    )}
                    {!job.is_new && (
                      <span className="bg-gray-100 text-gray-500 text-xs px-1.5 py-0.5 rounded">Still Active</span>
                    )}
                    {job.match_score && (
                      <span className="bg-blue-100 text-blue-700 text-xs px-1.5 py-0.5 rounded">{job.match_score}% match</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-600">{job.company}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {job.location && <span>{job.location}</span>}
                    {job.salary && <span> &middot; {job.salary}</span>}
                    {job.posting_date && <span> &middot; {new Date(job.posting_date).toLocaleDateString()}</span>}
                  </div>
                  {job.apply_options_json && job.apply_options_json.length > 0 && (
                    <div className="flex gap-2 mt-1.5">
                      {job.apply_options_json.map((opt, i) => (
                        <a
                          key={i}
                          href={opt.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          Apply on {opt.title || opt.source || 'Link'}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* My Resumes */}
      {resumes.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-lg font-medium">My Tailored Resumes</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {resumes.map((r) => (
              <div key={r.id} className="px-4 py-3 flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{r.job_title}</div>
                  <div className="text-sm text-gray-500">{r.company}</div>
                  <div className="text-xs text-gray-400">{new Date(r.created_at).toLocaleString()}</div>
                </div>
                <div className="flex gap-3">
                  <a
                    href={`/api/resumes/${r.id}/download`}
                    className="bg-gray-900 text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-gray-800"
                  >
                    Download
                  </a>
                  {r.google_drive_url && (
                    <a
                      href={r.google_drive_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:text-blue-800 self-center"
                    >
                      Google Drive
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
