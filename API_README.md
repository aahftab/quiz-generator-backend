# PDF API Server

A Flask-based API server that processes PDF files to generate summaries and quizzes using Google's Gemini AI and LlamaParse.

## Features

- **PDF Upload & Parsing**: Upload PDF files and extract text content using LlamaParse
- **Summary Generation**: Generate detailed summaries of PDF content using Gemini AI
- **Quiz Generation**: Create multiple-choice quizzes based on PDF content
- **File Management**: Track processed files and download generated content
- **REST API**: Clean RESTful API endpoints for easy integration

## Setup

### Prerequisites

- Python 3.8+
- Google Gemini API key
- LlamaParse API key

### Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
LLAMA_PARSE_API_KEY=your_llama_parse_api_key_here
```

### Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Create necessary directories:
```bash
mkdir uploads processed
```

3. Run the server:
```bash
python pdf_api_server.py
```

The server will start on `http://localhost:5001`

## API Endpoints

### 1. Health Check
```http
GET /api/health
```
Returns server status.

### 2. Upload PDF
```http
POST /api/upload-pdf
Content-Type: multipart/form-data

Parameters:
- file: PDF file (required)
```

**Response:**
```json
{
  "message": "PDF uploaded and parsed successfully",
  "file_id": "uuid-string",
  "filename": "document.pdf",
  "content_length": 12345
}
```

### 3. Generate Summary
```http
POST /api/generate-summary/<file_id>
```

**Response:**
```json
{
  "message": "Summary generated successfully",
  "file_id": "uuid-string",
  "summary": "Detailed summary text...",
  "summary_file": "uuid_summary.txt"
}
```

### 4. Generate Quiz
```http
POST /api/generate-quiz/<file_id>
Content-Type: application/json

Body (optional):
{
  "num_questions": 15
}
```

**Response:**
```json
{
  "message": "Quiz generated successfully",
  "file_id": "uuid-string",
  "quiz": {
    "quiz_title": "Generated Quiz",
    "questions": [
      {
        "question_id": 1,
        "question": "What is...?",
        "options": [
          {"option_id": 1, "option": "Answer A"},
          {"option_id": 2, "option": "Answer B"},
          {"option_id": 3, "option": "Answer C"},
          {"option_id": 4, "option": "Answer D"}
        ],
        "correct_option_id": 2
      }
    ]
  },
  "quiz_file": "uuid_quiz.json"
}
```

### 5. Get File Information
```http
GET /api/file-info/<file_id>
```

**Response:**
```json
{
  "file_id": "uuid-string",
  "filename": "document.pdf",
  "content_length": 12345,
  "has_summary": true,
  "has_quiz": false
}
```

### 6. Download Files
```http
GET /api/download/<file_type>/<file_id>
```

Where `file_type` is either `summary` or `quiz`.

### 7. List All Files
```http
GET /api/list-files
```

**Response:**
```json
{
  "message": "Files retrieved successfully",
  "files": [...],
  "total_files": 5
}
```

## Web Client

Open `pdf_client.html` in your browser to use the web interface. The client provides:

- Drag & drop PDF upload
- Real-time processing status
- Summary and quiz preview
- Download links for generated content

## Usage Example

### Using cURL

1. **Upload a PDF:**
```bash
curl -X POST \
  http://localhost:5001/api/upload-pdf \
  -F "file=@document.pdf"
```

2. **Generate Summary:**
```bash
curl -X POST \
  http://localhost:5001/api/generate-summary/your-file-id
```

3. **Generate Quiz:**
```bash
curl -X POST \
  http://localhost:5001/api/generate-quiz/your-file-id \
  -H "Content-Type: application/json" \
  -d '{"num_questions": 10}'
```

### Using Python

```python
import requests

# Upload PDF
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:5001/api/upload-pdf',
        files={'file': f}
    )
    file_id = response.json()['file_id']

# Generate summary
summary_response = requests.post(
    f'http://localhost:5001/api/generate-summary/{file_id}'
)
summary = summary_response.json()['summary']

# Generate quiz
quiz_response = requests.post(
    f'http://localhost:5001/api/generate-quiz/{file_id}',
    json={'num_questions': 15}
)
quiz = quiz_response.json()['quiz']
```

## File Structure

```
├── pdf_api_server.py      # Main API server
├── pdf_client.html        # Web client interface
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── uploads/              # Uploaded PDF files
└── processed/            # Generated summaries and quizzes
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid file, missing parameters)
- `404`: File not found
- `500`: Server error (parsing failed, AI generation failed)

## Rate Limiting

Consider implementing rate limiting for production use to prevent API abuse.

## Security Notes

- File uploads are limited to PDF files only
- Maximum file size is 16MB
- Files are stored with UUID prefixes to prevent naming conflicts
- Consider adding authentication for production deployment

## Troubleshooting

1. **Server won't start**: Check that all environment variables are set correctly
2. **PDF parsing fails**: Ensure LlamaParse API key is valid and has credits
3. **AI generation fails**: Check Gemini API key and quota limits
4. **File upload fails**: Verify file is a valid PDF and under size limit
