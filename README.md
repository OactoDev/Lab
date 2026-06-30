# File Upload App

A minimal full-stack application for uploading and retrieving files using FastAPI (backend) and Vue (frontend).

## Project Structure

```
.
├── backend/          # FastAPI backend
│   ├── app.py       # Main application
│   └── requirements.txt
├── frontend/        # Vue frontend
│   ├── src/
│   │   ├── App.vue  # Main component
│   │   └── main.js  # Entry point
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Setup

### Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the server:
   ```bash
   uvicorn app:app --reload
   ```
   The API will be available at `http://localhost:8000`

### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```
   The app will be available at `http://localhost:5173`

## Features

- **Upload Files**: Drag and drop or click to upload files
- **List Files**: View all uploaded files
- **Download Files**: Download any uploaded file
- **Delete Files**: Remove files from the server

## API Endpoints

- `POST /upload` - Upload a file
- `GET /files` - List all uploaded files
- `GET /download/{filename}` - Download a file
- `DELETE /delete/{filename}` - Delete a file

## Notes

- Uploaded files are stored in `backend/uploads/` directory
- The frontend is configured to connect to the backend on `http://localhost:8000`
- Both servers support auto-reload in development mode
