const mongoose = require('mongoose');

const { validatePassword, isPasswordHash } = require('../utils/password.js');

const schema = new mongoose.Schema({
  email: {
    type: String,
    required: true,
    index: true,
    unique: true,
    lowercase: true,
  },
  password: {
    type: String,
    required: true,
    validate: { validator: isPasswordHash, message: 'Invalid password hash' },
  },
  createdAt: {
    type: Date,
    default: Date.now,
    immutable: true,
  },
  lastLoginAt: {
    type: Date,
    default: Date.now,
  },
  isActive: {
    type: Boolean,
    default: true,
  },
}, {
  versionKey: false,
});

schema.set('toJSON', {
  /* eslint-disable */
  transform: (doc, ret, options) => {
    delete ret._id;
    delete ret.password;
    return ret;
  },
  /* eslint-enable */
});

schema.statics.authenticateWithPassword = async function authenticateWithPassword(email, password) {
  const user = await this.findOne({ email }).exec();
  if (!user) return null;

  const passwordValid = await validatePassword(password, user.password);
  if (!passwordValid) return null;

  user.lastLoginAt = Date.now();
  const updatedUser = await user.save();

  return updatedUser;
};

schema.pre('save', async function(next) {
  if (this.isModified('password')) {
    try {
      this.password = await bcrypt.hash(this.password, 10);
    } catch (error) {
      console.error('Error hashing password:', error);
      next(error);
    }
  }
  next();
});

const User = mongoose.model('User', schema);

module.exports = User;
