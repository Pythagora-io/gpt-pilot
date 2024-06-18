import pino from 'pino';

const DEFAULT_LOG_LEVEL = process.env.NODE_ENV === "production" ? "info" : "debug";
const level = process.env.LOG_LEVEL || DEFAULT_LOG_LEVEL;

if (!pino.levels.values[level]) {
  const validLevels = Object.keys(pino.levels.values).join(', ');
  throw new Error(`Log level must be one of: ${validLevels}`);
}

const logger = (name) => pino({ name, level });

export default logger;
