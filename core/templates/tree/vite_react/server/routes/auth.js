const express = require('express');
const UserService = require('../services/user.js');
const { requireUser } = require('./middleware/auth.js');
const logger = require('../utils/log.js');

const router = express.Router();
const log = logger('api/routes/authRoutes');

router.post('/login', async (req, res) => {
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

router.get('/login', (req, res) => res.status(405).json({ error: 'Login with POST instead' }));

router.post('/register', async (req, res, next) => {
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

router.get('/register', (req, res) => res.status(405).json({ error: 'Register with POST instead' }));

router.all('/logout', async (req, res) => {
  if (req.user) {
    await UserService.regenerateToken(req.user);
  }
  return res.status(204).send();
});

router.post('/password', requireUser, async (req, res) => {
  const { password } = req.body;

  if (!password) {
    return res.status(400).json({ error: 'Password is required' });
  }

  await UserService.setPassword(req.user, password);
  res.status(204).send();
});

router.get('/me', requireUser, async (req, res) => {
  return res.status(200).json(req.user);
});

module.exports = router;
