# -*- coding: utf-8 -*-

# Copyright (c) 2011, Yannick Hold-Geoffroy and Julien-Charles Lévesque on behalf of Université Laval
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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys

from collections import OrderedDict, deque
from xml.dom.minidom import parse

#local imports
import trace
import interpreter as interp
from interpreter import begin_memory_re, memory_re, memory_re_direct, registry_re
from components import FuncUnit, ROBEntry, ROB, Registers, State


class Simulator:
    '''
    Simulateur d'exécution du MIPS.

    Prends le code retourné par l'interpreteur et le fais exécuter sur la
    configuration entrée.
    '''
    def __init__(self, config_file, source_file, trace_file='', trace_mode='t'):
        #Initialisation des variables membres
        self.horloge = 0
        self.stall = False
        self.new_PC = None
        self.mem = []
        self.mem_size = 0
        self.ROB = ROB(maxlen=24)
        self.PC = 0
        self.RS = OrderedDict()

        #Initialisation des registres
        self.regs = Registers()

        #Lecture de la configuration et du code source à exécuter
        self.load_config(config_file)
        self.instructions = interp.interpret_asm(source_file)

        #Setup du fichier de trace si applicable
        if trace_file != '':
            if trace_mode =='t':
                self.trace = trace.TextTrace(trace_file)
            elif trace_mode == 'l':
                self.trace = trace.LatexTrace(trace_file)
        else:
            self.trace = None

    def go(self):
        '''
        Effectue la simulation

        Valeurs de retour:

        * 0 = Simulation terminée avec succès
        * 1 = Une erreur a été détectée lors de l'exécution du programme. Pour
              plus de détails, voir le flot d'erreur du programme.
        * 2 = Une erreur non-prévue s'est produite.
        '''

        while self.step() == 0:
            self.horloge += 1

        #L'exécution s'est complétée sans problème.
        print('Fin des instructions.')
        return 0

    def step(self):
        '''
        Effectue une itération de la simulation.

        * Retourne 0 si l'opération s'est déroulée avec succès et l'exécution \
        n'est pas terminée.
        * Retourne 1 si l'opération s'est déroulée avec succès et l'exécution \
        est terminée

        Une exception est levée si l'exécution ne s'est pas déroulée avec succès.
        '''

        print('Coup d\'horloge - PC = %s - Stall = %s' % (
          str(self.PC), str(self.stall)))

        # On sanctionne l'instruction via le ROB ( Premier élément de celui-ci )
        self.sanctionnement_rob()

        # Décrémentation du temps sur les unités fonctionnelles
        self.decrement_time()

        # Gestion des bulles et de la fin du programme
        if self.stall == True or self.PC >= len(self.instructions):
            print('Debug: Coup d\'horloge stallé.')
        else:
            self.issue_instr()

        # Avancement du Issue/Program Counter (PC)
        if self.new_PC != None:
            self.PC = self.new_PC
        self.new_PC = None

        #Si l'exécution est terminée et le ROB est vide
        if self.PC >= len(self.instructions) and len(self.ROB) == 0:
            return 1
        else:
            if self.trace:
                self.trace.mise_a_jour(self)
            return 0

    def sanctionnement_rob(self):
        '''
        Sanctionne les opérations dont le calcul est terminé dans l'ordre de lancement.
        Seule l'instruction à la tête du ROB peut être sanctionnée.
        '''
        if len(self.ROB) > 0 and self.ROB[0][1] != None:
            if self.verbose:
                print('Execution: %s' % self.ROB[0][1][1])
            architecture_proxy = {'self': self}

            # Quand une instruction est sanctionnée, s'assurer qu'elle n'écrit pas
            # une valeur qui est encore dans le ROB comme fixe (ie. registre)
            ecrire_registre = True
            if self.ROB[0][1][1].split('=')[0].strip().find('self.registre') == 0:
                exec(self.ROB[0][1][1].strip().replace('] ', 'T] ', 1), architecture_proxy)
                #Si le registre dans lequel cette instruction doit écrire attend
                #une valeur en provenance d'une autre unité fonctionnelle, il ne
                #faut pas écrire par dessus.

                #Contenu du registre à l'adresse d'écriture
                reg_str = self.ROB[0][1][1].split(' =')[0]
                reg = reg_str.split('\'')[1]
                val_reg = self.registre[reg]

                if isinstance(val_reg, str) and val_reg[1:] != self.ROB[0][0]:
                    #Il ne faut pas écrire par dessus le &UF
                    ecrire_registre = False

            else:
                # Vérifier qu'aucune opération pending wants to write to this register
                for b in [a for a in self.unite_fonctionnelle.list() if a not in ['Store', 'Branch']]:
                    # Prendre une référence sur l'unité fonctionnelle qu'on analyse
                    unite = self.unite_fonctionnelle[b]
                    for c in range(len(unite)):
                        # Vérifier que l'unité est actuellement utilisé :
                        if unite[c]['busy'] == True:
                            if unite[c]['op'].operands[0] == self.ROB[0][1][1].split('=')[0].strip().split('.')[-1]:
                                exec('%s = %s' % (self.ROB[0][1][1].split('=')[0].strip(), '&' + str(b) + str(c)), architecture_proxy)
                                self = ldict['self']

            if ecrire_registre:
                exec(self.ROB[0][1][1], architecture_proxy)

            # Mettre à jour les Vj/Vk Qj/Qk des autres éléments avant une autre
            # opération qui changerait le même registre
            for b in list(zip(*self.ROB))[0]:
                d = int(''.join([e for e in list(b) if e.isdigit()])) - 1
                c = ''.join([e for e in list(b) if not e.isdigit()])
                unite = self.unite_fonctionnelle[c][d]

                # Arrêter si l'unité fonctionnelle actuellement analysée va réécrire ce registre
                try:
                    if unite['op'].operands[0].strip() == self.ROB[0][1][0].strip():
                        break
                except KeyError:
                    pass
                except TypeError:
                    pass
                # Vérifier que l'unité est actuellement utilisé :
                if unite['busy'] == True:
                    # Mettre à jour Qj/Qk pour Vj/Vk
                    # On essaie de trouver l'élément (registre/mémoire) dans Qj/Qk. S'il est trouvé, on l'évalue
                    resultat = eval(self.ROB[0][1][0])
                    if unite['qj'] is not None and self.ROB[0][0] in unite['qj']:
                        if begin_memory_re.match(unite['qj']) is not None:
                            unite['vj'] = '%s(%s)' % (unite['qj'].split('(')[0], resultat)
                        else:
                            unite['vj'] = resultat
                        unite['qj'] = None
                    if unite['qk'] is not None and self.ROB[0][0] in unite['qk']:
                        if begin_memory_re.match(unite['qk']) is not None:
                            unite['vk'] = '%s(%s)' % (unite['qk'].split('(')[0], resultat)
                        else:
                            unite['vk'] = resultat
                        unite['qk'] = None

            # Gestion des branchs lors du sanctionnement
            if self.ROB[0][0][:6] == 'Branch':
                self.stall = False

                if (self.new_pc != None and self.ROB[0][2] == False) or (self.new_pc == None and self.ROB[0][2] == True):
                    # Mauvaise spéculation
                    # Remettre le pointeur à la bonne place

                    self.PC = self.ROB[0][3]
                    self.new_pc = None
                    # Clean du ROB
                    del self.ROB[:]
                    # Clean des stations de réservation
                    self.clean_unite_fonctionnelles()
                    # Clean des registres
                    self.registre['F0'] = self.registre['F0T']
                    for a in range(1, 31):
                        self.registre['R%d' % a] = self.registre['R%dT' % a]
                        self.registre['F%d' % a] = self.registre['F%dT' % a]
                else:
                    # Spéculation réussite, aucun changement requis.
                    self.new_pc = None

            # Une fois l'instruction sanctionnée, la retirer du ROB
            if len(self.ROB) > 0:
                self.ROB.pop(0)

            # Si nous ne sommes pas en présence d'un aléa, incrémenter le
            # compteur PC.
            if self.stall == False:
                self.new_pc = (self.PC + 1) if self.new_pc == None else self.new_pc

    def exec_tomasulo(self, in_unite):
        '''
        Prépare les variables pour l'exécution.
        Traduit les vj/vk/etc en paramètres directs pour faire fonctionner la commande exec_instr().
        '''

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

    def resolve_variables(self, param, memory_resolve=True):
        '''
        Permet de transformer les variables du code MIPS en variables Python.
        '''
        output = param

        #Mémoire
        if memory_resolve == True:
            if memory_re.match(output) is not None:
                import IPython; IPython.embed()
                output = 'self.mem[int(%s)]' % ('(int(' + str(output.split('(')[1][:-1]) + ') + ' + str(output.split('(')[0]) + ')/8')

            # Mémoire directe
            if memory_re_direct.match(output) is not None:
                output = 'self.mem[int(%s)]' % ('(' + str(output.split('(')[1][:-1]) + ' + ' + str(output.split('(')[0]) + ')/8')

        # Nombre direct
        output = output[1:] if output[0] == '#' else output

        # Registres
        output = registry_re.sub(r'self.regs[\1]', output)

        return output

    def exec_instr(self, in_instr):
        '''
        Exécution de l'instruction sous forme (['Unite_fctionnelle', 'destination = source_$0 + source_$1'], [param1, param2, ...])
        '''
        code = in_instr[0][1]
        if in_instr[0][0] == 'Branch':
            params = in_instr[1] + ['self.new_pc', 'self.PC', 'ERROR', 'ERROR', 'ERROR']
        else:
            params = in_instr[1] + ['ERROR', 'ERROR', 'ERROR', 'ERROR']

        for index, a in enumerate(params):
            params[index] = self.resolve_variables(a)

        # Remplacer les placeholders
        code = code.replace('$0', params[0]).replace('$1', params[1]).replace('$2', params[2]).replace('$3', params[3]).strip()

        # Détection des erreurs (sens assez littéraire :)
        if code.find('ERROR') > -1:
            raise SimulationException([in_instr, 'Paramètre manquant'])

        # Debug:
        if self.verbose:
            params = [a for a in params if a != 'ERROR']
            valeurs = []
            for a in params:
                valeurs.append('%s=%s' % (a, code))
            print('Debug: %s | %s' % (code.replace('self.', ''), str(valeurs)))

        # Wrapping de l'opération en code Python
        retour = '='.join(code.split('=')[1:])
        return (retour, code.split('=')[0] + ' = ' + str(retour))

    def clean_unite_fonctionnelles(self):
        for a in self.unite_fonctionnelle.list():
            # Prendre une référence sur l'unité fonctionnelle qu'on analyse
            unite = self.unite_fonctionnelle[a]
            for b in range(len(unite)):
                unite[b].reset()

    def decrement_time(self):
        '''
        Effectue un coup d'horloge, soit décrémente de un le temps restant de chaque unité
         fonctionnelle qui travaille en ce moment.

        Démarre les unités fonctionelles qui attendaient des données maintenant disponibles.
        '''
        # Reset des writeback buffer
        self.commit_now = []

        #Variable temporaire pour savoir si nous avons mis à jour une UF.
        updated = [[False] * len(funit) for funit in self.RS]

        #Première passe, les instructions devant fournir des opérandes doivent le faire
        #avant de tenter d'exécuter quoi que ce soit.
        #Les unités fonctionnelles sont regroupées par type dans la structure RS pour ReservationStations
        #Par exemple {'Load':[Load1, Load2], 'Store':[Store1, Store2], ...}
        for i, (unit_type, units) in enumerate(self.RS.items()):
            #Itérer sur les unités fonctionnelles dans la station de réservation
            for j, funit in enumerate(units):
                # Vérifier que l'unité est actuellement utilisée :
                if funit.busy:
                    # Si elle est déjà partie...
                    if funit.time != None:
                        updated[i][j] = True
                        #Si on passe de 0 à -1, l'unité redevient disponible et le résultat est
                        # écrit (Write de Tomasulo)
                        if funit.time < 1:
                            self.unite_sanctionnement_now.append(funit.name)

                            # Prêt au sanctionnement
                            retour = self.exec_tomasulo(funit)

                            # Reset de l'unité fonctionnelle
                            funit.reset()

                            import IPython; IPython.embed()
                            # Modifier l'information dans le ROB. Trouver et mettre à jour l'élément
                            # [1] du ROB avec retour
                            for k, entry in reversed(enumerate(self.ROB)):
                                if c[0] == a + str(b + 1):
                                    self.ROB[index][1] = retour
                                    break

                            retour = eval(retour[0])
                            # Writeback Tomasulo, écriture de l'instruction sur le CDB et mise à jour des stations de réservation
                            for n in self.unite_fonctionnelle.list():
                                uf = self.unite_fonctionnelle[n]
                                for i in range(len(uf)):
                                    # Mise à jour requise uniquement lorsque l'unité est occupée et attend après ses paramètres.
                                    if uf[i]['busy'] and uf[i]['temps'] == None:
                                        if uf[i]['qj'] is not None and uf[i]['qj'].find(nom_unite) != -1:
                                            if begin_memory_re.match(uf[i]['qj']) is not None:
                                                uf[i]['vj'] = '%s(%s)' % (uf[i]['qj'].split('(')[0], retour)
                                            else:
                                                uf[i]['vj'] = retour
                                            uf[i]['qj'] = None
                                        if uf[i]['qk'] is not None and uf[i]['qk'].find(nom_unite) != -1:
                                            if begin_memory_re.match(uf[i]['qk']) is not None:
                                                uf[i]['vk'] = '%s(%s)' % (uf[i]['qk'].split('(')[0], retour)
                                            else:
                                                uf[i]['vk'] = retour
                                            uf[i]['qk'] = None
                        # Sinon, simplement la décrémenter de 1
                        else:
                            funit.time -= 1

        #Seconde passe, tenter de démarrer l'exécution des unités fonctionnelles en attente d'opérandes.
        for i, (unit_type, units) in enumerate(self.RS.items()):
            for j, funit in enumerate(units):
                # Vérifier que l'unité est actuellement utilisée et qu'elle n'a pas été mise à jour dans
                # la passe précédente :
                if funit.busy and not updated[i][j]:
                    # Si l'unité fonctionnelle n'est pas démarrée (temps = None), vérifier si on peut la partir
                    if funit.time == None and funit.qj == None and funit.qk == None:
                        # On part l'exécution
                        # Exception pour l'unité fonctionnelle Mult
                        if unit_type == 'Mult':
                            if funit.action.find('*') > -1:
                                funit.time = funit.latency
                            else:
                                funit.time = funit.div_latency
                        else:
                            funit.time = funit.latency

    def issue_instr(self):
        '''
        Ajouter une instruction dans le ROB pendant son calcul par une unité fonctionelle.
        '''
        #Référence vers le conteneur pour toutes les unités fonctionnelles du type courant
        cur_instruction = self.instructions[self.PC]
        func_unit_type_ref = self.RS[cur_instruction.funit]
        #Vérifie si une unité fonctionnelle du type requis est libre
        funit_idx = self.find_funit(func_unit_type_ref, cur_instruction.funit)

        #Tester si un branch n'est pas déjà dans le ROB, le cas échéant ne pas lancer
        # de spéculation multiple
        if cur_instruction.funit == 'Branch':
            for entry in self.ROB:
                if entry.instr.funit == 'Branch':
                    self.stall = True
                    self.new_PC = self.PC
                    return

        # Attribuer l'opération à une station de réservation si possible
        if funit_idx > -1 and self.ROB.check_free_entry():
            cur_funit = func_unit_type_ref[funit_idx]
            cur_funit.reset()

            #Occuper une place dans le ROB
            rob_i, cur_rob_entry = self.ROB.get_free_entry()
            cur_rob_entry.instr = cur_instruction
            cur_rob_entry.state = State.ISSUE

            #Occuper l'unité fonctionnelle
            cur_funit.occupy(cur_instruction.operation)

            # Vérifier les paramètres des opérations voir s'ils vont dans le vj/vk ou qj/qk
            if cur_instruction.funit == 'Store':
                to_check = [0, 1]
            elif cur_instruction.funit == 'Branch':
                if cur_instruction.action == '$2 = $1 if $0 == 0 else $2' \
                or cur_instruction.action == '$2 = $1 if $0 != 0 else $2':
                    to_check = [0]
                elif cur_instruction.action == '$3 = $2 if $0 == $1 else $3' \
                or cur_instruction.action == '$3 = $2 if $0 != $1 else $3':
                    to_check = [0, 1]
                else:
                    to_check = []
            else:
                to_check = [1, 2]

            # Trouver Vj/Vk ou Qj/Qk
            first_operand = True
            for i in to_check:
                if len(cur_instruction.operands) < i + 1:
                    continue
                param = cur_instruction.operands[i]

                # On résoud la référence
                temp = self.resolve_variables(param, False)

                # Est-ce que on a déjà la valeur? Si oui, on la met dans Vj/Vk, sinon, Qj/Qk
                value = '#'
                # Ne pas résoudre les accès mémoire en ce moment
                if memory_re.match(param) is not None:
                    uf = eval(temp.split('(', 1)[1].rstrip(' )'))
                else:
                    uf = eval(temp)

                numeric = False
                if isinstance(uf, str) and '#' in uf:
                    rob = list(zip(*self.ROB))[0]
                    if uf[1:] in rob and self.ROB[rob.index(uf[1:])][1] is not None:
                        numeric = True
                        numeric_val = eval(self.ROB[rob.index(uf[1:])][1][0])
                        if memory_re.match(param) is not None:
                            valeur = '%s(%s)' % (temp.split('(')[0], numeric_val)
                        else:
                            valeur = numeric_val

                if not numeric:
                    if memory_re.match(param) is not None:
                        valeur = '%s(%s)' % (temp.split('(')[0], uf)
                    else:
                        valeur = uf

                if first == True:
                    if isinstance(valeur, str) and '#' in valeur:
                        #Utiliser la valeur de format '&UNITE_FCT' plutôt
                        #que le numéro de registre directement
                        cur_funit['qj'] = valeur
                        cur_funit['vj'] = None
                    else:
                        cur_funit['qj'] = None
                        cur_funit['vj'] = valeur
                else:
                    if isinstance(valeur, str) and '&' in valeur:
                        cur_funit['qk'] = valeur
                        cur_funit['vk'] = None
                    else:
                        cur_funit['qk'] = None
                        cur_funit['vk'] = valeur
                first = False

            if cur_funit['qj'] == None and cur_funit['qk'] == None:
                # On part l'exécution
                # Exception pour l'unité fonctionnelle Mult
                if cur_funit['op'].funit == 'Mult':
                    if cur_funit['op'].action.find('*') > -1:
                        cur_funit['temps'] = func_unit_ref.temps_execution
                    else:
                        cur_funit['temps'] = func_unit_ref.temps_execution_division
                else:
                    cur_funit['temps'] = func_unit_ref.temps_execution

            # Trouver le paramètre de destination, qui est l'inverse des paramètres d'entrée (sauf pour le Branch)
            destination = [a for a in range(len(self.instructions[self.PC].operands)) if a not in to_check]
            # Si l'opération est une branch, aucune destination à analyser - C'est un label.
            # Si aucune destination trouvée, ie un Store ou  Branch, mettre à None
            destination = destination[0] if len(destination) > 0 and self.instructions[self.PC].funit != 'Branch' else None

            # Mettre une référence dans la destination, soit &Unite_name
            if destination is not None and destination is not []:
                #Utiliser une notation débutant à 1.
                destination_value = '&' + self.instructions[self.PC].funit + str(funit_idx + 1)
                self.registre[self.instructions[self.PC].operands[destination]] = destination_value

            # Passer à l'opération suivante s'il n'y a pas de branch qui s'est déjà effectué
            if self.instructions[self.PC].funit != 'Branch':
                self.new_pc = (self.PC + 1) if self.new_pc == None else self.new_pc
            else:
                # Gestion des branchs / Spéculation
                # Déterminer si le branchement des forward ou backward
                forward_branch = (int(self.instructions[self.PC].operands[-1][1:]) > int(self.PC))
                if (self.unite_fonctionnelle['Branch'].spec_forward and forward_branch) or (self.unite_fonctionnelle['Branch'].spec_backward and (forward_branch == False)):
                    # Spéculation forward or backward ENGAGED
                    self.new_pc = int(self.instructions[self.PC].operands[-1][1:])
                    self.ROB[-1].append(True)
                    self.ROB[-1].append(int(self.PC + 1))
                else:
                    self.new_pc = int(self.PC + 1)
                    self.ROB[-1].append(False)
                    self.ROB[-1].append(int(self.instructions[self.PC].operands[-1][1:]))
        else:
            # Aucune unité fonctionnelle libre trouvée, on est COINCÉS COMME DES RATS et on attend.
            self.new_pc = self.PC

    def find_funit(self, funits, name):
        '''
        Prend une liste d'unités fonctionnelles en entrée, cherche une unité qui est n'est pas
        occupée (variable busy à False).
        '''
        for i, funit in enumerate(funits):
            if funit.busy or funit.name in self.commit_now:
                continue
            elif len(list(filter(lambda e: e == str_unite, self.ROB))) == 0:
                return i
        return None


    def load_config(self, config_file):
        '''
        Initialise le simulateur en fonction de ce qui est défini dans le fichier XML
         de configuration.
        '''

        # Ouvrir le fichier XML
        try:
            print('Lecture du fichier de configuration %s en cours...' % config_file)
            xml_data = parse(config_file)
            print('Fichier de configuration lu avec succès.')
        except:
            raise Exception('Impossible d\'utiliser le fichier de configuration '
                'XML.')

        self.RS['Load'] = create_functional_units(xml_data, 'Load', 1, 1)
        self.RS['Store'] = create_functional_units(xml_data, 'Store', 1, 1)
        self.RS['Add'] = create_functional_units(xml_data, 'Add', 1, 1)
        self.RS['Mult'] = create_functional_units(xml_data, 'Mult', 1, 1,
         additional_defaults={'div_latency': 1})
        self.RS['ALU'] = create_functional_units(xml_data, 'ALU', 1, 1)
        self.RS['Branch'] = create_functional_units(xml_data, 'Branch', 1, 1,
         additional_defaults={'spec_forward': False, 'spec_backward': True})

        # Attribution des registres
        register_nodes = xml_data.getElementsByTagName('Registers')[0].childNodes
        register_nodes = zip(register_nodes[::2], register_nodes[1::2])
        for a in register_nodes:
            name = a[1].tagName
            value = a[1]._attrs['value'].value
            self.regs[name] = value
            #TODO JCL: Seemed useless.
            #self.registre[registre_name + 'T'] = registre_value

        # Attribution de la mémoire
        try:
            mem_init_values = xml_data.getElementsByTagName('Memory')[0].childNodes[0].data.strip().split()
        except:
            mem_init_values = []
        self.mem_size = int(xml_data.getElementsByTagName('Memory')[0]._attrs['size'].value)
        self.mem = [0.0] * self.mem_size
        for i, v in enumerate(mem_init_values):
            self.mem[i] = v


def create_functional_units(xml_data, name, default_n, default_latency, additional_defaults={}):
    '''
    Créé une liste d'unités fonctionnelles de type `name` et tente de charger une configuration
    pour ce type dans `xml_data`.
    '''

    fu_params = {}
    fu_params.update(additional_defaults)
    fu_params['name'] = name
    #Les paramètres par défaut vont être écrasés.
    fu_params['n'] = default_n
    fu_params['latency'] = default_latency

    try:
        elements = xml_data.getElementsByTagName(name)[0]
        for k, v in elements._attrs.items():
            fu_params(k, v.value)
    except:
        print('Aucune configuration trouvée pour les unités fonctionnelles de type %s.'
            % name)

    #Générer les unités fonctionnelles
    n = fu_params.pop('n')
    funits = [FuncUnit(**fu_params) for i in range(n)]
    return funits


if __name__ == '__main__':
    sys.stderr.write('Ce module n\'est pas utilisable seul.')
    sys.exit(-1)
