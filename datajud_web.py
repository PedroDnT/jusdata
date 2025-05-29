#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataJud Web Interface - A web application for querying the Brazilian judiciary system

This script provides a Flask web interface for the DatajudAgent, allowing users
to search for judicial processes and view the results in a well-formatted way.
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datajud_agent import DatajudAgent

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'datajud-web-secret-key')

# Initialize the DatajudAgent
agent = DatajudAgent(verbose=False)

@app.route('/', methods=['GET'])
def index():
    """
    Render the home page with the search form.
    """
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    """
    Handle search requests and display results.
    """
    if request.method == 'POST':
        query = request.form.get('query', '')
        if not query:
            return render_template('index.html', error="Por favor, insira uma consulta.")
        
        # Redirect to GET request with query parameter to make results bookmarkable
        return redirect(url_for('search', q=query))
    
    # Handle GET request
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('index'))
    
    try:
        results = agent.process_query(query)
        return render_template('results.html', 
                              query=query, 
                              results=results, 
                              timestamp=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    except Exception as e:
        return render_template('index.html', 
                              query=query, 
                              error=f"Erro ao processar a consulta: {str(e)}")

@app.route('/api/search', methods=['POST'])
def api_search():
    """
    API endpoint for AJAX search requests.
    """
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'Por favor, insira uma consulta.'}), 400
    
    try:
        results = agent.process_query(query)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process/<process_number>', methods=['GET'])
def process_detail(process_number):
    """
    Display detailed information about a specific process.
    """
    try:
        # Identify court from process number
        court_code = agent.identify_court_from_process_number(process_number)
        if not court_code:
            return render_template('error.html', 
                                  error=f"Não foi possível identificar o tribunal para o processo {process_number}")
        
        # Build and execute query
        query = agent.build_process_number_query(process_number)
        response = agent.query_api(court_code, query)
        results = agent.format_response(response)
        
        # Add metadata
        results["metadata"] = {
            "process_number": process_number,
            "court": court_code,
            "timestamp": datetime.now().isoformat()
        }
        
        return render_template('process_detail.html', 
                              process_number=process_number, 
                              results=results)
    except Exception as e:
        return render_template('error.html', 
                              error=f"Erro ao buscar detalhes do processo: {str(e)}")

@app.template_filter('format_date')
def format_date(date_str):
    """
    Format date strings for display.
    """
    if not date_str or date_str == 'N/A':
        return 'N/A'
    
    try:
        # Try to parse ISO format
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime('%d/%m/%Y')
    except ValueError:
        # If parsing fails, return the original string
        return date_str

@app.template_filter('format_currency')
def format_currency(value):
    """
    Format currency values for display.
    """
    if not value or value == 'N/A':
        return 'N/A'
    
    try:
        # Convert to float and format as currency
        float_value = float(value)
        return f"R$ {float_value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except ValueError:
        # If conversion fails, return the original string
        return value

def create_app():
    """
    Create and configure the Flask application.
    """
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Create templates
    create_templates()
    
    # Create static files
    create_static_files()
    
    return app

def create_templates():
    """
    Create HTML templates for the application.
    """
    # Index template
    with open('templates/index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataJud - Consulta de Processos Judiciais</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">DataJud</a>
        </div>
    </nav>

    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-body">
                        <h1 class="card-title text-center mb-4">Consulta de Processos Judiciais</h1>
                        
                        {% if error %}
                        <div class="alert alert-danger" role="alert">
                            {{ error }}
                        </div>
                        {% endif %}
                        
                        <form action="{{ url_for('search') }}" method="post" id="search-form">
                            <div class="mb-3">
                                <label for="query" class="form-label">Digite sua consulta:</label>
                                <input type="text" class="form-control form-control-lg" id="query" name="query" 
                                       placeholder="Número do processo ou termos de busca" 
                                       value="{{ query|default('') }}" required>
                                <div class="form-text">
                                    Exemplos: 
                                    <ul>
                                        <li>Número do processo (formato CNJ): 0000000-00.0000.0.00.0000</li>
                                        <li>Termos de busca: habeas corpus, dano moral, etc.</li>
                                    </ul>
                                </div>
                            </div>
                            <div class="d-grid">
                                <button type="submit" class="btn btn-primary btn-lg" id="search-button">
                                    <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true" id="search-spinner"></span>
                                    Pesquisar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer class="footer mt-5 py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">DataJud - Consulta de Processos Judiciais - {{ timestamp|default(now().strftime('%d/%m/%Y')) }}</span>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
        ''')
    
    # Results template
    with open('templates/results.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resultados - DataJud</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">DataJud</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <form class="d-flex ms-auto" action="{{ url_for('search') }}" method="post">
                    <input class="form-control me-2" type="search" name="query" placeholder="Nova consulta" value="{{ query }}">
                    <button class="btn btn-light" type="submit">Pesquisar</button>
                </form>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <div class="card shadow mb-4">
                    <div class="card-header bg-light">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">Resultados para: "{{ query }}"</h5>
                            <span class="badge bg-primary">{{ results.total_hits }} processos encontrados</span>
                        </div>
                    </div>
                    <div class="card-body">
                        {% if results.total_hits == 0 %}
                            <div class="alert alert-info">
                                Nenhum processo encontrado para a consulta "{{ query }}".
                            </div>
                        {% else %}
                            <div class="mb-3">
                                <div class="input-group">
                                    <span class="input-group-text"><i class="bi bi-search"></i></span>
                                    <input type="text" class="form-control" id="filter-results" placeholder="Filtrar resultados...">
                                </div>
                            </div>
                            
                            <div class="table-responsive">
                                <table class="table table-hover" id="results-table">
                                    <thead>
                                        <tr>
                                            <th class="sortable" data-sort="numero">Número <i class="bi bi-arrow-down-up"></i></th>
                                            <th class="sortable" data-sort="classe">Classe <i class="bi bi-arrow-down-up"></i></th>
                                            <th class="sortable" data-sort="data">Data <i class="bi bi-arrow-down-up"></i></th>
                                            <th class="sortable" data-sort="orgao">Órgão Julgador <i class="bi bi-arrow-down-up"></i></th>
                                            <th>Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for process in results.processes %}
                                        <tr class="result-row">
                                            <td class="numero">{{ process.numero_processo }}</td>
                                            <td class="classe">{{ process.classe }}</td>
                                            <td class="data">{{ process.data_ajuizamento|format_date }}</td>
                                            <td class="orgao">{{ process.orgao_julgador }}</td>
                                            <td>
                                                <a href="{{ url_for('process_detail', process_number=process.numero_processo) }}" class="btn btn-sm btn-outline-primary">
                                                    <i class="bi bi-eye"></i> Detalhes
                                                </a>
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% endif %}
                    </div>
                    <div class="card-footer text-muted">
                        Consulta realizada em {{ timestamp }}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer class="footer mt-5 py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">DataJud - Consulta de Processos Judiciais - {{ timestamp }}</span>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
        ''')
    
    # Process detail template
    with open('templates/process_detail.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Processo {{ process_number }} - DataJud</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">DataJud</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <form class="d-flex ms-auto" action="{{ url_for('search') }}" method="post">
                    <input class="form-control me-2" type="search" name="query" placeholder="Nova consulta">
                    <button class="btn btn-light" type="submit">Pesquisar</button>
                </form>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="{{ url_for('index') }}">Início</a></li>
                <li class="breadcrumb-item active" aria-current="page">Processo {{ process_number }}</li>
            </ol>
        </nav>
        
        {% if results.processes|length == 0 %}
            <div class="alert alert-warning">
                Processo não encontrado.
            </div>
        {% else %}
            {% set process = results.processes[0] %}
            <div class="card shadow mb-4">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0">Processo {{ process.numero_processo }}</h4>
                </div>
                <div class="card-body">
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <h5>Dados Básicos</h5>
                            <table class="table table-sm">
                                <tr>
                                    <th>Classe:</th>
                                    <td>{{ process.classe }}</td>
                                </tr>
                                <tr>
                                    <th>Assunto:</th>
                                    <td>{{ process.assunto }}</td>
                                </tr>
                                <tr>
                                    <th>Data de Ajuizamento:</th>
                                    <td>{{ process.data_ajuizamento|format_date }}</td>
                                </tr>
                                <tr>
                                    <th>Valor da Causa:</th>
                                    <td>{{ process.valor_causa|format_currency }}</td>
                                </tr>
                                <tr>
                                    <th>Órgão Julgador:</th>
                                    <td>{{ process.orgao_julgador }}</td>
                                </tr>
                            </table>
                        </div>
                        <div class="col-md-6">
                            <h5>Partes do Processo</h5>
                            <div class="accordion" id="accordionPartes">
                                {% for parte in process.partes %}
                                <div class="accordion-item">
                                    <h2 class="accordion-header" id="heading{{ loop.index }}">
                                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" 
                                                data-bs-target="#collapse{{ loop.index }}">
                                            {{ parte.tipo }}: {{ parte.nome }}
                                        </button>
                                    </h2>
                                    <div id="collapse{{ loop.index }}" class="accordion-collapse collapse" 
                                         aria-labelledby="heading{{ loop.index }}" data-bs-parent="#accordionPartes">
                                        <div class="accordion-body">
                                            <p><strong>Documento:</strong> {{ parte.documento }}</p>
                                            {% if parte.advogados %}
                                                <p><strong>Advogados:</strong></p>
                                                <ul>
                                                    {% for adv in parte.advogados %}
                                                        <li>{{ adv.nome }} ({{ adv.documento }})</li>
                                                    {% endfor %}
                                                </ul>
                                            {% endif %}
                                        </div>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                    
                    <h5>Movimentações</h5>
                    <div class="table-responsive">
                        <table class="table table-striped table-hover">
                            <thead>
                                <tr>
                                    <th>Data</th>
                                    <th>Movimento</th>
                                    <th>Complemento</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for mov in process.movimentos %}
                                <tr>
                                    <td>{{ mov.data|format_date }}</td>
                                    <td>{{ mov.nome }}</td>
                                    <td>{{ mov.complemento }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="card-footer text-muted">
                    Tribunal: {{ results.metadata.court }} | Consulta realizada em {{ results.metadata.timestamp|format_date }}
                </div>
            </div>
        {% endif %}
    </div>

    <footer class="footer mt-5 py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">DataJud - Consulta de Processos Judiciais</span>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
        ''')
    
    # Error template
    with open('templates/error.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erro - DataJud</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">DataJud</a>
        </div>
    </nav>

    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-danger text-white">
                        <h4 class="mb-0">Erro</h4>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-danger">
                            {{ error }}
                        </div>
                        <div class="text-center mt-4">
                            <a href="{{ url_for('index') }}" class="btn btn-primary">Voltar para a página inicial</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer class="footer mt-5 py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">DataJud - Consulta de Processos Judiciais</span>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        ''')

def create_static_files():
    """
    Create static files (CSS and JavaScript) for the application.
    """
    # Create CSS directory
    os.makedirs('static/css', exist_ok=True)
    
    # Create JS directory
    os.makedirs('static/js', exist_ok=True)
    
    # CSS file
    with open('static/css/style.css', 'w') as f:
        f.write('''
body {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.footer {
    margin-top: auto;
}

.card {
    border-radius: 10px;
}

.card-header {
    border-top-left-radius: 10px !important;
    border-top-right-radius: 10px !important;
}

.sortable {
    cursor: pointer;
}

.sortable:hover {
    background-color: #f8f9fa;
}

.bi-arrow-down-up {
    font-size: 0.8rem;
    opacity: 0.5;
}

.sorting-asc .bi-arrow-down-up::before {
    content: "\\F143";
    opacity: 1;
}

.sorting-desc .bi-arrow-down-up::before {
    content: "\\F146";
    opacity: 1;
}
        ''')
    
    # JavaScript file
    with open('static/js/script.js', 'w') as f:
        f.write('''
document.addEventListener('DOMContentLoaded', function() {
    // Show loading spinner when form is submitted
    const searchForm = document.getElementById('search-form');
    const searchButton = document.getElementById('search-button');
    const searchSpinner = document.getElementById('search-spinner');
    
    if (searchForm) {
        searchForm.addEventListener('submit', function() {
            if (searchButton && searchSpinner) {
                searchButton.setAttribute('disabled', 'disabled');
                searchButton.innerHTML = 'Pesquisando...';
                searchSpinner.classList.remove('d-none');
            }
        });
    }
    
    // Filter results
    const filterInput = document.getElementById('filter-results');
    if (filterInput) {
        filterInput.addEventListener('keyup', function() {
            const filterValue = this.value.toLowerCase();
            const rows = document.querySelectorAll('#results-table tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(filterValue)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
    
    // Sorting
    const sortableHeaders = document.querySelectorAll('.sortable');
    if (sortableHeaders) {
        sortableHeaders.forEach(header => {
            header.addEventListener('click', function() {
                const sortBy = this.getAttribute('data-sort');
                const isAscending = this.classList.contains('sorting-asc');
                
                // Remove sorting classes from all headers
                document.querySelectorAll('.sortable').forEach(h => {
                    h.classList.remove('sorting-asc', 'sorting-desc');
                });
                
                // Add sorting class to current header
                this.classList.add(isAscending ? 'sorting-desc' : 'sorting-asc');
                
                // Sort the table
                sortTable(sortBy, !isAscending);
            });
        });
    }
    
    function sortTable(sortBy, ascending) {
        const table = document.getElementById('results-table');
        if (!table) return;
        
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aValue = a.querySelector('.' + sortBy).textContent.trim();
            const bValue = b.querySelector('.' + sortBy).textContent.trim();
            
            if (ascending) {
                return aValue.localeCompare(bValue);
            } else {
                return bValue.localeCompare(aValue);
            }
        });
        
        // Remove existing rows
        rows.forEach(row => {
            tbody.removeChild(row);
        });
        
        // Add sorted rows
        rows.forEach(row => {
            tbody.appendChild(row);
        });
    }
});
        ''')

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
