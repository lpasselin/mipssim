# -*- coding: utf-8 -*-

# Copyright (c) 2011, Yannick Hold-Geoffroy on behalf of Université Laval
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
#    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer 
#       in the documentation and/or other materials provided with the distribution.
#    Neither the name of the Université Laval nor the names of its contributors may be used to endorse or promote products derived 
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from xml.dom.minidom import parse#, parseString
import os
#import string
#import time
from src.simulateur import SimulationException
from collections import OrderedDict


# #########################
# Décorateur de validation
# #########################
def garantir_registre_valide(func):
    """
    Décorateur s'assurant que les registres accédés sont valides.
    """
    def function_handling(*args, **kwargs):
        if args[1][-1] == 'T':
            temp = args[1][:-1]
        else:
            temp = args[1]
        if temp[0] not in ['R', 'F'] or int(temp[1:]) not in range(0, 32):
            raise SimulationException('Accès à un registre non valide: %s.' % args[1])
        else:
            return func(*args, **kwargs)
    return function_handling


class unite_fct(OrderedDict):
    """
    Variables Tomasulo des unités fonctionnelles.
    
    Contient les champs suivants : 
    
     temps, addr, op, vj, vk, qj, qk
    
    """

    def __init__(self):
        """
        Les paramètres doivent être initialisés au Runtime 
        (dans le constructeur) sinon c'est la même copie qui est changée. 
        """
        super(unite_fct, self).__init__()
        self.update({"busy": False, "temps": None, "addr": None, "op": None,
              "vj": None, "vk": None, "qj": None, "qk": None})

    def reset(self):
        self.__init__()


class unite_tomasulo_speculation(unite_fct):
    """
    Ajoute la variable destination à l'unité fonctionnelle de base 
    """
    def __init__(self):
        super(unite_tomasulo_speculation, self).__init__()
        self['dest'] = None
        

class unite_lancement_multiple(unite_fct):
    pass


# #############################################
# Classes spécifiques des unités fonctionnelles
# #############################################
class unite_desc(object):
    """
    Classe template de base des unités fonctionnelles.
    
    Contient:
    
- temps_execution
- temps_execution_division
- quantite
- Liste contenant les unités fonctionnelles (peut être appelée x[num])

    """
    def __init__(self, in_architecture):
        """
        Initialisation des variables membres (peupler __dict__).
        """
        self.architecture = in_architecture
        self.temps_execution = 0
        self.temps_execution_division = 0
        self.quantite = 0
        self.conteneur = []
        
    def __len__(self):
        return self.quantite
    
    def __setitem__(self, key, value):
        if type(key) == int:
            if key > self.quantite - 1:
                raise SimulationException('Clef plus grande que la quantité: %d' % key)
            self.conteneur[key] = value
        else:
            raise SimulationException('Clef invalide: %s' % key)
            
    def __getitem__(self, key):
        if type(key) == int:
            if key > self.quantite - 1:
                raise SimulationException('Clef plus grande que la quantité: %d' % key)
            return self.conteneur[key]
        else:
            raise SimulationException('Clef invalide: %s' % key)
             
    def __setattr__(self, key, value):
        if key == 'quantite':
            value = int(value)
            self.__dict__['quantite'] = value
            self.__dict__['conteneur'] = [self.architecture() for a in range(value)]
        else:
            try:
                self.__dict__[key] = value
            except:
                raise SimulationException('Attribut invalide: %s' % key)
    
    def __iter__(self):
        for a in self.conteneur:
            yield a
            
    def __repr__(self):
        return 'Qte %d ExecTime: %d Exectime2: %d Contenu: %s' % (self.quantite,
         self.temps_execution,
         self.temps_execution_division,
         self.conteneur) 

        
class unite_math(unite_desc):
    """
    Classe racine des unités fonctionnelles mathématiques.
    """
    pass


class unite_store(unite_desc):
    """
    Classe racine des unités fonctionnelles de store.
    """
    pass


class unite_load(unite_desc):
    """
    Classe racine des unités fonctionnelles de load.
    """
    pass


class unite_branch(unite_desc):
    """
    Classe racine des unités fonctionnelles de branch.
    """
    def __init__(self, *args):
        super(unite_branch, self).__init__(*args)
        self.__dict__['spec_forward'] = False
        self.__dict__['spec_backward'] = False


# #######################
# Classe de configuration
# #######################
class mips_configuration(object):
    """
    Classe définissant la configuration et l'état du MIPS simulé.
    Contient les états des unités fonctionnelles, des registres et de la mémoire.

    Exemple d'utilisation de la classe:
        print(config.registre['R0'])
        print(config.registre['F1'])
        config.registre['R15'] = 5
        try:
            print(config.registre['R2154'])
        except:
            print('Could not access R2154, ce qui est normal...')
    """
    class unite_fonctionnelle_definition(object):
        """
        Unités fonctionnelles de l'émulateur MIPS.
        
        Chaque unité est une liste de la grandeur du nombre de ces unités fonctionnelles.
        Ie. le processeur a 4 unités Load. Load sera alors une liste de longueur 4.
        
        À l'intérieur de ces listes est l'information de la latence et l'état actuel des unités.
        
        Exemples d'utilisation:
        
-        len(Load)               <= Nombre d'unités fonctionnelles Load
-        Load.latency            <= Latence de l'unité de lecture
-        Mult.latency_mul        <= Latence de l'unité de multiplication
-        Mult.latency_div        <= Latence de l'unité de multiplication en division
-        Branch.spec_forward     <= Type de spéculation (boolean), si True, les jumps conditionnels plus loin que le pointeur actuel est supposé pris.
-        Branch.spec_backward    <= Type de spéculation (boolean), si True, les jumps conditionnels arrière (ie. boucles) seront supposé prises.
-        Load[0]['status']       <= Temps restant à l'exécution de l'unité fonctionnelle [-1: non-utilisée, 0: terminé, 1+: en calcul]
-        Store[0]['param1']      <= Premier paramètre de l'opération
-        Mult[0]['param2']       <= Second paramètre de l'opération

        Références internes:
        
-            quantite = 0
-            latency1 = 0
-            latency2 = 0
-            spec_forward = False
-            spec_backward = False
-            unite = []          # deviendra [{'status':-1, 'param1':'', 'param2':''}, {'status':-1, 'param1':'', 'param2':''}, ...]
        """
        def __init__(self, in_architecture):
            self.conteneur['Load'] = unite_load(in_architecture)
            self.conteneur['Store'] = unite_store(in_architecture)
            self.conteneur['Add'] = unite_math(in_architecture)
            self.conteneur['Mult'] = unite_math(in_architecture)
            self.conteneur['ALU'] = unite_math(in_architecture)
            self.conteneur['Branch'] = unite_branch(in_architecture)
        
        def list(self):
            """
            Retourne la liste des unités fonctionnelles présentes sur l'architecture.
            """
            return list(self.conteneur.keys())
        
        def __setitem__(self, key, value):
            self.conteneur[key] = value
        
        def __getitem__(self, key):
            return self.conteneur[key]
        
        def __repr__(self):
            return str(self.conteneur)

        conteneur = {}
                    
    class registre_definition():
        """
        Système de registres du MIPS simulé.
        
        Exemples d'utilisation: 

        - print(config.registre['R0'])
        - config.registre['R2'] = 5
        - config.registre['F2'] = 5.2
        
        """
        def __init__(self):
            # Initialisation des registres
            for a in [a[0] + str(a[1]) for a in zip(['R'] * 32 + ['F'] * 32, list(range(32)) * 2)]:
                self.conteneur[a] = 0
        
        def __repr__(self):
            """
            Affiche le contenu des registres.
            """
            return ", ".join(["%s: %s" % (a, b) for a, b in self.conteneur.items()])
        
        @garantir_registre_valide
        def __getitem__(self, item=None):
            try:
                return self.conteneur[item]
            except:
                return 0.0
        
        @garantir_registre_valide
        def __setitem__(self, item=None, value=None):
            """
            Assigne les valeurs des registres.
            """
            # Capturer un essai d'écriture sur R0
            if item == 'R0':
                raise SimulationException("Impossible d'utiliser R0, ce registre est une constante.")

            # Assigner la valeur au registre, le valider en entier si RX et en fraction si FX
            try:
                # ROB
                if isinstance(value, str) and value[0] == '&':
                    self.conteneur[item] = value
                elif item[0] == 'R':
                    self.conteneur[item] = int(value)
                else:
                    self.conteneur[item] = float(value)
            except:
                raise SimulationException('Valeur à assigner invalide: %s' % value)
        
        conteneur = OrderedDict()
    
    def __init__(self, in_config_file=None, in_architecture=unite_tomasulo_speculation):
        """
        Ouvre un fichier XML et initialise le MIPS simulé en fonction de cette configuration.
        """
        self.architecture = in_architecture
        self.unite_fonctionnelle = self.unite_fonctionnelle_definition(self.architecture)
        self.registre = self.registre_definition()
        self.memoire = []
        self.memoire_size = 0
        self.ROB = []
        
        # Ouvrir le fichier XML
        if in_config_file == None:
            raise Exception('Aucun fichier de configuration en entrée.')
        xml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", in_config_file))
        try:
            print('Lecture du fichier de configuration %s en cours...' % xml_path)
            xml_data = parse(xml_path)
            print('Fichier de configuration lu avec succès.')
        except:
            raise Exception("Impossible d'utiliser le fichier de configuration XML.")
        
        # Attribution des unités fonctionneles et valeurs écrites ou par défaut
        try:
            self.unite_fonctionnelle['Load'].quantite = int(xml_data.getElementsByTagName("Load")[0]._attrs['number'].value)
        except:
            self.unite_fonctionnelle['Load'].quantite = 1
        try:
            self.unite_fonctionnelle['Load'].temps_execution = int(xml_data.getElementsByTagName("Load")[0]._attrs['latency'].value)
        except:
            self.unite_fonctionnelle['Load'].temps_execution = 1

        try:
            self.unite_fonctionnelle['Store'].quantite = int(xml_data.getElementsByTagName("Store")[0]._attrs['number'].value)
        except:
            self.unite_fonctionnelle['Store'].quantite = 1
        try:    
            self.unite_fonctionnelle['Store'].temps_execution = int(xml_data.getElementsByTagName("Store")[0]._attrs['latency'].value)
        except:
            self.unite_fonctionnelle['Store'].temps_execution = 1

        try:
            self.unite_fonctionnelle['Add'].quantite = int(xml_data.getElementsByTagName("Add")[0]._attrs['number'].value)
        except:
            self.unite_fonctionnelle['Add'].quantite = 1
        try:
            self.unite_fonctionnelle['Add'].temps_execution = int(xml_data.getElementsByTagName("Add")[0]._attrs['latency'].value)
        except:
            self.unite_fonctionnelle['Add'].temps_execution = 1

        try:
            self.unite_fonctionnelle['Mult'].quantite = int(xml_data.getElementsByTagName("Mult")[0]._attrs['number'].value)
        except:
            self.unite_fonctionnelle['Mult'].quantite = 0
        try:
            self.unite_fonctionnelle['Mult'].temps_execution = int(xml_data.getElementsByTagName("Mult")[0]._attrs['latency_mul'].value)
        except:
            self.unite_fonctionnelle['Mult'].temps_execution = 1
        try:
            self.unite_fonctionnelle['Mult'].temps_execution_division = int(xml_data.getElementsByTagName("Mult")[0]._attrs['latency_div'].value)
        except:
            self.unite_fonctionnelle['Mult'].temps_execution_division = 1

        try:
            self.unite_fonctionnelle['ALU'].quantite = int(xml_data.getElementsByTagName("ALU")[0]._attrs['number'].value)
        except:
            self.unite_fonctionnelle['ALU'].quantite = 1
        try:
            self.unite_fonctionnelle['ALU'].temps_execution = int(xml_data.getElementsByTagName("ALU")[0]._attrs['latency'].value)
        except:
            self.unite_fonctionnelle['ALU'].temps_execution = 1

        #Il ne peut y avoir qu'un prédicteur de branchement.
        self.unite_fonctionnelle['Branch'].quantite = 1
        try:
            self.unite_fonctionnelle['Branch'].temps_execution = int(xml_data.getElementsByTagName("Branch")[0]._attrs['latency'].value)
        except:
            self.unite_fonctionnelle['Branch'].temps_execution = 1
        try:
            self.unite_fonctionnelle['Branch'].spec_forward = (xml_data.getElementsByTagName("Branch")[0]._attrs['spec_forward'].value).lower() == 'taken'
        except:
            self.unite_fonctionnelle['Branch'].spec_forward = False
        try:
            self.unite_fonctionnelle['Branch'].spec_backward = (xml_data.getElementsByTagName("Branch")[0]._attrs['spec_backward'].value).lower() == 'taken'
        except:
            self.unite_fonctionnelle['Branch'].spec_backward = True

        # Attribution des registres
        childNodes = xml_data.getElementsByTagName("Registers")[0].childNodes
        childNodes = zip(childNodes[::2], childNodes[1::2])
        for a in childNodes:
            registre_name = a[1].tagName
            registre_value = a[1]._attrs['value'].value
            self.registre[registre_name] = registre_value
            self.registre[registre_name + 'T'] = registre_value
        
        # Attribution de la mémoire
        try:
            mem_init_values = xml_data.getElementsByTagName("Memory")[0].childNodes[0].data.strip().split()
        except:
            mem_init_values = []
        self.memoire = [float(a) for a in mem_init_values]
        self.memoire_size = int(xml_data.getElementsByTagName("Memory")[0]._attrs['size'].value)
        self.memoire = self.memoire[0:self.memoire_size] + [0.0] * (self.memoire_size - len(self.memoire[0:self.memoire_size]))
        
    def __repr__(self):
        return "Unités fonctionnelles: %s\nRegistres: %s\nMémoire: %s\nProgram Counter: %s" % (str(self.unite_fonctionnelle),
                                                                                               str(self.registre),
                                                                                               str(self.memoire),
                                                                                               str(self.PC))

    PC = 0
