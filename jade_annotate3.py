# -*- coding: utf-8 -*-
"""
Created on Fri May  7 13:43:40 2021

@author: Marc

"""
# répertoire des fichiers xml, possible de séparer les arrêts lebon des autres 

LOCAL=True

if LOCAL:
    PATH_PREF="../../"
else:
    PATH_PREF="./"
# for server
#PATH_PREF="./"

DATA_SRC=PATH_PREF+"data/"
GENSIM_MAIN=DATA_SRC+"jade_gensim/"
REP_ALL=DATA_SRC+"jade_all/"
MODEL_SRC=DATA_SRC+"jade_Flaubertmodel/"
DATA_SRC=DATA_SRC+"jade_examples/"


#pour les noms des fichiers gensim
BASE_ALL="jade_all"
BASE_SOM="jade_som"
BASE_SOM_IDX="jade_som"
BASE_IDX="jade_all"

import re, jade_setup_class2, stanza
from transformers import FlaubertTokenizer, FlaubertForSequenceClassification, pipeline

def get_date_clair(date):
        date_cl = ""
        Mois = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        mois = date.month
        date_cl = str(date.day)+" "+Mois[mois-1]+" "+str(date.year)
        return date_cl
  
class Text_annotated():
   
    model_src=MODEL_SRC   
    data_src=DATA_SRC
    nlp = stanza.Pipeline(lang='fr', processors='tokenize, mwt, pos, lemma, depparse', download_method=None)
    
    

    
    
    def test_special(self, ln):
        result = ""
        test1 = re.search("DECIDE", ln)
        test2 = re.search("DÉCIDE", ln)
        test3 = re.search("D E C I D E", ln)
        test4 = re.search("D É C I D E", ln)
        test5 = re.search("O R D O N N E", ln)
        test6 = re.search("ORDONNE", ln)
        if (test1 or test2 or test3 or test4 or test5 or test6):
            result = "DISPOSITIF"
        test = re.search("Considérant ce qui suit", ln)
        if test:
            result = "MOTIFS"
        test = re.search("Décision du", ln)
        if test:
            result = "DATE"
        test = re.search("Article", ln)
        if test:
            result = "ARTICLE"
        return result
    
    def get_considerant(self, jgt_test):
        consid=[]
        section=""
       
        lines=jgt_test.split("#")
        #print(jgt_test)
        for line in lines:
            
         
          if (len(line)>5):
            line=line.strip()
            #print("--->"+line.strip())
            test=self.test_special(line)
            if not(test==section) and not(test=="") and not(test=="DATE") and not(test=="ARTICLE"): 
                    section=test
                    line=test
                    consid.append(line)
            if (test=="DATE"):
                        self.date=line
            if not(section=="") and not(line=="") and not(section=="DISPOSITIF") and (test==""):
                consid.append(line)
            if (section=="DISPOSITIF") and (test=="ARTICLE"):
                consid.append(line)
        return consid

  
    
    def bert_analyze(self, consid):
            limitconsid=' '.join(consid.split(' ')[-350:])
            output=self.classifier(limitconsid)
            evaluation=output[0]['label']
            score='%.2f' % output[0]['score']
            return evaluation, score
            
    def annotate_doc(self, doc):
        

        features=[]
        
        #on fait les annotations en regex du fichier jade_codes.txt
        for cod,mat, cl in zip(self.codes.cod_text, self.codes.cod_mat, self.codes.cod_class):
            for fcod in re.finditer(cod, doc, flags=re.I):
                #print('%02d-%02d: %s' % (fcod.start(), fcod.end(), fcod.group(0)))
                key=str(fcod.start())+"-"+str(fcod.end())
                item={"location":key,"name":fcod.group(0),"type":"code","matiere":mat, "classe":cl}
                features.append(item)
                
        
        
        #on fait les annotations en regex du fichier jade_patterns.txt
        for idx, r in enumerate(self.pat.pattern_re):
            label = self.pat.pattern_text[idx]
            for fcod in re.finditer(r, doc, flags=re.I):
                #print(label)
                #print('%02d-%02d: %s' % (fcod.start(), fcod.end(), fcod.group(0)))
                key=str(fcod.start())+"-"+str(fcod.end())
                item={"location":key,"name":fcod.group(0),"type":label,"matiere":None, "classe":None}
                features.append(item)
        self.message("Features done ")
        return features
    
    def analyze_consid(self):
        consid=[]
        motif=False
        dispositif=False
        for line in self.lines:

            self.message("Analysis --> "+line)

            if (line=="MOTIFS"):
                motif=True
                dispositif=False
            if (line=="DISPOSITIF"):
                dispositif=True
                motif=False
            if motif:
                #on enlève le numéro de paragraphe du début
                line=re.sub("\d{1,2}\.\s","",line)
                cons_text=line
                cons_nlp=self.nlp(line).to_dict()
                cons_type="MOTIFS"
                cons_eval, cons_score = self.bert_analyze(line)
                consid.append((cons_text, cons_nlp,cons_type,cons_eval, cons_score))
            if dispositif:
                cons_text=line
                cons_nlp=self.nlp(line).to_dict()
                cons_type="DISPOSITIF"
                cons_eval, cons_score = self.bert_analyze(line)
                consid.append((cons_text, cons_nlp,cons_type,cons_eval, cons_score))
                


        return consid
    
    
    def message(self, text):
        if not LOCAL:
           self.celery_task.update_state(task_id=self.tid, state='PROGRESS',
                meta={'message': text})
        else:
            print(text)
           
    def load_jugement(self, jgt_txt, jgt_name, celery_task, tid):
        self.title=jgt_name
        self.txt=jgt_txt
        self.celery_task=celery_task
        self.tid=tid
        self.lines=self.get_considerant(self.txt)
        self.considerants=self.analyze_consid()
        self.features=self.annotate_doc(self.txt)

        
    def __init__(self):
        self.txt=""
        self.date=""
        self.title=""
        self.celery_task=None
        self.tid=None
        self.considerants=[]
        self.features=[]
        self.lines=[]
        self.pathmodel = self.model_src
        self.codes = jade_setup_class2.Jade_cod()
        self.pat = jade_setup_class2.Jade_pattern()
       
        self.tokenizer = FlaubertTokenizer.from_pretrained(self.pathmodel,local_files_only=True)
        self.model =FlaubertForSequenceClassification.from_pretrained(self.pathmodel, local_files_only=True, num_labels=12 )
        self.classifier =pipeline('sentiment-analysis', model=self.model, tokenizer=self.tokenizer, num_workers=1)
        
      

        



    

        

