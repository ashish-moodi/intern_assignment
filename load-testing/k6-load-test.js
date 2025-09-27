import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");

// Test configuration
export const options = {
  stages: [
    { duration: "2m", target: 10 }, // Ramp up to 10 users
    { duration: "5m", target: 10 }, // Stay at 10 users
    { duration: "2m", target: 20 }, // Ramp up to 20 users
    { duration: "5m", target: 20 }, // Stay at 20 users
    { duration: "2m", target: 0 }, // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"], // 95% of requests must complete below 2s
    http_req_failed: ["rate<0.1"], // Error rate must be below 10%
    errors: ["rate<0.1"], // Custom error rate must be below 10%
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

// Test data
let authToken = "";
let userId = "";

export function setup() {
  // Register a test user
  const registerPayload = JSON.stringify({
    email: `test-${Date.now()}@example.com`,
    password: "testpassword123",
    first_name: "Test",
    last_name: "User",
  });

  const registerResponse = http.post(
    `${BASE_URL}/api/auth/register/`,
    registerPayload,
    {
      headers: { "Content-Type": "application/json" },
    }
  );

  if (registerResponse.status !== 201) {
    console.error("Failed to register user:", registerResponse.body);
    return {};
  }

  // Login to get auth token
  const loginPayload = JSON.stringify({
    email: JSON.parse(registerResponse.body).email,
    password: "testpassword123",
  });

  const loginResponse = http.post(`${BASE_URL}/api/auth/login/`, loginPayload, {
    headers: { "Content-Type": "application/json" },
  });

  if (loginResponse.status !== 200) {
    console.error("Failed to login:", loginResponse.body);
    return {};
  }

  const loginData = JSON.parse(loginResponse.body);
  return {
    authToken: loginData.access,
    userId: loginData.user.id,
  };
}

export default function (data) {
  const headers = {
    Authorization: `Bearer ${data.authToken}`,
    "Content-Type": "application/json",
  };

  // Test 1: Health check
  let response = http.get(`${BASE_URL}/api/health/`);
  let success = check(response, {
    "health check status is 200": (r) => r.status === 200,
    "health check response time < 500ms": (r) => r.timings.duration < 500,
  });
  errorRate.add(!success);
  sleep(1);

  // Test 2: Get user feed
  response = http.get(`${BASE_URL}/api/feed/`, { headers });
  success = check(response, {
    "feed status is 200": (r) => r.status === 200,
    "feed response time < 1000ms": (r) => r.timings.duration < 1000,
    "feed returns data": (r) => {
      const data = JSON.parse(r.body);
      return data.hasOwnProperty("results");
    },
  });
  errorRate.add(!success);
  sleep(1);

  // Test 3: Create a story
  const storyPayload = JSON.stringify({
    text: `Load test story ${Date.now()}`,
    visibility: "public",
  });

  response = http.post(`${BASE_URL}/api/stories/`, storyPayload, { headers });
  success = check(response, {
    "create story status is 201": (r) => r.status === 201,
    "create story response time < 2000ms": (r) => r.timings.duration < 2000,
  });
  errorRate.add(!success);
  sleep(2);

  // Test 4: Get stories list
  response = http.get(`${BASE_URL}/api/stories/`, { headers });
  success = check(response, {
    "stories list status is 200": (r) => r.status === 200,
    "stories list response time < 1000ms": (r) => r.timings.duration < 1000,
  });
  errorRate.add(!success);
  sleep(1);

  // Test 5: Get user profile
  response = http.get(`${BASE_URL}/api/user/profile/`, { headers });
  success = check(response, {
    "profile status is 200": (r) => r.status === 200,
    "profile response time < 500ms": (r) => r.timings.duration < 500,
  });
  errorRate.add(!success);
  sleep(1);
}

export function teardown(data) {
  // Cleanup: Delete test user if needed
  console.log("Load test completed");
}
