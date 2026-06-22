import { useState, useEffect } from 'react'
import { getJobHistory, updateOutcome } from '../api/jobs'

export default function History() {
  const [jobs, setJobs] = useState([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadHistory()
  }, [page])

  async function loadHistory() {
    setLoading(true)
    try {
      const data = await getJobHistory(page)
      setJobs(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function handleOutcome(jobId, status) {
    try {
      await updateOutcome(jobId, status)
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, _outcome: status } : j))
      )
    } catch (err) {
      alert('Failed to update outcome')
    }
  }

  if (loading) return <div className="text-gray-500">Loading history...</div>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Job History</h1>

      {jobs.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center text-gray-500">
          No jobs in your history yet.
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-200">
          {jobs.map((job) => (
            <div key={job.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-medium text-sm">{job.title}</div>
                  <div className="text-sm text-gray-600">{job.company}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {job.location} {job.salary && `· ${job.salary}`} &middot; Found {new Date(job.found_at).toLocaleDateString()}
                  </div>
                </div>
                <select
                  value={job._outcome || ''}
                  onChange={(e) => handleOutcome(job.id, e.target.value)}
                  className="text-xs border border-gray-300 rounded px-2 py-1"
                >
                  <option value="">Track outcome...</option>
                  <option value="applied">Applied</option>
                  <option value="heard_back">Heard Back</option>
                  <option value="interview">Interview</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-between">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          className="text-sm text-gray-500 hover:text-gray-900 disabled:opacity-50"
        >
          Previous
        </button>
        <span className="text-sm text-gray-500">Page {page}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={jobs.length < 20}
          className="text-sm text-gray-500 hover:text-gray-900 disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}
