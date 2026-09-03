"""Degrau 2: TF-IDF + regressão logística. Rápido e inspecionável."""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline


class Classico:
    nome = "classico"

    def __init__(self):
        self.pipeline = make_pipeline(
            # ngramas de 1 a 2 pegam negação ("não gostei") sem tratamento manual
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            # neutro domina em atendimento; sem isso o modelo colapsa na classe majoritária
            LogisticRegression(max_iter=1000, class_weight="balanced"),
        )

    def treinar(self, textos, rotulos):
        self.pipeline.fit(textos, rotulos)

    def prever(self, textos):
        probs = self.pipeline.predict_proba(textos)
        classes = self.pipeline.classes_
        indices = probs.argmax(axis=1)
        return list(classes[indices]), list(np.round(probs.max(axis=1), 4))

    def termos_por_classe(self, n=15):
        """Quais termos pesam em cada classe — o motivo de manter este degrau."""
        vetorizador, modelo = self.pipeline[0], self.pipeline[-1]
        vocab = np.array(vetorizador.get_feature_names_out())
        return {
            classe: list(vocab[np.argsort(coefs)[-n:][::-1]])
            for classe, coefs in zip(modelo.classes_, np.atleast_2d(modelo.coef_))
        }
