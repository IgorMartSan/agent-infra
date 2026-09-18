import os
import sys

# Coloca src/ no PYTHONPATH para os testes importarem os módulos da API.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))