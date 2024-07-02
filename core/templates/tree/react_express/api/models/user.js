import mongoose from 'mongoose';
import { randomUUID } from 'crypto';
import isEmail from 'validator/lib/isEmail.js';

import { generatePasswordHash, validatePassword, isPasswordHash } from '../utils/password.js';

const schema = new mongoose.Schema({
  email: {
    type: String,
    required: true,
    index: true,
    unique: true,
    lowercase: true,
    validate: { validator: isEmail, message: 'Invalid email' },
  },
  password: {
    type: String,
    required: true,
    validate: { validator: isPasswordHash, message: 'Invalid password hash' },
  },
  token: {
    type: String,
    unique: true,
    index: true,
    default: () => randomUUID(),
  },
  name: {
    type: String,
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

schema.methods.regenerateToken = async function regenerateToken() {
  this.token = randomUUID();
  if (!this.isNew) {
    await this.save();
  }
  return this;
};

const User = mongoose.model('User', schema);
export default User;
