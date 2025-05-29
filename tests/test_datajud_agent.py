#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the DatajudAgent class.

This module contains tests for the DatajudAgent class, which is responsible
for querying the Datajud API and processing responses.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the DatajudAgent class
from datajud_agent import DatajudAgent, COURT_ENDPOINTS

# Set API key as environment variable if provided
os.environ['DATAJUD_API_KEY'] = 'cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=='


# Sample data for tests
VALID_PROCESS_NUMBERS = [
    '0000001-70.2020.1.00.0000',  # Federal court
    '0000002-80.2020.2.00.0000',  # State court
    '0000003-90.2020.3.00.0000',  # Labor court
    '0000004-10.2020.4.00.0000',  # Electoral court
    '0000005-20.2020.6.00.0000',  # Superior court
]

INVALID_PROCESS_NUMBERS = [
    '000000-70.2020.1.00.0000',   # Missing digit
    '0000001-70.2020.9.00.0000',  # Invalid justice type
    '0000001-70.2020.1.99.0000',  # Invalid court
    'not-a-process-number',       # Not a process number
    '0000001702020100.0000',      # No separators
]

SAMPLE_TEXT_QUERY = "habeas corpus"

# Sample Elasticsearch-style response
SAMPLE_ES_RESPONSE = {
    "took": 5,
    "timed_out": False,
    "_shards": {
        "total": 1,
        "successful": 1,
        "skipped": 0,
        "failed": 0
    },
    "hits": {
        "total": {
            "value": 1,
            "relation": "eq"
        },
        "max_score": 1.0,
        "hits": [
            {
                "_index": "api_publica_stf",
                "_type": "_doc",
                "_id": "12345",
                "_score": 1.0,
                "_source": {
                    "numeroProcesso": "0000001-70.2020.6.00.0000",
                    "classe": {
                        "nome": "Habeas Corpus"
                    },
                    "assunto": {
                        "nome": "Direito Penal"
                    },
                    "dadosBasicos": {
                        "dataAjuizamento": "2020-01-01T00:00:00Z",
                        "valorCausa": "1000.00"
                    },
                    "orgaoJulgador": {
                        "nome": "Tribunal Pleno"
                    },
                    "partes": [
                        {
                            "tipo": "PACIENTE",
                            "pessoa": {
                                "nome": "João da Silva",
                                "numeroDocumentoPrincipal": "123.456.789-00"
                            },
                            "advogados": [
                                {
                                    "pessoa": {
                                        "nome": "Maria Advogada",
                                        "numeroDocumentoPrincipal": "OAB/DF 12345"
                                    }
                                }
                            ]
                        },
                        {
                            "tipo": "AUTORIDADE COATORA",
                            "pessoa": {
                                "nome": "Superior Tribunal de Justiça",
                                "numeroDocumentoPrincipal": ""
                            },
                            "advogados": []
                        }
                    ],
                    "movimentos": [
                        {
                            "data": "2020-01-02T00:00:00Z",
                            "nome": "Conclusos para decisão",
                            "complemento": ""
                        },
                        {
                            "data": "2020-01-03T00:00:00Z",
                            "nome": "Decisão monocrática",
                            "complemento": "Liminar deferida"
                        }
                    ]
                }
            }
        ]
    }
}

# Empty response
EMPTY_ES_RESPONSE = {
    "took": 5,
    "timed_out": False,
    "_shards": {
        "total": 1,
        "successful": 1,
        "skipped": 0,
        "failed": 0
    },
    "hits": {
        "total": {
            "value": 0,
            "relation": "eq"
        },
        "max_score": None,
        "hits": []
    }
}


@pytest.fixture
def agent():
    """Create a DatajudAgent instance for testing."""
    return DatajudAgent(verbose=True)


class TestDatajudAgent:
    """Tests for the DatajudAgent class."""

    def test_extract_process_number_valid(self, agent):
        """Test extracting valid process numbers from text."""
        for process_number in VALID_PROCESS_NUMBERS:
            text = f"This is a text containing a process number {process_number} in the middle."
            extracted = agent.extract_process_number(text)
            assert extracted == process_number

    def test_extract_process_number_invalid(self, agent):
        """Test extracting invalid process numbers from text."""
        for invalid_text in INVALID_PROCESS_NUMBERS:
            text = f"This is a text containing an invalid process number {invalid_text} in the middle."
            extracted = agent.extract_process_number(text)
            assert extracted is None

    def test_extract_process_number_not_found(self, agent):
        """Test extracting process numbers when none is present."""
        text = "This text does not contain any process number."
        extracted = agent.extract_process_number(text)
        assert extracted is None

    def test_identify_court_from_process_number_valid(self, agent):
        """Test identifying court from valid process numbers."""
        # Federal court
        court = agent.identify_court_from_process_number('0000001-70.2020.1.01.0000')
        assert court == 'trf1'

        # State court
        court = agent.identify_court_from_process_number('0000002-80.2020.2.26.0000')
        assert court == 'tjsp'

        # Labor court
        court = agent.identify_court_from_process_number('0000003-90.2020.3.05.0000')
        assert court == 'trt5'

        # Electoral court
        court = agent.identify_court_from_process_number('0000004-10.2020.4.11.0000')
        assert court == 'tre-mg'

        # Superior court
        court = agent.identify_court_from_process_number('0000005-20.2020.6.00.0000')
        assert court == 'stf'

    def test_identify_court_from_process_number_invalid(self, agent):
        """Test identifying court from invalid process numbers."""
        for invalid_number in INVALID_PROCESS_NUMBERS:
            court = agent.identify_court_from_process_number(invalid_number)
            assert court is None

    def test_build_process_number_query(self, agent):
        """Test building a query for a process number."""
        process_number = VALID_PROCESS_NUMBERS[0]
        query = agent.build_process_number_query(process_number)
        
        # Check query structure
        assert 'query' in query
        assert 'bool' in query['query']
        assert 'must' in query['query']['bool']
        assert len(query['query']['bool']['must']) > 0
        assert 'match' in query['query']['bool']['must'][0]
        assert 'numeroProcesso' in query['query']['bool']['must'][0]['match']
        assert query['query']['bool']['must'][0]['match']['numeroProcesso'] == process_number
        assert 'size' in query
        assert query['size'] > 0

    def test_build_text_search_query_no_field(self, agent):
        """Test building a text search query without specifying a field."""
        query = agent.build_text_search_query(SAMPLE_TEXT_QUERY)
        
        # Check query structure
        assert 'query' in query
        assert 'multi_match' in query['query']
        assert 'query' in query['query']['multi_match']
        assert query['query']['multi_match']['query'] == SAMPLE_TEXT_QUERY
        assert 'fields' in query['query']['multi_match']
        assert isinstance(query['query']['multi_match']['fields'], list)
        assert len(query['query']['multi_match']['fields']) > 0
        assert 'size' in query
        assert query['size'] > 0

    def test_build_text_search_query_with_field(self, agent):
        """Test building a text search query with a specific field."""
        field = "classe.nome"
        query = agent.build_text_search_query(SAMPLE_TEXT_QUERY, field)
        
        # Check query structure
        assert 'query' in query
        assert 'match' in query['query']
        assert field in query['query']['match']
        assert query['query']['match'][field] == SAMPLE_TEXT_QUERY
        assert 'size' in query
        assert query['size'] > 0

    def test_format_response_with_data(self, agent):
        """Test formatting a response with data."""
        formatted = agent.format_response(SAMPLE_ES_RESPONSE)
        
        # Check formatted response structure
        assert 'total_hits' in formatted
        assert formatted['total_hits'] == 1
        assert 'processes' in formatted
        assert len(formatted['processes']) == 1
        
        process = formatted['processes'][0]
        assert 'numero_processo' in process
        assert process['numero_processo'] == "0000001-70.2020.6.00.0000"
        assert 'classe' in process
        assert process['classe'] == "Habeas Corpus"
        assert 'assunto' in process
        assert process['assunto'] == "Direito Penal"
        assert 'data_ajuizamento' in process
        assert process['data_ajuizamento'] == "2020-01-01T00:00:00Z"
        assert 'valor_causa' in process
        assert process['valor_causa'] == "1000.00"
        assert 'orgao_julgador' in process
        assert process['orgao_julgador'] == "Tribunal Pleno"
        
        assert 'partes' in process
        assert len(process['partes']) == 2
        assert 'tipo' in process['partes'][0]
        assert 'nome' in process['partes'][0]
        assert 'documento' in process['partes'][0]
        assert 'advogados' in process['partes'][0]
        
        assert 'movimentos' in process
        assert len(process['movimentos']) == 2
        assert 'data' in process['movimentos'][0]
        assert 'nome' in process['movimentos'][0]
        assert 'complemento' in process['movimentos'][0]

    def test_format_response_empty(self, agent):
        """Test formatting an empty response."""
        formatted = agent.format_response(EMPTY_ES_RESPONSE)
        
        # Check formatted response structure
        assert 'total_hits' in formatted
        assert formatted['total_hits'] == 0
        assert 'processes' in formatted
        assert len(formatted['processes']) == 0

    @patch('requests.Session.post')
    def test_query_api_success(self, mock_post, agent):
        """Test querying the API with successful response."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_ES_RESPONSE
        mock_post.return_value = mock_response
        
        # Call the method
        court_code = 'stf'
        query = {"query": {"match_all": {}}}
        response = agent.query_api(court_code, query)
        
        # Verify the method was called correctly
        expected_url = f"{agent.API_BASE_URL}/{COURT_ENDPOINTS[court_code]}/_search"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['url'] == expected_url
        assert kwargs['headers']['Content-Type'] == 'application/json'
        assert kwargs['json'] == query
        
        # Verify the response
        assert response == SAMPLE_ES_RESPONSE

    @patch('requests.Session.post')
    def test_query_api_error(self, mock_post, agent):
        """Test querying the API with error response."""
        # Setup mock to raise an exception
        mock_post.side_effect = Exception("API Error")
        
        # Call the method and expect an exception
        court_code = 'stf'
        query = {"query": {"match_all": {}}}
        
        with pytest.raises(Exception) as excinfo:
            agent.query_api(court_code, query)
        
        assert "API Error" in str(excinfo.value)

    def test_query_api_invalid_court(self, agent):
        """Test querying the API with an invalid court code."""
        invalid_court = 'invalid_court'
        query = {"query": {"match_all": {}}}
        
        with pytest.raises(ValueError) as excinfo:
            agent.query_api(invalid_court, query)
        
        assert f"Invalid court code: {invalid_court}" in str(excinfo.value)

    @patch('datajud_agent.DatajudAgent.query_api')
    @patch('datajud_agent.DatajudAgent.identify_court_from_process_number')
    @patch('datajud_agent.DatajudAgent.extract_process_number')
    def test_process_query_with_process_number(self, mock_extract, mock_identify, mock_query, agent):
        """Test processing a query with a process number."""
        # Setup mocks
        process_number = VALID_PROCESS_NUMBERS[0]
        court_code = 'stf'
        mock_extract.return_value = process_number
        mock_identify.return_value = court_code
        mock_query.return_value = SAMPLE_ES_RESPONSE
        
        # Call the method
        query_text = f"Please find information about process {process_number}"
        result = agent.process_query(query_text)
        
        # Verify mocks were called correctly
        mock_extract.assert_called_once_with(query_text)
        mock_identify.assert_called_once_with(process_number)
        mock_query.assert_called_once()
        
        # Verify the result
        assert 'metadata' in result
        assert result['metadata']['query'] == query_text
        assert result['metadata']['process_number'] == process_number
        assert result['metadata']['court'] == court_code
        assert 'processes' in result
        assert len(result['processes']) == 1

    @patch('datajud_agent.DatajudAgent.query_api')
    @patch('datajud_agent.DatajudAgent.extract_process_number')
    def test_process_query_without_process_number(self, mock_extract, mock_query, agent):
        """Test processing a query without a process number."""
        # Setup mocks
        mock_extract.return_value = None
        mock_query.return_value = SAMPLE_ES_RESPONSE
        
        # Call the method
        query_text = "Find information about habeas corpus"
        result = agent.process_query(query_text)
        
        # Verify mocks were called correctly
        mock_extract.assert_called_once_with(query_text)
        mock_query.assert_called_once()
        
        # Verify the result
        assert 'metadata' in result
        assert result['metadata']['query'] == query_text
        assert result['metadata']['process_number'] is None
        assert 'court' in result['metadata']
        assert 'processes' in result
        assert len(result['processes']) == 1


if __name__ == '__main__':
    pytest.main(['-v', __file__])
