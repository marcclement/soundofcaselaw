# -*- coding: utf-8 -*-
"""
Sound of case-law main file
"""

from scamp import *
from scamp_extensions.pitch.scale import Scale
import random, copy, os
import os.path
import jade_annotate2
import pickle
import xml.etree.ElementTree as ET
import fluidsynth
from midi2audio import FluidSynth
import time, logging
from datetime import datetime
from pydub import AudioSegment
from io import StringIO
import sys, json

import miditoolkit

from pydub.silence import detect_nonsilent





logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate=True
fh = logging.FileHandler('jadelog.txt', mode='w')
formatter = logging.Formatter(fmt="%(levelname)s - %(asctime)s: %(message)s", datefmt='%H:%M:%S')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Local mode False is for server configuration
LOCAL=True
# Dump mode uses lines.pck and txt.pck instead of screening databases 
DUMP=False
# LISTALL for creating a list of all cases in directory DATA_ALL
LISTALL=False


if LOCAL:
    PATH_PREF="../../"
else:
    PATH_PREF="./"
    

DATA_SRC=PATH_PREF+"data/" 
SOUND_SRC= DATA_SRC+"jade_sound/"
WAV_SRC=PATH_PREF+"staticfiles/assets/jade_wav/"
DATA_ALL=DATA_SRC+"jade_all/"

if not LOCAL:
    buffer = StringIO()
    sys.stdout = buffer

class Pattern():
    def __init__(self,name, beats, lead, base1, base2, base3, silence, idpattern, nbserie):
        
         self.name=name
         self.lead=lead
         self.beats=beats
         self.base1=base1
         self.base1.restore()
         self.base2=base2
         self.base2.restore()
         self.base3=base3
         self.base3.restore()
         self.silence=silence
         
         self.idpattern=idpattern
         self.nbserie=nbserie
         
    def add2seq(self, sqarray, mcrarray, default_mcr, previous_mcr):
        seqarr=[]
        previous_mcr.clear_text()
        for sq in sqarray:
            m_outlist=True
            for m in mcrarray:
                if m.sequence==sq.name:
                    sq.add_microstructure(m) 
                    m_outlist=False
                    seqarr.append(sq)
            if m_outlist:
                if sq.name=="contra":
                    sq.add_microstructure(previous_mcr) 
                    seqarr.append(sq)
                else:
                    sq.add_microstructure(default_mcr)
                    seqarr.append(sq)
        
        return seqarr

         
    def add_sequence(self,sq_array, version):
        mcr_array=[]
        mcr_array.append(self.lead)
        # version 1 is for general
        if version==1:
            mcr_array.append(self.base1)
            if not self.nbserie==0:
               self.base2.slide([0.125,0.250,0.5],False)
               mcr_array.append(self.base2)
            #self.mcr_base3.superpose(False)
            self.base3.isolate_long(self.nbserie,[""],False)
            mcr_array.append(self.base3)
               
            sq_array=self.add2seq(sq_array,mcr_array,self.silence, self.silence)
     
            
        # version 2 is for TITRE 
        if version==2:
            mcr_array=[]
            mcr_array.append(self.lead)
            sq_array=self.add2seq(sq_array,mcr_array,self.silence, self.silence)
                
                


class Microstructure():
         
     instrument=""
     
     def __init__(self,nbnotes, pitch,length,vol, style, text, sqname, ceil):
         # we keep in _init the initial microstructure
         self.pitch_pattern_init=pitch
         self.length_pattern_init=length
         self.vol_pattern_init=vol 
         self.style_pattern_init=style
         self.text_pattern_init=text
         self.nbnotes_init=nbnotes
         self.totalduration_init=0
         for d in self.length_pattern_init:
             self.totalduration_init+=d
         self.ceil=ceil
         
         
         self.pitch_pattern=pitch
         self.length_pattern=length
         self.vol_pattern=vol
         self.nbnotes=nbnotes
         self.style_pattern=style
         self.text_pattern=text
         self.totalduration=0
         for d in self.length_pattern:
             self.totalduration+=d
         self.sequence=sqname
         self.ceil=ceil
         
         self.transformations=[]
         
     def set_sequence(self, sqname, sq_array):
         self.sequence=sqname
         for s in sq_array:
             if s.name==sqname:
                 self.volume(s.default_volume,s.default_volume)
         
         
     def restore(self):
         self.pitch_pattern=self.pitch_pattern_init
         self.length_pattern=self.length_pattern_init
         self.vol_pattern=self.vol_pattern_init
         self.style_pattern=self.style_pattern_init
         self.text_pattern=self.text_pattern_init
         self.transformations.append(("restore"))
         
     def volume(self,volinit, volend):
        
         nbnotes=len(self.vol_pattern)
         newvol=[x*(volend-volinit)/nbnotes+volinit for x in range(0,nbnotes)]
         self.vol_pattern=newvol
         self.transformations.append(("volume",volinit, volend))    
         
         
     def pitch(self,p):
         self.pitch_pattern=[ x+p if x>0 else 0 for x in self.pitch_pattern]
         self.transformations.append(("pitch",p)) 
         
     def volume_wave(self,volmin, volmax):

         nbvol=len(self.vol_pattern)
         indmiddle=int(nbvol/2)
         inc=(volmax-volmin)/indmiddle
         nv=volmin
         for i in range(nbvol):
             if i < indmiddle:
                 self.vol_pattern[i]=nv
                 nv=nv+inc
             if i == indmiddle:
                 self.vol_pattern[i]=volmax
                 nv=nv-inc
             if i > indmiddle:
                 self.vol_pattern[i]=nv
                 nv=nv-inc
                 
         
         self.transformations.append(("volume_wave,volmin, volmax"))  
         
     def reverse(self):
         self.pitch_pattern=self.pitch_pattern[::-1]
         self.length_pattern = self.length_pattern[::1]
         self.vol_pattern = self.vol_pattern[::-1]
         self.style_pattern = self.style_pattern[::-1]
         self.text_pattern = self.text_pattern[::-1]
         self.transformations.append(("reverse"))
         
     def substitute(self, pitch, duration, vol, style, text):
         self.pitch_pattern=pitch
         self.length_pattern = duration
         self.vol_pattern = vol
         self.style_pattern = style
         self.text_pattern = text
         self.totalduration=sum(self.length_pattern)
         self.transformations.append(("substitute"))
         
     def silence(self):
         self.pitch_pattern=[0 for x in self.pitch_pattern]
         self.transformations.append(("silence"))  
         
         
         
     def clear_text(self):
             self.text_pattern=["None" for x in self.text_pattern]
             self.transformations.append(("clear text"))  
     def isolate(self, rank, origin):
         if origin:
             pitch=self.pitch_pattern_init
         else:
             pitch=self.pitch_pattern
         
         self.pitch_pattern=[pitch[x] if x==rank else 0 for x in range(len(pitch))]
 
         self.transformations.append(("isolate",rank))
         
     def isolate_long(self, rank, effect, origin):
         if origin:
             pitch=self.pitch_pattern_init
         else:
             pitch=self.pitch_pattern
         
         
         self.pitch_pattern=[pitch[x] if x==rank else 0 for x in range(len(pitch))]
         if not rank==len(pitch):
             self.pitch_pattern=self.pitch_pattern[:rank+1]
             self.length_pattern=self.length_pattern[:rank+1]
     
             self.vol_pattern=self.vol_pattern[:rank+1]
             self.style_pattern=self.style_pattern[:rank+1]
             self.text_pattern=self.text_pattern[:rank+1]
             tot=sum(self.length_pattern)
             
             print("isolate lenght:"+str(self.length_pattern)+" rank:"+ str(rank))
             self.length_pattern[rank]=self.totalduration-tot+self.length_pattern[rank]
             self.style_pattern[rank]=effect        
         self.transformations.append(("isolate_long",rank))
         
     def transpose(self, nb, origin):
         if origin:
                 pitch=self.pitch_pattern_init
         else:
                 pitch=self.pitch_pattern
         self.pitch_pattern=[x+nb if type(x) is not list and x>0  else x for x in pitch]
         self.transformations.append(("transpose",nb))
         
     def superpose(self, origin):
         if origin:
                pitch=self.pitch_pattern_init
         else:
                pitch=self.pitch_pattern
         newpitch=[]
         for i in range(len(pitch)):
             chord=pitch[0:i+1]
             newpitch.append(chord)
         self.pitch_pattern=newpitch     
        
         self.transformations.append(("superpose"))
      
     def drop(self, nbkeep, origin):
         # origin flag allows if True to apply transformation to original pattern 
         # nbkeep is the number of note kept every x notes
         # for instance, if nbkeep is set to 5 one note is kept every 5 notes
         pitcharray=[]
         if origin:
            pitch=self.pitch_pattern_init
         else:
            pitch=self.pitch_pattern
         drop=nbkeep
         for p in pitch:
            if drop==nbkeep:
               pitcharray.append(p)
               drop=nbkeep-1
            else:
               pitcharray.append(0)
               drop=drop-1
               if drop<=0:
                   drop=nbkeep
         self.pitch_pattern=pitcharray
         self.transformations.append(("drop",nbkeep))
         
     def slide(self, slidearray, origin):
         # origin flag allows if True to apply transformation to original pattern 
         # slidearray is an array of possible duration
         # 
         
   
         if origin:
             length=self.length_pattern_init
         else:
             length=self.length_pattern
         
         random_index = random.randint(0, len(length) - 1)
         slide=random.choice(slidearray)
         if random_index==len(length)-1:
             indexfollow=0
         else:
             indexfollow=random_index+1
         inc=slide-length[random_index]
         
         length[random_index]=slide
         idx=indexfollow
         while (not inc==0):  
         
             if (length[idx]-inc>0.125):
                 length[idx]=length[idx]-inc
                 inc=0
             else:
                 if (length[idx]>0.125):
                     inc=inc-(length[idx]-0.125)
                     length[idx]=0.125
                     
                 if (idx+1>len(length)-1):
                     idx=0
                 else:
                     idx=idx+1
         
         self.length_pattern=length
         self.transformations.append(("slide",slidearray))
         
         
     def arpergiaze(self, intervals, origin):
             
             # transform microstructure by expanding a note which is note in quater or eight
             # with the following notes in intervals
             # if the "note" is a chord then it applies on the first note of the chord
             # the intervals are given in "intervals" and to keep the first note untouched it is
             # possible to put zero as first element of intervals
             
             if origin:
                 pitch=self.pitch_pattern_init
                 dur=self.length_pattern_init
                 vol=self.vol_pattern_init
                 style=self.style_pattern_init
                 text=self.text_pattern_init
             else:
                 pitch=self.pitch_pattern
                 dur=self.length_pattern
                 vol=self.vol_pattern
                 style=self.style_pattern
                 text=self.text_pattern
             npitch=[]
             ndur=[]
             nvol=[]
             nstyle=[]
             ntext=[]
             for p, d, v, s, t in zip(pitch, dur, vol, style, text):
                 if d>0.075:
                     l=d/len(intervals)
                     for i in range(len(intervals)):
                         if type(p) is list:
                             npitch.append(p[0]+intervals[i])
                             nvol.append(v)
                             ndur.append(l) 
                             nstyle.append(s)
                             ntext.append(t)
                         else:    
                             if (p>0) :
                                
                                 npitch.append(p+intervals[i])
                                 nvol.append(v)
                                 ndur.append(l)
                                 nstyle.append(s)
                                 ntext.append(t)
                             else:
                                 npitch.append(p)
                                 nvol.append(v)
                                 ndur.append(l)
                                 nstyle.append(s)
                                 ntext.append(t)
                         
             self.pitch_pattern=npitch
             self.vol_pattern=nvol
             self.length_pattern=ndur
             self.style_pattern=nstyle
             self.text_pattern=ntext
             self.transformations.append(("arpegiaze",intervals))
             
     def modulate(self, variation, minimum, origin):
         
         if origin:
             pitch=self.pitch_pattern_init
             dur=self.length_pattern_init
             vol=self.vol_pattern_init
             style=self.style_pattern_init
             text=self.text_pattern_init
         else:
             pitch=self.pitch_pattern
             dur=self.length_pattern
             vol=self.vol_pattern
             style=self.style_pattern
             text=self.text_pattern
             
             npitch=[]
             ndur=[]
             nvol=[]
             nstyle=[]
             ntext=[]
             
             for p, d, v, s, t in zip(pitch, dur, vol, style, text):
                 if d>minimum:
                     nb=int(d//0.125)
                     for i in range(nb-1):
                         ind=random.randint(-10,10)
                         npitch.append(p+variation*ind)
                         ndur.append(0.075)
                         nvol.append(abs(0.1*ind))
                         nstyle.append(s)
                         ntext.append(t)
               
                     ind=random.randint(1,20)
                     npitch.append(p+variation*ind)
                     ndur.append(0.075+d-nb*0.075)
                     nvol.append(0.2)
                     nstyle.append(s)
                     ntext.append(t)
                 else:
                     npitch.append(p)
                     ndur.append(d)
                     nvol.append(0.8)
                     nstyle.append(s)
                     ntext.append(t)
                      
             self.pitch_pattern=npitch
             self.vol_pattern=nvol
             self.length_pattern=ndur
             self.style_pattern=nstyle
             self.text_pattern=ntext
             self.transformations.append(("modulate",variation, minimum))
             
             
     def pattern(self, rank, pattern, version, origin):
             
             # transform microstructure by keeping the n first notes
             # and playing them to fill the bar with repetitions of pattern 
             
             if origin:
                 pitch=self.pitch_pattern_init
                 dur=self.length_pattern_init
                 vol=self.vol_pattern_init
                 style=self.style_pattern_init
                 text=self.text_pattern_init
             else:
                 pitch=self.pitch_pattern
                 dur=self.length_pattern
                 vol=self.vol_pattern
                 style=self.style_pattern
                 text=self.text_pattern
             npitch=[]
             ndur=[]
             nvol=[]
             nstyle=[]
             ntext=[]
             basepitch=pitch[rank]
             basedur=1/len(pattern)
            
             basevol=0.8
             
             if version==1:
                  nbnotes=int(self.totalduration/len(pattern))
                  
                  for n in range(nbnotes):
                      npitch += [basepitch+x for x in pattern]
                   
                  ndur=[basedur for i in range(nbnotes*len(pattern))]
                  nvol=[basevol for i in range(nbnotes*len(pattern))]
                  nstyle=[[""] for i in range(nbnotes*len(pattern))]
                  ntext=[[""] for i in range(nbnotes*len(pattern))]
      
             self.pitch_pattern=npitch
             self.vol_pattern=nvol
             self.length_pattern=ndur
             self.style_pattern=nstyle
             self.text_pattern=ntext
             self.transformations.append(("pattern",rank, pattern, version))
         
         
     def converge(self, focus, step, origin):
         # origin flag allows if True to apply transformation to original pattern 
         # focus is the pitch which is the target : each note is increased/decreased
         # by step to converge to focus
         
         pitcharray=[]
         if origin:
            pitch=self.pitch_pattern_init
         else:
            pitch=self.pitch_pattern
    
         for p in pitch:
            if p>focus:
               np=max(p-step,focus) 
               pitcharray.append(np)
            else:
               np=min(p+step,focus) 
               pitcharray.append(np)
 
         self.pitch_pattern=pitcharray
         self.transformations.append(("converge",focus))       
 
         
 
 
class Phrase():
     
     def load_part(self, part):
         
             nbp=0
             for n in self.names:
                 if n==part.instrument:
                     if not self.parts[nbp]:
                         self.parts[nbp].append(copy.deepcopy(part))
                        
                     else:
                         self.parts[nbp][0].merge(part)
                        
                         
                 nbp+=1  
      
                 
     def play(self):
         for i in range(len(self.parts)):
             for sq in self.parts[i]:
                 
                 self.s.fork(sq.play, args=[self.instp[i]]) 
         
     def __init__(self,insts, session):
         self.parts=[]
         self.names=[]
         self.instp=[]
         self.s=session
         for inst in insts:
             self.parts.append([])
         for inst in insts:
             self.names.append(inst[0])
         for inst in insts:
             self.instp.append(session.new_part(inst[0]))
         for inst in self.instp:
             inst.set_max_pitch_bend(4)
         
         
 
     
 
class Sequence():
     def export_text(self, tempo):
         text_sq=[]
         clock=0
         for d,t in zip(self.durations, self.texts):
             text_sq.append([clock,t])
             clock+=d*60/tempo
         print(clock)
         return text_sq
     
     def play(self, instrument):
         t=0
         for p, d, v, s, tx in zip(self.pitcharray, self.durations, self.volumes, self.styles, self.texts):
             # if pitch 0, then silent
             t+=d
             if s[0]=="":
                 noteprop=[StaffText(tx)]
             else:
                 noteprop=[s,StaffText(tx)]
             if type(p) is list:
                 instrument.play_chord(p, v, d)
             else:
                 if p==0:
                     wait(d)
                 else:
                     instrument.play_note(p, v, d)
                     

         #print("Sequence play :"+str(t))
     
     def add_microstructure(self,mcr):
         self.add_durations(mcr.length_pattern)
         self.add_pitches(mcr.pitch_pattern, mcr.ceil)
         self.add_volumes(mcr.vol_pattern)
         self.add_styles(mcr.style_pattern)
         self.add_texts(mcr.text_pattern)
         self.totalduration+=mcr.totalduration
         
     def add_durations(self,durations):
         self.durations.extend(durations)
         
     def add_texts(self,texts):
         self.texts.extend(texts)
         
     
     def add_pitches(self,pitch, ceil):
         
         for d in pitch:
           if type(d) is list:
               nd=[]
               ds=0
               for dd in d:
                   if ceil:
                       ds=self.scale.ceil(self.scale_note+dd)
                   else:
                       ds=self.scale_note+dd
                   nd.append(ds)
               self.pitcharray.append(nd)
           else:
               if d==0:
                   self.pitcharray.append(d)   
               else:
                   if ceil:
                       ds=self.scale.ceil(self.scale_note+d)
                   else:
                       ds=self.scale_note+d
                   self.pitcharray.append(ds)
         
         self.nbnotes+=len(pitch)
     
     def add_volumes(self,volumes):
         self.volumes.extend(volumes)
         
             
     def add_styles(self,styles):
         self.styles.extend(styles)
     
     def merge(self, sq):
         self.totalduration+=sq.totalduration
         self.nbnotes+=sq.nbnotes
         self.pitcharray.extend(sq.pitcharray)
         self.durations.extend(sq.durations)
         self.volumes.extend(sq.volumes)
         self.styles.extend(sq.styles)
         self.texts.extend(sq.texts)
         
     def reverse(self):
         self.pitcharray=self.pitcharray[::-1]
         self.durations = self.durations[::1]
         self.volumes = self.volumes[::-1]
         self.styles = self.styles[::-1]
         self.texts = self.texts[::-1]
 
         
     def __init__(self, name, instrument, scale_type, volume):
         # a sequence is based on an instrument to play the couple pitch/durations
         # 
         self.totalduration=0
         self.nbnotes=0
         self.pitcharray=[]
         self.durations=[]
         self.volumes=[]
         self.styles=[]
         self.texts=[]
        

         scale_func = eval("Scale." + scale_type)
         self.scale=scale_func(instrument[1])
         self.scale_note=instrument[1]
         self.instrument=instrument[0]
         self.name=name
         self.default_volume=volume
       
         
 




class Jade_sound():
    
    
    jade_examples_path=DATA_SRC+"jade_examples/"
    jade_all_path=DATA_SRC+"jade_all/"
    path_sound_data=SOUND_SRC
    sound_data_wav_path=WAV_SRC


    
    id2label = {12: "PRINCIPE", 1: "PROCEDURE", 2:"REJETE", 3:"ACCEPTE", 
                4:"TITRE", 5:"TEXTE", 6:"AUTRE", 7:"DEBUT MOTIFS", 
                8:"FRAIS IRREPETIBLES", 9:"APPEL", 10:"FIN REJET", 11:"FIN ACCEPTE" }
    label2id = {"PRINCIPE": 12, "PROCEDURE": 1, "REJETE":2, "ACCEPTE" : 3,
                "TITRE" : 4, "TEXTE": 5, "AUTRE":6, "DEBUT MOTIFS":7,
                "FRAIS IRREPETIBLES":8, "APPEL":9, "FIN REJET":10, "FIN ACCEPTE":11}
    
   
    def __init__(self):
        self.celery_task=None
        self.tid=None
        self.annotator=jade_annotate2.Text_annotated()
        with open(self.path_sound_data + "selected_cases.pck",'rb') as fhand:
            self.selected_cases = pickle.load(fhand)
   

    def clean_xml(self,case_raw):
        case_raw = case_raw.replace("\n", " ")
        case_raw = case_raw.replace("<br/><br/>", "#")
        case_raw = case_raw.replace("<br/>", "#")
        return case_raw
    
    def analyse_jgt(self, feat):
        features=[]
        for f in feat:
            if f['type']=='code':
                features.append(f['classe'])
        features=set(features)
        
        return features
    
    
    def get_case(self, number):
      
        if LISTALL:
            list_all=os.listdir(DATA_ALL)
            with open(SOUND_SRC+'list_all.pck', 'wb') as handle:
                pickle.dump(list_all, handle)
        
        
        if DUMP:
            with open(SOUND_SRC+"lines.pck",'rb') as fhand:
                lines = pickle.load(fhand)
            jgt_test="dump"
            titre="Jugement dump"
            search_matiere=""

            with open(SOUND_SRC+"txt.pck",'rb') as fhand:
                txt = pickle.load(fhand)
            with open(SOUND_SRC+"context.pck",'rb') as fhand:
                jgt_context = pickle.load(fhand)
             
        else:   
            txt=""
            number_failed=False
            lines=[]
            jgt_context=[]
            jgt_test="unknown"
            titre="unknown"
            search_matiere=""

            while txt=="" and not number_failed:
                text=""
                if number=="Random":    
                    jgt_test=random.choice(list(self.selected_cases.values()))
                else:
                    if number in self.selected_cases:
                        jgt_test=self.selected_cases[number]
                    else:
                       for e in self.ensembles:
                         if number==e['matiere']:
                             jgt_test=random.choice(list(self.selected_cases.values()))
                             search_matiere=number
                       if search_matiere=="":
                             self.message(number+" not found !")
                             number_failed=True
                if not number_failed:
                
                    self.message("Scan :"+jgt_test)
                    case_file = open(self.jade_all_path+jgt_test, "r", encoding="utf8")
                    case_raw = case_file.read()
                    case_file.close()
                    case_raw = self.clean_xml(case_raw)
                    tree = ET.fromstring(case_raw)
                    
                    for elt in tree.iter('DATE_DEC'):
                        date = elt.text
                        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                        if int(date[:4])>2018:
                            # take only decisions from 2018
                            for elt in tree.iter('NUMERO'):
                                numero = elt.text.strip()
                                # take only CE decisions (no CAA)
                                if numero[2:4].isnumeric():
                                    for elt in tree.iter('CONTENU'):
                                        text=elt.text
                                        break
                    if not (text==""):
                        self.annotator.load_jugement(text,jgt_test,self.celery_task, self.tid)
                        lines=self.annotator.considerants
                        
                        jgt_context=self.annotator.features
                        for ln in lines:
                            self.message(ln[0])
                            txt=text
                                
                            date_clair = jade_annotate2.get_date_clair(date_obj)
                            lebon="C"
                            for elt in tree.iter('PUBLI_RECUEIL'):
                                if not(elt.text.strip() == ""):
                                    lebon = elt.text
                            juridiction="CE"
                            for elt in tree.iter('NUMERO'):
                                numero = elt.text.strip()
                                if not(numero[2:4].isnumeric()):
                                    juridiction = numero[2:4]    
                            num="n°"+numero
                            if (juridiction == "CE"):
                                 titre = "CE "+date_clair+" "+num+" "+lebon
                            else:
                                 titre = "CAA "+juridiction+" " + \
                                                date_clair+" "+num+" "+lebon
                        found_case=False
                        for f in jgt_context:
                           if f['classe']==search_matiere:
                               found_case=True
                        if not found_case and search_matiere!="":
                            txt=""
                print(search_matiere)
                if txt=="" and number!="Random" and search_matiere=="":
                    number_failed=True
            if LOCAL and not number_failed: 
                with open(SOUND_SRC+'lines.pck', 'wb') as handle:
                    pickle.dump(lines, handle)  
                with open(SOUND_SRC+'txt.pck', 'wb') as handle:
                        pickle.dump(txt, handle) 
                with open(SOUND_SRC+'context.pck', 'wb') as handle:
                        pickle.dump(jgt_context, handle) 
            if not number_failed:        
                self.message("Titre :"+titre)
        return txt, jgt_test, lines, titre, jgt_context, search_matiere

                
       
    
    

    def normalize(self,num, minx, maxx, miny, maxy):
        norm=(maxy-miny)*(num-minx)/(maxx-minx)+miny
        return norm
    
    def get_pitch(self,w,  miny, maxy):
        dict = {'a':'1','b':'2','c':'3','d':'4','e':'5','f':'6','g':'7','h':'8','i':'9','j':'10','k':'11',
                'l':'12','m':'13','n':'14','o':'15','p':'16','q':'17','r':'18','s':'19','t':'20','u':'21',
                'v':'22','w':'23','x':'24','y':'25','z':'26'}
        w = w.lower()
        pitcharray=[]
        
        for c in w:
          
          if c in dict:
            p=self.normalize(int(dict[c]),1,25,miny, maxy)  
            
            pitcharray.append(p)
          else:
            pitcharray.append(0)
        return pitcharray
    
    
    def get_pitch_from_w(self,w):
        # associate to each letter a pitch from 1 to 12 based on normalize alphabet
        # if not a letter in word then pitch set to zero
        dict = {'a':'1','b':'2','c':'3','d':'4','e':'5','f':'6','g':'7','h':'8','i':'9','j':'10','k':'11',
                'l':'12','m':'13','n':'14','o':'15','p':'16','q':'17','r':'18','s':'19','t':'20','u':'21',
                'v':'22','w':'23','x':'24','y':'25','z':'26'}
        w = w.lower()
        pitcharray=[]
        for c in w:  
          if c in dict:
            p=self.normalize(int(dict[c]),1,25,1, 11)  
            pitcharray.append(p)
          else:
            pitcharray.append(0)
        return pitcharray
    

    
    def set_envelope(self, version):
        adsr_envelope = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3)
        adsr_envelope.show_plot("ADSR envelope")
        return adsr_envelope
    

             
    def set_phrase(self,csd, beats, vol, styl):  
        pitch=[]
        duration=[]
        durval=[0.125,0.250,0.5,1]
        volume=[]
        style=[]
        text=[]
        for phr in csd:
           # the span of pitches is based root pitch plus maximum calculated
           # with the number of words in phrase with a maximum of 10 points 
           # increase
           maxpitch=max(10,int(len(phr)/(min(len(phr),10)))) 
           for w in phr:  
              pitch+=self.get_pitch_from_w(w["text"][0])
              duration.append(durval[min(len(w)// 8,len(durval)-1)])
              key='upos'
              if key in w:
                  if w['upos']=="NOUN" and len(w['text'])>7:
                      text.append(w['text'])
                  else:
                      text.append('None')
              else:
                  text.append('None')
        # we operate a reduction to have a maximum of
        # 2*beats notes 
        reduction=int(len(pitch)/min(len(pitch),beats))
        print("Reduction : "+str(reduction))  
        pitch=pitch[::reduction]
        duration=duration[::reduction]
        text=text[::reduction]
        print(str(sum(duration))+" beats")
        
        while not sum(duration)==beats :
            id=random.randrange(0,len(duration)-1)
            duration[id]=duration[id]+(beats-sum(duration))
        print(str("Nb notes : "+str(len(pitch)))+" Duration :"+str(sum(duration)))
        for i in enumerate(duration):
            volume.append(vol)
            style.append(styl)
            
        
        return pitch, duration, volume, style, text
    
    def make_pattern(self, name, mcr, sq_array, idpattern, nbserie):
       
        mcr_silence=copy.deepcopy(mcr)
        mcr_silence.silence()
        mcr_base1=copy.deepcopy(mcr)
        mcr_base1.set_sequence("base1", sq_array)
        mcr_base2=copy.deepcopy(mcr)
        mcr_base2.set_sequence("base2", sq_array)
        mcr_base3=copy.deepcopy(mcr)
        mcr_base3.set_sequence("base3", sq_array)
        beats=mcr.totalduration
        
        pattern=Pattern(name, beats, mcr, mcr_base1, mcr_base2, mcr_base3, mcr_silence, idpattern, nbserie)
        
        return pattern
         
    
            
    def partition(self, mcr_motifs, mcr_dispositif, sq_array,  motifs, dispositif):
     
         
         nbmotif=0
         
         pat_array=[]
         

         idmcr=0
         idpattern=0
         mcr_init=mcr_motifs[idmcr]
         
         for csd in motifs:
            
             mcr_array=[]
             
             if nbmotif>=(idmcr+1)*8:
                    idmcr+=1
                    mcr_init=mcr_motifs[idmcr]
             idmotif=nbmotif-idmcr*8
             
             mcr_proc=copy.deepcopy(mcr_init)
             mcr_proc.set_sequence("contra", sq_array)
                 
             mcr_texte=copy.deepcopy(mcr_init)
             mcr_texte.set_sequence("lead", sq_array)
             mcr_texte.reverse()
                 
             mcr_fir=copy.deepcopy(mcr_init)
             mcr_fir.set_sequence("lead", sq_array)
             mcr_fir.volume(0.8,0.1)
             mcr_fir.reverse()
                 
             mcr_princ=copy.deepcopy(mcr_init)
             mcr_princ.arpergiaze([1,3], False)
             mcr_princ.set_sequence("lead", sq_array)
                
                 
             mcr_rej=copy.deepcopy(mcr_init)
             mcr_rej.set_sequence("lead", sq_array)
                 
             mcr_acc=copy.deepcopy(mcr_init)
             mcr_acc.set_sequence("lead", sq_array)
             
             if (csd[3]=="TITRE"):
                 mcr_titre=self.gen_microstructure_titre(csd)
                 pat_titre=self.make_pattern(csd[3], mcr_titre, sq_array, idpattern, idmotif)
                 pat_array.append(pat_titre)
                 pat_titre.add_sequence(sq_array,2)
                
                 idpattern+=1

             elif (csd[3]=="PRINCIPE"):      
                 pat_princ=self.make_pattern(csd[3], mcr_princ, sq_array, idpattern, idmotif)
                 pat_array.append(pat_princ)
                 pat_princ.add_sequence(sq_array,1)
                 idpattern+=1
                 
             elif(csd[3]=="PROCEDURE"):    
                 pat_proc=self.make_pattern(csd[3], mcr_proc, sq_array, idpattern, idmotif)
                 pat_array.append(pat_proc)
                 pat_proc.add_sequence(sq_array,1)
                 idpattern+=1
         
             elif(csd[3]=="REJETE"):        
                 pitch, duration, vol, styl, text =self.set_phrase(csd[1],mcr_rej.totalduration, 0.8, [""])  
                 mcr_rej.substitute(pitch, duration, vol, styl, text)                  
                 pat_rej=self.make_pattern(csd[3], mcr_rej, sq_array, idpattern, idmotif)
                 pat_array.append(pat_rej)
                 pat_rej.add_sequence(sq_array,1)
                 idpattern+=1                   
            
             elif(csd[3]=="ACCEPTE"):
                 pitch, duration, vol, styl, text =self.set_phrase(csd[1],mcr_acc.totalduration, 0.8, [""])  
                 mcr_acc.substitute(pitch, duration, vol, styl, text)                  
                 pat_acc=self.make_pattern(csd[3], mcr_acc, sq_array, idpattern, idmotif)
                 pat_array.append(pat_acc)
                 pat_acc.add_sequence(sq_array,1)
                 idpattern+=1 
  
             elif(csd[3]=="TEXTE"):                  
                 pat_texte=self.make_pattern(csd[3], mcr_texte, sq_array, idpattern, idmotif)
                 pat_array.append(pat_texte)
                 pat_texte.add_sequence(sq_array,1)
                 idpattern+=1
 
             elif(csd[3]=="FRAIS IRREPETIBLES"):                  
                 pat_fir=self.make_pattern(csd[3], mcr_fir, sq_array, idpattern, idmotif)
                 pat_array.append(pat_fir)
                 pat_fir.add_sequence(sq_array,1)
                 idpattern+=1
             else:
                 pat_texte=self.make_pattern(csd[3], mcr_texte, sq_array, idpattern, idmotif)
                 pat_array.append(pat_texte)
                 pat_texte.add_sequence(sq_array,1)
                 idpattern+=1
           
             nbmotif+=1
             
        
         nbdispositif=0
         mcr_end=copy.deepcopy(mcr_dispositif)
         for csd in dispositif:
            
            mcr_end.set_sequence("lead", sq_array)
            mcr_end.isolate_long(0,[""],False)
            pat_end=self.make_pattern(csd[3], mcr_end, sq_array, idpattern, nbdispositif)
            pat_array.append(pat_end)
            pat_end.add_sequence(sq_array,1)
            idpattern+=1
            nbdispositif+=1
    
             
         return sq_array   
     
        
    def gen_microstructure_titre(self,csd):  
         beats=4
         ceil=True
         pitch=[]
         duration=[]
         durval=[0.125,0.250,0.5,1]
         volume=[]
         style=[]
         text=[]
         vol=0.8
         styl=[""]
         for phr in csd[1]:
            # the span of pitches is based root pitch plus maximum calculated
            # with the number of words in phrase with a maximum of 10 points 
            # increase
            maxpitch=max(10,int(len(phr)/(min(len(phr),10)))) 
            for w in phr:  
               pitch+=self.get_pitch_from_w(w["text"][0])
               duration.append(durval[min(len(w)// 8,len(durval)-1)])
               text.append(w['text'])
               
         # we operate a reduction to have a maximum of
         # 2*beats notes 
         reduction=int(len(pitch)/min(len(pitch),beats))
         print("Reduction titre : "+str(reduction))  
         pitch=pitch[::reduction]
         duration=duration[::reduction]
         text=text[::reduction]
         print(str(sum(duration))+" beats")
         
         while not sum(duration)==beats :
             id=random.randrange(0,len(duration)-1)
             duration[id]=duration[id]+(beats-sum(duration))
         print(str("Nb notes titre : "+str(len(pitch)))+" Duration titre :"+str(sum(duration)))
         for i in enumerate(duration):
             volume.append(vol)
             style.append(styl)
             
         mcr=Microstructure(len(pitch), pitch, duration, volume, style, text, "titre", ceil)
        
         return mcr


    
    def gen_microstructure(self,notes, beats, volumes , styles, texts, sqname, ceil):
        
        nbnotes=0
        nbbeats=0
        pitch=[]
        dur=[]
        vol=[]
        st=[]
        txt=[]
        previousnote=-1
        nbrepeat=1
        notes_repeat=[]
        for n in notes:
            if n==previousnote:
                nbrepeat+=1
                previousnote=n
            else:
                if previousnote!=-1:
                    notes_repeat.append((previousnote,nbrepeat))
                previousnote=n
                nbrepeat=1
                
        if previousnote==-1:
            notes_repeat.append((notes[len(notes)-1],nbrepeat))
        else:
            notes_repeat.append((previousnote,nbrepeat))

        if beats <= 8:
            d=beats/len(notes)
            for n, t in zip(notes, texts):
                nbbeats+=d
                dur.append(d)
                pitch.append(n)
                vol.append(volumes)
                st.append(styles)
                txt.append("None")
                nbnotes+=1 
            if nbbeats<beats:
                d=beats-nbbeats
                nbbeats+=d
                dur.append(d)
                pitch.append(0)
                vol.append(volumes)
                st.append(styles)
                txt.append("None")
                nbnotes+=1 
        else:
            d=beats/len(notes_repeat)
            for n, t in zip(notes_repeat, texts):
              for i in range(n[1]):
                nbbeats+=d
                dur.append(d/n[1])
                pitch.append(n[0])
                vol.append(volumes)
                st.append(styles)
                txt.append("None")
                nbnotes+=1 
            if nbbeats<beats:
                d=beats-nbbeats
                nbbeats+=d
                dur.append(d)
                pitch.append(0)
                vol.append(volumes)
                st.append(styles)
                txt.append("None")
                nbnotes+=1 
    
        mcr=Microstructure(nbnotes, pitch, dur, vol, st, txt, sqname, ceil)
        
        return mcr
    
    
    def remove_sil(self, path_in, path_out, format="wav"):
        sound = AudioSegment.from_file(path_in, format=format)
        non_sil_times = detect_nonsilent(sound, min_silence_len=50, silence_thresh=sound.dBFS * 1.5)
        if len(non_sil_times) > 0:
            non_sil_times_concat = [non_sil_times[0]]
            if len(non_sil_times) > 1:
                for t in non_sil_times[1:]:
                    if t[0] - non_sil_times_concat[-1][-1] < 200:
                        non_sil_times_concat[-1][-1] = t[1]
                    else:
                        non_sil_times_concat.append(t)
            non_sil_times = [t for t in non_sil_times_concat if t[1] - t[0] > 350]
            sound[non_sil_times[0][0]: non_sil_times[-1][1]].export(path_out, format='wav')
    
    def message(self, text):
        if not LOCAL:
            self.celery_task.update_state(task_id=self.tid, state='PROGRESS',
                meta={'message': text})
        else:
            print(text)
               
    def make_lyrics(self,sq_array,texts, tempo, beats_motifs, beats_dispositif, titre):
        lyrics=[]
        lyrics_spots=[]
        
        clock=0.1
        ind=0
        for t in texts:                
            lyrics.append([clock,t[0]])
            ind+=1
            if t[2]=="MOTIFS":
                clock=ind*beats_motifs*60/tempo
            else:
                clock=ind*beats_dispositif*60/tempo
        # add title in the end of lyrics
        lyrics.append([clock-1,titre])
            
        for sq in sq_array:
            l=sq.export_text(tempo)
            for c in l:
                if not c[1]=="None":
                    lyrics.append(c)
                    lyrics_spots.append(c)
        lyrics=sorted(lyrics)
        lyrics_spots=sorted(lyrics_spots)
        return lyrics, lyrics_spots
    
    def generate_main(self, number):

        adsr=self.set_envelope(1)
        sf2_file=self.path_sound_data+"Arachno SoundFont - Version 1.0.sf2"
        #sf2_file=self.path_sound_data+"Sonatina_Symphonic_Orchestra.sf2"
        #sf2_file=self.path_sound_data+"wt_183k_G.sf2"
        #sf2_file=self.path_sound_data+"MS Basic.sf3"
        with open(self.path_sound_data+"jade_ensembles.json") as ens_file:
                file_contents = ens_file.read()
      
        self.ensembles = json.loads(file_contents)['ensembles']
        
        
        s = Session(default_soundfont=sf2_file)
        
        s.print_default_soundfont_presets()
        if not LOCAL:
            print_output = buffer.getvalue()
        
        s.fast_forward_in_beats(float("inf")) 
       
        text, name, lines, titre, context, matiere =self.get_case(number) 
        if (text!=""): 
            self.message(titre)
            name=name.split(".")[0]
        
            #playback_settings.recording_file_path = self.sound_data_wav_path+name+".wav"

            ensemble=[]
            volume=[]
            # in not matiere mode we take first matiere which is not CJA if any
            Done=False
            if matiere=="":
                for f in context:
                 if f['classe']!='CJA':
                      for e in self.ensembles:
                        if f['classe']==e['matiere'] and not Done:
                            self.message(e['matiere'])
                            s.tempo=e['tempo']
                            scale_type=e['scale']
                            for i, k,v in zip(e['instruments'],e['keys'], e['levels']):
                                ensemble.append((i,k))
                                volume.append(float(v))
                            Done=True


            # default ensemble is CJA or matiere 
            if matiere=="":
                defaultmatiere="CJA"
            else:
                defaultmatiere=matiere
            if not Done:
                for e in self.ensembles:
                    if e['matiere']==defaultmatiere:
                        self.message(e['matiere'])
                        s.tempo=e['tempo']
                        scale_type=e['scale']
                        for i, k,v in zip(e['instruments'],e['keys'], e['levels']):
                            ensemble.append((i,k))
                            volume.append(float(v))

            ph=Phrase(ensemble,s)
            
            motifs=[]
            dispositif=[]
            mot=True
            
            for csd in lines:
                if not (csd[0]=="MOTIFS") and not (csd[0]=="DISPOSITIF"):
                  if mot==True:
                    motifs.append(csd)
                  else:
                    dispositif.append(csd)
                if csd[0]=="DISPOSITIF":
                    mot=False
            styles=[""]  
            
            notes_motifs=[]
            notes_dispositif=[]

            
            texts=[]
            
            for  csd in motifs:
                note=int(self.label2id[csd[3]])
                notes_motifs.append(note)
                texts.append(csd)
                
            for csd in dispositif:
                note=int(self.label2id[csd[3]])
                notes_dispositif.append(note)
                texts.append(csd)
            
         
            beats_motifs=(max(len(notes_motifs) // 4, 1))*4
            beats_motifs=min(beats_motifs,8)
            
      
            
            print("Beats motifs: "+str(beats_motifs))
            
            beats_dispositif=(max(len(notes_dispositif) // 4, 1))*4
      
            
            print("Beats dispositif: "+str(beats_dispositif))
            # if nb of considerant > 8 then with split in chunks of 8 notes
            motif_chunks=[]
            if len(notes_motifs)>8:
                for i in range(0, len(notes_motifs), 8):
                    motif_chunks.append(notes_motifs[i:i + 8])
            else:
                motif_chunks.append(notes_motifs)
           
            for  csd in dispositif:
                print(csd[3])
           
           
            default_volume=0.8
            sq1=Sequence("base1",ensemble[4], scale_type, volume[4])
            sq2=Sequence("base2",ensemble[5], scale_type, volume[5])
            sq3=Sequence("base3",ensemble[3], scale_type, volume[3])
            sq4=Sequence("titre",ensemble[2], scale_type, volume[2])
            sq5=Sequence("lead",ensemble[0], scale_type,volume[0])
            sq6=Sequence("contra",ensemble[1], scale_type,volume[1])
           
            sq_array=[sq1,sq2,sq3, sq4, sq5, sq6]
            mcr_motifs=[]
            
            for notes in motif_chunks:
                mcr_motifs.append(self.gen_microstructure(notes,  beats_motifs,
                                         default_volume,styles,texts,"", True))
            mcr_dispositif =self.gen_microstructure(notes_dispositif, beats_dispositif,
                                         default_volume,styles,texts,"", True)
            sq_array=self.partition(mcr_motifs, mcr_dispositif, sq_array, motifs, dispositif)
           
            
            for sq in sq_array: 
                ph.load_part(sq)
            if LOCAL:
                with open(SOUND_SRC+'sequences.pck', 'wb') as handle:
                            pickle.dump(sq_array, handle) 

            
                
            s.start_transcribing()  
            
            if not LOCAL: 
                self.message(print_output)
    
    
            ph.play()
            s.wait_for_children_to_finish()
            
                   
            performance = s.stop_transcribing()
            
            performance.quantize()
            perf_result="Number of measures :"+str(performance.num_measures())

    
            self.message(perf_result)
            
            if performance.num_measures()>0:
                lyrics, lyrics_spots =self.make_lyrics(sq_array, texts, s.tempo, beats_motifs, beats_dispositif, titre)
                with open(self.sound_data_wav_path+name+".json",'w') as outfile:
                    outfile.write(json.dumps(lyrics, indent=4))
                with open(self.sound_data_wav_path+name+".spot",'w') as outfile:
                    outfile.write(json.dumps(lyrics_spots, indent=4))
    
                    
                performance.export_to_midi_file(self.path_sound_data+'midi_scamp.mid') 
                performance.to_score(title=titre,composer="www.LawDataWorkshop.eu").export_pdf(self.sound_data_wav_path+name+".pdf")
                performance.to_score(title=titre,composer="www.LawDataWorkshop.eu").export_lilypond(self.path_sound_data+'lily_file.ly')   
            
                i=0
                presets=[]
                for tr in performance.parts:
                    notempty=False
                    for imp in tr.instrument.playback_implementations:
                        for sq in ph.parts[i]:
                            for p in sq.pitcharray:
                                if type(p) is not list:
                                    if p>0:
                                        notempty=True
                                        break
                                else:
                                    notempty=True
                                    break
                        if notempty:
                            presets.append(imp.bank_and_preset)
                    i+=1
                    print(presets)
                midi_obj = miditoolkit.MidiFile(self.path_sound_data+'midi_scamp.mid')
            
                for track, ps in zip(midi_obj.instruments, presets):
       
                    track.program=ps[1]
                    if ps[0]>0:
                        track.program=ps[1]
                        track.is_drum=True
                    else:
                        track.program=ps[1]
                   
                midi_obj.dump(self.path_sound_data+'midi_inst.mid')
                os.remove(self.path_sound_data+'midi_scamp.mid')
            else:
                self.celery_task.update_state(task_ids=self.tid, state='FAILED',
                        meta={'message': 'Empty performance'})
       
            
                   
            fs = FluidSynth(sound_font=sf2_file)
            if (os.path.exists(self.path_sound_data+'midi_inst.mid')):
                fs.midi_to_audio(self.path_sound_data+'midi_inst.mid', self.sound_data_wav_path+name+".wav")
                # need to cut silence by the end on wav file
                self.remove_sil(self.sound_data_wav_path+name+".wav",self.sound_data_wav_path+name+".wav", format="wav")
                if not LOCAL:
                     self.celery_task.update_state(task_id=self.tid, state='SUCCESS',
                                            meta={'titre': titre, 'name': name})
            else:
                 if not LOCAL:
                    self.celery_task.update_state(task_id=self.tid, state='FAILED',
                                             meta={'message': 'File not available'})
                 else: 
                     print("Failed : no midi file")
            s.kill()    
        else:
            self.message("Cannot find case number :"+number)
            if not LOCAL:
              self.celery_task.update_state(task_id=self.tid, state='SUCCESS',
                                                 meta={'titre': titre, 'name': name})
              
        return name, lyrics, lyrics_spots, titre


    def generate(self, celery_task, tid, number):
             self.celery_task=celery_task
             self.tid=tid
             
             name, lyrics, lyrics_spots, titre=self.generate_main(number)
             self.celery_task.update_state(task_id=tid, state='FAILED',
                                        meta={'message': 'Not all done !'})
             return name
      
if __name__ == "__main__":
    if LOCAL:
        soundjade=Jade_sound()
        # soulevement 476384
        name, lyrics, lyrics_spots, titre=soundjade.generate_main("465835")

    
    

   


 

                                      