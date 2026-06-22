import client from './client'

export async function getJobs() {
  const { data } = await client.get('/jobs/')
  return data
}

export async function getJobHistory(page = 1) {
  const { data } = await client.get(`/jobs/history?page=${page}`)
  return data
}

export async function selectJobs(jobIds) {
  const { data } = await client.post('/jobs/select', { job_listing_ids: jobIds })
  return data
}

export async function updateOutcome(jobId, status) {
  const { data } = await client.put(`/jobs/${jobId}/outcome`, { status })
  return data
}

export async function getDashboardStats() {
  const { data } = await client.get('/settings/dashboard-stats')
  return data
}
