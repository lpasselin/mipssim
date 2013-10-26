#!/usr/bin/env python3
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
'''

'''

import argparse
import sys
if sys.version_info < (2, 7):
    print('ATTENTION!!!')
    print('Vous tentez de lancer mipssim.py sur une version de Python inférieure à 2.7!')
    print('Python 2.6 et ses versions antérieures ne supportent pas OrderedDict, qui')
    print('est requise pour ce simulateur.')
    sys.exit(1)

import interpreter as interp
import simulator as sim

auteurs = ''

def main(config_file, source_file, trace_file, debug):
    # Génération du simulateur
    simulator = sim.Simulator(config_file, source_file, trace_file, debug=debug)

    # Affichage de l'état initial de la mémoire et des registre.
    print('État initial des registres: ' + str(simulator.regs))
    print('État initial de la mémoire: ' + str(simulator.mem))

    # Démarrage du simulateur
    print('Démarrage de la simulation.')
    err = simulator.go()
    print('Arrêt de la simulation.')

    # Affichage de l'état final de la mémoire et des registre.
    print('État final des registres : ' + str(simulator.regs))
    print('État final de la mémoire : ' + str(simulator.mem))

    # Affichage de l'état du processus à sa terminaison.
    if err == 0:
        print('Simulation terminée avec succès.')
    else:
        print('Une erreur est survenue lors de l\'exécution du programme.')
    return err

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simulateur de MIPS en Python (2.7+). Testé avec Python 2.7 et 3.3.')

    parser.add_argument('config_file', help='Fichier xml contenant la configuration du simulateur.')
    parser.add_argument('source_file', help='Fichier contenant le code source à exécuter.')
    parser.add_argument('trace_file', nargs='?', default='', help='Ficher dans lequel sera écrit l\'état du simulateur à tous les pas de temps.')
    parser.add_argument('-t', default='t', dest='text_trace', help="Sauvegarde l'état du simulateur à chaque coup d'horloge dans un fichier texte." )
    parser.add_argument('-d', default=False, action='store_true', dest='debug', help="Force l'impression de davantage d'information à chaque étape de l'exécution dans la ligne de commande.")

    args = parser.parse_args()

    sys.exit(main(args.config_file, args.source_file, args.trace_file, args.debug))
