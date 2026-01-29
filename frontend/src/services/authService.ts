import api from './api'

export interface LoginResponse {
    access_token: string
    token_type: string
}

export interface User {
    id: number
    email: string
    full_name: string
    role: string
    preferred_language: string
    is_active: boolean
    practice_id: number
}

export const authService = {
    login: async (username: string, password: string): Promise<LoginResponse> => {
        const response = await api.post<LoginResponse>('/auth/login', { username, password })
        return response.data
    },

    getMe: async (): Promise<User> => {
        const response = await api.get<User>('/auth/me')
        return response.data
    },

    // Admin endpoints
    getUsers: async (): Promise<User[]> => {
        const response = await api.get<User[]>('/users/')
        return response.data
    },

    createUser: async (userData: Partial<User> & { password: string }): Promise<User> => {
        const response = await api.post<User>('/users/', userData)
        return response.data
    },

    updateUser: async (id: number, userData: Partial<User>): Promise<User> => {
        const response = await api.put<User>(`/users/${id}`, userData)
        return response.data
    }
}
