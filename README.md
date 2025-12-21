# 📚 arXiv Paper Crawler

A Python web application for searching and saving paper abstracts from [arXiv.org](https://arxiv.org/).

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- 🔍 **Smart Search**: Search papers by keywords, authors, or categories
- 💾 **Save Abstracts**: Store paper abstracts locally in JSON format
- 🌐 **Web Interface**: Beautiful, responsive web UI
- 📊 **RESTful API**: Full API access for programmatic integration
- ⚡ **Async Architecture**: Built with async Python for efficient requests
- 📱 **Mobile Friendly**: Responsive design works on all devices

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Clone/Navigate to the project directory**

```bash
cd /mnt/raid0/heyanguang/code/python_web_crawler
```

2. **Create a virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run the application**

```bash
python run.py
```

5. **Open your browser**

Navigate to [http://localhost:8000](http://localhost:8000)

## 📁 Project Structure

```
python_web_crawler/
├── app/                          # Web application module
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── routes/                   # API routes
│   │   ├── search.py             # Search endpoints
│   │   └── papers.py             # Paper management endpoints
│   ├── templates/                # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── results.html
│   │   ├── papers.html
│   │   └── paper_detail.html
│   └── static/                   # Static assets
│       ├── css/style.css
│       └── js/app.js
│
├── crawler/                      # arXiv crawler module
│   ├── __init__.py
│   ├── models.py                 # Data models (Paper, SearchResult)
│   └── arxiv_client.py           # arXiv API client
│
├── storage/                      # File storage module
│   ├── __init__.py
│   └── file_handler.py           # JSON file operations
│
├── config/                       # Configuration module
│   ├── __init__.py
│   └── settings.py               # App settings
│
├── data/                         # Data storage directory
│   └── papers/                   # Saved paper JSONs
│
├── tests/                        # Test suite
├── requirements.txt              # Python dependencies
├── run.py                        # Application entry point
└── README.md                     # This file
```

## 🔧 Configuration

Configuration can be set via environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `0.0.0.0` | Server host |
| `APP_PORT` | `8000` | Server port |
| `DEBUG` | `True` | Debug mode |
| `ARXIV_MAX_RESULTS` | `10` | Default max search results |
| `ARXIV_RATE_LIMIT_DELAY` | `3.0` | Delay between API requests (seconds) |
| `DATA_DIR` | `data/papers` | Paper storage directory |

## 📖 API Documentation

Once the server is running, access:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Home page |
| `POST` | `/search` | Search papers (form) |
| `GET` | `/search?q=...` | Search papers (URL params) |
| `GET` | `/api/search` | Search API (JSON response) |
| `GET` | `/api/search/author` | Search by author |
| `GET` | `/api/search/category` | Search by category |
| `GET` | `/papers` | List saved papers |
| `GET` | `/papers/{id}` | View paper details |
| `DELETE` | `/papers/api/{id}` | Delete saved paper |
| `POST` | `/papers/api/save/{id}` | Save paper by ID |

### Example API Usage

```bash
# Search for papers
curl "http://localhost:8000/api/search?query=machine+learning&max_results=5"

# Search by author
curl "http://localhost:8000/api/search/author?author=Hinton"

# Search by category
curl "http://localhost:8000/api/search/category?category=cs.AI"

# Save a paper
curl -X POST "http://localhost:8000/papers/api/save/2312.12345"

# Delete a saved paper
curl -X DELETE "http://localhost:8000/papers/api/2312.12345"
```

## 🛠️ Development

### Running in Development Mode

```bash
# With auto-reload
DEBUG=True python run.py
```

### Running Tests

```bash
pytest tests/
```

## 📝 Notes

- This application uses the [arXiv API](https://arxiv.org/help/api/index) to fetch paper data
- Please respect arXiv's rate limits (default: 3 seconds between requests)
- arXiv data is not peer-reviewed; it's a preprint repository
- Saved papers are stored as JSON files in the `data/papers/` directory

## 🙏 Acknowledgments

- [arXiv.org](https://arxiv.org/) for providing open access to research papers
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [feedparser](https://feedparser.readthedocs.io/) for Atom feed parsing

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

Made with ❤️ for researchers and developers

