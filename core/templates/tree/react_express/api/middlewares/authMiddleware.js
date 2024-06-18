import UserService from '../services/userService.js';

export const authenticateWithToken = (req, res, next) => {
  const authHeader = req.get('Authorization');
  if (authHeader) {
    const m = authHeader.match(/^(Token|Bearer) (.+)/i);
    if (m) {
      UserService.authenticateWithToken(m[2])
        .then((user) => {
          req.user = user;
          next();
        })
        .catch((err) => {
          next(err);
        });
      return;
    }
  }

  next();
};

export const requireUser = (req, res, next) => {
  if (!req.user) {
    return res.status(401).json({ error: 'Authentication required' });
  }

  next();
};
