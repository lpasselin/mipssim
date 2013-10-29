# -*- coding: utf-8 -*-
#
# Copyright (c) 2011-2013, Julien-Charles Lévesque <levesque.jc@gmail.com>
#  and contributors.
#
# Distributed under the terms of the MIT license. See the COPYING file at
#  the top-level directory of this project and at
#  https://bitbucket.org/levesque/mipssim/raw/tip/COPYING

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
        self.trace_f.write('Cycle: %d\n' % simulator.clock)
        self.trace_f.write('Program Counter : %d\n' % simulator.PC)
        self.trace_f.write('Stations de réservation:\n%s\n' % str(rs_table))
        self.trace_f.write('Registres: \n%s\n' % str(reg_table))
        self.trace_f.write('ROB: \n%s\n' % (rob_table))


        self.trace_f.flush()




class LaTeXTrace:
    pass





