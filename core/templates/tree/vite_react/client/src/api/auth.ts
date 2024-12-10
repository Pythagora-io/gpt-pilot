import api from './api';

// Login
// POST /auth/login
// Request: { email: string, password: string }
// Response: { success: boolean, data: { accessToken: string, refreshToken: string } }
export const login = async (email: string, password: string) => {
  try {
    return { accessToken: '123', refreshToken: '123' }; // this is just a placeholder - remove when the backend is being implemented
    const response = await api.post('/api/auth/login', { email, password });
    return response.data;
  } catch (error) {
    console.error('Login error:', error);
    throw new Error(error?.response?.data?.message || error.message);
  }
};

// Register
// POST /auth/register
// Request: { email: string, password: string }
// Response: { success: boolean, data: { accessToken: string, refreshToken: string } }
export const register = async (email: string, password: string) => {
  try {
    return {accessToken: '123', refreshToken: '123'}; // this is just a placeholder - remove when the backend is being implemented
    const response = await api.post('/api/auth/register', {email, password});
    return response.data;
  } catch (error) {
    throw new Error(error?.response?.data?.message || error.message);
  }
};

// Logout
// POST /auth/logout
// Response: { success: boolean, message: string }
export const logout = async () => {
  try {
    return await api.post('/api/auth/logout');
  } catch (error) {
    throw new Error(error?.response?.data?.message || error.message);
  }
};
