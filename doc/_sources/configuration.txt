Module de configuration
=======================

Utilisation du module
---------------------

Le module de configuration s'instancie avec le chemin de sa configuration en paramètre comme suit::

    from src.configuration import *
    config = mips_configuration(config_file)

Les fichiers de configurations sont en document XML pouvant prendre l'arborescence suivante::

    <MIPSSim>
      <FunctUnits>
        <Load   number="1" latency="2"/>
        <Store  number="1" latency="4"/>
        <Add    number="2" latency="2"/>
        <Mult   number="2" latency="2"/>
        <ALU    number="2" latency="1"/>
        <Branch number="1" latency="1" spec_forward="nottaken" spec_backward="taken"/>
      </FunctUnits>
      <Registers>
        <R1 value="1"/>
        <R2 value="2"/>
        <F2 value="3.0"/>
      </Registers>
      <Memory size="24">
        1.0 1.2 1.4 1.6 1.8 2.0 2.2 2.4 2.6 2.8 3.0 3.2 3.4 3.6 3.8 4.0 4.2 4.4 4.6 4.8 5.0 5.2 5.4 5.6
      </Memory>
    </MIPSSim>

Accès à la configuration de l'architecture MIPS
-----------------------------------------------

Accès au *Program Counter*::

    config.PC
    
Exemples d'accès aux définitions des unités fonctionnelles::

    config.unite_fonctionnelle['Load']
    config.unite_fonctionnelle['Store']
    config.unite_fonctionnelle['Add'].execution_time
    config.unite_fonctionnelle['Mult'].execution_time_division
    config.unite_fonctionnelle['ALU'].quantite
    config.unite_fonctionnelle['Branch']

Accès aux unités fonctionnelles et à ses paramètres::
    
    config.unite_fonctionnelle['Load'][0]['temps'] # Le temps restant d'exécution de la première unité fonctionnelle Load
    config.unite_fonctionnelle['Store'][1]['busy'] # Booléen stipulant l'utilisation de la deuxième unité fonctionnelle Store
    config.unite_fonctionnelle['Add'][2]['vj']     # Valeur de la variable de Tomasulo Vj pour la troisième unité fonctionnelle Add
    config.unite_fonctionnelle['Mult'][0]['vk']    # Valeur de la varaible de Tomasulo Vk pour la première unité fonctionnelle Mult
    

Classes et membres du module de configuration
---------------------------------------------
    
.. automodule:: src.configuration
    :members:
    :undoc-members:
    :inherited-members: