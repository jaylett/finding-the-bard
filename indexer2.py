#!/usr/bin/python
#
# Index plays in Jon Bosak's XML schema.
#
# A document is at speech level, with document data in omega format, with
# the following fields:
#   play, act, scene, speech (actual text), filename
#
# Terms are generated stemmed compatible with QueryParser (we don't bother
# doing the + suffix stuff because it's not going to come up).
#
# We also index the various titles (at the end, because that's easier) with
# a jump of 10 in position between each.
#
# We also generate terms with the following prefixes:
#
#   S	all titles
#   XS  speaker of each line

import xapian
import xml.sax, xml.sax.handler

MAX_PROB_TERM_LENGTH=64 # just ignore beyond that (probably a parser problem)

_db = None
def get_db(): # Singleton
    global _db
    if _db==None:
        _db = xapian.WritableDatabase('shakespeare2', xapian.DB_CREATE_OR_OPEN)
    return _db

def safe(s): # Get rid of characters we can't carry in document data
    return str(s).replace("\n", " ")

def p_plusminus(c):
    return c=='+' or c=='-'

class Handler(xml.sax.handler.ContentHandler):
    def __init__(self, filename):
        self.play = ''
        self.act = ''
        self.scene = ''
        self.state = '' # we'll do this using strings
        self.doc = xapian.Document()
        self.position = 1
        self.filename = filename
        self.stemmer = xapian.Stem("en")
        self.act_count = 0
        self.scene_count = 0
        self.speech_count = 0
        self.speech = ''

    def add_stuff(self):
        self.index_text(self.play, 'S', 10)
        self.index_text(self.act, 'S', 10)
        self.index_text(self.scene, 'S', 10)
        self.index_text(self.scene, '', 10)
        data = "play=%s\nact=%s\nscene=%s\nspeech=%s\nfilename=%s" % \
               (safe(self.play),
                safe(self.act),
                safe(self.scene),
                safe(self.speech),
                self.filename)
        self.doc.set_data(data)
        unique_term = "Q-%s-%i-%i-%i" % (self.filename, self.act_count, self.scene_count, self.speech_count)
        self.doc.add_term(unique_term)
        return unique_term

    def index_text(self, text, prefix='', position_inc=0, wdfinc=1):
        if text==None or text=="":
            return
        text = str(text) # probably came in as Unicode, but this is Shakespeare so we don't really care :-)
        self.position += position_inc
        rprefix = prefix
        if len(prefix)>1 and prefix[-1]!=':':
            rprefix = "%s:R" % prefix
        else:
            rprefix = "%sR" % prefix
        
        j = 0
        s_end = len(text)
        while True:
            first = j
            while first!=s_end and not text[first].isalnum():
                first+=1
            if first==s_end:
                break
            term = ""
            
            if text[first].isupper():
                j = first
                term = text[j]
                j+=1
                while j!=s_end and text[j]=='.':
                    if j+1!=s_end and text[j+1].isupper():
                        j+=1
                        term += (text[j])
                    else:
                        break
                if len(term) < 2 or j!=len(text) and text[j].isalnum():
                    term = ""
                last = j
    
            if len(term)==0:
                j=first
                while text[j].isalnum():
                    term += (text[j])
                    j+=1
                    if j==s_end:
                        break
                    if text[j]=='&':
                        next = j
                        next+=1
                        if next==len(text) or not text[next].isalnum():
                            break
                        term += ('&')
                        j = next
    
                last = j
                if j!=s_end and (text[j]=='#' or p_plusminus(text[j])):
                    length = len(term)
                    if text[j]=='#':
                        term += ('#')
                        cont = True
                        while cont:
                            j+=1
                            cont = (j!=s_end and text[j]=='#')
                    else:
                        while j!=s_end and p_plusminus(text[j]):
                            term += (text[j])
                            j+=1
                    if j!=s_end and text[j].isalnum():
                        term = term[0:length]
                    else:
                        last = j
    
            if len(term)<MAX_PROB_TERM_LENGTH:
                term = term.lower()
                if text[first].isupper():
                    if self.position!=None:
                        self.doc.add_posting(rprefix + term, self.position, wdfinc)
                    else:
                        self.doc.add_term(rprefix + term, wdfinc)
    
                term = self.stemmer.stem_word(term)
                if self.position!=None:
                    self.position+=1
                    self.doc.add_posting(prefix + term, self.position, wdfinc)
                else:
                    self.doc.add_term(prefix + term, wdfinc)

    def startElement(self, name, attrs):
        if name=='PLAY':
            self.state='play'
        elif name=='PERSONAE':
            self.state='personae'
        elif name in ('INDUCT', 'ACT', 'PROLOGUE', 'EPILOGUE'):
            self.act_count += 1
            self.state='act'
        elif name=='SCENE':
            self.scene_count += 1
            self.state='scene'
        elif name=='TITLE':
            if self.state in ('play', 'personae', 'act', 'scene'):
                self.state="%s-title" % self.state
        elif name=='STAGEDIR' or name=='SPEECH':
            if self.state!='speech':
                self.speech_count += 1
                self.state='speech'
        elif name=='SPEAKER':
            self.state='speaker'
        elif name=='LINE':
            self.state='line'

    def add_doc(self):
        unique_term = self.add_stuff()
        get_db().replace_document(unique_term, self.doc)
        self.doc = xapian.Document()

    def endElement(self, name):
        if name=='LINE':
            self.state='speech'
        elif name=='SPEAKER':
            self.state='speech'
        elif name=='STAGEDIR':
            if self.state=='speech':
                self.add_doc()
                self.speech = ''
                self.state = 'scene'
            else:
                self.state='speech'
        elif name=='SPEECH':
            self.add_doc()
            self.speech = ''
            self.state = 'scene'
        elif name=='SCENE':
            self.scene = ''
        elif name=='TITLE':
            if self.state[-6:]=='-title':
                self.state=self.state[:-6]
        elif name=='ACT':
            self.act = ''
        elif name=='PERSONAE':
            pass
        elif name=='PLAY':
            self.play = ''

    def characters(self, content):
        if self.state=='play-title':
            self.play += ' ' + content
        elif self.state=='personae-title':
            pass
        elif self.state=='act-title':
            self.act += ' ' + content
        elif self.state=='scene-title':
            self.scene += ' ' + content
        elif self.state=='stagedir' or self.state=='line':
            self.index_text(content)
            self.speech += "\n" + content
        elif self.state=='speaker':
            self.index_text(content)
            self.index_text(content, 'XS')
            self.speech += "\n" + content

def index_file(file):
    handler = Handler(file)
    xml.sax.parse(file, handler)

if __name__ == "__main__":
    import sys
    for fname in sys.argv[1:]:
        index_file(fname)
