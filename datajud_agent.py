#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataJud Agent - A tool for querying the Brazilian judiciary system via the Datajud API

This script provides an agent that can process natural language queries about
the Brazilian judiciary system, extract relevant information, query the Datajud API,
and return the results in a user-friendly format.

The Datajud API is a public service provided by the Conselho Nacional de Justiça (CNJ)
that offers access to metadata from judicial processes across Brazil.
"""

import re
import os
import json
import logging
import argparse
from typing import Dict, List, Optional, Tuple, Union, Any
import requests
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("datajud_agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("datajud_agent")

# Constants
API_BASE_URL = "https://api-publica.datajud.cnj.jus.br"
DEFAULT_TIMEOUT = 30  # seconds
MAX_RESULTS = 100

# Court codes and their respective endpoints
COURT_ENDPOINTS = {
    # Federal Courts (TRF)
    "trf1": "api_publica_trf1",
    "trf2": "api_publica_trf2",
    "trf3": "api_publica_trf3",
    "trf4": "api_publica_trf4",
    "trf5": "api_publica_trf5",
    "trf6": "api_publica_trf6",
    
    # Superior Courts
    "tst": "api_publica_tst",
    "stj": "api_publica_stj",
    "stf": "api_publica_stf",
    
    # Electoral Courts (TRE)
    "tre-ac": "api_publica_tre-ac",
    "tre-al": "api_publica_tre-al",
    "tre-am": "api_publica_tre-am",
    "tre-ap": "api_publica_tre-ap",
    "tre-ba": "api_publica_tre-ba",
    "tre-ce": "api_publica_tre-ce",
    "tre-dft": "api_publica_tre-dft",
    "tre-es": "api_publica_tre-es",
    "tre-go": "api_publica_tre-go",
    "tre-ma": "api_publica_tre-ma",
    "tre-mg": "api_publica_tre-mg",
    "tre-ms": "api_publica_tre-ms",
    "tre-mt": "api_publica_tre-mt",
    "tre-pa": "api_publica_tre-pa",
    "tre-pb": "api_publica_tre-pb",
    "tre-pe": "api_publica_tre-pe",
    "tre-pi": "api_publica_tre-pi",
    "tre-pr": "api_publica_tre-pr",
    "tre-rj": "api_publica_tre-rj",
    "tre-rn": "api_publica_tre-rn",
    "tre-ro": "api_publica_tre-ro",
    "tre-rr": "api_publica_tre-rr",
    "tre-rs": "api_publica_tre-rs",
    "tre-sc": "api_publica_tre-sc",
    "tre-se": "api_publica_tre-se",
    "tre-sp": "api_publica_tre-sp",
    "tre-to": "api_publica_tre-to",
    
    # State Courts (TJ)
    "tjac": "api_publica_tjac",
    "tjal": "api_publica_tjal",
    "tjam": "api_publica_tjam",
    "tjap": "api_publica_tjap",
    "tjba": "api_publica_tjba",
    "tjce": "api_publica_tjce",
    "tjdft": "api_publica_tjdft",
    "tjes": "api_publica_tjes",
    "tjgo": "api_publica_tjgo",
    "tjma": "api_publica_tjma",
    "tjmg": "api_publica_tjmg",
    "tjms": "api_publica_tjms",
    "tjmt": "api_publica_tjmt",
    "tjpa": "api_publica_tjpa",
    "tjpb": "api_publica_tjpb",
    "tjpe": "api_publica_tjpe",
    "tjpi": "api_publica_tjpi",
    "tjpr": "api_publica_tjpr",
    "tjrj": "api_publica_tjrj",
    "tjrn": "api_publica_tjrn",
    "tjro": "api_publica_tjro",
    "tjrr": "api_publica_tjrr",
    "tjrs": "api_publica_tjrs",
    "tjsc": "api_publica_tjsc",
    "tjse": "api_publica_tjse",
    "tjsp": "api_publica_tjsp",
    "tjto": "api_publica_tjto",
    
    # Labor Courts (TRT)
    "trt1": "api_publica_trt1",
    "trt2": "api_publica_trt2",
    "trt3": "api_publica_trt3",
    "trt4": "api_publica_trt4",
    "trt5": "api_publica_trt5",
    "trt6": "api_publica_trt6",
    "trt7": "api_publica_trt7",
    "trt8": "api_publica_trt8",
    "trt9": "api_publica_trt9",
    "trt10": "api_publica_trt10",
    "trt11": "api_publica_trt11",
    "trt12": "api_publica_trt12",
    "trt13": "api_publica_trt13",
    "trt14": "api_publica_trt14",
    "trt15": "api_publica_trt15",
    "trt16": "api_publica_trt16",
    "trt17": "api_publica_trt17",
    "trt18": "api_publica_trt18",
    "trt19": "api_publica_trt19",
    "trt20": "api_publica_trt20",
    "trt21": "api_publica_trt21",
    "trt22": "api_publica_trt22",
    "trt23": "api_publica_trt23",
    "trt24": "api_publica_trt24",
}

# Court code mapping from CNJ process number format
# The 7th and 8th digits in the CNJ format represent the court type
COURT_CODE_MAPPING = {
    "1": {  # Justice type 1 = Federal Courts
        "01": "trf1",
        "02": "trf2",
        "03": "trf3",
        "04": "trf4",
        "05": "trf5",
        "06": "trf6",
    },
    "2": {  # Justice type 2 = State Courts
        "01": "tjac",
        "02": "tjal",
        "03": "tjap",
        "04": "tjam",
        "05": "tjba",
        "06": "tjce",
        "07": "tjdft",
        "08": "tjes",
        "09": "tjgo",
        "10": "tjma",
        "11": "tjmg",
        "12": "tjms",
        "13": "tjmt",
        "14": "tjpa",
        "15": "tjpb",
        "16": "tjpe",
        "17": "tjpi",
        "18": "tjpr",
        "19": "tjrj",
        "20": "tjrn",
        "21": "tjro",
        "22": "tjrr",
        "23": "tjrs",
        "24": "tjsc",
        "25": "tjse",
        "26": "tjsp",
        "27": "tjto",
    },
    "3": {  # Justice type 3 = Labor Courts
        "01": "trt1",
        "02": "trt2",
        "03": "trt3",
        "04": "trt4",
        "05": "trt5",
        "06": "trt6",
        "07": "trt7",
        "08": "trt8",
        "09": "trt9",
        "10": "trt10",
        "11": "trt11",
        "12": "trt12",
        "13": "trt13",
        "14": "trt14",
        "15": "trt15",
        "16": "trt16",
        "17": "trt17",
        "18": "trt18",
        "19": "trt19",
        "20": "trt20",
        "21": "trt21",
        "22": "trt22",
        "23": "trt23",
        "24": "trt24",
    },
    "4": {  # Justice type 4 = Electoral Courts
        "01": "tre-ac",
        "02": "tre-al",
        "03": "tre-ap",
        "04": "tre-am",
        "05": "tre-ba",
        "06": "tre-ce",
        "07": "tre-dft",
        "08": "tre-es",
        "09": "tre-go",
        "10": "tre-ma",
        "11": "tre-mg",
        "12": "tre-ms",
        "13": "tre-mt",
        "14": "tre-pa",
        "15": "tre-pb",
        "16": "tre-pe",
        "17": "tre-pi",
        "18": "tre-pr",
        "19": "tre-rj",
        "20": "tre-rn",
        "21": "tre-ro",
        "22": "tre-rr",
        "23": "tre-rs",
        "24": "tre-sc",
        "25": "tre-se",
        "26": "tre-sp",
        "27": "tre-to",
    },
    "5": {  # Justice type 5 = Military Courts
        # Add military courts if needed
    },
    "6": {  # Justice type 6 = Superior Courts
        "00": "stf",  # Supreme Federal Court
        "01": "stj",  # Superior Court of Justice
        "02": "tst",  # Superior Labor Court
    },
}


class DatajudAgent:
    """
    Agent for querying the Datajud API and processing responses.
    
    This class provides methods to:
    - Parse natural language queries
    - Extract process numbers
    - Identify the appropriate court
    - Format and send requests to the Datajud API
    - Process and format responses
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the DatajudAgent.
        
        Args:
            verbose: If True, enables detailed logging
        """
        self.verbose = verbose
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        self.session = requests.Session()
        logger.debug("DatajudAgent initialized")
    
    def extract_process_number(self, text: str) -> Optional[str]:
        """
        Extract a CNJ-formatted process number from text.
        
        The CNJ format is: NNNNNNN-DD.AAAA.J.TR.OOOO
        Where:
        - NNNNNNN: Sequential number
        - DD: Check digit
        - AAAA: Year
        - J: Justice type (1=Federal, 2=State, 3=Labor, 4=Electoral, 5=Military, 6=Superior)
        - TR: Court identifier
        - OOOO: Origin identifier
        
        Args:
            text: Text to search for a process number
            
        Returns:
            Extracted process number or None if not found
        """
        # Pattern for CNJ-formatted process numbers
        pattern = r'\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b'
        match = re.search(pattern, text)
        
        if match:
            process_number = match.group(0)
            logger.debug(f"Extracted process number: {process_number}")
            return process_number
        
        logger.debug("No process number found in text")
        return None
    
    def identify_court_from_process_number(self, process_number: str) -> Optional[str]:
        """
        Identify the court from a CNJ-formatted process number.
        
        Args:
            process_number: CNJ-formatted process number
            
        Returns:
            Court code or None if not identifiable
        """
        try:
            # Extract justice type (J) and court identifier (TR)
            parts = process_number.split('.')
            if len(parts) != 5:
                logger.warning(f"Invalid process number format: {process_number}")
                return None
            
            justice_type = parts[2]
            court_id = parts[3]
            
            if justice_type in COURT_CODE_MAPPING and court_id in COURT_CODE_MAPPING[justice_type]:
                court_code = COURT_CODE_MAPPING[justice_type][court_id]
                logger.debug(f"Identified court: {court_code} from process number: {process_number}")
                return court_code
            
            logger.warning(f"Could not identify court for process number: {process_number}")
            return None
        
        except Exception as e:
            logger.error(f"Error identifying court from process number: {e}")
            return None
    
    def build_process_number_query(self, process_number: str) -> Dict:
        """
        Build a query to search for a specific process number.
        
        Args:
            process_number: CNJ-formatted process number
            
        Returns:
            Query dictionary for the API
        """
        # Replace special characters for the query
        clean_number = process_number.replace('-', '').replace('.', '')
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "numeroProcesso": process_number
                            }
                        }
                    ]
                }
            },
            "size": MAX_RESULTS
        }
        
        logger.debug(f"Built query for process number: {process_number}")
        return query
    
    def build_text_search_query(self, text: str, field: str = None) -> Dict:
        """
        Build a query to search for text in process metadata.
        
        Args:
            text: Text to search for
            field: Specific field to search in (optional)
            
        Returns:
            Query dictionary for the API
        """
        if field:
            query = {
                "query": {
                    "match": {
                        field: text
                    }
                },
                "size": MAX_RESULTS
            }
        else:
            # Search across multiple relevant fields
            query = {
                "query": {
                    "multi_match": {
                        "query": text,
                        "fields": ["classe.nome", "assunto.nome", "orgaoJulgador.nome", "dadosBasicos.valorCausa"]
                    }
                },
                "size": MAX_RESULTS
            }
        
        logger.debug(f"Built text search query for: {text}")
        return query
    
    def query_api(self, court_code: str, query: Dict) -> Dict:
        """
        Send a query to the Datajud API.
        
        Args:
            court_code: Court code to determine the endpoint
            query: Query dictionary
            
        Returns:
            API response as a dictionary
            
        Raises:
            ValueError: If court_code is invalid
            requests.RequestException: For API request errors
        """
        if court_code not in COURT_ENDPOINTS:
            raise ValueError(f"Invalid court code: {court_code}")
        
        endpoint = COURT_ENDPOINTS[court_code]
        url = f"{API_BASE_URL}/{endpoint}/_search"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add API key to headers if available
        api_key = os.environ.get('DATAJUD_API_KEY')
        if api_key:
            headers['X-API-Key'] = api_key
            logger.debug("Added API key to request headers")
        
        try:
            logger.debug(f"Sending request to: {url}")
            logger.debug(f"Query: {json.dumps(query)}")
            
            response = self.session.post(
                url,
                headers=headers,
                json=query,
                timeout=DEFAULT_TIMEOUT
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"Received response with {len(data.get('hits', {}).get('hits', []))} hits")
            return data
        
        except requests.RequestException as e:
            logger.error(f"API request error: {e}")
            raise
    
    def format_response(self, response: Dict) -> Dict:
        """
        Format the API response into a more user-friendly structure.
        
        Args:
            response: Raw API response
            
        Returns:
            Formatted response dictionary
        """
        formatted = {
            "total_hits": response.get("hits", {}).get("total", {}).get("value", 0),
            "processes": []
        }
        
        hits = response.get("hits", {}).get("hits", [])
        
        for hit in hits:
            source = hit.get("_source", {})
            
            # Extract basic process information
            process = {
                "numero_processo": source.get("numeroProcesso", "N/A"),
                "classe": source.get("classe", {}).get("nome", "N/A"),
                "assunto": source.get("assunto", {}).get("nome", "N/A"),
                "data_ajuizamento": source.get("dadosBasicos", {}).get("dataAjuizamento", "N/A"),
                "valor_causa": source.get("dadosBasicos", {}).get("valorCausa", "N/A"),
                "orgao_julgador": source.get("orgaoJulgador", {}).get("nome", "N/A"),
                "partes": []
            }
            
            # Extract parties information
            for parte in source.get("partes", []):
                party = {
                    "tipo": parte.get("tipo", "N/A"),
                    "nome": parte.get("pessoa", {}).get("nome", "N/A"),
                    "documento": parte.get("pessoa", {}).get("numeroDocumentoPrincipal", "N/A"),
                    "advogados": []
                }
                
                # Extract lawyers information
                for advogado in parte.get("advogados", []):
                    lawyer = {
                        "nome": advogado.get("pessoa", {}).get("nome", "N/A"),
                        "documento": advogado.get("pessoa", {}).get("numeroDocumentoPrincipal", "N/A")
                    }
                    party["advogados"].append(lawyer)
                
                process["partes"].append(party)
            
            # Extract movements information
            process["movimentos"] = []
            for movimento in source.get("movimentos", []):
                movement = {
                    "data": movimento.get("data", "N/A"),
                    "nome": movimento.get("nome", "N/A"),
                    "complemento": movimento.get("complemento", "N/A")
                }
                process["movimentos"].append(movement)
            
            formatted["processes"].append(process)
        
        return formatted
    
    def process_query(self, query_text: str) -> Dict:
        """
        Process a natural language query and return results from the Datajud API.
        
        This method:
        1. Extracts a process number if present
        2. Identifies the appropriate court
        3. Builds and sends the query
        4. Formats the response
        
        Args:
            query_text: Natural language query text
            
        Returns:
            Formatted response dictionary
            
        Raises:
            ValueError: For invalid inputs or court identification failures
            requests.RequestException: For API request errors
        """
        logger.info(f"Processing query: {query_text}")
        
        # Try to extract a process number
        process_number = self.extract_process_number(query_text)
        
        if process_number:
            # If we have a process number, identify the court
            court_code = self.identify_court_from_process_number(process_number)
            
            if not court_code:
                raise ValueError(f"Could not identify court for process number: {process_number}")
            
            # Build a query for the process number
            query = self.build_process_number_query(process_number)
            
        else:
            # If no process number, try to extract other search parameters
            # For simplicity, we'll default to the Federal Supreme Court (STF)
            # In a more sophisticated implementation, we would analyze the query
            # to determine the most appropriate court
            court_code = "stf"
            query = self.build_text_search_query(query_text)
        
        # Send the query to the API
        try:
            response = self.query_api(court_code, query)
            
            # Format the response
            formatted_response = self.format_response(response)
            
            # Add metadata
            formatted_response["metadata"] = {
                "query": query_text,
                "process_number": process_number,
                "court": court_code,
                "timestamp": datetime.now().isoformat()
            }
            
            return formatted_response
            
        except requests.RequestException as e:
            logger.error(f"Error querying API: {e}")
            raise
    
    def pretty_print_results(self, results: Dict) -> None:
        """
        Print the results in a human-readable format.
        
        Args:
            results: Formatted results dictionary
        """
        metadata = results.get("metadata", {})
        processes = results.get("processes", [])
        total_hits = results.get("total_hits", 0)
        
        print("\n" + "="*80)
        print(f"DATAJUD QUERY RESULTS")
        print("="*80)
        print(f"Query: {metadata.get('query', 'N/A')}")
        print(f"Process Number: {metadata.get('process_number', 'N/A')}")
        print(f"Court: {metadata.get('court', 'N/A')}")
        print(f"Timestamp: {metadata.get('timestamp', 'N/A')}")
        print(f"Total Hits: {total_hits}")
        print("-"*80)
        
        if not processes:
            print("No results found.")
            return
        
        for i, process in enumerate(processes, 1):
            print(f"\nPROCESS {i}/{len(processes)}:")
            print(f"  Número: {process.get('numero_processo', 'N/A')}")
            print(f"  Classe: {process.get('classe', 'N/A')}")
            print(f"  Assunto: {process.get('assunto', 'N/A')}")
            print(f"  Data de Ajuizamento: {process.get('data_ajuizamento', 'N/A')}")
            print(f"  Valor da Causa: {process.get('valor_causa', 'N/A')}")
            print(f"  Órgão Julgador: {process.get('orgao_julgador', 'N/A')}")
            
            print("\n  PARTES:")
            for parte in process.get("partes", []):
                print(f"    {parte.get('tipo', 'N/A')}: {parte.get('nome', 'N/A')}")
                print(f"      Documento: {parte.get('documento', 'N/A')}")
                
                if parte.get("advogados"):
                    print("      Advogados:")
                    for adv in parte.get("advogados", []):
                        print(f"        - {adv.get('nome', 'N/A')} ({adv.get('documento', 'N/A')})")
            
            print("\n  MOVIMENTOS RECENTES:")
            for j, mov in enumerate(process.get("movimentos", [])[:5], 1):
                print(f"    {j}. {mov.get('data', 'N/A')} - {mov.get('nome', 'N/A')}")
                if mov.get("complemento"):
                    print(f"       {mov.get('complemento', '')}")
            
            if len(process.get("movimentos", [])) > 5:
                print(f"    ... and {len(process.get('movimentos', [])) - 5} more movements")
            
            print("-"*80)


def main():
    """
    Main function to run the DatajudAgent from the command line.
    """
    parser = argparse.ArgumentParser(description="Query the Datajud API with natural language")
    parser.add_argument("query", nargs="*", help="Natural language query")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    agent = DatajudAgent(verbose=args.verbose)
    
    if args.interactive:
        print("DataJud Agent - Interactive Mode")
        print("Type 'exit' or 'quit' to exit")
        
        while True:
            query = input("\nEnter your query: ")
            
            if query.lower() in ["exit", "quit"]:
                break
            
            try:
                results = agent.process_query(query)
                agent.pretty_print_results(results)
            except Exception as e:
                print(f"Error: {e}")
    
    elif args.query:
        query = " ".join(args.query)
        try:
            results = agent.process_query(query)
            agent.pretty_print_results(results)
        except Exception as e:
            print(f"Error: {e}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
