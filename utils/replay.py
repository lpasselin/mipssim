#!/usr/bin/env python
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

def main(argv=None):
    """
    Permet d'afficher une trace par coup l'horloge.
    """
    argv = sys.argv if argv == None else argv
    try:
        # Buffer file in input
        fichier = open(argv[1], 'r')
        le_fichier = fichier.readlines()
        fichier.close()
        index = 1
        last_screen = 1
        while True:
            if index > len(le_fichier):
                break
            ligne = le_fichier[index]
            print(ligne)
            if ligne.strip()[:3] == '===':
                cmd = input().strip()
                if cmd.lower() == 'a':
                    for buffer_index in range(last_screen - 1, -1, -1):
                        if le_fichier[buffer_index][:3] == '===':
                            print(buffer_index)
                            index = buffer_index
                            break
                last_screen = index
            index += 1
        return 0
    except:
        print("Veuillez spécifier un fichier valide en argument")
        print("Entrez \"a\" pour revenir en arrière de 1 cycle.")
        return 2

if __name__ == "__main__":
    sys.exit(main())