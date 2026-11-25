import pandas as pd
from app.recommender import RecommendationEngine
from app.evaluation import precision_recall_at_k, ndcg_at_k

def sample_engine():
    products=pd.DataFrame([
      ["P1","Python","Books","learn python","coding"],
      ["P2","PyTorch","Books","deep learning","AI coding"],
      ["P3","Shoes","Sports","running shoes","fitness"],
      ["P4","Keyboard","Electronics","typing keyboard","computer"],
    ],columns=["product_id","title","category","description","tags"])
    interactions=pd.DataFrame([
      ["U1","P1","purchase",5],["U1","P2","like",5],
      ["U2","P1","purchase",5],["U2","P2","purchase",4],
      ["U2","P3","view",3],["U3","P3","purchase",5],
    ],columns=["user_id","product_id","event_type","rating"])
    return RecommendationEngine(products,interactions)

def test_recommendations_exclude_seen_items():
    engine=sample_engine()
    recs=engine.recommend("U1",limit=3)
    assert all(x["product_id"] not in {"P1","P2"} for x in recs)

def test_unknown_user_gets_popular_fallback():
    engine=sample_engine()
    recs=engine.recommend("NEW_USER",limit=2,method="popular")
    assert len(recs)==2

def test_metrics():
    p,r=precision_recall_at_k(["a","b","c"],{"a","c"},k=3)
    assert round(p,3)==0.667 and r==1
    assert 0 < ndcg_at_k(["a","x","c"],{"a","c"},k=3) <= 1
