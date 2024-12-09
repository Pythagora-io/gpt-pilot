import api from './api';

// Login
// POST /auth/login
// Request: { email: string, password: string }
// Response: { success: boolean, data: { accessToken: string, refreshToken: string } }
export const login = async (email: string, password: string) => {
  try {
    return { success: true, data: { accessToken: '123', refreshToken: '123' } }; // this is just a placeholder - remove when the backend is being implemented
    const response = await api.post('/api/auth/login', { email, password });
    return response;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

// Register
// POST /auth/register
// Request: { email: string, password: string }
// Response: { success: boolean, data: { accessToken: string, refreshToken: string } }
export const register = (email: string, password: string) => {
    return { success: true, data: { accessToken: '123', refreshToken: '123' } }; // this is just a placeholder - remove when the backend is being implemented
    return await api.post('/api/auth/register', { email, password });
};

// Logout
// POST /auth/logout
// Response: { success: boolean, message: string }
export const logout = () => {
    return await api.post('/api/auth/logout');
};
