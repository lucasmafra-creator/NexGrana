import httpx
from app import ai_advisor

def test_ai_off_by_default(monkeypatch):
    monkeypatch.setenv('SIM_AI_PROVIDER','none')
    assert ai_advisor.advise('TEST DATA',{}) is None
    assert ai_advisor.status()['enabled'] is False

def test_ai_rejects_remote_endpoint(monkeypatch):
    monkeypatch.setenv('SIM_AI_PROVIDER','ollama');monkeypatch.setenv('SIM_AI_MODEL','TEST_DATA_MODEL');monkeypatch.setenv('SIM_AI_URL','http://example.com')
    assert ai_advisor.status()['enabled'] is False
    assert ai_advisor.advise('TEST DATA',{})['ok'] is False

def test_local_ai_response_is_labeled_and_has_no_tools(monkeypatch):
    monkeypatch.setenv('SIM_AI_PROVIDER','ollama');monkeypatch.setenv('SIM_AI_MODEL','TEST_DATA_MODEL');monkeypatch.setenv('SIM_AI_URL','http://127.0.0.1:11434')
    sent=[]
    class Client:
        def __init__(self,**kwargs): assert kwargs['follow_redirects'] is False
        def __enter__(self): return self
        def __exit__(self,*_): pass
        def post(self,url,json):
            sent.append(json);assert url=='http://127.0.0.1:11434/api/chat'
            return httpx.Response(200,json={'message':{'content':'TEST DATA MOCK: conferir evidência antes de encerrar.'}})
    monkeypatch.setattr(ai_advisor.httpx,'Client',Client)
    reply=ai_advisor.advise('TEST DATA pedido',{'tasks_registered':1})
    assert reply['ok'];assert 'proposta não verificada' in reply['text'];assert 'tools' not in sent[0]

def test_ai_transport_failure_preserves_workflow(monkeypatch):
    monkeypatch.setenv('SIM_AI_PROVIDER','ollama');monkeypatch.setenv('SIM_AI_MODEL','TEST_DATA_MODEL');monkeypatch.setenv('SIM_AI_URL','http://127.0.0.1:11434')
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): raise httpx.ConnectError('TEST DATA no local model')
        def __exit__(self,*_): pass
    monkeypatch.setattr(ai_advisor.httpx,'Client',Client)
    assert ai_advisor.advise('TEST DATA',{})['ok'] is False
