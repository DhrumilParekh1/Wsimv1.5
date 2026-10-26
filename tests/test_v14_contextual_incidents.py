from wrestling_sim.starter import new_game
from wrestling_sim.press_and_incidents import incident_options, answer_incident, ensure_incidents
from wrestling_sim.storage import restore_game
from dataclasses import asdict

def test_mentor_has_only_relevant_options():
    names=[o['label'] for o in incident_options('mentoring')]
    assert 'Approve the mentorship' in names
    assert 'Establish clear professional standards' not in names

def test_mediation_has_disciplinary_choices():
    ids={o['id'] for o in incident_options('argument')}
    assert 'listen' in ids and 'mediate' in ids and 'approve' not in ids

def test_generated_options_are_contextual():
    s=new_game()
    for incident in ensure_incidents(s):
        assert incident['options']==incident_options(incident['kind'])

def test_mentorship_decision_and_save_roundtrip():
    s=new_game()
    ids=[x.id for x in s.wrestlers.values() if x.company_id==s.player_company_id][:2]
    s.incidents=[{'id':'incident-custom', 'year':s.year,'week':s.week,'kind':'mentoring',
                  'title':'Mentoring request','description':'Mentoring request',
                  'wrestler_ids':ids,'status':'open','choice':None,'severity':'minor',
                  'options':incident_options('mentoring')}]
    # Choose RNG seed that produces approval success without depending on a real model.
    for seed in range(100):
        s.seed=seed
        from wrestling_sim.press_and_incidents import _rng
        # verify predictable response outcome using current decision rules
        import copy
        trial=copy.deepcopy(s)
        outcome=answer_incident(trial,'incident-custom','approve')
        if outcome['success']:
            assert trial.mentorships
            restored=restore_game(asdict(trial))
            assert restored.mentorships[0]['mentor_id']==ids[0]
            return
    assert False,'Could not get an approved mentorship in deterministic seeds'
