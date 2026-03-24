import spacy
import spacy.cli

class QualityTypes:
    VALUE = 'V'
    MODIFIER = 'M'

class Quality:
    __slots__ = ['txt', 'typ', 'xtra']
    def __init__(self, txt, typ, xtra=None):
        self.txt = txt
        self.typ = typ
        self.xtra = list(xtra or [])
    def __eq__(self, oth):
        if isinstance(oth, Quality):
            return oth.txt == self.txt
        return oth == self.txt
    def __str__(self):
        if self.xtra:
            xtra = "" if not self.xtra else str(self.xtra)
            return f"{self.typ}<{self.txt} {xtra}>"
        return f"{self.typ}({self.txt})"
    def __repr__(self):
        return str(self)

class Tok:
    __slots__ = ['tok', 'children', 'info', 'personalInfo']
    def __init__(self, token):
        self.tok = token
        self.children = []
        self.info = []
        for c in token.children:
            t = Tok(c)
            appl, keep = t.application(self.tok)
            if keep:
                self.children.append(t)
            self.info.extend(appl)
        self.thisApplication()

    def _apply_map(self, morph, mapping, appls):
        for k, v in morph.items():
            for nam in mapping:
                if k == nam:
                    vals = mapping[nam]
                    if v in vals:
                        appls.append(Quality(vals[v], QualityTypes.VALUE))
                        break

    def application(self, ontotok):
        if self.tok.pos_ == "PUNC" or "punc" in self.tok.dep_:
            return [], True
        appls = []
        keep = True
        morph = self.tok.morph.to_dict()

        self._apply_map(morph, {
            "Degree": {
                "Abs": "best",
                "Pos": "positive",
                "Equ": "same",
                "Cmp": "compared",
                "Sup": "most",
                # In size, force, affection, etc.
                "Dim": "small",
                "Aug": "large",
            },
            "Poss": {
                "Yes": "owned",
            },
            "Polarity": {
                "Neg": "no",
                "Pos": "yes",
            },
            "Definite": {
                "Ind": "any",
                "Spec": "specific",
                "Def": "the",
            },
        }, appls)
        if self.tok.pos_ in {"PART", "DET"} or self.tok.dep_ in {"det"}:
            keep = False

        if ontotok.pos_ in {"NOUN", "PRON", "ADJ", "ADV"} and self.tok.pos_ in {"PRON", "ADJ", "ADV"}:
            keep = False
            done = False
            if self.tok.pos_ == "PRON" and "PronType" in morph:
                vals = {
                    "Prs": "I",
                    "Rcp": "we",
                    "Art": "a",
                    "Int": "?",
                    "Tot": "everyone",
                    "Neg": "noone",
                    "Ind": "some"
                }
                typ = morph["PronType"]
                if typ in vals:
                    appls.append(Quality(vals[typ], QualityTypes.VALUE, self.personalInfo))
                    done = True
            if not done:
                appls.append(Quality(self.tok.text, QualityTypes.MODIFIER, self.personalInfo))

        if keep:
            return appls, True
        return self.info+appls, False

    def thisApplication(self):
        self.personalInfo = []
        morph = self.tok.morph.to_dict()
        self._apply_map(morph, {
            "Number": {
                "Sing": "one",
                "Dual": "two",
                "Tri": "three",
                "Plur": "four",
                "Pauc": "a few",
            },
            "Person": {
                "1": "1stPerson",
                "2": "2ndPerson",
                "3": "3rdPerson",
            },
        }, self.personalInfo)

    def __eq__(self, oth):
        return oth.tok == self.tok

    def prune_children(self, roots):
        self.children = [c if c not in roots else TokRef(c) for c in self.children]
        for c in self.children:
            c.prune_children(roots)

    def __str__(self):
        base = "" if self.tok.lemma_ == self.tok.text else f" ({self.tok.lemma_})"
        xtra1 = "" if not self.personalInfo else " - "+", ".join(str(i) for i in self.personalInfo)
        xtra2 = "" if not self.info else " - "+", ".join(str(i) for i in self.info)
        return f"{self.tok.text}{base} {self.tok.pos_}, {self.tok.dep_}"+xtra1+xtra2
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

    def debug_tree(self, token, level=0):
        base = "" if token.lemma_ == token.text else f" ({token.lemma_})"
        xtra = "" if not token.morph else " - "+str(token.morph)
        txt = f"{token.text}{base} {token.pos_}, {token.dep_}"+xtra

        outs = ["  " * level + txt]
        for child in token.children:
            outs.append(self.debug_tree(child, level + 1))
        return '\n'.join(outs)

    def dbug(self, txt):
        doc = self.doc(txt)
        roots = [t for t in doc if self.is_root(t)]
        return '\n'.join(self.debug_tree(r) for r in roots)

    def __call__(self, txt):
        doc = self.doc(txt)
        roots = [Root(t) for t in doc if self.is_root(t)]
        for r in roots:
            r.prune_children(roots)

        return '\n'.join(r.prt_tree() for r in roots)

