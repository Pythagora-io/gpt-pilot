import path from 'path';

import cors from 'cors';
import express from 'express';

{% if options.auth %}
import authRoutes from './routes/authRoutes.js';
import { authenticateWithToken } from './middlewares/authMiddleware.js';
{% endif %}
import apiRoutes from './routes/index.js';

// Set up Express app
const app = express();

// Pretty-print JSON responses
app.enable('json spaces');
// We want to be consistent with URL paths, so we enable strict routing
app.enable('strict routing');

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cors());
{% if options.auth %}

// Authentication routes
app.use(authRoutes);
app.use(authenticateWithToken);
{% endif %}

app.use(apiRoutes);

app.use(express.static(path.join(import.meta.dirname, "..", "dist")));

// Assume all other routes are frontend and serve pre-built frontend from ../dist/ folder
app.get(/.*/, async (req, res) => {
    res.sendFile(path.join(import.meta.dirname, "..", "dist", "index.html"));
});

export default app;
