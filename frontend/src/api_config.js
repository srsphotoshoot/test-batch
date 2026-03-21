const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || (process.env.NODE_ENV === 'production' ? window.location.origin : 'http://localhost:8000');
export default API_BASE_URL;
