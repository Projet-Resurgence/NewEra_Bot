def get_global_context():
    return "Tu es une IA assistant des joueurs dans un jeu de stratégie post-apocalyptique situé en 2045, suite à une guerre nucléaire mondiale. Ton rôle est d’expliquer les règles, de générer des récits immersifs, ou d’analyser des décisions politiques ou militaires, selon la requête. Réponds avec précision, sans digression. Le style doit être sobre, informatif, cohérent avec l’univers décrit, toujours en utilisant la langue française."

def get_military_context():
    return """
    """
    
def get_economy_context():
    return """
    """
    
def get_yearly_context():
    return """
    """
    
def get_server_context():
    return """
Nouvelle Ère V5 est un jeu de rôle géopolitique post-effondrement. La Terre a subi une crise climatique d’ampleur cataclysmique, entraînant l’extinction de 90 % de l’humanité. Les populations survivantes se sont réfugiées dans des bunkers souterrains pendant près de 250 ans.

Seuls les pays ayant anticipé et financé des infrastructures de survie ont pu préserver jusqu'à 10 % de leur population, avec un maximum mondial de 50 millions de survivants par pays. La technologie militaire, l’énergie industrielle, les transports motorisés et l’industrie lourde ont été perdues ou bannies. Seules les technologies liées à la survie — traitement de l’eau, génie civil, construction — ont été entièrement conservées.

À la sortie des bunkers, les sociétés émergentes font face à un monde reconquis par la nature. La faune s’est intensifiée et étendue : des espèces animales dangereuses, voire mutées, peuplent aujourd’hui tous les biomes, y compris des régions autrefois tempérées. L’environnement est hostile, les maladies sont revenues, les ressources sont rares, et la logistique d'exploration du territoire est périlleuse.

Les civilisations redémarrent avec des technologies hétérogènes :
- Technologies de survie (eau, nourriture, abris) : niveau 2010
- Génie civil, médecine de base, infrastructures essentielles : niveau 2010
- Technologies militaires, transports, industrie lourde : niveau ~1910
- Energie (hors nucléaire), communications, télécoms : primitives ou disparues
- Pas de systèmes d'IA, pas d’Internet global, pas de réseaux satellite

Trois archétypes technologiques émergent :
1. **Technocrates** : focus sur l'ingénierie, l'infrastructure, la reconstruction.
2. **Survivalistes** : focus sur la résilience, l'autonomie, la gestion des ressources vitales.
3. **Militaristes** : possèdent un léger avantage dans l’armement (niveau ~1950), mais sont en retard dans toutes les autres disciplines.

Durant la première année de jeu, aucun commerce, diplomatie ni contact inter-national ne sont possibles. Chaque nation agit en isolement total. Les langues ont évolué ou été simplifiées, et les priorités sont la survie, la conquête territoriale, et la reconstruction progressive.

Les catégories technologiques majeures sont :
- Ressources vitales (eau, nourriture, stockage, agriculture)
- Énergie
- Transport
- Armement
- Industrie
- Culture et mémoire collective
- Sciences biologiques et santé
- TIC (technologies de l'information et communication)

L’objectif est de reconstruire une société fonctionnelle à partir d’un socle technologique incomplet, dans un monde hostile, fragmenté, et imprévisible.
"""

typed_contexts = {
    'global': get_global_context(),
    'military': get_military_context(),
    'economy': get_economy_context(),
    'yearly_report': get_yearly_context()
}

def get_context(type):
    return typed_contexts[type] if type in typed_contexts else get_global_context()