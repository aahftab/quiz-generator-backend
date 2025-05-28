from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import uuid
import asyncio
import nest_asyncio
from werkzeug.utils import secure_filename
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Import required libraries
import google.generativeai as genai
from llama_parse import LlamaParse
from llama_index.core import SimpleDirectoryReader

# Configure Gemini AI
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# AI Model Configuration
quiz_generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 20,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",
}

summary_generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 60,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

GEMINI_PRO_2_5 = "gemini-2.5-flash-preview-05-20"

quiz_model = genai.GenerativeModel(
    model_name=GEMINI_PRO_2_5,
    generation_config=quiz_generation_config,
    system_instruction="You are a helpful assistant which helps teachers generate quiz from given content based on user requirements.",
)

summary_model = genai.GenerativeModel(
    model_name=GEMINI_PRO_2_5,
    generation_config=summary_generation_config,
    system_instruction="You are a helpful assistant which helps teachers generate summary from given content based on user requirements.",
)

# Quiz format template
quiz_format = """
{
  "quiz_title": str,
  "questions": [
    {
      "question_id": int,
      "question": str,
      "options": [{"option_id": int, "option": str}],
      "correct_option_id": int
    }
  ]
}
"""

# Global storage for processed files
processed_files = {}

def allowed_file(filename):
    """Check if file is a PDF"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

async def parse_pdf(file_path):
    """Parse PDF file and extract text content"""
    try:
        # Set up parser
        parser = LlamaParse(result_type="markdown")
        file_extractor = {".pdf": parser}
        
        # Load documents
        documents = await SimpleDirectoryReader(
            input_files=[file_path], 
            file_extractor=file_extractor
        ).aload_data(show_progress=True)
        
        # Extract text
        all_text = "\n".join([doc.text_resource.text for doc in documents])
        return all_text
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return None

def generate_summary(text):
    """Generate summary from text"""
    try:
        summary_chat_session = summary_model.start_chat(history=[])
        response = summary_chat_session.send_message(
            f"Generate detailed and precise summary in points without leaving any small detail from the given content: {text}"
        )
        return response.text
    except Exception as e:
        print(f"Error generating summary: {e}")
        return None

def generate_quiz(text, num_questions=20):
    """Generate quiz from text"""
    try:
        quiz_chat_session = quiz_model.start_chat(history=[])
        response = quiz_chat_session.send_message(
            f"Create a quiz of {num_questions} questions returning data in this JSON format: \n{quiz_format} on the content given below\n\n{text}"
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating quiz: {e}")
        return None

# API Routes

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "PDF API Server is running"}), 200

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """Upload PDF file and parse it"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        unique_filename = f"{file_id}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Parse PDF asynchronously
        nest_asyncio.apply()
        pdf_text = asyncio.run(parse_pdf(file_path))
        
        if not pdf_text:
            return jsonify({"error": "Failed to parse PDF"}), 500
        
        # Store parsed content
        processed_files[file_id] = {
            "filename": filename,
            "file_path": file_path,
            "text_content": pdf_text,
            "summary": None,
            "quiz": None
        }
        
        return jsonify({
            "message": "PDF uploaded and parsed successfully",
            "file_id": file_id,
            "filename": filename,
            "content_length": len(pdf_text)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-summary/<file_id>', methods=['POST'])
def generate_summary_endpoint(file_id):
    """Generate summary for uploaded PDF"""
    try:
        if file_id not in processed_files:
            return jsonify({"error": "File not found"}), 404
        
        file_data = processed_files[file_id]
        
        # Check if summary already exists
        if file_data["summary"]:
            return jsonify({
                "message": "Summary already exists",
                "file_id": file_id,
                "summary": file_data["summary"]
            }), 200
        
        # Generate summary
        summary = generate_summary(file_data["text_content"])
        
        if not summary:
            return jsonify({"error": "Failed to generate summary"}), 500
        
        # Store summary
        file_data["summary"] = summary
        
        # Save summary to file
        summary_filename = f"{file_id}_summary.txt"
        summary_path = os.path.join(PROCESSED_FOLDER, summary_filename)
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        return jsonify({
            "message": "Summary generated successfully",
            "file_id": file_id,
            "summary": summary,
            "summary_file": summary_filename
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-quiz/<file_id>', methods=['POST'])
def generate_quiz_endpoint(file_id):
    """Generate quiz for uploaded PDF"""
    try:
        if file_id not in processed_files:
            return jsonify({"error": "File not found"}), 404
        
        file_data = processed_files[file_id]
        
        # Get number of questions from request
        num_questions = request.json.get('num_questions', 20) if request.is_json else 20
        
        # Check if quiz already exists
        if file_data["quiz"]:
            return jsonify({
                "message": "Quiz already exists",
                "file_id": file_id,
                "quiz": file_data["quiz"]
            }), 200
        
        # Generate quiz
        quiz_data = generate_quiz(file_data["text_content"], num_questions)
        
        if not quiz_data:
            return jsonify({"error": "Failed to generate quiz"}), 500
        
        # Store quiz
        file_data["quiz"] = quiz_data
        
        # Save quiz to file
        quiz_filename = f"{file_id}_quiz.json"
        quiz_path = os.path.join(PROCESSED_FOLDER, quiz_filename)
        with open(quiz_path, 'w', encoding='utf-8') as f:
            json.dump(quiz_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "message": "Quiz generated successfully",
            "file_id": file_id,
            "quiz_file": quiz_filename,
            "quiz": quiz_data
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/file-info/<file_id>', methods=['GET'])
def get_file_info(file_id):
    """Get information about processed file"""
    try:
        if file_id not in processed_files:
            return jsonify({"error": "File not found"}), 404
        
        file_data = processed_files[file_id]
        
        return jsonify({
            "file_id": file_id,
            "filename": file_data["filename"],
            "content_length": len(file_data["text_content"]),
            "has_summary": file_data["summary"] is not None,
            "has_quiz": file_data["quiz"] is not None
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<file_type>/<file_id>', methods=['GET'])
def download_file(file_type, file_id):
    """Download generated files"""
    try:
        if file_type not in ['summary', 'quiz']:
            return jsonify({"error": "Invalid file type"}), 400
        
        if file_id not in processed_files:
            return jsonify({"error": "File not found"}), 404
        
        if file_type == 'summary':
            filename = f"{file_id}_summary.txt"
        else:
            filename = f"{file_id}_quiz.json"
        
        return send_from_directory(PROCESSED_FOLDER, filename, as_attachment=True)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/list-files', methods=['GET'])
def list_files():
    """List all processed files"""
    try:
        files_info = []
        for file_id, file_data in processed_files.items():
            files_info.append({
                "file_id": file_id,
                "filename": file_data["filename"],
                "content_length": len(file_data["text_content"]),
                "has_summary": file_data["summary"] is not None,
                "has_quiz": file_data["quiz"] is not None
            })
        
        return jsonify({
            "message": "Files retrieved successfully",
            "files": files_info,
            "total_files": len(files_info)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting PDF API Server...")
    print("Available endpoints:")
    print("- POST /api/upload-pdf - Upload and parse PDF file")
    print("- POST /api/generate-summary/<file_id> - Generate summary")
    print("- POST /api/generate-quiz/<file_id> - Generate quiz")
    print("- GET /api/file-info/<file_id> - Get file information")
    print("- GET /api/download/<file_type>/<file_id> - Download files")
    print("- GET /api/list-files - List all processed files")
    print("- GET /api/health - Health check")
    
    app.run(debug=True, port=5001, host='0.0.0.0')
