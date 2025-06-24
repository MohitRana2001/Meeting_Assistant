# Meeting Assistant

An intelligent meeting assistant that automatically extracts tasks from meeting recordings and integrates with Google Tasks and Calendar.

## 🚀 Features

- **Automatic Meeting Processing**: Processes meeting recordings from Google Drive
- **AI-Powered Task Extraction**: Uses Gemini AI to extract actionable tasks with assignees and due dates
- **Google Integration**: Automatically creates tasks in Google Tasks and calendar events
- **Real-time Processing**: Webhook-based processing for instant task creation
- **Multi-format Support**: Supports Google Docs, Word documents, and plain text files

## 🏗️ Architecture

- **Backend**: FastAPI with SQLModel for database operations
- **AI**: Google Gemini for intelligent task extraction
- **Google APIs**: Drive, Tasks, and Calendar integration
- **Database**: SQLite with Alembic migrations
- **Background Processing**: Celery with Redis

## 📋 Prerequisites

- Python 3.9+
- Redis server
- Google Cloud Project with APIs enabled:
  - Google Drive API
  - Google Tasks API
  - Google Calendar API
  - Google OAuth 2.0

## 🛠️ Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd meeting-assistant
   ```

2. **Set up the backend**

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your Google Cloud credentials
   ```

4. **Set up the database**

   ```bash
   alembic upgrade head
   ```

5. **Start Redis server**

   ```bash
   redis-server
   ```

6. **Start the Celery worker**

   ```bash
   celery -A workers.task worker --loglevel=info
   ```

7. **Start the FastAPI server**
   ```bash
   uvicorn main:app --reload
   ```

## 🔧 Configuration

### Google Cloud Setup

1. Create a Google Cloud Project
2. Enable the required APIs:
   - Google Drive API
   - Google Tasks API
   - Google Calendar API
3. Create OAuth 2.0 credentials
4. Configure the OAuth consent screen with required scopes:
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/tasks`
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `openid`

### Environment Variables

```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_APPLICATION_CREDENTIALS=path_to_service_account.json
GEMINI_API_KEY=your_gemini_api_key
REDIS_URL=redis://localhost:6379/0
API_BASE_URL=http://localhost:8000
```

## 📖 Usage

1. **Authenticate with Google**

   - Visit `/api/v1/auth/google` to start OAuth flow
   - Grant required permissions

2. **Upload Meeting Recordings**

   - Upload meeting recordings to Google Drive
   - Place them in the "Meet Recordings" folder
   - The system will automatically process them

3. **View Results**
   - Check Google Tasks for extracted tasks
   - Check Google Calendar for scheduled events
   - View summaries via the API

## 🔌 API Endpoints

- `GET /api/v1/auth/google` - Start OAuth flow
- `GET /api/v1/auth/google/callback` - OAuth callback
- `GET /api/v1/summaries` - Get meeting summaries
- `POST /api/v1/drive/webhook` - Google Drive webhook

## 🤖 AI Task Extraction

The system uses Google Gemini AI to intelligently extract tasks from meeting transcripts:

- **Task Identification**: Recognizes actionable items
- **Assignee Detection**: Identifies who is responsible
- **Due Date Extraction**: Parses deadlines and timelines
- **Priority Assessment**: Determines task importance
- **Context Preservation**: Maintains meeting context

## 🔄 Workflow

1. **Meeting Recording**: Uploaded to Google Drive
2. **Webhook Trigger**: Google Drive notifies the system
3. **Text Extraction**: System extracts text from the file
4. **AI Processing**: Gemini AI analyzes the transcript
5. **Task Extraction**: Identifies tasks, assignees, and due dates
6. **Google Integration**: Creates tasks and calendar events
7. **Database Storage**: Saves summary and task information

## 🧪 Testing

```bash
# Run tests
pytest

# Test specific functionality
python -m pytest tests/test_task_extraction.py
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions, please open an issue on GitHub.
