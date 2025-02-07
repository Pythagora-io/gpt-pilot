{% if options.auth %}
const jwt = require('jsonwebtoken');

const generateAccessToken = (user) => {
  return jwt.sign(user.toObject(), process.env.JWT_SECRET, { expiresIn: '1d' }); // TODO set to 15 minutes
};

const generateRefreshToken = (user) => {
  return jwt.sign(user.toObject(), process.env.REFRESH_TOKEN_SECRET, { expiresIn: '30d' });
};

module.exports = {
  generateAccessToken,
  generateRefreshToken
};
{% endif %}
