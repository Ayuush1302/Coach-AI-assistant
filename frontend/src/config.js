// Central API configuration
// Uses Render URL in production, localhost in development
const API_BASE_URL = import.meta.env.PROD
    ? 'https://coach-ai-assistant.onrender.com'
    : 'http://localhost:8000';

export default API_BASE_URL;
