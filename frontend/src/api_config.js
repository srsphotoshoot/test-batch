const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || (process.env.NODE_ENV === 'production' ? window.location.origin : 'http://localhost:8000');

if (process.env.NODE_ENV === 'production' && !process.env.REACT_APP_API_BASE_URL && window.location.origin.includes('vercel.app')) {
    console.warn('⚠️ WARNING: REACT_APP_API_BASE_URL is not set in Vercel. API calls may fail if the backend is on a different platform (e.g., Railway).');
}

export default API_BASE_URL;
