# Vibeforming AI

AI-powered backend service for intelligent form generation and response analysis. Built at **Hub200 Hackathon** where our team won the competition.

## About

This project was created during Hub200 hackathon, where we were challenged to build a Google Forms alternative with enhanced features. We added:

- **AI Form Generation** - Generate complete forms from natural language prompts
- **AI Data Analysis** - Analyze form responses with AI-powered insights, charts, and statistics

## Features

### Form Generation (`/generate`)
Generate forms from plain text descriptions. The AI creates properly structured forms with:
- Multiple field types (text, textarea, number, date, select, radio, checkbox, etc.)
- Validation rules (regex patterns for email, phone, URLs)
- Smart defaults and placeholders

### Data Analysis (`/analyze`)
Analyze CSV data from form responses. Returns:
- **Graphs** - Bar, line, pie, and area charts
- **Numbers** - Aggregated statistics (mean, sum, count)
- **Texts** - AI-generated insights

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate` | Generate a form from a prompt |
| POST | `/analyze` | Analyze CSV data with a question |
| GET | `/` | Health check |

### Generate Form
```bash
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a contact form with name, email, and message"}'
```

### Analyze Data
```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the average rating?", "csv_data": "rating\n5\n4\n3\n5\n4"}'
```

## Setup

### Prerequisites
- Python 3.10+
- OpenAI API key

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/vibeforming-ai.git
cd vibeforming-ai
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

5. Run the server
```bash
flask run
```

The API will be available at `http://localhost:5000`

## Tech Stack

- **Flask** - Web framework
- **OpenAI API** - GPT-4o for form generation and data analysis
- **Python** - Backend language

## Team

Built with passion at Hub200 Hackathon.

## License

MIT
