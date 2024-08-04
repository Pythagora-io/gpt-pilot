import path from 'path';
import { existsSync } from 'fs';
import { fileURLToPath } from 'node:url';

import cors from 'cors';
import express from 'express';

{% if options.auth %}
import authRoutes from './routes/authRoutes.js';
import { authenticateWithToken } from './middlewares/authMiddleware.js';
{% endif %}
import apiRoutes from './routes/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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
app.use(authenticateWithToken);
app.use(authRoutes);
{% endif %}

app.use(apiRoutes);

app.use(express.static(path.join(__dirname, "..", "dist")));

// Assume all other routes are frontend
app.get(/.*/, async (req, res) => {
    // Try to serve pre-built frontend from ../dist/ folder
    const clientBundlePath = path.join(__dirname, "..", "dist", "index.html");

    if (!existsSync(clientBundlePath)) {
        if (process.env.NODE_ENV === "development") {
            // In development, we just want to redirect to the Vite dev server
            return res.redirect("http://localhost:5173");
        } else {
            // Looks like "npm run build:ui" wasn't run and the UI isn't built, show a nice error message instead
            return res.status(404).send("Front-end not available.");
        }
    }
    res.sendFile(path.join(import.meta.dirname, "..", "dist", "index.html"));
});

export default app;
