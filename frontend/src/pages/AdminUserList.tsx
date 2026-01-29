import React, { useEffect, useState } from 'react'
import { authService, User } from '../services/authService'
import { useAppStore } from '../stores/appStore'

const AdminUserList = () => {
    const [users, setUsers] = useState<User[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [showAddForm, setShowAddForm] = useState(false)
    const { userRole } = useAppStore()

    // Form state
    const [newUser, setNewUser] = useState({
        email: '',
        password: '',
        full_name: '',
        role: 'assistant',
        preferred_language: 'de'
    })

    const fetchUsers = async () => {
        try {
            const data = await authService.getUsers()
            setUsers(data)
            setError('')
        } catch (err: any) {
            setError('Failed to load users')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (userRole === 'admin') {
            fetchUsers()
        }
    }, [userRole])

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            await authService.createUser(newUser)
            setShowAddForm(false)
            setNewUser({
                email: '',
                password: '',
                full_name: '',
                role: 'assistant',
                preferred_language: 'de'
            })
            fetchUsers()
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to create user')
        }
    }

    if (userRole !== 'admin') {
        return <div className="p-4">Access Denied</div>
    }

    if (loading) return <div className="p-4">Loading users...</div>

    return (
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            <div className="px-4 py-5 sm:px-6 flex justify-between items-center">
                <div>
                    <h3 className="text-lg leading-6 font-medium text-gray-900">User Management</h3>
                    <p className="mt-1 max-w-2xl text-sm text-gray-500">Manage practice users and roles.</p>
                </div>
                <button
                    onClick={() => setShowAddForm(!showAddForm)}
                    className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700"
                >
                    {showAddForm ? 'Cancel' : 'Add User'}
                </button>
            </div>

            {error && <div className="text-red-500 px-4">{error}</div>}

            {showAddForm && (
                <div className="bg-white shadow sm:rounded-lg mb-6 mx-4 p-4 border border-gray-200">
                    <h4 className="text-md font-medium mb-4">Add New User</h4>
                    <form onSubmit={handleCreateUser} className="space-y-4 max-w-lg">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Full Name</label>
                            <input
                                type="text"
                                required
                                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                                value={newUser.full_name}
                                onChange={e => setNewUser({ ...newUser, full_name: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Email</label>
                            <input
                                type="email"
                                required
                                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                                value={newUser.email}
                                onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Password</label>
                            <input
                                type="password"
                                required
                                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                                value={newUser.password}
                                onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Role</label>
                            <select
                                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                                value={newUser.role}
                                onChange={e => setNewUser({ ...newUser, role: e.target.value })}
                            >
                                <option value="de">Deutsch (German)</option>
                                <option value="en">English</option>
                                <option value="fr">Français (French)</option>
                                <option value="es">Español (Spanish)</option>
                                <option value="it">Italiano (Italian)</option>
                                <option value="pt">Português (Portuguese)</option>
                                <option value="nl">Nederlands (Dutch)</option>
                                <option value="pl">Polski (Polish)</option>
                                <option value="ru">Русский (Russian)</option>
                                <option value="tr">Türkçe (Turkish)</option>
                                <option value="da">Dansk (Danish)</option>
                                <option value="sv">Svenska (Swedish)</option>
                                <option value="no">Norsk (Norwegian)</option>
                                <option value="fi">Suomi (Finnish)</option>
                                <option value="el">Ελληνικά (Greek)</option>
                                <option value="cs">Čeština (Czech)</option>
                                <option value="hu">Magyar (Hungarian)</option>
                                <option value="ro">Română (Romanian)</option>
                                <option value="bg">Български (Bulgarian)</option>
                                <option value="hr">Hrvatski (Croatian)</option>
                                <option value="sk">Slovenčina (Slovak)</option>
                                <option value="sl">Slovenščina (Slovenian)</option>
                                <option value="et">Eesti (Estonian)</option>
                                <option value="lv">Latviešu (Latvian)</option>
                                <option value="lt">Lietuvių (Lithuanian)</option>
                            </select>
                        </div>
                        <button
                            type="submit"
                            className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
                        >
                            Save User
                        </button>
                    </form>
                </div>
            )}

            <div className="flex flex-col">
                <div className="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                    <div className="py-2 align-middle inline-block min-w-full sm:px-6 lg:px-8">
                        <div className="shadow overflow-hidden border-b border-gray-200 sm:rounded-lg">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Name
                                        </th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Email
                                        </th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Role
                                        </th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Language
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {users.map((user) => (
                                        <tr key={user.id}>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm font-medium text-gray-900">{user.full_name}</div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm text-gray-500">{user.email}</div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                                    {user.role}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {user.preferred_language}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default AdminUserList
