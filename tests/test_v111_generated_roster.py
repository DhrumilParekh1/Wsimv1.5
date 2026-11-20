"""V1.11: permanent starter-rookie generation and front-end cache regressions."""
from dataclasses import asdict
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from wrestling_sim.real_universe import build_universe
from wrestling_sim.company_creation import TIERS,create_company
from wrestling_sim.generated_roster import COUNTS,generate_rookies
from wrestling_sim.ratings import rating_breakdown
from wrestling_sim.database import save_database,load_database

@pytest.mark.parametrize("tier,draft_per_division,men,women,total",[
    ("indie",1,5,3,10),("startup",2,6,4,14),("juggernaut",3,7,4,17)
])
def test_all_tiers_have_exact_generated_counts_and_realistic_ratings(tmp_path,tier,draft_per_division,men,women,total):
    state=build_universe(tmp_path/"people.db",add_independents=False)
    available=[w for w in state.wrestlers.values() if w.company_id=="player"]
    draft_m=[w.id for w in available if w.division=="men"][:draft_per_division]
    draft_w=[w.id for w in available if w.division=="women"][:draft_per_division]
    founded=create_company(state,"Vesper Game Wrestling",tier,draft_m,draft_w)
    mine=[w for w in founded.wrestlers.values() if w.company_id=="player"]
    generated=[w for w in mine if w.id.startswith("gen_")]
    assert len(mine)==total
    assert (len([w for w in generated if w.division=="men"]),
            len([w for w in generated if w.division=="women"]))==(men,women)
    assert len({w.name.casefold() for w in founded.wrestlers.values()})==len(founded.wrestlers)
    assert len({w.id for w in generated})==men+women
    assert all(39<=rating_breakdown(w)["current_ability"]<=70 for w in generated)
    assert len({round(rating_breakdown(w)["current_ability"],1) for w in generated})>=4
    assert all(w.company_id=="player" and w.contract_weeks>0 and w.salary_weekly>0 for w in generated)
    assert len(founded.storylines)==0  # no fabricated opening rivalries
    assert founded.player_company.roster_limit>=total
    assert any(entry["type"]=="company_foundation" and
               len(entry["generated_wrestler_ids"])==men+women for entry in founded.activity_log)
    assert len([w for w in state.wrestlers if w.startswith("gen_")])==0
    saved=tmp_path/"created.db"
    save_database(founded,saved)
    reloaded=load_database(saved)
    assert {w.id for w in generated}=={w.id for w in reloaded.wrestlers.values() if w.id.startswith("gen_")}
    assert {w.id:(w.name,w.attributes) for w in generated}=={
        w.id:(w.name,w.attributes) for w in reloaded.wrestlers.values() if w.id.startswith("gen_")}

def test_rookies_deterministically_derived_from_seed_tier_and_name(tmp_path):
    state=build_universe(tmp_path/"people.db",add_independents=False)
    a=generate_rookies(state,"indie","Northern Star")
    b=generate_rookies(state,"indie","Northern Star")
    assert [(w.id,w.name,w.attributes) for w in a]==[(w.id,w.name,w.attributes) for w in b]
    assert [(w.id,w.name) for w in a]!=[(w.id,w.name) for w in generate_rookies(state,"startup","Northern Star")]

def test_fresh_html_uses_versioned_assets_and_no_cache():
    from wrestling_sim.api import app
    response=TestClient(app).get("/")
    assert response.status_code==200
    assert "no-store" in response.headers["cache-control"]
    assert 'app.js?v=1.11.0' in response.text
    assert 'styles.css?v=1.11.0' in response.text
    assert TestClient(app).get("/ui/build-info").json()["frontend_version"]=="1.11.0"
