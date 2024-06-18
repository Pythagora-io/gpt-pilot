import { randomUUID } from 'crypto';

{% set mongoose = options.db_type == 'nosql' %}
{% if mongoose %}
import User from '../models/user.js';
{% else %}
import { User } from '../models/init.js';
{% endif %}
import { generatePasswordHash, validatePassword } from '../utils/password.js';

class UserService {
  static async list() {
    try {
{% if mongoose %}
      return User.find();
{% else %}
      const users = await User.findMany();
      return users.map((u) => ({ ...u, password: undefined }));
{% endif %}
    } catch (err) {
      throw `Database error while listing users: ${err}`;
    }
  }

  static async get(id) {
    try {
{% if mongoose %}
      return User.findOne({ _id: id }).exec();
{% else %}
      const user = await User.findUnique({
        where: { id },
      });

      if (!user) return null;

      delete user.password;
      return user;
{% endif %}
    } catch (err) {
      throw `Database error while getting the user by their ID: ${err}`;
    }
  }

  static async getByEmail(email) {
    try {
{% if mongoose %}
      return User.findOne({ email }).exec();
{% else %}
      const user = await User.findUnique({
        where: { email },
      });

      if (!user) return null;

      delete user.password;
      return user;
{% endif %}
    } catch (err) {
      throw `Database error while getting the user by their email: ${err}`;
    }
  }

  static async update(id, data) {
    try {
{% if mongoose %}
      return User.findOneAndUpdate({ _id: id }, data, { new: true, upsert: false });
{% else %}
      return User.update({
        where: { id },
      }, {
        data,
      });
{% endif %}
    } catch (err) {
      throw `Database error while updating user ${id}: ${err}`;
    }
  }

  static async delete(id) {
    try {
{% if mongoose %}
      const result = await User.deleteOne({ _id: id }).exec();
      return (result.deletedCount === 1);
{% else %}
      return User.delete({
        where: { id },
      });
{% endif %}
    } catch (err) {
      throw `Database error while deleting user ${id}: ${err}`;
    }
  }

  static async authenticateWithPassword(email, password) {
    if (!email) throw 'Email is required';
    if (!password) throw 'Password is required';

    try {
{% if mongoose %}
      const user = await User.findOne({email}).exec();
{% else %}
      const user = await User.findUnique({
        where: {email},
      });
{% endif %}
      if (!user) return null;

      const passwordValid = await validatePassword(password, user.password);
      if (!passwordValid) return null;

{% if mongoose %}
      user.lastLoginAt = Date.now();
      const updatedUser = await user.save();
{% else %}
      user.lastLoginAt = new Date();
      const updatedUser = await User.update({
        where: { id: user.id },
        data: { lastLoginAt: user.lastLoginAt },
      });

      delete updatedUser.password;
{% endif %}
      return updatedUser;
    } catch (err) {
      throw `Database error while authenticating user ${email} with password: ${err}`;
    }
  }

  static async authenticateWithToken(token) {
    try {
{% if mongoose %}
      return User.findOne({ token }).exec();
{% else %}
      const user = await User.findUnique({
        where: { token },
      });
      if (!user) return null;

      delete user.password;
      return user;
{% endif %}
    } catch (err) {
      throw `Database error while authenticating user ${email} with token: ${err}`;
    }
  }

  static async createUser({ email, password, name = '' }) {
    if (!email) throw 'Email is required';
    if (!password) throw 'Password is required';

    const existingUser = await UserService.getByEmail(email);
    if (existingUser) throw 'User with this email already exists';

    const hash = await generatePasswordHash(password);

    try {
{% if mongoose %}
      const user = new User({
        email,
        password: hash,
        name,
        token: randomUUID(),
      });

      await user.save();
{% else %}
      const data = {
        email,
        password: hash,
        name,
        token: randomUUID(),
      };

      const user = await User.create({ data });

      delete user.password;
{% endif %}
      return user;
    } catch (err) {
      throw `Database error while creating new user: ${err}`;
    }
  }

  static async setPassword(user, password) {
    if (!password) throw 'Password is required';
    user.password = await generatePasswordHash(password); // eslint-disable-line

    try {
{% if mongoose %}
      if (!user.isNew) {
        await user.save();
      }
{% else %}
      if (user.id) {
        return User.update({
          where: { id: user.id },
          data: { password: user.password },
        });
      }
{% endif %}

      return user;
    } catch (err) {
      throw `Database error while setting user password: ${err}`;
    }
  }

  static async regenerateToken(user) {
    user.token = randomUUID(); // eslint-disable-line

    try {
{% if mongoose %}
      if (!user.isNew) {
        await user.save();
      }
{% else %}
      if (user.id) {
        return User.update({
          where: { id: user.id },
          data: { password: user.password },
        });
      }
{% endif %}

      return user;
    } catch (err) {
      throw `Database error while generating user token: ${err}`;
    }
  }
}

export default UserService;
