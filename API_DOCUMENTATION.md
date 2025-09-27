# Ephemeral Stories API Documentation

## Overview

The Ephemeral Stories API is a production-ready backend for creating and managing ephemeral content (stories) that automatically expire after 24 hours. The API provides comprehensive social features, media upload capabilities, and real-time interactions.

## Base URL

- **Development**: `http://localhost:8000/api/`
- **Production**: `https://api.stories.example.com/api/`

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

### Getting JWT Tokens

**POST** `/api/token/`
```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Refresh Token:**
**POST** `/api/token/refresh/`
```json
{
  "refresh": "your_refresh_token"
}
```

## API Endpoints

### Stories Management

#### List Stories
**GET** `/api/stories/`

Get a paginated list of stories visible to the authenticated user.

**Query Parameters:**
- `cursor` (string, optional): Cursor for pagination

**Response:**
```json
{
  "count": 25,
  "next": "http://api/stories/?cursor=eyJpZCI6MTIzfQ",
  "previous": null,
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "author": "user@example.com",
      "author_email": "user@example.com",
      "author_first_name": "John",
      "author_last_name": "Doe",
      "text": "Hello world!",
      "media_key": "stories/user123/image.jpg",
      "visibility": "public",
      "created_at": "2024-01-01T12:00:00Z",
      "expires_at": "2024-01-02T12:00:00Z",
      "view_count": 5,
      "reaction_count": 2,
      "user_reaction": "👍",
      "is_viewed": true
    }
  ]
}
```

#### Create Story
**POST** `/api/stories/`

Create a new ephemeral story.

**Request Body:**
```json
{
  "text": "Just had an amazing day at the beach! 🏖️",
  "media_key": "stories/user123/sunset.jpg",
  "visibility": "public",
  "audience_user_ids": ["user-id-1", "user-id-2"]
}
```

**Visibility Options:**
- `public`: Visible to everyone
- `friends`: Visible only to followers
- `private`: Visible only to the author

#### Get Story
**GET** `/api/stories/{id}/`

Retrieve a specific story by ID. Automatically records a view.

#### Update Story
**PUT** `/api/stories/{id}/` or **PATCH** `/api/stories/{id}/`

Update an existing story (author only).

#### Delete Story
**DELETE** `/api/stories/{id}/`

Delete a story (author only).

### Feed

#### Get User Feed
**GET** `/api/feed/`

Get a personalized feed of stories for the authenticated user.

**Query Parameters:**
- `cursor` (string, optional): Cursor for pagination

### Story Interactions

#### Record Story View
**POST** `/api/stories/{id}/view/`

Record that the user has viewed a story (idempotent).

**Response:**
```json
{
  "viewed": true
}
```

#### Add Story Reaction
**POST** `/api/stories/{id}/reactions/`

Add or update a reaction to a story.

**Request Body:**
```json
{
  "emoji": "👍"
}
```

**Valid Emojis:** 👍 ❤️ 😂 😮 😢 🔥

**Response:**
```json
{
  "id": "reaction-uuid",
  "story": "story-uuid",
  "user": "user-uuid",
  "user_email": "user@example.com",
  "emoji": "👍",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Social Features

#### Follow User
**POST** `/api/follow/{user_id}/`

Follow another user to see their friends-only stories.

**Response:**
```json
{
  "message": "Successfully followed user"
}
```

#### Unfollow User
**DELETE** `/api/unfollow/{user_id}/`

Stop following a user.

**Response:**
```json
{
  "message": "Successfully unfollowed user"
}
```

### Media Upload

#### Generate Upload URL
**POST** `/api/upload-url/`

Generate a presigned URL for uploading media files.

**Request Body:**
```json
{
  "content_type": "image/jpeg",
  "file_size": 1048576
}
```

**Response:**
```json
{
  "upload_url": "https://minio.example.com/stories-media/stories/user123/image.jpg?X-Amz-Algorithm=...",
  "media_key": "stories/user123/image.jpg",
  "expires_in": 3600
}
```

**Supported Content Types:**
- Images: `image/jpeg`, `image/png`, `image/gif`, `image/webp`
- Videos: `video/mp4`, `video/webm`, `video/quicktime`

**File Size Limit:** 50MB

### Analytics

#### Get User Statistics
**GET** `/api/me/stats/`

Get comprehensive statistics for the authenticated user.

**Response:**
```json
{
  "stories_posted": 25,
  "total_views": 150,
  "unique_viewers": 45,
  "reaction_breakdown": {
    "👍": 12,
    "❤️": 8,
    "😂": 5,
    "😮": 3,
    "😢": 1,
    "🔥": 6
  },
  "last_7_days": {
    "stories_posted": 5,
    "views": 30
  }
}
```

### System

#### Health Check
**GET** `/api/health/`

Check the health status of the API and its dependencies.

**Response (Healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "database": "ok",
    "cache": "ok"
  }
}
```

**Response (Unhealthy):**
```json
{
  "status": "unhealthy",
  "error": "Database connection failed"
}
```

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message description"
}
```

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Rate Limiting

- **Stories Creation**: 20 requests per minute per user
- **Reactions**: 60 requests per minute per user

## Data Models

### Story
- `id`: UUID (primary key)
- `author`: User ID (foreign key)
- `text`: Text content (optional)
- `media_key`: S3 object key (optional)
- `visibility`: `public`, `friends`, or `private`
- `created_at`: Creation timestamp
- `expires_at`: Expiration timestamp (24 hours from creation)
- `deleted_at`: Soft deletion timestamp (null if active)

### User
- `id`: UUID (primary key)
- `email`: Email address (unique)
- `first_name`: First name
- `last_name`: Last name
- `created_at`: Account creation timestamp

### Follow
- `follower`: User ID (foreign key)
- `followee`: User ID (foreign key)
- `created_at`: Follow timestamp

### Reaction
- `id`: UUID (primary key)
- `story`: Story ID (foreign key)
- `user`: User ID (foreign key)
- `emoji`: Reaction emoji
- `created_at`: Reaction timestamp

## Swagger Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

## Examples

### Complete Workflow

1. **Authenticate:**
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

2. **Create a Story:**
```bash
curl -X POST http://localhost:8000/api/stories/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world!", "visibility": "public"}'
```

3. **Get Feed:**
```bash
curl -X GET http://localhost:8000/api/feed/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

4. **Add Reaction:**
```bash
curl -X POST http://localhost:8000/api/stories/STORY_ID/reactions/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"emoji": "👍"}'
```

## Support

For API support and questions, please refer to the Swagger documentation or contact the development team.
