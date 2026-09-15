import sys
import os

# Adicionar src ao PYTHONPATH
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

# Importar e rodar a app
import uvicorn
from main import app

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)