import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import client from '../api/client'

export default function Onboarding() {
  const { user, updateUser } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStatus()
  }, [])

  async function loadStatus() {
    try {
      const { data } = await client.get('/onboarding/status')
      setStatus(data)
      if (data.onboarding_completed) {
        navigate('/dashboard')
        return
      }
      if (data.criteria_set) setStep(4)
      else if (data.interview_completed) setStep(3)
      else if (data.has_resume) setStep(2)
      else setStep(1)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  function handleResumeUploaded(extraction) {
    setStatus((s) => ({ ...s, has_resume: true, has_extraction: !!extraction }))
    setStep(2)
  }

  function handleInterviewDone() {
    setStatus((s) => ({ ...s, interview_completed: true }))
    setStep(3)
  }

  function handleCriteriaApproved() {
    updateUser({ onboarding_completed: true })
    navigate('/dashboard')
  }

  const steps = [
    { num: 1, label: 'Upload Resume' },
    { num: 2, label: 'AI Interview' },
    { num: 3, label: 'Review Criteria' },
  ]

  if (loading) return <div className="text-gray-500">Loading...</div>

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold">Welcome to Job Scout</h1>
      <p className="text-sm text-gray-500">Let's set up your job search profile.</p>

      <div className="flex items-center gap-2">
        {steps.map((s) => (
          <div key={s.num} className="flex items-center gap-2">
            <button
              onClick={() => setStep(s.num)}
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium cursor-pointer transition-colors ${
                step === s.num
                  ? 'bg-gray-900 text-white'
                  : step > s.num
                    ? 'bg-gray-700 text-white hover:bg-gray-600'
                    : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
              }`}
            >
              {s.num}
            </button>
            <span
              onClick={() => setStep(s.num)}
              className="text-sm text-gray-600 hidden sm:inline cursor-pointer hover:text-gray-900"
            >
              {s.label}
            </span>
            {s.num < 3 && <div className="w-8 h-px bg-gray-300" />}
          </div>
        ))}
      </div>

      {step === 1 && <ResumeUpload onDone={handleResumeUploaded} />}
      {step === 2 && (
        <InterviewChat
          sessionId={status?.active_session_id}
          onDone={handleInterviewDone}
          onSkip={() => setStep(3)}
        />
      )}
      {step === 3 && <CriteriaReview onDone={handleCriteriaApproved} />}
    </div>
  )
}

function ResumeUpload({ onDone }) {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [extraction, setExtraction] = useState(null)

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setUploading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const { data } = await client.post('/onboarding/upload-resume', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setExtraction(data.extraction)
      onDone(data.extraction)
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <form onSubmit={handleUpload} className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
      <h2 className="font-medium">Upload Your Resume</h2>
      <p className="text-sm text-gray-500">
        Upload your current resume (.pdf or .docx). We'll analyze it with AI to pre-fill your profile.
      </p>
      <input
        type="file"
        accept=".pdf,.docx"
        onChange={(e) => setFile(e.target.files[0])}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
      />
      <button
        type="submit"
        disabled={!file || uploading}
        className="bg-gray-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
      >
        {uploading ? 'Uploading & Analyzing...' : 'Upload & Continue'}
      </button>
    </form>
  )
}

function InterviewChat({ sessionId: initialSessionId, onDone, onSkip }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sessionId, setSessionId] = useState(initialSessionId)
  const [started, setStarted] = useState(false)
  const [complete, setComplete] = useState(false)
  const messagesEnd = useRef(null)

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function startInterview() {
    setSending(true)
    try {
      const { data } = await client.post('/onboarding/interview/start')
      setSessionId(data.session_id)
      setMessages([{ role: 'assistant', content: data.reply }])
      setStarted(true)
      if (data.is_complete) setComplete(true)
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to start interview'
      if (err.response?.status === 503 || detail.includes('unavailable')) {
        alert(detail + '\n\nYou can still set up your profile using the manual entry form.')
        onSkip()
        return
      }
      alert(detail)
    } finally {
      setSending(false)
    }
  }

  async function sendMessage(e) {
    e.preventDefault()
    if (!input.trim() || sending) return

    const userMsg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setSending(true)

    try {
      const { data } = await client.post('/onboarding/interview/message', {
        message: userMsg,
        session_id: sessionId,
      })
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
      if (data.is_complete) setComplete(true)
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h2 className="font-medium">AI Interview</h2>
        <button onClick={onSkip} className="text-xs text-gray-500 hover:text-gray-900">
          Skip to manual entry
        </button>
      </div>

      {!started ? (
        <div className="p-6 text-center space-y-3">
          <p className="text-sm text-gray-500">
            Our AI will review your resume and ask a few questions about your job preferences.
            It usually takes 5-7 questions.
          </p>
          <button
            onClick={startInterview}
            disabled={sending}
            className="bg-gray-900 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
          >
            {sending ? 'Starting...' : 'Start Interview'}
          </button>
        </div>
      ) : (
        <>
          <div className="h-80 overflow-y-auto px-4 py-3 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                  msg.role === 'user'
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
                  dangerouslySetInnerHTML={
                    msg.role === 'assistant'
                      ? { __html: msg.content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>') }
                      : undefined
                  }
                >
                  {msg.role === 'user' ? msg.content : undefined}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-gray-100 text-gray-400 px-3 py-2 rounded-lg text-sm">Thinking...</div>
              </div>
            )}
            <div ref={messagesEnd} />
          </div>

          {complete ? (
            <div className="px-4 py-3 border-t border-gray-200 text-center">
              <p className="text-sm text-gray-500 mb-2">Interview complete!</p>
              <button
                onClick={onDone}
                className="bg-gray-900 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-gray-800"
              >
                Review Criteria
              </button>
            </div>
          ) : (
            <form onSubmit={sendMessage} className="flex px-4 py-3 border-t border-gray-200 gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your answer..."
                disabled={sending}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
              />
              <button
                type="submit"
                disabled={!input.trim() || sending}
                className="bg-gray-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
              >
                Send
              </button>
            </form>
          )}
        </>
      )}
    </div>
  )
}

function CriteriaReview({ onDone }) {
  const [criteria, setCriteria] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    generateCriteria()
  }, [])

  async function generateCriteria() {
    try {
      const { data } = await client.post('/onboarding/interview/generate-criteria')
      setCriteria(data.criteria)
    } catch (err) {
      setCriteria({
        titles: [],
        include_keywords: [],
        exclude_keywords: [],
        location: '',
        radius_miles: 25,
        remote_preference: 'any',
        experience_level: '',
        job_type: 'full_time',
        salary_minimum: null,
        industries: [],
      })
    } finally {
      setLoading(false)
    }
  }

  function handleChange(field, value) {
    setCriteria((prev) => ({ ...prev, [field]: value }))
  }

  function handleArrayChange(field, value) {
    setCriteria((prev) => ({
      ...prev,
      [field]: value.split(',').map((s) => s.trim()).filter(Boolean),
    }))
  }

  async function handleApprove() {
    setSaving(true)
    try {
      await client.post('/onboarding/criteria/approve', criteria)
      onDone()
    } catch (err) {
      alert('Failed to save criteria')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
        <p className="text-sm text-gray-500">Generating search criteria from your profile...</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">Recommended Search Criteria</h2>
        <button
          onClick={() => setEditing(!editing)}
          className="text-xs text-blue-600 hover:text-blue-800"
        >
          {editing ? 'Done Editing' : 'Edit'}
        </button>
      </div>
      <p className="text-sm text-gray-500">
        These criteria were generated from your resume and interview. Review and approve them to start scanning for jobs.
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        <CriteriaField
          label="Target Titles"
          value={criteria.titles?.join(', ') || ''}
          editing={editing}
          onChange={(v) => handleArrayChange('titles', v)}
        />
        <CriteriaField
          label="Location"
          value={criteria.location || ''}
          editing={editing}
          onChange={(v) => handleChange('location', v)}
        />
        <CriteriaField
          label="Include Keywords"
          value={criteria.include_keywords?.join(', ') || ''}
          editing={editing}
          onChange={(v) => handleArrayChange('include_keywords', v)}
        />
        <CriteriaField
          label="Exclude Keywords"
          value={criteria.exclude_keywords?.join(', ') || ''}
          editing={editing}
          onChange={(v) => handleArrayChange('exclude_keywords', v)}
        />
        <CriteriaField
          label="Radius (miles)"
          value={String(criteria.radius_miles || 25)}
          editing={editing}
          onChange={(v) => handleChange('radius_miles', parseInt(v) || 25)}
        />
        <CriteriaField
          label="Remote Preference"
          value={criteria.remote_preference || 'any'}
          editing={editing}
          onChange={(v) => handleChange('remote_preference', v)}
          options={['any', 'remote', 'hybrid', 'on_site']}
        />
        <CriteriaField
          label="Job Type"
          value={criteria.job_type || 'full_time'}
          editing={editing}
          onChange={(v) => handleChange('job_type', v)}
          options={['full_time', 'part_time', 'internship', 'contract']}
        />
        <CriteriaField
          label="Experience Level"
          value={criteria.experience_level || ''}
          editing={editing}
          onChange={(v) => handleChange('experience_level', v)}
          options={['entry', 'mid', 'senior', 'executive']}
        />
        <CriteriaField
          label="Minimum Salary"
          value={String(criteria.salary_minimum || '')}
          editing={editing}
          onChange={(v) => handleChange('salary_minimum', parseInt(v) || null)}
        />
        <CriteriaField
          label="Industries"
          value={criteria.industries?.join(', ') || ''}
          editing={editing}
          onChange={(v) => handleArrayChange('industries', v)}
        />
      </div>

      <button
        onClick={handleApprove}
        disabled={saving}
        className="w-full bg-gray-900 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
      >
        {saving ? 'Saving...' : 'Approve & Start Scanning'}
      </button>
    </div>
  )
}

function CriteriaField({ label, value, editing, onChange, options }) {
  if (!editing) {
    return (
      <div>
        <div className="text-xs font-medium text-gray-500">{label}</div>
        <div className="text-sm mt-0.5">{value || <span className="text-gray-400">Not set</span>}</div>
      </div>
    )
  }

  if (options) {
    return (
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-1.5 border border-gray-300 rounded-md text-sm"
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>{opt.replace('_', ' ')}</option>
          ))}
        </select>
      </div>
    )
  }

  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-1.5 border border-gray-300 rounded-md text-sm"
      />
    </div>
  )
}
