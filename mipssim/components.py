# -*- coding: utf-8 -*-
# Copyright (c) 2013, Julien-Charles Lévesque on behalf of Université Laval
# All rights reserved.

from collections import OrderedDict, namedtuple


'''Instruction: tuple nommé contenant les champs importants représentant une instruction.
Paramètres:
-----------
operation: opération assembleur à effectuer, e.g. LD, MUL, BEQ
funit: nom de l'unité fonctionnelle exécutant ce type d'instruction
action: type d'action réalisé par l'instruction sous forme mathématique
operands: opérandes de l'instruction (nombre varie selon l'instruction)
'''
Instruction = namedtuple('Instruction', ['addr', 'code', 'funit', 'action', 'operands', 'operator'])


#Enumération pour les états des instructions dans le ROB
class State:
        UNUSED, ISSUE, EXECUTE, WRITE, COMMIT = range(0,5)


class ROBEntry:
    '''
    Entrée dans la table de réordonnancement. Voir la section 3.7 (Hardware-based speculation) de
     Hennessy (3ème édition).
    '''

    def __init__(self, i, instr=None, dest=None, value=None):
        self.i = i
        self.instr = instr
        self.state = State.UNUSED
        self.dest = dest
        self.value = value
        self.ready = False

    def free(self):
        self.ready = False
        self.state = State.UNUSED
        self.dest = None
        self.value = None
        self.instr = None

    def __repr__(self):
        #Won't preserve ordering.
        return str(self.__dict__)


class ROB:
    '''
    Tampon de réordonnancement, contient essentiellement une liste d'instances de `ROBEntry`
     et quelques fonctions pour faciliter l'utilisation.
    '''
    def __init__(self, maxlen):
        self.maxlen = maxlen
        self.start = 0
        self.end = 0
        self.count = 0
        self.entries = [ROBEntry(i) for i in range(self.maxlen)]

    def reset(self):
        self.__init__(self.maxlen)

    def get_free_entry(self):
        '''
        Retourne la première entrée disponible dans le ROB, sinon retourne -1.
        '''
        if self.count < self.maxlen:
            i = self.end
            self.end = (self.end + 1) % self.maxlen
            self.count += 1
            return i, self.entries[i]
        else:
        #Si aucune entrée libre, retourner -1 et une entrée invalide.
            return -1, None

    def check_free_entry(self):
        if self.count < self.maxlen:
            return True
        return False

    def free_head_entry(self):
        '''
        La seule fonction utilisable pour retirer une entrée du ROB, soit de retirer la tête.
        '''
        if self.count > 0:
            self.entries[self.start].free()
            self.count -= 1
            self.start = (self.start + 1) % self.maxlen

    def __getitem__(self, index):
        return self.entries[index]
        
    def __iter__(self):
        i = self.start
        while i != self.end:
            yield self.entries[i]
            i = (i + 1) % self.maxlen

    def __len__(self):
        return self.count

    def __repr__(self):
        # On ne veut pas afficher d'indices 0
        return '\n'.join([str((i + 1, e)) for i, e in enumerate(self.entries) if e.state != State.UNUSED])


class FuncUnit:
    '''
    Unité fonctionnelle. Encore une fois, consulter le chapitre 3 de Hennessy pour des
     explications détaillées.

    Nous trichons un peu dans la conception de ce simulateur et supposons que les branchements et
     opérations sur entiers sont également réalisés par des unités fonctionnelles.

    Ces unités fonctionnelles ont également quelques propriétés pouvant varier d'une unité
     à l'autre, par exemple la définition du type de prédiction de branchement pour les unités de
     branchement et la définition du temps de multiplication vs. division pour les unités de
     multiplication.
    '''
    def __init__(self, name, latency, **kwargs):
        self.name = name
        self.latency = latency

        #Assimilation automatique des autres paramètres
        for k, v in kwargs.items():
            self.__setattr__(k, v)

        self.reset()

    def reset(self, busy=False):
        '''
        Initialise ou réinitialise les champs de l'unité fonctionnelle, cette fonction est
        appelée à la construction et également lorsqu'on cesse d'utiliser une UF.
        '''
        self.qj = None
        self.qk = None
        self.vj = None
        self.vk = None
        self.busy = busy
        self.dest = None
        self.time = None
        self.A = None
        self.instr = None

    def occupy(self, instr):
        self.reset(busy=True)
        self.instr = instr

    def __repr__(self):
        #Won't preserve ordering.
        return str(self.__dict__)


def check_valid_register(func):
    '''
    Décorateur s'assurant que les registres accédés sont valides.
    '''
    def function_handling(*args, **kwargs):
        temp = args[1]
        if temp[0] not in ['R', 'F'] or int(temp[1:]) not in range(0, 32):
            raise SimulationException('Accès à un registre non valide: %s.' % args[1])
        else:
            return func(*args, **kwargs)
    return function_handling


class Registers(OrderedDict):
    '''
    Système de registres du MIPS simulé. Utilisable comme un dictionnaire ordonné. Nous ajoutons
    à celui-ci une vérification de la validité des accès.
    '''
    def __init__(self):
        '''Initialisation des registres.'''
        super(Registers, self).__init__(self)
        
        self.stat = OrderedDict() #Copie servant uniquement à savoir si un registre est utilisé
        #ou non, requis pour annuler des instructions en cas de branchement tout en permettant
        #d'écrire dans les registres aux commits.
        
        #Remplissage des registres
        names = ['R%i' % (i) for i in range(32)] + ['F%i' % (i) for i in range(32)]
        for n in names:
            #Bypass les vérifications pour pouvoir assigner 0 au registre R0
            self.__setitem__(n, 0, bypass=True)
            self.stat[n] = None
            
    def reset_stat(self):
        for k, v in self.stat.items():
            self.stat[k] = None

    def __repr__(self):
        '''Affiche le contenu des registres.'''
        return ', '.join(['%s: %s' % (a, b) for a, b in self.items()])

    @check_valid_register
    def __getitem__(self, item):
        return super(Registers, self).__getitem__(item)

    @check_valid_register
    def __setitem__(self, item, value, bypass=False):
        '''
        Assigne les valeurs des registres.
        '''
        # Capturer un essai d'écriture sur R0
        if not bypass and item == 'R0':
            raise Exception('Impossible d\'utiliser R0, ce '
                                      'registre est une constante.')

        # Assigner la valeur au registre, le valider en entier si RX et en
        # fraction si FX
        try:
            # ROB entry
            if isinstance(value, str) and value[0] == '#':
                #ne pas transformer la variable.
                pass
            elif item[0] == 'R':
                value = int(value)
            else:
                value = float(value)
        except:
            raise Exception('Valeur à assigner invalide: %s' % value)

        super(Registers, self).__setitem__(item, value)


class Memory():
    '''
    Système de mémoire du simulateur MIPS.
    '''
    def __init__(self, mem_size, init_values):
        self.data = [0.0] * mem_size
        for i, v in enumerate(init_values):
            self.data[i] = float(v)
        
    def __repr__(self):
        '''Affiche le contenu de la mémoire.'''
        return ', '.join(['%s' % d for d in self.data])

    def __getitem__(self, index):
        i = int(index / 8)
        if i - index / 8 > 1e-4:
            raise Exception('Indexation invalide de la mémoire (%i), doit être un multiple de 8' %
              index)
        return self.data[i]

    def __setitem__(self, index, value):
        i = int(index / 8)
        if i - index / 8 > 1e-4:
            raise Exception('Indexation invalide de la mémoire (%i), doit être un multiple de 8' %
              index)
        self.data[i] = float(value)
