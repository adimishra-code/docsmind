import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 100 },  // Ramp-up to 100 users
    { duration: '1m', target: 500 },   // Spike to 500 users
    { duration: '2m', target: 1000 },  // Sustained 1000 users
    { duration: '30s', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests should be below 500ms
    http_req_failed: ['rate<0.01'],   // Error rate should be less than 1%
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000/api/v1';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || 'test_token';

export default function () {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${AUTH_TOKEN}`,
    },
  };

  // 1. Simulate Document Search (Dense + Sparse Retrieval)
  const searchPayload = JSON.stringify({
    query: "Enterprise SLA agreements",
    limit: 5
  });
  
  const searchRes = http.post(`${BASE_URL}/documents/search`, searchPayload, params);
  check(searchRes, {
    'search status is 200': (r) => r.status === 200,
    'search returns results': (r) => JSON.parse(r.body).results.length > 0,
  });

  sleep(1);

  // 2. Simulate Chat (LangGraph Orchestrator)
  // Note: k6 does not natively support SSE streaming validation easily without websockets,
  // so we test the initial connection latency.
  const chatPayload = JSON.stringify({
    message: "Summarize the SLA terms",
    document_ids: []
  });

  const chatRes = http.post(`${BASE_URL}/chat/stream`, chatPayload, params);
  check(chatRes, {
    'chat stream initiates': (r) => r.status === 200,
  });

  sleep(randomIntBetween(2, 5));
}

function randomIntBetween(min, max) {
  return Math.floor(Math.random() * (max - min + 1) + min);
}
