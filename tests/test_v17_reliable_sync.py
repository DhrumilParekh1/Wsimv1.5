"""Offline tests of the real-data network boundary (never call Wikidata)."""
import io
import json
from urllib.error import HTTPError, URLError
import pytest
import wrestling_sim.real_data as real_data


def test_query_limits_expensive_optional_fields_to_pilot_selection():
    query=real_data.sparql_query(25)
    assert "SELECT DISTINCT ?person" in query
    assert query.index("LIMIT 25") < query.index("OPTIONAL")
    assert "wd:Q13474373" in query


def test_request_uses_descriptive_user_agent(monkeypatch):
    observed={}
    def fake_request(request,timeout):
        observed["agent"]=request.get_header("User-agent")
        observed["timeout"]=timeout
        data={"results":{"bindings":[{"person":{"value":"http://www.wikidata.org/entity/Q7"}}]}}
        return io.BytesIO(json.dumps(data).encode())
    monkeypatch.setattr(real_data,"urlopen",fake_request)
    assert len(real_data.fetch_wikidata(1))==1
    assert "github.com/" in observed["agent"]
    assert observed["timeout"]<=60


def test_http_403_explains_failure_instead_of_stack_trace(monkeypatch):
    def deny(*args,**kwargs):
        raise HTTPError("https://query.wikidata.org/sparql",403,"Forbidden",{},None)
    monkeypatch.setattr(real_data,"urlopen",deny)
    with pytest.raises(RuntimeError,match="HTTP 403"):
        real_data.fetch_wikidata(10)


def test_http_429_respects_retry_after(monkeypatch):
    attempts=[]
    sleeps=[]
    def rate_limit_then_succeed(*args,**kwargs):
        attempts.append(1)
        if len(attempts)==1:
            raise HTTPError("https://query.wikidata.org/sparql",429,"Rate Limited",{"Retry-After":"2"},None)
        return io.BytesIO(b'{"results":{"bindings":[]}}')
    monkeypatch.setattr(real_data,"urlopen",rate_limit_then_succeed)
    monkeypatch.setattr(real_data.time,"sleep",sleeps.append)
    assert real_data.fetch_wikidata(2)==[]
    assert len(attempts)==2
    assert sleeps==[2]


def test_long_rate_limit_does_not_hammer_server(monkeypatch):
    def rate_limit(*args,**kwargs):
        raise HTTPError("https://query.wikidata.org/sparql",429,"Rate Limited",{"Retry-After":"120"},None)
    monkeypatch.setattr(real_data,"urlopen",rate_limit)
    with pytest.raises(RuntimeError,match="wait at least 120 seconds"):
        real_data.fetch_wikidata(2)


def test_transient_503_is_retried(monkeypatch):
    calls=[]
    def temporary(*args,**kwargs):
        calls.append(1)
        if len(calls)<3:
            raise HTTPError("https://query.wikidata.org/sparql",503,"Unavailable",{},None)
        return io.BytesIO(b'{"results":{"bindings":[]}}')
    monkeypatch.setattr(real_data,"urlopen",temporary)
    monkeypatch.setattr(real_data.time,"sleep",lambda _:None)
    assert real_data.fetch_wikidata(4)==[]
    assert len(calls)==3


def test_connection_failure_gives_actionable_feedback(monkeypatch):
    monkeypatch.setattr(real_data,"urlopen",lambda *args,**kwargs: (_ for _ in ()).throw(URLError("DNS failed")))
    monkeypatch.setattr(real_data.time,"sleep",lambda _:None)
    with pytest.raises(RuntimeError,match="Check internet access"):
        real_data.fetch_wikidata(4)
