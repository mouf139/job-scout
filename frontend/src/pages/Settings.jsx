import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

export default function Settings() {
  const navigate = useNavigate()
  const [criteria, setCriteria] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    titles: '',
    include_keywords: '',
    exclude_keywords: '',
    location: '',
    radius_miles: 25,
    remote_preference: 'any',
    experience_level: '',
    job_type: 'full_time',
    salary_minimum: '',
    industries: '',
    timezone: 'America/New_York',
    email_notifications_enabled: false,
  })

  useEffect(() => {
    loadCriteria()
  }, [])

  async function loadCriteria() {
    try {
      const { data } = await client.get('/settings/criteria')
      if (data) {
        setCriteria(data)
        setForm({
          titles: data.titles?.join(', ') || '',
          include_keywords: data.include_keywords?.join(', ') || '',
          exclude_keywords: data.exclude_keywords?.join(', ') || '',
          location: data.location || '',
          radius_miles: data.radius_miles || 25,
          remote_preference: data.remote_preference || 'any',
          experience_level: data.experience_level || '',
          job_type: data.job_type || 'full_time',
          salary_minimum: data.salary_minimum || '',
          industries: data.industries?.join(', ') || '',
          timezone: data.timezone || 'America/New_York',
          email_notifications_enabled: data.email_notifications_enabled || false,
        })
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  function handleChange(e) {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        titles: form.titles ? form.titles.split(',').map((s) => s.trim()) : [],
        include_keywords: form.include_keywords ? form.include_keywords.split(',').map((s) => s.trim()) : [],
        exclude_keywords: form.exclude_keywords ? form.exclude_keywords.split(',').map((s) => s.trim()) : [],
        location: form.location,
        radius_miles: parseInt(form.radius_miles) || 25,
        remote_preference: form.remote_preference,
        experience_level: form.experience_level,
        job_type: form.job_type,
        salary_minimum: parseInt(form.salary_minimum) || null,
        industries: form.industries ? form.industries.split(',').map((s) => s.trim()) : [],
        timezone: form.timezone,
        email_notifications_enabled: form.email_notifications_enabled,
      }
      await client.put('/settings/criteria', payload)
      alert('Settings saved')
    } catch (err) {
      alert('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="text-gray-500">Loading settings...</div>

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold">Search Settings</h1>
      <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Job Titles</label>
            <input name="titles" value={form.titles} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
            <input name="location" value={form.location} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Include Keywords</label>
            <input name="include_keywords" value={form.include_keywords} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Exclude Keywords</label>
            <input name="exclude_keywords" value={form.exclude_keywords} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Radius (miles)</label>
            <input name="radius_miles" type="number" value={form.radius_miles} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Remote Preference</label>
            <select name="remote_preference" value={form.remote_preference} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
              <option value="any">Any</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="on_site">On-site</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Job Type</label>
            <select name="job_type" value={form.job_type} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
              <option value="full_time">Full-time</option>
              <option value="part_time">Part-time</option>
              <option value="internship">Internship</option>
              <option value="contract">Contract</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Minimum Salary</label>
            <input name="salary_minimum" type="number" value={form.salary_minimum} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Industries</label>
            <input name="industries" value={form.industries} onChange={handleChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div className="sm:col-span-2">
            <label className="flex items-center gap-2 text-sm">
              <input name="email_notifications_enabled" type="checkbox" checked={form.email_notifications_enabled} onChange={handleChange} className="h-4 w-4 rounded border-gray-300" />
              <span className="font-medium text-gray-700">Enable email notifications</span>
            </label>
          </div>
        </div>
        <button
          type="submit"
          disabled={saving}
          className="bg-gray-900 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>

      <ResumeSection onReplace={() => navigate('/onboarding')} />
    </div>
  )
}

function ResumeSection({ onReplace }) {
  const [resume, setResume] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [file, setFile] = useState(null)

  useEffect(() => {
    loadResume()
  }, [])

  async function loadResume() {
    try {
      const { data } = await client.get('/onboarding/status')
      setResume(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setUploading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      await client.post('/onboarding/upload-resume', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setFile(null)
      alert('Resume replaced successfully')
      loadResume()
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  if (loading) return null

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
      <h2 className="text-lg font-semibold">Base Resume</h2>
      <p className="text-sm text-gray-500">
        {resume?.has_resume
          ? 'Your base resume is on file. Upload a new one to replace it.'
          : 'No base resume uploaded yet.'}
      </p>
      <form onSubmit={handleUpload} className="flex flex-wrap items-end gap-3">
        <input
          type="file"
          accept=".pdf,.docx"
          onChange={(e) => setFile(e.target.files[0])}
          className="block text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
        />
        <button
          type="submit"
          disabled={!file || uploading}
          className="bg-gray-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
        >
          {uploading ? 'Uploading...' : 'Replace Resume'}
        </button>
      </form>

      <div className="pt-2 border-t border-gray-200">
        <p className="text-sm text-gray-500 mb-2">Want to redo the full onboarding interview?</p>
        <button
          onClick={async () => {
            try {
              await client.post('/onboarding/restart')
              onReplace()
            } catch (err) {
              alert('Failed to restart onboarding')
            }
          }}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Restart Onboarding
        </button>
      </div>
    </div>
  )
}
