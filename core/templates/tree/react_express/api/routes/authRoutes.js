import { Router } from 'express';

import UserService from '../services/userService.js';
import { requireUser } from '../middlewares/authMiddleware.js';
import logger from '../utils/log.js';

const log = logger('api/routes/authRoutes');

const router = Router();

router.post('/api/auth/login', async (req, res) => {
  const sendError = msg => res.status(400).json({ error: msg });
  const { email, password } = req.body;

  if (!email || !password) {
    return sendError('Email and password are required');
  }

  const user = await UserService.authenticateWithPassword(email, password);

  if (user) {
    return res.json(user);
  } else {
    return sendError('Email or password is incorrect');

  }
});

router.get('/api/auth/login', (req, res) => res.status(405).json({ error: 'Login with POST instead' }));

router.post('/api/auth/register', async (req, res, next) => {
  if (req.user) {
    return res.json({ user: req.user });
  }
  try {
    const user = await UserService.createUser(req.body);
    return res.status(201).json(user);
  } catch (error) {
    log.error('Error while registering user', error);
    return res.status(400).json({ error });
  }
});

router.get('/api/auth/register', (req, res) => res.status(405).json({ error: 'Register with POST instead' }));

router.all('/api/auth/logout', async (req, res) => {
  if (req.user) {
    await UserService.regenerateToken(req.user);
  }
  return res.status(204).send();
});

router.post('/api/auth/password', requireUser, async (req, res) => {
  const { password } = req.body;

  if (!password) {
    return res.status(400).json({ error: 'Password is required' });
  }

  await UserService.setPassword(req.user, password);
  res.status(204).send();
});

router.get('/api/auth/me', requireUser, async (req, res) => {
  return res.status(200).json(req.user);
});

export default router;
