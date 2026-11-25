import numpy as np
def precision_recall_at_k(recommended, relevant, k=5):
    relevant=set(relevant)
    top=list(recommended[:k])
    hits=sum(1 for x in top if x in relevant)
    precision=hits/k if k else 0.0
    recall=hits/len(relevant) if relevant else 0.0
    return precision,recall
def ndcg_at_k(recommended,relevant,k=5):
    relevant=set(relevant)
    dcg=sum((1/np.log2(i+2)) for i,x in enumerate(recommended[:k]) if x in relevant)
    ideal=sum(1/np.log2(i+2) for i in range(min(len(relevant),k)))
    return float(dcg/ideal) if ideal else 0.0
