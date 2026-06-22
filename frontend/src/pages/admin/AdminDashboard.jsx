import { useState, useEffect } from 'react'
import { listUsers, createUser, updateUser, deleteUser, impersonateUser } from '../../api/users'
import { useAuth } from '../../contexts/AuthContext'

export default function AdminDashboard() {
  const { loginUser } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newUser, setNewUser] = useState({ name: '', email: '', password: '' })
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    loadUsers()
  }, [])

  async function loadUsers() {
    try {
      const data = await listUsers()
      setUsers(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setCreating(true)
    try {
      await createUser(newUser.name, newUser.email, newUser.password)
      setNewUser({ name: '', email: '', password: '' })
      setShowCreate(false)
      loadUsers()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create user')
    } finally {
      setCreating(false)
    }
  }

  async function handleToggleActive(user) {
    try {
      await updateUser(user.id, { is_active: !user.is_active })
      loadUsers()
    } catch (err) {
      alert('Failed to update user')
    }
  }

  async function handleDelete(user) {
    if (!confirm(`Delete ${user.name}? This cannot be undone.`)) return
    try {
      await deleteUser(user.id)
      loadUsers()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete user')
    }
  }

  async function handleImpersonate(user) {
    try {
      const data = await impersonateUser(user.id)
      loginUser(data.access_token, { ...user, role: user.role })
      window.location.href = '/dashboard'
    } catch (err) {
      alert('Failed to impersonate')
    }
  }

  if (loading) return <div className="text-gray-500">Loading users...</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">User Management</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="bg-gray-900 text-white px-4 py-1.5 rounded-md text-sm font-medium hover:bg-gray-800"
        >
          {showCreate ? 'Cancel' : 'Create User'}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-white rounded-lg border border-gray-200 p-4 flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
            <input
              value={newUser.name}
              onChange={(e) => setNewUser((p) => ({ ...p, name: e.target.value }))}
              required
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Email</label>
            <input
              type="email"
              value={newUser.email}
              onChange={(e) => setNewUser((p) => ({ ...p, email: e.target.value }))}
              required
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Temp Password</label>
            <input
              type="password"
              value={newUser.password}
              onChange={(e) => setNewUser((p) => ({ ...p, password: e.target.value }))}
              required
              minLength={8}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={creating}
            className="bg-gray-900 text-white px-4 py-1.5 rounded-md text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
          >
            {creating ? 'Creating...' : 'Create'}
          </button>
        </form>
      )}

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-2 font-medium text-gray-500">Name</th>
                <th className="text-left px-4 py-2 font-medium text-gray-500">Email</th>
                <th className="text-left px-4 py-2 font-medium text-gray-500">Status</th>
                <th className="text-left px-4 py-2 font-medium text-gray-500">Jobs</th>
                <th className="text-left px-4 py-2 font-medium text-gray-500">Resumes</th>
                <th className="text-left px-4 py-2 font-medium text-gray-500">Last Run</th>
                <th className="text-left px-4 py-2 font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-2">
                    {u.name}
                    {u.role === 'admin' && (
                      <span className="ml-1 text-xs text-gray-400">(admin)</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-gray-500">{u.email}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                    {!u.onboarding_completed && u.role !== 'admin' && (
                      <span className="ml-1 text-xs text-yellow-600">Setup pending</span>
                    )}
                  </td>
                  <td className="px-4 py-2">{u.jobs_found}</td>
                  <td className="px-4 py-2">{u.resumes_generated}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">
                    {u.last_run ? new Date(u.last_run).toLocaleString() : 'Never'}
                    {u.last_error && <div className="text-red-500 truncate max-w-[150px]">{u.last_error}</div>}
                  </td>
                  <td className="px-4 py-2">
                    {u.role !== 'admin' && (
                      <div className="flex gap-2">
                        <button onClick={() => handleImpersonate(u)} className="text-xs text-blue-600 hover:text-blue-800">
                          Impersonate
                        </button>
                        <button onClick={() => handleToggleActive(u)} className="text-xs text-gray-500 hover:text-gray-900">
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button onClick={() => handleDelete(u)} className="text-xs text-red-500 hover:text-red-700">
                          Delete
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
