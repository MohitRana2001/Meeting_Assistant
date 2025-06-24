# Meeting Assistant

An intelligent meeting assistant that automatically extracts tasks from meeting recordings and integrates with Google Tasks and Calendar. Features a modern React frontend with a FastAPI backend.

## 🚀 Features

- **Modern Web Interface**: Beautiful landing page and dashboard built with Next.js and Tailwind CSS
- **Automatic Meeting Processing**: Processes meeting recordings from Google Drive
- **AI-Powered Task Extraction**: Uses Gemini AI to extract actionable tasks with assignees and due dates
- **Google Integration**: Automatically creates tasks in Google Tasks and calendar events
- **Real-time Processing**: Webhook-based processing for instant task creation
- **Multi-format Support**: Supports Google Docs, Word documents, and plain text files
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## 🏗️ Architecture

- **Frontend**: Next.js 15 with TypeScript, Tailwind CSS, and shadcn/ui components
- **Backend**: FastAPI with SQLModel for database operations
- **AI**: Google Gemini for intelligent task extraction
- **Google APIs**: Drive, Tasks, and Calendar integration
- **Database**: SQLite with Alembic migrations
- **Background Processing**: Celery with Redis

## 📋 Prerequisites

- Node.js 18+ and npm/pnpm
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

2. **Install all dependencies**

   ```bash
   npm run install:all
   ```

3. **Configure environment variables**

   ```bash
   # Backend environment
   cd backend
   cp .env.example .env
   # Edit .env with your Google Cloud credentials

   # Frontend environment
   cd ../frontend
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   ```

4. **Set up the database**

   ```bash
   npm run setup
   ```

5. **Start Redis server**

   ```bash
   redis-server
   ```

6. **Start the Celery worker (in a new terminal)**

   ```bash
   cd backend
   celery -A workers.task worker --loglevel=info
   ```

7. **Start both frontend and backend**

   ```bash
   npm run dev
   ```

This will start:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

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

**Backend (.env)**

```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_APPLICATION_CREDENTIALS=path_to_service_account.json
GEMINI_API_KEY=your_gemini_api_key
REDIS_URL=redis://localhost:6379/0
API_BASE_URL=http://localhost:8000
```

**Frontend (.env.local)**

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📖 Usage

1. **Visit the landing page**

   - Open http://localhost:3000
   - Explore the features and testimonials
   - Click "Get Started Free" to begin

2. **Authenticate with Google**

   - The system will redirect you to Google OAuth
   - Grant required permissions for Drive, Tasks, and Calendar

3. **Access the dashboard**

   - After authentication, you'll be redirected to the dashboard
   - View your meeting summaries and extracted tasks
   - Click on any summary to see details and manage tasks

4. **Upload Meeting Recordings**

   - Upload meeting recordings to Google Drive
   - Place them in the "Meet Recordings" folder
   - The system will automatically process them

5. **View Results**
   - Check Google Tasks for extracted tasks
   - Check Google Calendar for scheduled events
   - View summaries via the dashboard

## 🔌 API Endpoints

- `GET /api/v1/auth/google` - Start OAuth flow
- `GET /api/v1/auth/google/callback` - OAuth callback
- `GET /api/v1/auth/check-permissions` - Check user permissions
- `GET /api/v1/meetings/summaries` - Get meeting summaries
- `POST /api/v1/drive/webhook` - Google Drive webhook

## 🎨 Frontend Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── page.tsx           # Landing page
│   └── dashboard/         # Dashboard route
├── components/            # Reusable components
│   ├── ui/               # shadcn/ui components
│   ├── sidebar.tsx       # Navigation sidebar
│   ├── top-bar.tsx       # Top navigation bar
│   └── ...               # Other components
├── lib/                  # Utilities and services
│   └── api.ts           # API service functions
└── dashboard.tsx         # Main dashboard component
```

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
8. **Frontend Display**: Real-time updates in the dashboard

## 🧪 Testing

```bash
# Run backend tests
cd backend
pytest

# Run frontend tests
cd frontend
npm test

# Test specific functionality
python -m pytest tests/test_task_extraction.py
```

## 📝 Development

### Available Scripts

- `npm run dev` - Start both frontend and backend in development mode
- `npm run dev:frontend` - Start only the frontend
- `npm run dev:backend` - Start only the backend
- `npm run build` - Build the frontend for production
- `npm run install:all` - Install all dependencies
- `npm run setup` - Setup database and install dependencies

### Code Structure

- **Frontend**: Modern React with TypeScript, using Next.js 15 app router
- **Backend**: FastAPI with async/await patterns and SQLModel ORM
- **Database**: SQLite with Alembic migrations for schema management
- **Styling**: Tailwind CSS with shadcn/ui component library

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions, please open an issue on GitHub.
