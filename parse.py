from base import NLP

def is_root(token):
    return token.pos_ in {"VERB", "AUX"} and \
        (token.dep_ in {"ROOT", "conj"} or token.dep_[1:] == "comp")

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
    __slots__ = ['tok', 'parent', 'children', 'usefulChildren', 'info', 'personalInfo']
    def __init__(self, token, parent=None):
        self.tok = token
        self.parent = parent
        self.children = []
        self.info = []
        for c in token.children:
            t = Tok(c, self)
            appl, keep = t.application(self.tok)
            if keep:
                self.children.append(t)
            self.info.extend(appl)
        self.thisApplication()
        self.parse()
    def parse(self):
        pass

    def flatten(self, all=True, includethis=True):
        if includethis:
            yield self
        for c in (self.children if all else self.usefulChildren):
            yield from c.flatten(all)

    def _apply_map(self, morph, mapping, appls):
        for k, v in morph.items():
            for nam in mapping:
                if k == nam:
                    vals = mapping[nam]
                    if v in vals:
                        appls.append(Quality(vals[v], QualityTypes.VALUE))
                        break

    def application(self, ontotok):
        if "PUNC" in self.tok.pos_ or "punc" in self.tok.dep_:
            return [], False
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
                keep = False
                appls.append(Quality(vals[typ], QualityTypes.VALUE, self.personalInfo))
        if keep and ontotok.pos_ in {"PROPN", "NOUN", "PRON", "ADJ", "ADV"} and self.tok.pos_ in {"PRON", "ADJ", "ADV"}:
            keep = False
            appls.append(Quality(self.tok.norm_, QualityTypes.MODIFIER, self.personalInfo))

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
                "Plur": "several",
                "Ptan": "one", # scissors
                "Pauc": "a few",
            },
            "Person": {
                "1": "1stPerson",
                "2": "2ndPerson",
                "3": "3rdPerson",
            },
            "Tense": {
                "Past": "past",
                "Imp": "past",
                "Pqp": "past",
                "Pres": "present",
                "Fut": "future",
            },
            "Aspect": {
                "Imp": "happening",
                "Perf": "done",
                "Prosp": "will be done",
                "Prog": "happening",
                "Hab": "does often",
                "Iter": "does multiple times",
            },
            "Mood": {
                "Ind": "statement", # Something is happening
                "Cnd": "not statement", # Something is NOT happening
                "Pot": "can statement", # Something CAN happen
                "Jus": "wish statement", # I WISH something happened
                "Prp": "going to statement", # I am GOING TO do something
                "Qot": "quoting statement", # This was said to have happened

                "Opt": "expression", # I wish I were rich!
                "Imp": "order", # Eat your vegetables!
                "Des": "want", # I want to eat
                "Nec": "necessity", # I should eat
                "Int": "yesnoQ", # Have you eaten?
                "Irr": "irrealis", # Let me be at the table
                "Adm": "doubt", # You ate food?
            },
        }, self.personalInfo)

    def Usage(self):
        if is_root(self.tok):
            return "root"
        pos = self.tok.pos_
        rel = self.tok.dep_
        if rel == "prep" or pos == "ADP":
            return "link"
        if "advmod" in rel:
            return "modifier"
        if rel in {"compound", "discourse"}:
            return rel
        if "subj" in rel:
            return "subject"
        if "obj" in rel or "comp" in rel:
            return "object"
        if rel == "mark":
            return "clause"
        if pos in {"ADJ", "ADV"}:
            return "description"
        return ""
    def Type(self):
        if is_root(self.tok):
            return "root"
        pos = self.tok.pos_
        if pos == "VERB":
            return "event"
        if pos in {"NOUN", "PROPN", "PRON"}:
            return "object"
        return ""

    def __eq__(self, oth):
        return oth.tok == self.tok

    def prune_children(self, roots):
        self.children = [c if c not in roots else TokRef(c) for c in self.children]
        self.usefulChildren = []
        for c in self.children:
            c.prune_children(roots)
            if c.Usage() != "":
                self.usefulChildren.append(c)

    def __str__(self):
        use = self.Usage()
        typ = self.Type()
        if use and typ:
            pref = f"{use} <{typ}>: "
        elif not (use or typ):
            pref = ""
        else:
            pref = (use or f"<{typ}>") + "\033[0m: "

        base = "" if self.tok.lemma_ == self.tok.text else f" ({self.tok.lemma_})"
        mid = f" {self.tok.pos_}, {self.tok.dep_}"

        xtra1 = "" if not self.personalInfo else " - "+", ".join(str(i) for i in self.personalInfo)
        xtra2 = "" if not self.info else " - "+", ".join(str(i) for i in self.info)
        return "│\033[32m"+pref+"\033[35;1m" + self.tok.norm_+base+"\033[0;33m"+mid+"\033[0m" + xtra1+xtra2
        #return pref + self.tok.norm_+base+mid + xtra1+xtra2
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
        self.info = []
        self.thisApplication()
    def __str__(self):
        return "-> "+super().__str__()


class ParserResults:
    __slots__ = ['_id', 'roots']
    def __init__(self, roots):
        self.roots = roots

    def flatten(self):
        for r in self.roots:
            yield from r.flatten()

    def find(self, matchfn):
        for tok in self.flatten():
            if matchfn(tok):
                yield tok

class Parser:
    __slots__ = ['nlp']
    def __init__(self):
        self.nlp = NLP()
    def debug_tree(self, token, level=0):
        base = "" if token.lemma_ == token.text else f" ({token.lemma_})"
        xtra = "" if not token.morph else " - "+str(token.morph)
        txt = f"{token.text}{base} {token.pos_}, {token.dep_}"+xtra

        outs = ["  " * level + txt]
        for child in token.children:
            outs.append(self.debug_tree(child, level + 1))
        return '\n'.join(outs)

    def tree_dbug(self, txt):
        doc = self.nlp(txt)
        roots = [Tok(t) for t in doc if is_root(t)]
        return '\n'.join(r.prt_tree() for r in roots)

    def tree(self, txt):
        return '\n'.join(r.prt_tree() for r in self(txt).roots)

    def __call__(self, txt):
        doc = self.nlp(txt)
        roots = [Tok(t) for t in doc if is_root(t)]
        for r in roots:
            r.prune_children(roots)

        return ParserResults(roots)

