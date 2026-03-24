import spacy

lang = "en"
model = {
    "en": "en_core_web_sm",
}.get(lang, "xx_ent_wiki_sm")

try:
    doc = spacy.load(model)
except OSError:
    spacy.cli.download(model)
    doc = spacy.load(model)

pass
