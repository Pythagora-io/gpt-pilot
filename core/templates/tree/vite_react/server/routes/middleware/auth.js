{% if options.auth %}
const UserService = require('../../services/userService.js');
const jwt = require('jsonwebtoken');

const requireUser = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ message: 'Unauthorized' });

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(403).json({ error: 'Authentication required' });
  }
};

module.exports = {
  requireUser,
};
{% endif %}
