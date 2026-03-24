import spacy
import spacy.cli

class Tok:
    __slots__ = ['tok', 'children', 'info']
    def __init__(self, token):
        self.tok = token
        self.children = []
        self.info = self.thisApplication()
        for c in token.children:
            t = Tok(c)
            appl, keep = t.application()
            if keep:
                self.children.append(t)
            self.info.extend(appl)

    def application(self):
        if self.tok.pos_ == "PUNC" or "punc" in self.tok.dep_:
            return [], True
        appls = []
        keep = True
        if self.tok.pos_ == "PART":
            keep = False
            morph = self.tok.morph.to_dict()
            for k, v in morph.items():
                if k == "Polarity":
                    pols = {"Neg": 'no', "Pos": 'yes'}
                    if v in pols:
                        appls.append(pols[v])
        return appls, keep

    def thisApplication(self):
        appls = []
        morph = self.tok.morph.to_dict()
        for k, v in morph.items():
            if k == "Number":
                if v == 'Sing':
                    appls.append("One")
                elif v == 'Dual':
                    appls.append("Two")
                elif v == 'Tri':
                    appls.append("Three")
                elif v == 'Plur':
                    appls.append("Several")
                elif v == 'Pauc':
                    appls.append("A few")
        return appls

    def __eq__(self, oth):
        return oth.tok == self.tok

    def prune_children(self, roots):
        self.children = [c if c not in roots else TokRef(c) for c in self.children]
        for c in self.children:
            c.prune_children(roots)

    def __str__(self):
        base = "" if self.tok.lemma_ == self.tok.text else f" ({self.tok.lemma_})"
        xtra = "" if not self.tok.morph else " - "+", ".join(self.info)
        return f"{self.tok.text}{base} {self.tok.pos_}, {self.tok.dep_}"+xtra
    def __repr__(self):
        return self.tok.text

    def prt_tree(self):
        if len(self.children) == 0:
            return str(self)
        out = str(self) + '\n' + '\n'.join(i.prt_tree() for i in self.children)
        return out.replace('\n', '\n  ')

    def __iter__(self):
        return iter(self.children)

class TokRef(Tok):
    def __init__(self, token):
        self.tok = token.tok
        self.children = []
    def __str__(self):
        return "-> "+super().__str__()

class Root(Tok):
    __slots__ = ['head']
    def __init__(self, token):
        super().__init__(token)
        self.head = token.head
        while self.head.head != self.head:
            self.head = self.head.head


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

    def is_root(self, token):
        return token.pos_ in {"VERB", "AUX"} and \
            token.dep_ in {"ROOT", "conj", "advcl"}

    def __call__(self, txt):
        doc = self.doc(txt)
        roots = [Root(t) for t in doc if self.is_root(t)]
        for r in roots:
            r.prune_children(roots)

        return '\n'.join(r.prt_tree() for r in roots)

