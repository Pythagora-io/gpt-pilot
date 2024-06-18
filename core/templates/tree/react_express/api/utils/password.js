import bcrypt from 'bcrypt';

/**
 * Hashes the password using bcrypt algorithm
 * @param {string} password - The password to hash
 * @return {string} Password hash
 */
export const generatePasswordHash = async (password) => {
  const salt = await bcrypt.genSalt();
  const hash = await bcrypt.hash(password, salt);
  return hash;
};

/**
 * Validates the password against the hash
 * @param {string} password - The password to verify
 * @param {string} hash - Password hash to verify against
 * @return {boolean} True if the password matches the hash, false otherwise
 */
export const validatePassword = async (password, hash) => {
  const result = await bcrypt.compare(password, hash);
  return result;
};

/**
 * Checks that the hash has a valid format
 * @param {string} hash - Hash to check format for
 * @return {boolean} True if passed string seems like valid hash, false otherwise
 */
export const isPasswordHash = (hash) => {
  if (!hash || hash.length !== 60) return false;
  try {
    bcrypt.getRounds(hash);
    return true;
  } catch {
    return false;
  }
};
