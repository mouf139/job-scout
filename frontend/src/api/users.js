import client from './client'

export async function listUsers() {
  const { data } = await client.get('/users/')
  return data
}

export async function createUser(name, email, password) {
  const { data } = await client.post('/users/', { name, email, password })
  return data
}

export async function updateUser(userId, updates) {
  const { data } = await client.patch(`/users/${userId}`, updates)
  return data
}

export async function deleteUser(userId) {
  await client.delete(`/users/${userId}`)
}

export async function impersonateUser(userId) {
  const { data } = await client.post(`/users/${userId}/impersonate`)
  return data
}
