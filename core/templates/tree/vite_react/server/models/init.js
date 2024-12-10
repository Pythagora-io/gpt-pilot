{% if options.db_type == 'nosql' %}
const mongoose = require('mongoose');

const dbInit = async (options = {}) => {
  const mongoUrl = process.env.DATABASE_URL || 'mongodb://localhost/myDb';

  try {
    await mongoose.connect(mongoUrl, options);
    console.log(`Connected to MongoDB at ${mongoUrl}`);
  } catch (err) {
    console.error(`Error connecting to database ${mongoUrl}:`, err);
    throw err;
  }
};

module.exports = dbInit;
{% endif %}
{% if options.db_type == 'sql' %}
const Prisma = require('@prisma/client');

// PrismaClient is not available when testing
const { PrismaClient } = Prisma || {};
const prisma = PrismaClient ? new PrismaClient() : {};

{% if options.auth %}
const User = prisma.user;
module.exports = User;
{% endif %}
{% endif %}
