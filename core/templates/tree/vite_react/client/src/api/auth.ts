import api from './api';

// Login
// POST /auth/login
// Request: { email: string, password: string }
// Response: { success: boolean, message: string, token: string }
export const login = async (email: string, password: string) => {
  try {
    const response = await api.post('/auth/login', { email, password });
    localStorage.setItem('authToken', response.data.token);
    return response.data;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

// Register
// POST /auth/register
// Request: { email: string, password: string }
// Response: { success: boolean, message: string }
export const register = (data: { email: string; password: string }) => {
    return api.post('/auth/register', data);
};

// Logout
// POST /auth/logout
// Response: { success: boolean, message: string }
export const logout = () => {
    return api.post('/auth/logout');
};