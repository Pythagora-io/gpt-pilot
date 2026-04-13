#!/bin/bash
# Seed a test user in the QA MongoDB database
# Usage: ./seed-test-user.sh [database_name]
#
# CONFIGURATION: Set these environment variables before running:
#   MONGODB_URI    — Full MongoDB connection string (or set in environment.md)
#   TEST_EMAIL     — Test account email (default: from environment.md)
#   TEST_PASSWORD  — Test account password (default: from environment.md)
#   PLATFORM_REPO_PATH — Path to platform repo (for bcrypt dependency)

set -euo pipefail

DB_NAME="${1:-${MONGODB_DEFAULT_DB:-myDB}}"

# These must be set by the user or pulled from environment.md
MONGO_URI="${MONGODB_URI:?Set MONGODB_URI to your MongoDB connection string}"
TEST_EMAIL="${TEST_ACCOUNT_EMAIL:-qa@example.com}"
TEST_PASSWORD="${TEST_ACCOUNT_PASSWORD:-TestPass123!}"
REPO_PATH="${PLATFORM_REPO_PATH:-/home/user/my-platform}"

echo "Seeding test user in database: $DB_NAME"

cd "$REPO_PATH"

node -e "
const { MongoClient } = require('mongodb');
const bcrypt = require('bcryptjs');

(async () => {
  const client = new MongoClient('$MONGO_URI');
  try {
    await client.connect();
    const db = client.db('$DB_NAME');

    // Hash password
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash('$TEST_PASSWORD', salt);

    // Upsert test user
    const result = await db.collection('users').updateOne(
      { email: '$TEST_EMAIL' },
      {
        \\\$set: {
          email: '$TEST_EMAIL',
          password: hashedPassword,
          name: 'QA Agent',
          credits: 1000000,
          plan: 'pro',
          authProvider: 'email',
          isVerified: true,
          updatedAt: new Date()
        },
        \\\$setOnInsert: {
          createdAt: new Date()
        }
      },
      { upsert: true }
    );

    console.log(result.upsertedCount ? 'User created' : 'User updated');
    console.log('Email: $TEST_EMAIL');
    console.log('Credits: 1000000');
  } catch(e) {
    console.error('Error:', e.message);
    process.exit(1);
  } finally {
    await client.close();
  }
})();
"

echo "✅ Test user seeded"
