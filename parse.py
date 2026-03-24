import spacy
import spacy.cli

class Parser:
    lang = "en"
    MODELS = {
        "en": "en_core_web_sm",
    }

    def __new__(cls):
        if not hasattr(cls, "doc"):
            model = cls.MODELS.get(cls.lang, "xx_ent_wiki_sm")
            try:
                cls.doc = spacy.load(model)
            except OSError:
                print("Downloading...")
                spacy.cli.download(model)
                cls.doc = spacy.load(model)
        return super().__new__(cls)

    def to_tree(self, token, level=0):
        outs = ["  " * level + f"{token.text} ({token.pos_}, {token.dep_})"]
        for child in token.children:
            outs.append(self.to_tree(child, level + 1))
        return '\n'.join(outs)

    def __call__(self, txt):
        doc = self.doc(txt)
        heads = [t for t in doc if t.head == t]

        return '\n'.join(self.to_tree(h) for h in heads)

