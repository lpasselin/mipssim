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

import os
import re

# Instruction Set: {'INSTR': ["Unite_fonctionnelle", "operation"]}
# $0 = premier argument, $1 = 2e argument, etc.
INSTRUCTION_SET = {'LD':    ["Load", "$0 = $1"],        # 0. Memory Read
                   'L.D':   ["Load", "$0 = $1"],
                   'SD':    ["Store", "$1 = $0"],       # 2. Memory Save
                   'S.D':   ["Store", "$1 = $0"],
                   'ADD.D': ["Add", "$0 = $1 + $2"],    # 4. Floating point operations
                   'SUB.D': ["Add", "$0 = $1 - $2"],
                   'MUL.D': ["Mult", "$0 = $1 * $2"],
                   'DIV.D': ["Mult", "$0 = $1 / $2"],
                   'DADD':  ["ALU", "$0 = $1 + $2"],    # 8. Integer operations
                   'DADDU': ["ALU", "$0 = $1 + $2"],
                   'DADDI': ["ALU", "$0 = $1 + $2"],
                   'DADDIU':["ALU", "$0 = $1 + $2"],
                   'DSUB':  ["ALU", "$0 = $1 - $2"],
                   'DSUBU': ["ALU", "$0 = $1 - $2"],
                   'DMUL':  ["ALU", "$0 = $1 * $2"],
                   'DMULU': ["ALU", "$0 = $1 * $2"],
                   'DDIV':  ["ALU", "$0 = $1 / $2"],
                   'DDIVU': ["ALU", "$0 = $1 / $2"],
                   'AND':   ["ALU", "$0 = $1 & $2"],
                   'BEQZ':  ["Branch", "$2 = $1 if $0 == 0 else $2"],      # 19. Branching operations
                   'BNEZ':  ["Branch", "$2 = $1 if $0 != 0 else $2"],
                   'BEQ':   ["Branch", "$3 = $2 if $0 == $1 else $3"],
                   'BNE':   ["Branch", "$3 = $2 if $0 != $1 else $3"],
                   'J':     ["Branch", "$1 = $0"]
                   }

# ##############################################
# CLasse d'interpétation de la source assembleur
# ##############################################

class mips_interpreteur:
    """
    Interpréteur de source assembleur du MIPS.

    Entrée: Source en assembleur MIPS 64 bits.
    Sortie: Une liste. Chaque élément de la liste est une ligne de code.
    
    Ces éléments sont des tuples de la forme suivante::
        (["Unite_fonctionnelle", "Operation_a_effectuer"], ["Param1", "Param2", ...])
        
    """
    def __init__(self, source_file=None):
        """
        Ouvre un fichier source assembleur de MIPS et en génère une 
        représentation utile au simulateur.
        """

        # Ouvrir le fichier source
        if source_file == None:
            raise Exception('Aucun fichier source en entrée.')
        source_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                   "..",
                                                   source_file)
                                      )
        try:
            print('Lecture du fichier source %s en cours...' % source_path)
            f = open(source_path, 'r')
            print('Fichier source lu avec succès')
            asm = f.readlines()
        except:
            raise Exception("Impossible d'utiliser le fichier source.")
        self.flow = self.parse_assembler(asm)

    def parse_assembler(self, in_source):
        """
        Convertis le code assembleur en mnémoniques représentés par 
        l'énumération au début du fichier.
        """
        if type(in_source) != list:
            raise Exception('Source non-valide.')

        # Gestion des labels. Après cette opération, les labels sont
        # enlevés de la source
        source = in_source
        source = self.parse_labels(source)
        
        # Mapping des opérations dans la table en haut du fichier.
        # Retourne une liste de tuple [(instruction_reference, parametres), ...]
        source = self.parse_instructions(source)

        # Conversion des paramètres en liste.
        source = self.parse_parameters(source)

        return source

    def parse_labels(self, in_source):
        """
        Cherche les labels dans le code et les assigne au dictionnaire labels de
        la classe sous la forme :
        labels['nom_du_label'] = numero_de_l'operation
        ou
        {'nom_du_label': numero_de_l'operation, 'nom_du_label_2': numero_de_l'operation_2}
        """
        # Sectionnement de la source à la première césure de chaque ligne sous
        # forme de tokens
        # ie. [['Loop:', 'L.D    F0,0(R1)'], ['ADD.D', 'F4,F0,F2'], ['S.D', 'F4,0(R1)'], ['DADDIU', 'R1,R1,#-8'], ['BNE', 'R1,R2,Loop']]
        source = [[token.strip() for token in ligne.split(None, 1)] for ligne in in_source]
        
        # Population du dictionnaire des labels
        for index, operation in enumerate(source):
            # Trouver un label
            if operation[0][-1] == ':':
                # Assigner dans le dictionnaire des labels la ligne à laquel
                # ce label est.
                self.labels[operation[0][:-1]] = index


        # Effacement des labels dans le source
        for index in self.labels.values():
            source[index] = source[index][1:]

        # Retour à une forme solide et opaque des lignes
        # ie. ['L.D    F0,0(R1)', 'ADD.D F4,F0,F2', 'S.D F4,0(R1)', 'DADDIU R1,R1,#-8', 'BNE R1,R2,Loop']
        return [" ".join(a) for a in source]

    def parse_instructions(self, in_source):
        """
        Convertis une source composée des lignes de codes, labels exclus, en 
        une liste de tuples représentant l'instruction puis ses paramètres opaques.
        ie. [(instruction_number, parameters), ...]
        """
        # Sectionnement de la source à la première césure de chaque ligne sous forme de tokens
        # ie. [['L.D', 'F0,0(R1)'], ['ADD.D', 'F4,F0,F2'], ['S.D', 'F4,0(R1)'], ['DADDIU', 'R1,R1,#-8'], ['BNE', 'R1,R2,Loop']]
        source = [[token.strip() for token in ligne.split(None, 1)] for ligne in in_source]

        # Génère une liste de tuples contenant dans sa première valeur la référence à 
        # l'instruction en haut du fichier et en deuxième valeur ses paramètres.
        # une instruction '-1' est attribuée à une instruction inconnue
        # ie. [(1, 'F0,0(R1)'), (4, 'F4,F0,F2'), (3, 'F4,0(R1)'), (11, 'R1,R1,#-8'), (22, 'R1,R2,Loop')]
        source = [(INSTRUCTION_SET.setdefault(ligne[0].upper(), [None, ligne[0]]), ligne[1]) for ligne in source]
        return source

    def parse_parameters(self, in_source):
        """
        Segmente les paramètres des opérations en une liste d'éléments au sein 
        de la liste de tuples retourné par la fonction parse_instructions.
        """
        # Sectionnement du deuxième élément du tuple (paramètres) selon les virgules.
        # ie. [(1, ['F0', '0(R1)']), (4, ['F4', 'F0', 'F2']), (3, ['F4', '0(R1)']), (11, ['R1', 'R1', '#-8']), (22, ['R1', 'R2', 'Loop'])]
        source = [(ligne[0], [token.strip() for token in ligne[1].split(',')]) for ligne in in_source]

        # Remplacement des labels par les # de ligne. [ format #CHIFFRE pour simplifier l'évaluation ]
        for line_num, line in enumerate(source):
            elems = []
            for b in line[1]:
                elems += ["#"+str(self.labels[b])] if b in self.labels.keys() else [b]
            source[line_num] = (line[0], elems)
            
        return source

    def __repr__(self):
        return str(self.flow)

    def __len__(self):
        """
        Calcule le nombre de d'opérations dans la source, soit le nombre de 
        lignes d'assembleur.
        """
        return len(self.flow)
                
    
    flow = []
    labels = {}

begin_memory_re = re.compile('^-*\d+\(')
memory_re = re.compile('^-*\d+\([RF][-]?\d+[.]?\d*\)$')
#memory_re_double_reg = re.compile('^-*[RF][-]?\d+[.]?\d*\([RF][-]?\d+[.]?\d*\)$')
memory_re_direct = re.compile('^-*\d+\([-]?\d+[.]?\d*\)$')
registry_re = re.compile('([RF]\d{1,2})')

if __name__ == '__main__':
    import sys
    sys.stderr.write("Ce module n'est pas utilisable seul.")
    sys.exit(-1)