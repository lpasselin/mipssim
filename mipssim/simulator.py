# -*- coding: utf-8 -*-

# Copyright (c) 2011, Yannick Hold-Geoffroy and Julien-Charles Lévesque on behalf of Université Laval
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
#    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#    Neither the name of the Université Laval nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
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
from interpreter import memory_re
import components
from components import State


class Simulator:
    '''
    Simulateur d'exécution du MIPS.

    Prends le code retourné par l'interpreteur et le fais exécuter sur la
    configuration entrée.
    '''
    def __init__(self, config_file, source_file, trace_file='', trace_mode='t', debug=False):
        #Initialisation des variables membres
        self.horloge = 0
        self.stall = False
        self.new_PC = None
        self.ROB = components.ROB(maxlen=24)
        self.PC = 0
        self.RS = OrderedDict()

        self.debug = debug

        #Initialisation des registres
        self.regs = components.Registers()

        #Lecture de la configuration et du code source à exécuter
        self.load_config(config_file)
        self.instructions = interp.interpret_asm(source_file)

        #Setup du fichier de trace si applicable
        if trace_file != '':
            if trace_mode =='t':
                self.trace = trace.TextTrace(trace_file)
            elif trace_mode == 'l':
                self.trace = trace.LaTeXTrace(trace_file)
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

        * Retourne 0 si l'opération s'est déroulée avec succès et l'exécution
        n'est pas terminée.
        * Retourne 1 si l'opération s'est déroulée avec succès et l'exécution
        est terminée

        Une exception est levée si l'exécution ne s'est pas déroulée avec succès.
        '''
        if self.debug:
            print('Coup d\'horloge - PC = %s - Stall = %s' % (
                str(self.PC), str(self.stall)))

        #Les opérations sont inversées pour éviter d'accomplir plusieurs actions sur une même
        # instruction dans un seul coup d'horloge.
        
        #On sanctionne l'instruction via le ROB ( Premier élément de celui-ci )
        self.commit_instr()

        #Décrémentation du temps sur les unités fonctionnelles
        self.decrement_time()

        # Gestion des bulles et de la fin du programme
        if self.stall == True or self.PC + 1 > len(self.instructions):
            print('Aucune instruction lancée.')
        else:
            self.issue_instr()

        #Avancement du Issue/Program Counter (PC)
        if self.new_PC != None:
            self.PC = self.new_PC
        self.new_PC = None

        #Si l'exécution est terminée et le ROB est vide
        if self.PC >= len(self.instructions) and len(self.ROB) == 0:
            return 1
        else:
            if self.trace:
                self.trace.update(self)
            return 0

    def commit_instr(self):
        '''
        Sanctionne les opérations dont le calcul est terminé dans l'ordre de lancement.
        Seule l'instruction à la tête du ROB peut être sanctionnée.
        '''
        rob_idx = self.ROB.start
        rob_head = self.ROB[rob_idx]
        if len(self.ROB) > 0 and rob_head.state == State.WRITE and rob_head.ready:
            cur_rob_entry = self.ROB[rob_idx]
            if self.debug:
                print('Sanctionnement: %s' % cur_rob_entry)
            
            if cur_rob_entry.dest != None:
                self.regs[cur_rob_entry.dest] = cur_rob_entry.value
                #Si cette instruction était la seule (ou la dernière) à devoir écrire dans le ROB,
                #effacer le marqueur à cet effet dans regs.stat
                if self.regs.stat[cur_rob_entry.dest] != None:
                     dest_i = self.regs.stat[cur_rob_entry.dest]
                     if dest_i == rob_idx:
                         self.regs.stat[cur_rob_entry.dest] = None

            # Gestion des branchs lors du sanctionnement
            if rob_head.instr.funit == 'Branch':
                if (rob_head.prediction != rob_head.value):
                    # Mauvaise spéculation
                    #Si il y avait un blocage, il disparaît car on flush le ROB et les RS
                    self.stall = False
                    if rob_head.value:
                        #On force la prise de ce branchement, on modifie directement le PC
                        self.PC = int(rob_head.instr.operands[-1][1:])
                    else:
                        #On retourne à l'instruction suivant le branchement
                        self.PC = rob_head.instr.addr + 1
                    
                    self.new_PC = None
                    
                    #Flush le ROB
                    self.ROB.reset()
    
                    #Remet les drapeaux d'écriture des registres à None
                    self.regs.reset_stat()

                    #Clean les stations de réservation
                    self.reset_funits()
                else:
                    # Spéculation réussite, aucun changement requis.
                    self.new_PC = None
            elif rob_head.instr.funit == 'Store':
                #On écrit le résultat en mémoire.
                self.mem[rob_head.addr] = rob_head.value

            # Une fois l'instruction sanctionnée, la retirer du ROB
            self.ROB.free_head_entry()

            self.new_PC = (self.PC + 1) if self.new_PC == None else self.new_PC

    def exec_instr(self, func_unit, rob_entry):
        '''
        Termine l'exécution de l'instruction dans ´func_unit´, place les résultas aux bons
         endroits.
        '''
        instr = rob_entry.instr
        
        if func_unit.name[:-1] == 'Branch':
            #Déterminer si le branchement est pris.
            branch = False
            if instr.code == 'BEQ':
                if func_unit.vj == func_unit.vk:
                    branch = True
            elif instr.code == 'BNE':
                if func_unit.vj != func_unit.vk:
                    branch = True
            elif instr.code == 'BEQZ':
                if func_unit.vk == 0:
                    branch = True
            elif instr.code == 'BNEZ':
                if func_unit.vj != 0:
                    branch = True
            elif instr.code == 'J':
                branch = True
            else:
                raise Exception('Instruction de branchement inconnue.')
            #On place le comportement final du branchement dans le ROB.
            rob_entry.value = branch
            
        elif func_unit.name[:-1] == 'Store':
            #Store pas exécuté à cette étape, mais on connaît maintenant sa destination.
            rob_entry.addr = func_unit.vk + func_unit.A #ne respecte pas la nomenclature Hennessy.
        elif func_unit.name[:-1] == 'Load':
            #Le load ne peut pas s'exécuter tant qu'il y a un store le précédent dans le ROB,
            #donc rendu ici aucun problème.
            rob_entry.value = self.mem[func_unit.A]
        else:
            if instr.operator == '+':
                value = func_unit.vj + func_unit.vk
            elif instr.operator == '-':
                value = func_unit.vj - func_unit.vk
            elif instr.operator == '/':
                value = func_unit.vj / func_unit.vk
            elif instr.operator == '*':
                value = func_unit.vj * func_unit.vk
            elif instr.operator == '&':
                value = func_unit.vj & func_unit.vk
            else:
                raise Exception('Invalid operator.')
            rob_entry.value = value

        rob_entry.state = State.EXECUTE
        return

    def resolve_operand(self, operand):
        '''
        Permet de transformer les variables du code MIPS en variables Python.
        '''
        
        if operand[0] == '#':
            value = int(operand[1:])
            rob_i = None
        elif operand[0] in ['R', 'F']:
            #si rob_i != None, la valeur dans value doit être invalidée, car on ne peut l'utiliser
            rob_i = self.regs.stat[operand]
            value = self.regs[operand]
            if rob_i != None:
                rob_i = rob_i
                value = None
        else:
            raise Exception('Opérande invalide.')
        
        return value, rob_i
        
    def resolve_memory_operand(self, operand):
        mem_reg_value = 0
        
        reg_name = operand.split('(')[1].split(')')[0]
        mem_adr_value, rob_i = self.resolve_operand(reg_name)
        
        #décalage immédiat de l'adresse: IMM(RX)
        mem_imm = int(operand.split('(')[0])
        
        return mem_imm, mem_adr_value, rob_i

    def reset_funits(self):
        for _, funit_type in self.RS.items():
            # Prendre une référence sur l'unité fonctionnelle qu'on analyse
            for funit in funit_type:
                funit.reset()

    def decrement_time(self):
        '''
        Effectue un coup d'horloge, soit décrémente de un le temps restant de chaque unité
         fonctionnelle qui travaille en ce moment.

        Démarre les unités fonctionelles qui attendaient des données maintenant disponibles.
        '''
        #Variable temporaire pour savoir si nous avons mis à jour une UF.
        updated = [[False] * len(funit) for _, funit in self.RS.items()]

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
                            #Le load se fait en deux étapes (voir p. 233 Hennesssy, Execute)
                            if funit.name[:-1] == 'Load' and funit.vj is not None:
                                #Il ne doit pas y avoir de store précédant le load dans le ROB
                                store = False
                                for e in self.ROB:
                                    #Arrivé à l'instruction courante, cesse de parcourir le ROB
                                    if e.i == funit.dest:
                                        break
                                    if e.instr.funit == 'Store':
                                        store = True
                                if not store:
                                    funit.A = funit.vj + funit.A
                                    funit.vj = None
                                else:
                                    #Sinon il faut attendre pour commencer le Load
                                    continue

                            #Calcule le résultat
                            exec_rob_entry = self.ROB[funit.dest]
                            self.exec_instr(funit, exec_rob_entry)

                            # Writeback Tomasulo, écriture de l'instruction sur le CDB et mise à
                            # jour des stations de réservation
                            self.writeback_tomasulo(funit, funit.dest, exec_rob_entry.value)
                            
                            # Reset de l'unité fonctionnelle
                            funit.reset()
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
                            if funit.instr.action.find('*') > -1:
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
            
            if self.debug:
                print('Lance l\'instruction :', cur_instruction)

            #Occuper une place dans le ROB
            cur_rob_i, cur_rob_entry = self.ROB.get_free_entry()
            cur_rob_entry.instr = cur_instruction
            cur_rob_entry.state = State.ISSUE
            cur_rob_entry.ready = False

            #Occuper l'unité fonctionnelle
            cur_funit.occupy(cur_instruction)

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
                raw_operand = cur_instruction.operands[i]
                if self.debug:
                    print('Traite l\'opérande ', raw_operand)

                # Est-ce qu'on a déjà la valeur? Si oui, on la met dans Vj/Vk, sinon, Qj/Qk
                # Ne pas résoudre les accès mémoire en ce moment
                memory_operand = memory_re.match(raw_operand) is not None
                if memory_operand:
                    mem_imm, value, rob_i = self.resolve_memory_operand(raw_operand)
                    cur_funit.A = mem_imm
                else:
                    value, rob_i = self.resolve_operand(raw_operand)
                    
                #Si nous n'avons pas encore la valeur de cette opérande
                if rob_i is not None:
                    waiting_op_rob = self.ROB[rob_i]
                    #Si cette instruction avait terminé de s'exécuter, on peut
                    #prendre son résultat
                    if waiting_op_rob.state == State.WRITE or waiting_op_rob.state == State.COMMIT:
                        value = waiting_op_rob.value
                        value_ready = True
                    #Sinon on place un pointeur vers le ROB.
                    else:
                        value = rob_i
                        value_ready = False
                #Sinon value contiendra une donnée valide et prête à utiliser.
                else:
                    value_ready = True
                
                if first_operand:
                    if value_ready:
                        cur_funit.vj = value
                    else:
                        #Utiliser la valeur de format '#ROB' plutôt
                        #que le numéro de registre directement
                        cur_funit.qj = value
                else:
                    if value_ready:
                        cur_funit.vk = value
                    else:
                        #Utiliser la valeur de format '#ROB' plutôt
                        #que le numéro de registre directement
                        cur_funit.qk = value
                first_operand = False
            
            if cur_funit.qj == None and cur_funit.qk == None:
                # On part l'exécution
                # Exception pour l'unité fonctionnelle Mult
                if cur_instruction.funit == 'Mult':
                    if cur_instruction.action.find('*') > -1:
                        cur_funit.time = cur_funit.latency
                    else:
                        cur_funit.time = cur_funit.div_latency
                else:
                    cur_funit.time = cur_funit.latency

            # Trouver le paramètre de destination, qui est l'inverse des paramètres d'entrée (sauf pour le Branch)
            destination = [a for a in range(len(self.instructions[self.PC].operands)) if a not in to_check]
            # Si l'opération est un branch, aucune destination à analyser - c'est un label.
            # Si aucune destination trouvée, i.e. un Store ou  Branch, mettre à None
            if len(destination) > 0 and self.instructions[self.PC].funit != 'Branch':
                destination = destination[0]
            else:
                destination = None


            # Mettre une référence dans la destination, soit #ROB
            if destination is not None:
                cur_rob_entry.dest = self.instructions[self.PC].operands[destination]
                #Indiquer que le registre attend une valeur de `cur_rob_i`
                self.regs.stat[self.instructions[self.PC].operands[destination]] = cur_rob_i

            #La destination pour l'UF est toujours l'entrée ROB correspondante.
            cur_funit.dest = cur_rob_i

            if self.debug:
                print('Debug: cur_rob_entry: ', cur_rob_entry)
                print('Debug: cur_funit: ', cur_funit)

            # Passer à l'opération suivante s'il n'y a pas de branch qui s'est déjà effectué
            if self.instructions[self.PC].funit != 'Branch':
                self.new_PC = (self.PC + 1) if self.new_PC == None else self.new_PC
            else:
                # Gestion des branchs / Spéculation
                # adresse du branchement
                cur_funit.A = int(self.instructions[self.PC].operands[-1][1:])
                
                # Vrai si le branch va vers l'avant
                forward_branch = cur_funit.A > int(self.PC)
                
                if (self.RS['Branch'][0].spec_forward == 'taken' and forward_branch)\
                  or (self.RS['Branch'][0].spec_backward == 'taken' and not forward_branch):
                    #Prédiction d'un branchement pris.
                    cur_rob_entry.prediction = True #Hennessy ne spécifie pas où placer la prédiction
                    self.new_PC = cur_funit.A
                else:
                    #Prédiction d'un branchement non pris.
                    cur_rob_entry.prediction = False
                    self.new_PC = int(self.PC + 1)

        else:
            # Aucune unité fonctionnelle libre trouvée ou bien plus de place dans le ROB
            # On est coincés comme des rats, on attend.
            self.new_PC = self.PC

    def writeback_tomasulo(self, wb_funit, wb_rob_entry_idx, value=None):
        '''
        Une fois l'exécution d'une instruction terminée, il est possible de placer sa valeur 
         sur le CDB et donc de mettre à jour les unités fonctionnelles attendant cette valeur.
        '''
        rob_entry = self.ROB[wb_rob_entry_idx]
        #Le Store procède différemment
        if wb_funit.name[:-1] == 'Store':
            if wb_funit.qj == None: #Différent de la convention d'Hennessy... pas dramatique.
                rob_entry.value = wb_funit.vj
            else:
                raise Exception('Not sure we should get there.')
        else:
            for _, funit_type in self.RS.items():
                for funit in funit_type:
                    #Mise à jour requise uniquement lorsque l'unité est occupée
                    # et attend après ses paramètres.
                    if funit.busy and funit.time == None:
                        if funit.qj is not None and funit.qj == wb_rob_entry_idx:
                            funit.vj = value
                            funit.qj = None
                        if funit.qk is not None and funit.qk == wb_rob_entry_idx:
                            funit.vk = value
                            funit.qk = None
            rob_entry.value = value

        #Writeback complété
        rob_entry.ready = True
        rob_entry.state = State.WRITE
        #Libère l'unité fonctionnelle
        wb_funit.reset()

    def find_funit(self, funits, name):
        '''
        Prend une liste d'unités fonctionnelles en entrée, cherche une unité qui est n'est pas
        occupée (variable busy à False).
        '''
        for i, funit in enumerate(funits):
            if funit.busy:
                continue
            #TODO JCL: S'assurer que l'unité fonctionnelle n'est plus impliquée dans le ROB
            return i
        return -1


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
         additional_defaults={'spec_forward': 'not_taken', 'spec_backward': 'taken'})

        # Attribution des registres
        register_nodes = xml_data.getElementsByTagName('Registers')[0].childNodes
        register_nodes = zip(register_nodes[::2], register_nodes[1::2])
        for a in register_nodes:
            name = a[1].tagName
            value = a[1]._attrs['value'].value
            self.regs[name] = value

        # Attribution de la mémoire
        try:
            mem_init_values = xml_data.getElementsByTagName('Memory')[0].childNodes[0].data.strip().split()
        except:
            mem_init_values = []
        mem_size = int(xml_data.getElementsByTagName('Memory')[0]._attrs['size'].value)
        self.mem = components.Memory(mem_size, mem_init_values)

def update_operands(funit, rob_entry):
    '''
    Remplace les opérandes dans qk et/ou qj avec les valeurs nouvellement calculées.
    '''
    if funit.qj == rob_entry.i:
        funit.vj = rob_entry.value
        funit.qj = None
    if funit.qk == rob_entry.i:
        funit.vk = rob_entry.value
        funit.qk = None


def create_functional_units(xml_data, name, default_n, default_latency, additional_defaults={}):
    '''
    Créé une liste d'unités fonctionnelles de type `name` et tente de charger une configuration
    pour ce type dans `xml_data`.
    '''

    fu_params = {}
    fu_params.update(additional_defaults)
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
    funits = [components.FuncUnit(name='%s%i'%(name, i+1), **fu_params) for i in range(n)]
    return funits


if __name__ == '__main__':
    sys.stderr.write('Ce module n\'est pas utilisable seul.')
    sys.exit(-1)