
import deepl
from .keys import DEEPL_AUTH_KEY

class Translator(object):
    def __init__(self):
        if DEEPL_AUTH_KEY:
            self.translator = deepl.Translator(DEEPL_AUTH_KEY)
        else:
            self.translator = None

    async def translate(self, from_lang, to_lang, query_text) :
        return self.translator.translate_text(query_text, target_lang = to_lang).text.split('\n')


