import pandas as pd
from .store import DualIndexStore

def ingest_csv(path: str, store: DualIndexStore, mark_hot=False):
    df = pd.read_csv(path)
    store.add_offers_from_df(df, mark_hot=mark_hot)
    store.build_indexes()
