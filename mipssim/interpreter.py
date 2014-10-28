# -*- coding: utf-8 -*-
#
# Copyright (c) 2011-2013, Julien-Charles Lévesque <levesque.jc@gmail.com>
#  and contributors.
#
# Distributed under the terms of the MIT license. See the COPYING file at
#  the top-level directory of this project and at
#  https://bitbucket.org/levesque/mipssim/raw/tip/COPYING

import os
import re

#local imports
from components import Instruction

DIRECTIVE_SET = {}

# Instruction Set: {'INSTR': ['Unite_fonctionnelle', 'action', 'operator']}
# $0 = premier argument, $1 = 2e argument, etc.
INSTRUCTION_SET = {'LD':     ('Load', '$0 = $1'),        # 0. Memory Read
                   'L.D':    ('Load', '$0 = $1'),
                   'LW':     ('Load', '$0 = $1'),
                   'SD':     ('Store', '$1 = $0'),       # 2. Memory Save
                   'S.D':    ('Store', '$1 = $0'),
                   'SW':     ('Store', '$1 = $0'),
                   'MOVE':   ('Move', '$0 = $1'),
                   'ADD.D':  ('Add', '$0 = $1 + $2', '+'),    # 4. Floating point operations
                   'SUB.D':  ('Add', '$0 = $1 - $2', '-'),
                   'MUL.D':  ('Mult', '$0 = $1 * $2', '*'),
                   'DIV.D':  ('Mult', '$0 = $1 / $2', '/'),
                   'DADD':   ('ALU', '$0 = $1 + $2', '+'),    # 8. Integer operations
                   'DADDU':  ('ALU', '$0 = $1 + $2', '+'),
                   'DADDI':  ('ALU', '$0 = $1 + $2', '+'),
                   'DADDIU': ('ALU', '$0 = $1 + $2', '+'),
                   'ADDIU':  ('ALU', '$0 = $1 + $2', '+'),
                   'DSUB':   ('ALU', '$0 = $1 - $2', '-'),
                   'DSUBU':  ('ALU', '$0 = $1 - $2', '-'),
                   'DMUL':   ('ALU', '$0 = $1 * $2', '*'),
                   'DMULU':  ('ALU', '$0 = $1 * $2', '*'),
                   'DDIV':   ('ALU', '$0 = $1 / $2', '/'),
                   'DDIVU':  ('ALU', '$0 = $1 / $2', '/'),
                   'AND':    ('ALU', '$0 = $1 & $2', '&'),
                   'BEQZ':   ('Branch', '$2 = $1 if $0 == 0 else $2'),      # 19. Branching operations
                   'BNEZ':   ('Branch', '$2 = $1 if $0 != 0 else $2'),
                   'BEQ':    ('Branch', '$3 = $2 if $0 == $1 else $3'),
                   'BNE':    ('Branch', '$3 = $2 if $0 != $1 else $3'),
                   'J':      ('Branch', '$1 = $0'),
                   'NOP':    ('Nop', '')
                   }

memory_re = re.compile('^-?\d+\(\$')

def interpret_asm(simulator, source_file):
    '''
    Interpréteur de source assembleur du MIPS.

    Entrée: Source en assembleur MIPS 64 bits.
    Sortie: Une liste. Chaque élément de la liste est une ligne de code.

    Ces éléments sont des tuples de la forme suivante:
        (['Unite_fonctionnelle', 'Operation_a_effectuer'], ['Param1', 'Param2', ...])

    '''
    print('Lecture du fichier source %s en cours...' % source_file)
    f = open(source_file, 'r')
    source = f.readlines()
    print('Fichier source lu avec succès!')

    # Retrait des caractères de fin de ligne et des commentaires
    # ; et # sont considérés comme des commentaires
    source = [s.strip().split(';')[0].split('#')[0] for s in source]
    source = [s for s in source if len(s) != 0]

    # Gestion des labels. Après cette opération, les labels sont
    # enlevés de la source
    source, labels = parse_labels(source)
    print(source)

    # Mapping des opérations dans la table en haut du fichier.
    # Retourne une liste de tuple [(instruction_reference, parametres), ...]
    source = parse_instructions(simulator, source, labels)
    print(source)

    return source


def parse_labels(source):
    '''
    Cherche les labels dans le code et les assigne au dictionnaire labels de
    la classe sous la forme :
    labels['nom_du_label'] = numero_de_l'operation
    ou
      {'nom_du_label': numero_de_l'operation,
       'nom_du_label_2': numero_de_l'operation_2}
    '''
    # Sectionnement de chaque ligne sous forme de tokens au premier espace
    # ie. [['Loop:', 'L.D    F0,0(R1)'], ['ADD.D', 'F4,F0,F2'], ['S.D', 'F4,0(R1)'], ['DADDIU', 'R1,R1,#-8'], ['BNE', 'R1,R2,Loop']]
    source = [[token.strip() for token in ligne.split(None, 1)] for ligne in source]
    labels = {}

    # Population du dictionnaire des labels
    for index, operation in enumerate(source):
        # Trouver un label, enlever le cas spécial des strings
        if operation[0][-1] == ':' and len(operation) == 1:
            # Assigner dans le dictionnaire des labels la ligne à laquel
            # ce label est.
            labels[operation[0][:-1]] = index

    # Effacement des labels dans le source
    for index in labels.values():
        source[index] = source[index][1:]

    # Retour à une forme solide et opaque des lignes
    # ie. ['L.D    F0,0(R1)', 'ADD.D F4,F0,F2', 'S.D F4,0(R1)', 'DADDIU R1,R1,#-8', 'BNE R1,R2,Loop']
    return [' '.join(a) for a in source], labels


def parse_instructions(simulator, source, labels):
    '''
    Convertis une source composée des lignes de codes, labels exclus, en
    une liste de tuples représentant l'instruction puis ses paramètres opaques.

    Chaque instruction est un namedtuple défini tel que suit :
        Instruction(UNITE_FCN, ACTION/OPERATION, OPERANDES)

    Ex:
    instructions = [
    #instruction #1
    Instruction(funit='Load', action='$0 = $1', operands=['F0', '0(R1)']),
    #instruction #2.
    Instruction(funit='Add', action='$0 = $1 + $2', operands=['F4', 'F0', 'F2']),
    ... etc.
    ]
    '''
    instructions = []

    # Remplacement des labels par les # de ligne. [ format #CHIFFRE pour simplifier l'évaluation ]
    instr_num = 0
    for line_num, line in enumerate(source):
        if line == '':
            continue

        elems = line.split()
        operation = elems[0].upper()

        #Si la ligne débute par un ., il s'agit d'une directive, on peut la
        # traiter maintenant.
        if line[0] == '.':
            #directive = DIRECTIVE_SET[operation]
            #ignore directives for now, ouch.
            pass
        else:
            instr = INSTRUCTION_SET[operation]

            if len(elems) > 1:
                operands = elems[1].split(',')
                operator = None
                if len(instr) > 2:
                    operator = instr[2]

                #Remplace les labels par des # de ligne.
                for i, o in enumerate(operands):
                    if o in labels.keys():
                        operands[i] = '#' + str(labels[o])

                instructions.append(Instruction(line_num, operation, instr[0], instr[1], operands, operator))
            else:
                instructions.append(Instruction(line_num, operation, instr[0], instr[1], [], None))
            instr_num += 1

    return instructions


if __name__ == '__main__':
    import sys
    sys.stderr.write('Ce module n\'est pas utilisable seul.')
    sys.exit(-1)
