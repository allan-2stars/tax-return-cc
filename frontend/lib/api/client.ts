import axios from 'axios'

const client = axios.create({
  // Relative base — Next.js rewrites proxy /api/* → backend:8000/api/*
  baseURL: '/',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

export default client
