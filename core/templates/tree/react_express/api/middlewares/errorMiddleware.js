import logger from '../utils/log.js';

const log = logger('api:middleware');

/* 404 handler for the missing API endpoints
 * Due to how Express works, we don't know if the URL or HTTP method is
 * incorrect, so we return 404 in both cases.
 */
export const handle404 = (req, res, next) => {
  const { method, originalUrl } = req;
  log.info({ method, originalUrl }, `Unhandled API request ${method} ${originalUrl}`);
  return res.status(404).json({ error: 'Resource not found or unsupported HTTP method' });
};

/* 500 handler in case we have an error in one of our route handlers
 */
export const handleError = (error, req, res, next) => {
  const { method, originalUrl } = req;

  log.error({ method, originalUrl, error }, `Error while handling ${method} ${originalUrl}`);
  res.status(500).json({ error });
};
