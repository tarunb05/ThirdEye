from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import analyze

app = FastAPI(
    title='ThirdEye API',
    description='Multi-LLM Solidity vulnerability scanner',
    version='0.1.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(analyze.router, prefix='/api', tags=['analyze'])

@app.get('/')
def root():
    return {'message': 'ThirdEye API is running', 'version': '0.1.0'}

@app.get('/health')
def health():
    return {'status': 'healthy'}
