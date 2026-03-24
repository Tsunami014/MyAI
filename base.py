import spacy
import spacy.cli

class NLP:
    lang = "en"
    MODELS = {
        "en": "en_core_web_sm",
    }

    def __new__(cls):
        if not hasattr(cls, "nlp"):
            model = cls.MODELS.get(cls.lang, "xx_ent_wiki_sm")
            try:
                cls.nlp = spacy.load(model)
            except OSError:
                print("Downloading...")
                spacy.cli.download(model)
                cls.nlp = spacy.load(model)
        return cls.nlp
