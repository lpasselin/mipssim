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

import os

from output.prettytable import PrettyTable
from interpreter import INSTRUCTION_SET, memory_re

noneify = lambda x: x if x != None else ''

def get_vars_and_subvars(var_names, extractee):
    row = []
    for v in var_names:
        if '.' in v:
            temp = extractee.__getattribute__(v.split('.')[0])
            try:
                elem = temp.__getattribute__(v.split('.')[1])
            except:
                elem = None
        else:
            elem = extractee.__getattribute__(v)
        elem = str(noneify(elem))
        row.append(elem)
    return row

class TextTrace:
    '''
    Laisse une trace dans un fichier texte.
    '''
    def __init__(self, trace_file):
        self.trace_f = open(trace_file, 'w')
        self.horloge = 0

    def __del__(self):
        self.trace_f.close()

    def update(self, simulator):
        '''
        Écrit l'état du ROB, des stations de reservation (des unités fonctionnelles) et de la
         mémoire le fichier `self.trace_f` à chaque itération. 
        '''
        #Tampon de réordonnancement
        rob_variables = ['i', 'instr.code', 'instr.operands', 'state', 'dest', 'value']
        rob_labels = ['Entrée', 'Instruction', '', 'État', 'Dest.', 'Valeur']
        rob_table = PrettyTable(rob_labels)
        for rob_entry in simulator.ROB:
            row = get_vars_and_subvars(rob_variables, rob_entry)
            rob_table.add_row(row)
        
        #Table des stations de réservation
        rs_variables = ['name', 'instr.code', 'vj', 'vk', 'qj', 'qk', 'dest', 'A']
        rs_labels = ['Station', 'Op', 'Vj', 'Vk', 'Qj', 'Qk', 'Dest', 'A']
        rs_table = PrettyTable(rs_labels)
        for station_type, funits in simulator.RS.items():
            for i, funit in enumerate(funits):
                row = get_vars_and_subvars(rs_variables, funit)
                rs_table.add_row(row)

        # Table des registres
        num_regs = int(len(simulator.regs) / 2)
        reg_table = PrettyTable([' '] + [str(a) for a in range(10)])
        for reg_type in ['R', 'F']:
            for row_start in range(0, num_regs, 10):
                remainder = num_regs - row_start
                if remainder < 10:
                    padding = ['X'] * (10 - remainder)
                    row_end = row_start + remainder
                else:
                    padding = []
                    row_end = row_start + 10
                reg_stat_row = ['ROB#'] + [noneify(simulator.regs.stat[reg_type + str(a)])
                    for a in range(row_start, row_end)] + padding
                reg_table.add_row(reg_stat_row)
                
                reg_value_row = [reg_type + str(row_start)] +\
                    [simulator.regs[reg_type + str(a)] for a in range(row_start, row_end)] +\
                    padding
                reg_table.add_row(reg_value_row)
                
        # Affichage des tableaux précédemment créés
        self.trace_f.write('%s\n' % ('=' * 80))
        self.trace_f.write('Cycle: %d\n' % simulator.horloge)
        self.trace_f.write('Program Counter : %d\n' % simulator.PC)
        self.trace_f.write('Stations de réservation:\n%s\n' % str(rs_table))
        self.trace_f.write('Registres: \n%s\n' % str(reg_table))
        self.trace_f.write('ROB: \n%s\n' % (rob_table))


        self.trace_f.flush()




class LaTeXTrace:
    pass





