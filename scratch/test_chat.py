import requests, sys, json
base='http://127.0.0.1:8000'

def check_db():
    try:
        r=requests.get(f'{base}/db-health')
        print('DB health status:', r.status_code, r.text)
    except Exception as e:
        print('DB health error:', e)
        sys.exit(1)

def create_conv():
    r=requests.post(f'{base}/conversations', json={'title':'TestConv'})
    print('Create conv response:', r.status_code, r.text)
    data=r.json()
    return data.get('conversation_id')

def chat(conv_id, msg):
    payload={'conversation_id':conv_id,'message':msg}
    r=requests.post(f'{base}/chat', json=payload)
    print('Chat status:', r.status_code)
    print('Chat response:', r.text)

if __name__=='__main__':
    check_db()
    cid=create_conv()
    if not cid:
        print('No conversation id')
        sys.exit(1)
    chat(cid,'Hello AI')
