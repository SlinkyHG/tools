# Usage: 

## Explications
Permet de générer une liste d'objets comprenant : 
- Le numéro de la machine dans le cluster
- Un datastore pour le déploiement de la vm
- Un host pour la mise en service

Le script parcours les différents vcenters et dc de chaque plateforme à la recherche de datastores et d'hosts répondant aux critères de CPU, RAM et d'espace disponible. 
Il choisi ensuite, dans l'ordre de disponibilité le plus grand un DC et un host, en alternant si plusieurs vcenters présentés. Enfin, si le nombre de réplicats est plus grand que le nombre de DS ou d'Hosts, il continue en reprenant dans l'ordre de disponibilités de ces derniers. 

## Output du script: 

```json
[
    {
        'vmNum': 0, 
        'host': {
            'name': 'hostname.domain.ext', 
            'ram': 10.08711455564962, 
            'cpu': 36, 
            'sum': '36% CPU usage, 10% Free Memory',
            'cpuSum': '51141.0Mhz CPU capacity, 18430Mhz CPU usage',
            'ramSum': '393.0GB ram capacity, 353.0GB ram usage',
            'uptime': 75
        }, 
        'ds': {
            'name': 'mon_ds', 
            'freeSpace': 693877772288, 
            'freeSpacePercentage': 15.392150179136035, 
            'sum': '15% free disk space,
            4299.0GB disk space capacity,
            662.0GB disk space used'
        }
    },

    ...
]
```

## Configuration: 

### Constantes du script: 
- `REGEX_HOST_FILTER = "."` : . Signifie "wildcard" dans une expression régulière. Il est possible de spécifier une norme de nommage pour le nom des hosts à selectionner
- `REGEX_DS_FILTER = "."` : . Signifie "wildcard" dans une expression régulière. Il est possible de spécifier une norme de nommage pour le nom des datastores à selectionner

- `LIST_DC_IGNORED = []` : Tableau à complèter dans le cas ou il est nécéssaire d'ignorer certains datacenters (Ex: datacenters d'une agence)
- `LIST_HOSTS_IGNORED = []` : Tableau à complèter dans le cas ou il est nécéssaire d'ignorer certains hosts (Ex: hosts réservés à une DMZ)
- `LIST_DS_IGNORED = []` : Tableau à complèter dans le cas ou il est nécéssaire d'ignorer certains datastores (Ex: Baie SSD réservée aux bases de données)
- `LIMIT_DS_FREE_SPACE = 10` : Limitation d'espace libre nécéssaire au minimum pour qu'un datastore soit éligible (en pourcentage)
- `LIMIT_HOSTS_FREE_RAM = 10` : Limitation de ram nécéssaire au minimum pour qu'un host soit éligible (en pourcentage)
- `LIMIT_HOSTS_FREE_CPU = 10` : Limitation de cpu nécéssaire au minimum pour qu'un host soit éligible (en pourcentage)

### Variables d'environnement:
- USERNAME : Nom du compte de service utilisé pour le reccueil de données des vCenters
- USERNAME : Mot de passe du compte de service utilisé pour le reccueil de données des vCenters

### Arguments du script:
- -s ou --host : Nom du ou des serveurs vcenters (Dans le cas de plusieurs, les séparer par virgules, **sans aucun espace, sans protocole**.)
- -o ou --port : Port du service vCenter (443 ou 80 la plus-part du temps).
- -u ou --user : Si spécifié, écrase l'obligation d'avoir une variable d'environnement USERNAME
- -p ou --password : Si spécifié, écrase l'obligation d'avoir une variable d'environnement PASSWORD
- -i ou --size : Nombre de VM voulues