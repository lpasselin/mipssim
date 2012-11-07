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

import sys
from src.trace import gestion_deverminage
from src.interpreteur import begin_memory_re, memory_re, memory_re_direct, registry_re


class SimulationException(Exception):
    """
    Wrapper d'erreur de simulation
    """
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)


class mips_simulateur(object):
    """
    Simulateur d'exécution du MIPS.

    Prends le code retourné par l'interpreteur et le fais exécuter sur la
    configuration entrée.
    """
    def __init__(self, configuration, interpreteur, fichier_trace=None):
        self.config = configuration
        self.interpreter = interpreteur
      
        #Didn't seem to be used...
        #self.trace_ptr = None
        #self.horloge = 0
        #self.unite_sanctionnement_now = []
        self.stall = False
        self.new_pc = None

        if fichier_trace != None:
            self.deverminage = gestion_deverminage(fichier_trace)

    def go(self, debug=False):
        """
        Effectue la simulation
        
        Valeurs de retour:
        
        * 0 = Simulation terminée avec succès
        * 1 = Une erreur a été détectée lors de l'exécution du programme. Pour
              plus de détails, voir le flot d'erreur du programme.
        * 2 = Une erreur non-prévue s'est produite.
        """
        self.verbose = debug
        try:
            while self.step() == 0:
                pass
            else:
                # La boucle s'est effectuée jusq'au bout
                print("Source EOF")
                return 0
        except SimulationException as err_desc:
            # Une erreur a été détectée
            sys.stderr.write("Une erreur a été détectée lors de l'exécution du \
                programme à la ligne : %s" % err_desc)
            return 1
        return 2

    def step(self):
        """
        Effectue une itération de la simulation.
        
        * Retourne 0 si l'opération s'est déroulée avec succès et \
l'exécution n'est pas terminée.
        * Retourne 1 si l'opération s'est déroulée avec succès et \
l'exécution est terminée
        
        Une exception est levée si l'exécution ne s'est pas déroulée avec succès.
        """

        # Check si l'unité fonctionnelle requise est libre
        if self.verbose:
            print("Coup d'horloge - PC = %s - Stall = %s" % (
                  str(self.config.PC), 
                  str(self.stall))
                 )

        # On sanctionne l'instruction via le ROB ( Premier élément de celui-ci )
        self.sanctionnement_rob()
            
        # Décrémentation du temps sur les unités fonctionnelles
        self.decrement_time()

        # Gestion des bulles et de la fin du programme
        if self.stall == True \
        or self.config.PC + 1 > len(self.interpreter.flow):
            if self.verbose:
                print("Debug: Coup d'horloge stallé")
        else:
            self.issue_instr()

        # Avancement du Issue/Program Counter (PC)
        self.config.PC = self.new_pc if self.new_pc != None else self.config.PC
        self.new_pc = None

        # Si le Program Counter est > la longueur du code, on a 
        # (potentiellement) fini la job et on attend le ROB!
        if (self.config.PC >= len(self.interpreter) \
        or self.config.PC == None) and len(self.config.ROB) < 1:
            return 1
        else:
            # Impression de la trace_ptr
            if 'deverminage' in list(self.__dict__.keys()):
                self.deverminage.mise_a_jour_trace(self.config)
            return 0

    def sanctionnement_rob(self):
        """
        Fonction sanctionnant les opérations dans l'ordre d'origine dont le 
        calcul est terminé.
        Les opérations du ROB dont l'unité fonctionnelle a terminé sont alors 
        effectuées.
        """
        if len(self.config.ROB) > 0 and self.config.ROB[0][1] != None:
            if self.verbose:
                print("Execution: %s" % self.config.ROB[0][1][1])
            architecture_proxy = {'self': self}

            # Quand une instruction est sanctionnée, s'assurer qu'elle n'écrit pas
            # une valeur qui est encore dans le ROB comme fixe (ie. registre)
            ecrire_registre = True
            if self.config.ROB[0][1][1].split("=")[0].strip().find("self.config.registre") == 0:
                exec(self.config.ROB[0][1][1].strip().replace("'] ", "T'] ", 1), architecture_proxy)
                #JCL: Tentative différente
                #Si le registre dans lequel cette instruction doit écrire attend
                #une valeur en provenance d'une autre unité fonctionnelle, il ne
                #faut pas écrire par dessus.
                
                #Contenu du registre à l'adresse d'écriture                
                reg_str = self.config.ROB[0][1][1].split(" =")[0]
                reg = reg_str.split('\'')[1]
                val_reg = self.config.registre[reg]

                if isinstance(val_reg, str) and val_reg[1:] != self.config.ROB[0][0]:
                    #Il ne faut pas écrire par dessus le &UF
                    ecrire_registre = False

            else:
                # Vérifier qu'aucune opération pending wants to write to this register
                for b in [a for a in self.config.unite_fonctionnelle.list() if a not in ["Store", "Branch"]]:
                    # Prendre une référence sur l'unité fonctionnelle qu'on analyse
                    unite = self.config.unite_fonctionnelle[b] 
                    for c in range(len(unite)):
                        # Vérifier que l'unité est actuellement utilisé :
                        if unite[c]['busy'] == True:
                            if unite[c]['op'][1][0] == self.config.ROB[0][1][1].split("=")[0].strip().split(".")[-1]:
                                exec('%s = "%s"' % (self.config.ROB[0][1][1].split("=")[0].strip(), "&" + str(b) + str(c)), architecture_proxy)
                                self = ldict['self']

            if ecrire_registre:
                exec(self.config.ROB[0][1][1], architecture_proxy)
            
            # Mettre à jour les Vj/Vk Qj/Qk des autres éléments avant une autre
            # opération qui changerait le même registre
            for b in list(zip(*self.config.ROB))[0]:
                d = int("".join([e for e in list(b) if e.isdigit()])) - 1
                c = "".join([e for e in list(b) if not e.isdigit()])
                unite = self.config.unite_fonctionnelle[c][d]
                
                # Arrêter si l'unité fonctionnelle actuellement analysée va réécrire ce registre
                try:
                    if unite['op'][1][0].strip() == self.config.ROB[0][1][0].strip():
                        break
                except KeyError:
                    pass
                except TypeError:
                    pass
                # Vérifier que l'unité est actuellement utilisé :
                if unite['busy'] == True:
                    # Mettre à jour Qj/Qk pour Vj/Vk
                    # On essaie de trouver l'élément (registre/mémoire) dans Qj/Qk. S'il est trouvé, on l'évalue
                    resultat = eval(self.config.ROB[0][1][0])
                    if unite['qj'] is not None and self.config.ROB[0][0] in unite['qj']:
                        if begin_memory_re.match(unite['qj']) is not None:
                            unite['vj'] = "%s(%s)" % (unite['qj'].split('(')[0], resultat)
                        else:
                            unite['vj'] = resultat
                        unite['qj'] = None
                    if unite['qk'] is not None and self.config.ROB[0][0] in unite['qk']:
                        if begin_memory_re.match(unite['qk']) is not None:
                            unite['vk'] = "%s(%s)" % (unite['qk'].split('(')[0], resultat)
                        else:
                            unite['vk'] = resultat
                        unite['qk'] = None
                                    
            # Gestion des branchs lors du sanctionnement
            if self.config.ROB[0][0][:6] == 'Branch':     
                self.stall = False
                
                if (self.new_pc != None and self.config.ROB[0][2] == False) or (self.new_pc == None and self.config.ROB[0][2] == True):
                    # Mauvaise spéculation
                    # Remettre le pointeur à la bonne place
                    
                    self.config.PC = self.config.ROB[0][3]
                    self.new_pc = None
                    # Clean du ROB
                    del self.config.ROB[:]
                    # Clean des stations de réservation
                    self.clean_unite_fonctionnelles()
                    # Clean des registres
                    self.config.registre['F0'] = self.config.registre['F0T']
                    for a in range(1, 31):
                        self.config.registre['R%d' % a] = self.config.registre['R%dT' % a]
                        self.config.registre['F%d' % a] = self.config.registre['F%dT' % a]
                else:
                    # Spéculation réussite, aucun changement requis.
                    self.new_pc = None
            
            # Une fois l'instruction sanctionnée, la retirer du ROB
            if len(self.config.ROB) > 0:
                self.config.ROB.pop(0)
            
            # Si nous ne sommes pas en présence d'un aléa, incrémenter le 
            # compteur PC.
            if self.stall == False:
                self.new_pc = (self.config.PC + 1) if self.new_pc == None else self.new_pc
            
    def exec_tomasulo(self, in_unite):
        """
        Prépare les variables pour l'exécution.
        Traduit les vj/vk/etc en paramètres directs pour faire fonctionner la commande exec_instr().
        """
        
        in_instr = in_unite['op']
        # Résoudre les adresses d'accès mémoire
        vj = in_unite['vj']
        if len(in_instr[1]) > 2:
            vk = in_unite['vk']
        addr = None
        params = [str(a) for a in [in_instr[1][0], in_unite['vj'], in_unite['vk']] if a != None]
        # Cas spécial pour store où les unités sont inversés, Quix hax
        if in_instr[0][0] == 'Load':
            pass
        elif in_instr[0][0] == 'Store':
            params[0] = params[1]
            params[1] = params[2]
        elif in_instr[0][0] == 'Branch':
            params[0] = params[1]
            if len(params) > 2:
                params[1] = params[2]
                params[2] = in_instr[1][-1]
            else:
                params[1] = in_instr[1][-1]
        return self.exec_instr((in_instr[0], params))

    def resolve_variables(self, in_param, memory_resolve=True):
        """
        Permet de transformer les variables du code MIPS en variables Python selon l'architecture de la configuration. 
        """
        output = in_param
        # Remplacer les paramètres par les références
        # Mémoire éloignée
        if memory_resolve == True:
            if memory_re.match(output) is not None:
                output = 'self.config.memoire[int(%s)]' % ('(int(' + str(output.split('(')[1][:-1]) + ') + ' + str(output.split('(')[0]) + ')/8')
            
            # Mémoire directe
            if memory_re_direct.match(output) is not None:
                output = 'self.config.memoire[int(%s)]' % ('(' + str(output.split('(')[1][:-1]) + ' + ' + str(output.split('(')[0]) + ')/8')

        # Nombre direct
        output = output[1:] if output[0] == "#" else output
        
        # Registres
        output = registry_re.sub(r"self.config.registre['\1']", output)
        
        return output

    def exec_instr(self, in_instr):
        """
        Exécution de l'instruction sous forme (["Unite_fctionnelle", "destination = source_$0 + source_$1"], [param1, param2, ...])
        """
        code = in_instr[0][1]
        if in_instr[0][0] == 'Branch':
            params = in_instr[1] + ['self.new_pc', 'self.config.PC', 'ERROR', 'ERROR', 'ERROR']
        else:
            params = in_instr[1] + ['ERROR', 'ERROR', 'ERROR', 'ERROR']

        for index, a in enumerate(params):
            params[index] = self.resolve_variables(a)
        
        # Remplacer les placeholders
        code = code.replace("$0", params[0]).replace("$1", params[1]).replace("$2", params[2]).replace("$3", params[3]).strip()

        # Détection des erreurs (sens assez littéraire :)
        if code.find("ERROR") > -1:
            raise SimulationException([in_instr, "Paramètre manquant"])
        
        # Debug:
        if self.verbose:
            params = [a for a in params if a != 'ERROR']
            valeurs = []
            for a in params:
                valeurs.append("%s=%s" % (a, code))
            print('Debug: %s | %s' % (code.replace("self.config.", ""), str(valeurs)))

        # Wrapping de l'opération en code Python
        retour = "=".join(code.split("=")[1:])
        return (retour, code.split("=")[0] + " = " + str(retour))

    def clean_unite_fonctionnelles(self):
        for a in self.config.unite_fonctionnelle.list():
            # Prendre une référence sur l'unité fonctionnelle qu'on analyse
            unite = self.config.unite_fonctionnelle[a]
            for b in range(len(unite)):
                unite[b].reset()

    def decrement_time(self):
        """
        Effectue un coup d'horloge, soit décrémente de un le temps restant de chaque unité fonctionnelle qui travaille en ce moment.
        
        Part les unités fonctionelles qui attendaient après des données qui sont maintenant disponibles
        """
        # Reset des writeback buffer
        self.unite_sanctionnement_now = []

        for a in self.config.unite_fonctionnelle.list():
            # Prendre une référence sur l'unité fonctionnelle qu'on analyse
            unite = self.config.unite_fonctionnelle[a]
            for b in range(len(unite)):
                # Vérifier que l'unité est actuellement utilisée :
                if unite[b]['busy'] == True:
                    # Si l'unité fonctionnelle n'est pas démarrée (temps = None), vérifier si on peut la partir
                    if unite[b]['temps'] == None:
                        if unite[b]['qj'] == None and unite[b]['qk'] == None:
                            # On part l'exécution
                            # Exception pour l'unité fonctionnelle Mult
                            if a == 'Mult':
                                if unite[b]['op'][0][1].find('*') > -1:
                                    unite[b]['temps'] = unite.temps_execution
                                else:
                                    unite[b]['temps'] = unite.temps_execution_division
                            else:
                                unite[b]['temps'] = unite.temps_execution
                    # Si elle est déjà partie...
                    else:
                        # Si on passe de 0 à -1, l'unité redevient available et le résultat est écrit (Write de Tomasulo)
                        if unite[b]['temps'] < 1:
                            nom_unite = a + str(b + 1)
                            self.unite_sanctionnement_now.append(nom_unite)
                            
                            # Prêt au sanctionnement
                            retour = self.exec_tomasulo(unite[b])

                            # Reset de l'unité fonctionnelle
                            unite[b].reset()
                            # Modifier l'information dans le ROB. Trouver et mettre à jour l'élément [1] du ROB avec retour
                            for index, c in reversed([(index, i) for index, i in enumerate(self.config.ROB)]):
                                if c[0] == a + str(b + 1):
                                    self.config.ROB[index][1] = retour
                                    break
                            
                            retour = eval(retour[0])
                            # Writeback Tomasulo, écriture de l'instruction sur le CDB et mise à jour des stations de réservation
                            for n in self.config.unite_fonctionnelle.list():
                                uf = self.config.unite_fonctionnelle[n]
                                for i in range(len(uf)):
                                    # Mise à jour requise uniquement lorsque l'unité est occupée et attend après ses paramètres.
                                    if uf[i]['busy'] and uf[i]['temps'] == None:
                                        if uf[i]['qj'] is not None and uf[i]['qj'].find(nom_unite) != -1:
                                            if begin_memory_re.match(uf[i]['qj']) is not None:
                                                uf[i]['vj'] = "%s(%s)" % (uf[i]['qj'].split('(')[0], retour)
                                            else:
                                                uf[i]['vj'] = retour
                                            uf[i]['qj'] = None
                                        if uf[i]['qk'] is not None and uf[i]['qk'].find(nom_unite) != -1:
                                            if begin_memory_re.match(uf[i]['qk']) is not None:
                                                uf[i]['vk'] = "%s(%s)" % (uf[i]['qk'].split('(')[0], retour)
                                            else:
                                                uf[i]['vk'] = retour
                                            uf[i]['qk'] = None
                        # Sinon, simplement la décrémenter de 1
                        else:
                            unite[b]['temps'] -= 1

    def issue_instr(self):
        """
        Ajouter une instruction dans le ROB pendant son calcul par une unité fonctionelle.
        """
        ref_unite_fct = self.config.unite_fonctionnelle[self.interpreter.flow[self.config.PC][0][0]]
        unite_index = self.find_unite_fct(ref_unite_fct, self.interpreter.flow[self.config.PC][0][0])
        # Tester si un branch n'est pas déjà dans le ROB, le cas échéant ne pas partir de spéculation multiple
        if self.interpreter.flow[self.config.PC][0][0] == 'Branch':
            for a in self.config.ROB:
                if a[0][:6] == 'Branch':
                    self.stall = True
                    self.new_pc = self.config.PC
                    return
        # Attribuer l'opération à une station de réservation si possible
        if unite_index != None:
            # Ajouter l'info au ROB
            self.config.ROB.append([self.interpreter.flow[self.config.PC][0][0] + str(unite_index + 1), None])
            # Attribuer les variables de Tomasulo
            ref_unite_fct[unite_index]['busy'] = True
            ref_unite_fct[unite_index]['temps'] = None
            ref_unite_fct[unite_index]['addr'] = None
            ref_unite_fct[unite_index]['dest'] = None
            ref_unite_fct[unite_index]['op'] = self.interpreter.flow[self.config.PC]
            
            # Vérifier les paramètres des opérations voir s'ils vont dans le vj/vk ou qj/qk
            if ref_unite_fct[unite_index]['op'][0][0] == "Store":
                to_check = [0, 1]
            elif ref_unite_fct[unite_index]['op'][0][0] == "Branch":
                if ref_unite_fct[unite_index]['op'][0][1] == '$2 = $1 if $0 == 0 else $2' \
                or ref_unite_fct[unite_index]['op'][0][1] == '$2 = $1 if $0 != 0 else $2':
                    to_check = [0]
                elif ref_unite_fct[unite_index]['op'][0][1] == '$3 = $2 if $0 == $1 else $3' \
                or ref_unite_fct[unite_index]['op'][0][1] == '$3 = $2 if $0 != $1 else $3':
                    to_check = [0, 1]
                else:
                    to_check = []
            else:
                to_check = [1, 2]

            # Trouver Vj/Vk ou Qj/Qk
            premier = True
            for param_index, a in enumerate(to_check):
                if len(self.interpreter.flow[self.config.PC][1]) < a + 1:
                    continue
                param = self.interpreter.flow[self.config.PC][1][a]                
                
                # On résoud la référence
                temp = self.resolve_variables(param, False)
                
                # Est-ce que on a déjà la valeur? Si oui, on la met dans Vj/Vk, sinon, Qj/Qk
                valeur = "&"
                try:
                    # Ne pas résoudre les accès mémoire en ce moment
                    if memory_re.match(param) is not None:
                        uf = eval(temp.split('(', 1)[1].rstrip(" )"))
                    else:
                        uf = eval(temp)
                    
                    numeric = False
                    if isinstance(uf, str) and '&' in uf:
                        rob = list(zip(*self.config.ROB))[0]
                        if uf[1:] in rob and self.config.ROB[rob.index(uf[1:])][1] is not None:
                            numeric = True
                            numeric_val = eval(self.config.ROB[rob.index(uf[1:])][1][0])                    
                            if memory_re.match(param) is not None:
                                valeur = "%s(%s)" % (temp.split('(')[0], numeric_val)
                            else:
                                valeur = numeric_val
                                
                    if not numeric:
                        if memory_re.match(param) is not None:
                            valeur = "%s(%s)" % (temp.split('(')[0], uf)
                        else:
                            valeur = uf
                except BaseException as e:
                    # RAISE ERROR
                    print("Erreur lors de l'execution: %s - %s" % (temp, e))
                
                if premier == True:
                    if isinstance(valeur, str) and '&' in valeur:
                        #Utiliser la valeur de format '&UNITE_FCT' plutôt 
                        #que le numéro de registre directement
                        ref_unite_fct[unite_index]['qj'] = valeur
                        ref_unite_fct[unite_index]['vj'] = None
                    else:
                        ref_unite_fct[unite_index]['qj'] = None
                        ref_unite_fct[unite_index]['vj'] = valeur
                else:
                    if isinstance(valeur, str) and '&' in valeur:
                        ref_unite_fct[unite_index]['qk'] = valeur
                        ref_unite_fct[unite_index]['vk'] = None
                    else:
                        ref_unite_fct[unite_index]['qk'] = None
                        ref_unite_fct[unite_index]['vk'] = valeur
                premier = False
            
            if ref_unite_fct[unite_index]['qj'] == None and ref_unite_fct[unite_index]['qk'] == None:
                # On part l'exécution
                # Exception pour l'unité fonctionnelle Mult                
                if ref_unite_fct[unite_index]['op'][0][0] == 'Mult':
                    if ref_unite_fct[unite_index]['op'][0][1].find('*') > -1:
                        ref_unite_fct[unite_index]['temps'] = ref_unite_fct.temps_execution
                    else:
                        ref_unite_fct[unite_index]['temps'] = ref_unite_fct.temps_execution_division
                else:
                    ref_unite_fct[unite_index]['temps'] = ref_unite_fct.temps_execution

            # Trouver le paramètre de destination, qui est l'inverse des paramètres d'entrée (sauf pour le Branch)
            destination = [a for a in range(len(self.interpreter.flow[self.config.PC][1])) if a not in to_check]
            # Si l'opération est une branch, aucune destination à analyser - C'est un label.
            # Si aucune destination trouvée, ie un Store ou  Branch, mettre à None
            destination = destination[0] if len(destination) > 0 and self.interpreter.flow[self.config.PC][0][0] != 'Branch' else None

            # Mettre une référence dans la destination, soit &Unite_name
            if destination is not None and destination is not []:
                #Utiliser une notation débutant à 1.
                destination_value = '&' + self.interpreter.flow[self.config.PC][0][0] + str(unite_index + 1)
                self.config.registre[self.interpreter.flow[self.config.PC][1][destination]] = destination_value

            # Passer à l'opération suivante s'il n'y a pas de branch qui s'est déjà effectué
            if self.interpreter.flow[self.config.PC][0][0] != 'Branch':
                self.new_pc = (self.config.PC + 1) if self.new_pc == None else self.new_pc
            else:
                # Gestion des branchs / Spéculation
                # Déterminer si le branchement des forward ou backward
                forward_branch = (int(self.interpreter.flow[self.config.PC][1][-1][1:]) > int(self.config.PC))
                if (self.config.unite_fonctionnelle['Branch'].spec_forward and forward_branch) or (self.config.unite_fonctionnelle['Branch'].spec_backward and (forward_branch == False)):
                    # Spéculation forward or backward ENGAGED
                    self.new_pc = int(self.interpreter.flow[self.config.PC][1][-1][1:])
                    self.config.ROB[-1].append(True)
                    self.config.ROB[-1].append(int(self.config.PC + 1))
                else:
                    self.new_pc = int(self.config.PC + 1)
                    self.config.ROB[-1].append(False)
                    self.config.ROB[-1].append(int(self.interpreter.flow[self.config.PC][1][-1][1:]))
        else:
            # Aucune unité fonctionnelle libre trouvée, on est COINCÉS COMME DES RATS et on attend.
            self.new_pc = self.config.PC

    def find_unite_fct(self, unite, nom_unite):
        for index, a in enumerate(unite):
            str_unite = nom_unite + str(index + 1)
            if a['busy'] == False and str_unite not in self.unite_sanctionnement_now and len(list(filter(lambda r: r[0] == str_unite, self.config.ROB))) == 0:
                return index 
        else:
            return None

    
if __name__ == '__main__':
    sys.stderr.write("Ce module n'est pas utilisable seul.")
    sys.exit(-1)
