import os
import sys
# Ensure project root is in PYTHONPATH
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_db_health():
    resp = client.get('/db-health')
    print('DB health status code:', resp.status_code)
    print('DB health json:', resp.json())

def test_chat_flow():
    # create a conversation
    conv_resp = client.post('/conversations', json={'title': 'TestConv'})
    print('Create conv status:', conv_resp.status_code)
    conv_data = conv_resp.json()
    conv_id = conv_data.get('conversation_id')
    print('Conversation ID:', conv_id)
    # call chat endpoint
    chat_resp = client.post('/chat', json={'conversation_id': conv_id, 'message': 'Hello AI'})
    print('Chat status:', chat_resp.status_code)
    print('Chat response json:', chat_resp.json())

if __name__ == '__main__':
    test_db_health()
    test_chat_flow()
