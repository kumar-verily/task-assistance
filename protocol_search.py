#!/usr/bin/env python3
"""
Clinical Protocol RAG Search Interface
A self-contained web interface for searching clinical protocols using Pinecone

Run this script and open http://localhost:5000 in your browser
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pinecone import Pinecone
import os
from dotenv import load_dotenv
import webbrowser
import threading

# Load environment
load_dotenv()

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
pinecone_index = pc.Index("clinical-protocols-rag")

# Embedded HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clinical Protocol Search</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }

        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .search-box {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }

        .search-input-wrapper {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        #searchInput {
            flex: 1;
            padding: 15px 20px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            transition: border-color 0.3s;
        }

        #searchInput:focus {
            outline: none;
            border-color: #667eea;
        }

        #searchButton {
            padding: 15px 40px;
            font-size: 16px;
            font-weight: 600;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        #searchButton:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        #searchButton:active {
            transform: translateY(0);
        }

        #searchButton:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .filters {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }

        .filter-group {
            flex: 1;
            min-width: 200px;
        }

        .filter-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
            font-size: 14px;
        }

        .filter-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            background: white;
            cursor: pointer;
        }

        .results-container {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            min-height: 200px;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 18px;
        }

        .loading:after {
            content: '...';
            animation: dots 1.5s steps(4, end) infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }

        .result-card {
            border: 2px solid #f0f0f0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            transition: border-color 0.3s, box-shadow 0.3s;
        }

        .result-card:hover {
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
        }

        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }

        .result-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }

        .result-code {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .result-meta {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }

        .meta-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 5px 12px;
            background: #f5f5f5;
            border-radius: 6px;
            font-size: 0.9rem;
            color: #666;
        }

        .meta-badge strong {
            color: #333;
        }

        .priority-p1 { background: #fee; color: #c33; }
        .priority-p2 { background: #ffeaa7; color: #d63031; }
        .priority-p3 { background: #dfe6e9; color: #636e72; }

        .result-content {
            color: #555;
            line-height: 1.6;
            margin-bottom: 15px;
            white-space: pre-wrap;
        }

        .result-score {
            text-align: right;
            font-size: 0.9rem;
            color: #999;
        }

        .score-bar {
            display: inline-block;
            width: 100px;
            height: 8px;
            background: #f0f0f0;
            border-radius: 4px;
            overflow: hidden;
            vertical-align: middle;
            margin-left: 10px;
        }

        .score-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }

        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }

        .no-results h3 {
            font-size: 1.5rem;
            margin-bottom: 10px;
        }

        .stats {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .stats-text {
            color: #666;
            font-size: 0.95rem;
        }

        .example-queries {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .example-queries h4 {
            margin-bottom: 10px;
            color: #555;
            font-size: 0.9rem;
        }

        .example-tag {
            display: inline-block;
            padding: 6px 12px;
            margin: 4px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s;
        }

        .example-tag:hover {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8rem;
            }

            .search-input-wrapper {
                flex-direction: column;
            }

            .result-header {
                flex-direction: column;
            }

            .filter-group {
                min-width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Clinical Protocol Search</h1>
            <p>Semantic search powered by Pinecone RAG</p>
        </div>

        <div class="search-box">
            <div class="search-input-wrapper">
                <input
                    type="text"
                    id="searchInput"
                    placeholder="Search protocols... (e.g., 'A1C test', 'onboarding', 'CGM sensor')"
                    autofocus
                />
                <button id="searchButton" onclick="performSearch()">Search</button>
            </div>

            <div class="filters">
                <div class="filter-group">
                    <label for="priorityFilter">Priority</label>
                    <select id="priorityFilter">
                        <option value="">All Priorities</option>
                        <option value="P1">P1 - High</option>
                        <option value="P2">P2 - Medium</option>
                        <option value="P3">P3 - Low</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="programFilter">Program</label>
                    <select id="programFilter">
                        <option value="">All Programs</option>
                        <option value="lightpath">Lightpath</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="topKFilter">Results</label>
                    <select id="topKFilter">
                        <option value="5">Top 5</option>
                        <option value="10" selected>Top 10</option>
                        <option value="20">Top 20</option>
                    </select>
                </div>
            </div>

            <div class="example-queries">
                <h4>💡 Try these example searches:</h4>
                <span class="example-tag" onclick="setQuery('A1C test results')">A1C test results</span>
                <span class="example-tag" onclick="setQuery('onboarding new patient')">Onboarding new patient</span>
                <span class="example-tag" onclick="setQuery('CGM sensor issues')">CGM sensor issues</span>
                <span class="example-tag" onclick="setQuery('medication management')">Medication management</span>
                <span class="example-tag" onclick="setQuery('RN escalation')">RN escalation</span>
                <span class="example-tag" onclick="setQuery('custom to do')">Custom to do</span>
            </div>
        </div>

        <div class="results-container" id="resultsContainer">
            <div class="no-results">
                <h3>👋 Welcome!</h3>
                <p>Enter a search query above to find clinical protocols</p>
            </div>
        </div>
    </div>

    <script>
        // Handle Enter key in search input
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });

        function setQuery(query) {
            document.getElementById('searchInput').value = query;
            performSearch();
        }

        async function performSearch() {
            const query = document.getElementById('searchInput').value.trim();
            const priority = document.getElementById('priorityFilter').value;
            const program = document.getElementById('programFilter').value;
            const topK = parseInt(document.getElementById('topKFilter').value);

            if (!query) {
                alert('Please enter a search query');
                return;
            }

            const resultsContainer = document.getElementById('resultsContainer');
            const searchButton = document.getElementById('searchButton');

            // Show loading state
            searchButton.disabled = true;
            searchButton.textContent = 'Searching...';
            resultsContainer.innerHTML = '<div class="loading">Searching protocols</div>';

            try {
                const response = await fetch('/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        query: query,
                        priority: priority,
                        program: program,
                        top_k: topK
                    })
                });

                const data = await response.json();

                if (data.error) {
                    resultsContainer.innerHTML = `
                        <div class="no-results">
                            <h3>⚠️ Error</h3>
                            <p>${data.error}</p>
                        </div>
                    `;
                    return;
                }

                displayResults(data.results, data.query, data.count);

            } catch (error) {
                resultsContainer.innerHTML = `
                    <div class="no-results">
                        <h3>⚠️ Error</h3>
                        <p>Failed to search: ${error.message}</p>
                    </div>
                `;
            } finally {
                searchButton.disabled = false;
                searchButton.textContent = 'Search';
            }
        }

        function displayResults(results, query, count) {
            const resultsContainer = document.getElementById('resultsContainer');

            if (results.length === 0) {
                resultsContainer.innerHTML = `
                    <div class="no-results">
                        <h3>No results found</h3>
                        <p>Try different keywords or adjust filters</p>
                    </div>
                `;
                return;
            }

            let html = `
                <div class="stats">
                    <span class="stats-text">
                        Found ${count} result${count !== 1 ? 's' : ''} for "${query}"
                    </span>
                </div>
            `;

            results.forEach((result, index) => {
                const priorityClass = result.priority.toLowerCase().replace(/[^a-z0-9]/g, '-');
                const score = result.score || 0;
                const scorePercent = Math.min(100, score * 100);

                html += `
                    <div class="result-card">
                        <div class="result-header">
                            <div>
                                <div class="result-title">${escapeHtml(result.task_name)}</div>
                                <span class="result-code">${escapeHtml(result.task_code)}</span>
                            </div>
                        </div>

                        <div class="result-meta">
                            <span class="meta-badge priority-${priorityClass}">
                                <strong>Priority:</strong> ${escapeHtml(result.priority)}
                            </span>
                            <span class="meta-badge">
                                <strong>Program:</strong> ${escapeHtml(result.program)}
                            </span>
                            ${result.roles ? `
                                <span class="meta-badge">
                                    <strong>Roles:</strong> ${escapeHtml(result.roles)}
                                </span>
                            ` : ''}
                        </div>

                        <div class="result-content">${escapeHtml(result.content).substring(0, 500)}${result.content.length > 500 ? '...' : ''}</div>

                        <div class="result-score">
                            Relevance: ${score.toFixed(3)}
                            <span class="score-bar">
                                <span class="score-fill" style="width: ${scorePercent}%"></span>
                            </span>
                        </div>
                    </div>
                `;
            });

            resultsContainer.innerHTML = html;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Auto-focus search input
        window.addEventListener('load', () => {
            document.getElementById('searchInput').focus();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main search interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/search', methods=['POST'])
def search():
    """Search protocols endpoint"""
    try:
        data = request.json
        query_text = data.get('query', '')
        priority_filter = data.get('priority', '')
        program_filter = data.get('program', '')
        top_k = data.get('top_k', 10)

        if not query_text:
            return jsonify({'error': 'Query is required'}), 400

        # Build filter
        filters = {}
        if priority_filter:
            filters['priority'] = {'$eq': priority_filter}
        if program_filter:
            filters['program'] = {'$eq': program_filter}

        # Construct query
        search_query = {
            "top_k": top_k * 2,  # Get more for reranking
            "inputs": {"text": query_text}
        }

        if filters:
            search_query["filter"] = filters

        # Search with reranking
        results = pinecone_index.search(
            namespace="protocols",
            query=search_query,
            rerank={
                "model": "bge-reranker-v2-m3",
                "top_n": top_k,
                "rank_fields": ["content"]
            }
        )

        # Format results
        formatted_results = []
        for hit in results['result']['hits']:
            fields = hit['fields']
            formatted_results.append({
                'task_code': fields.get('task_code', ''),
                'task_name': fields.get('task_name', ''),
                'priority': fields.get('priority', ''),
                'program': fields.get('program', ''),
                'content': fields.get('content', ''),
                'roles': fields.get('roles', ''),
                'score': hit.get('_score', 0)
            })

        return jsonify({
            'results': formatted_results,
            'count': len(formatted_results),
            'query': query_text
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': str(type(e))}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        stats = pinecone_index.describe_index_stats()
        return jsonify({
            'status': 'healthy',
            'total_vectors': stats.total_vector_count,
            'namespaces': list(stats.namespaces.keys())
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

def open_browser():
    """Open browser after a short delay"""
    import time
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("="*80)
    print("CLINICAL PROTOCOL RAG SEARCH INTERFACE")
    print("="*80)
    print()
    print("Starting server...")
    print("Opening browser at http://localhost:5000")
    print()
    print("Press Ctrl+C to stop the server")
    print("="*80)
    print()

    # Open browser in background
    threading.Thread(target=open_browser, daemon=True).start()

    # Start Flask server
    app.run(debug=True, host='0.0.0.0', port=5000)
