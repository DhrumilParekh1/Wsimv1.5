"""Tests for reliable Ollama-facing APIs irrespective of cached generation."""
from wrestling_sim.starter import new_game
from wrestling_sim.dialogue import begin_meeting
from wrestling_sim.narrative import enhance_dialogue


def test_cached_ai_dialogue_keeps_immutable_contract(monkeypatch):
    state=new_game()
    meeting=begin_meeting(state,'steel','booking')
    monkeypatch.setattr('wrestling_sim.narrative._generate',
                        lambda *args,**kwargs:{'reply':'I understand the plan and appreciate your explanation.'})
    first=enhance_dialogue(state,'meeting',meeting['id'])
    again=enhance_dialogue(state,'meeting',meeting['id'])
    assert first['immutable_outcome'] is True
    assert again['immutable_outcome'] is True
    assert again['already_generated'] is True
    assert again['canonical_reply']==first['canonical_reply']
