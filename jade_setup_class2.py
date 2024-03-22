# -*- coding: utf-8 -*-
"""
Created on Fri Apr 23 13:42:47 2021

@author: Marc
"""
# Local mode False is for server configuration
LOCAL=True


if LOCAL:
    PATH_PREF="../../"
else:
    PATH_PREF="./"
    

DATA_SRC=PATH_PREF+"data/" 
SOUND_SRC= DATA_SRC+"jade_sound/"



class Jade_cod:
    cod_text = []
    cod_text_tk=[]
    cod_mat=[]
    cod_class=[]
    
    def __init__(self):
        list_cod = open(SOUND_SRC+'jade_codes.txt','r', encoding="utf-8")
        cod_lines = list_cod.readlines()
        cd_temp=[]
        cl_temp=[]
        i=0
        while i < len(cod_lines):
            self.cod_text.append(cod_lines[i].strip())
            self.cod_mat.append(cod_lines[i+1].strip())
            i=i+2
            self.cod_text_tk.append('COD')
        self.cod_par=list(map(lambda x, y:(x,y), self.cod_text, self.cod_text_tk))
        with open(SOUND_SRC+'jade_sound_classe.txt', 'r') as handle:
            class_lines = handle.readlines()
            i=0
            while i < len(class_lines):
                cl_temp.append(class_lines[i].strip())
                cd_temp.append(class_lines[i+1].strip())
                i+=2
        for i, cd in enumerate(self.cod_mat):
            if cd==cd_temp[i]:
                    self.cod_class.append(cl_temp[i])
            else:
                    self.cod_class.append("unknown")
                        
        
    def show(self):
        print(self.cod_text)
        
        


class Jade_pattern:
    pattern_re = []
    pattern_text = []
    def __init__(self):
        list_pat = open(SOUND_SRC+'jade_patterns.txt','r', encoding="utf-8")
        pat_lines = list_pat.readlines()
        list_pat.close()
        for t in pat_lines:
            self.pattern_re.append(t.split(' ')[0].strip())
            self.pattern_text.append(t.split(' ')[1].strip())
        self.pat_par=list(map(lambda x, y:(x,y), self.pattern_re, self.pattern_text))
    def show(self):
        print(self.pattern_text)
        print(self.pattern_re)


class Jade_tag:
    tag_text = []
    tag_tag = []
    def __init__(self):
        list_tag = open(SOUND_SRC+'jade_tags.txt','r', encoding="utf-8")
        tag_lines = list_tag.readlines()
        list_tag.close()
        for t in tag_lines:
            self.tag_text.append(t.split(' ')[0].strip())
            self.tag_tag.append(t.split(' ')[1].strip())
    def show(self):
        print(self.tag_text)
        print(self.tag_tag)
        
        
class Jade_mat:
    mat_id = []
    mat_text = []
    def __init__(self):
        list_mat = open(SOUND_SRC+'jade_matieres.txt','r', encoding="utf-8")
        mat_lines = list_mat.readlines()
        list_mat.close()
        for line in mat_lines:
            line_bk = line.split(" ",1)
            self.mat_id.append(line_bk[0].strip())
            txt=line_bk[1].strip()
            self.mat_text.append(txt)
    def get_text(self,num):
        mat = 'unknown'
        i=0
        for idx in self.mat_id:
            if idx == num:
                mat = self.mat_text[i]
            i+=1
        return mat
    def show(self):
        print(*self.mat_id)
        print(*self.mat_text)

