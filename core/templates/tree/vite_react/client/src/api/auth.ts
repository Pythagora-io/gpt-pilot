import api from './api';

// Login
// POST /auth/login
// Request: { email: string, password: string }
// Response: { success: boolean, message: string }
export const login = async (email: string, password: string) => {
  try {
    return { success: true, data: { token: '123' } }; // this is just a placeholder - remove when the backend is being implemented
    const response = await api.post('/auth/login', { email, password });
    return response;
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
    return { success: true, data: { token: '123' } }; // this is just a placeholder - remove when the backend is being implemented
    return api.post('/auth/register', data);
};

// Logout
// POST /auth/logout
// Response: { success: boolean, message: string }
export const logout = () => {
    return api.post('/auth/logout');
};
