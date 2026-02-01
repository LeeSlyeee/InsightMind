import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.PROD ? "/api/v1/" : "http://127.0.0.1:8000/api/v1/",
  timeout: 5000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: Token Injection
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

export default api;
