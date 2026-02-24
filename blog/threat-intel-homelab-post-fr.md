---
title: "Construire une Plateforme de Threat Intelligence avec ML dans son Homelab"
date: 2026-02-24
draft: false
tags: ["threat-intelligence", "cybersecurity", "machine-learning", "osint", "telegram", "homelab", "docker-swarm", "nlp", "ner", "mitre-attack"]
summary: "Comment j'ai construit, en partant de zéro, une plateforme de threat intelligence de niveau production qui prédit les attaques DDoS en surveillant les canaux Telegram hacktivistes."
description: "Parcours d'un débutant qui a construit une plateforme CTI avec NER multilingue, bots Telegram OSINT et intégration MITRE ATT&CK sur un homelab Docker Swarm auto-hébergé."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Il y a six mois, je ne connaissais presque rien aux infrastructures de cybersécurité. Aujourd'hui, je gère une plateforme de threat intelligence de niveau production qui prédit les attaques DDoS en surveillant les canaux Telegram hacktivistes. Si vous lisez ceci en pensant "ça semble impossible pour quelqu'un qui débute" - je comprends. Je pensais la même chose.

Ce post est pour vous : le débutant curieux qui veut construire de vrais outils de sécurité mais ne sait pas par où commencer.

## C'est Quoi Exactement Ce Truc ?

Laissez-moi commencer par expliquer ce que fait mon système en français simple :

**Le Postulat** : Les groupes hacktivistes annoncent leurs cibles d'attaque sur Telegram avant de lancer des attaques DDoS. Les organisations françaises deviennent souvent des cibles, mais il n'existe pas de moyen automatisé pour détecter ces menaces en avance.

**Ma Solution** : Un système qui :
1. Surveille les canaux Telegram où les hacktivistes traînent
2. Lit les messages dans plusieurs langues (parce que les hacktivistes ne parlent pas tous anglais)
3. Identifie quand des organisations sont mentionnées
4. Évalue à quel point la discussion est "active" ou menaçante
5. M'alerte quand une organisation française pourrait être sous menace

Imaginez un robot qui lit des forums menaçants 24h/24 et 7j/7 et vous tape sur l'épaule quand des ennuis se préparent.

## Pourquoi Vous Pouvez Construire Ça (Même en Tant que Débutant)

Voici mon avis controversé : **vous n'avez plus besoin d'être un expert en code pour construire des systèmes de sécurité sophistiqués**.

Mon approche repose sur trois principes :

### 1. Laissez l'IA Écrire Votre Code
Je n'écris pas beaucoup de code à la main. À la place, je gère les prompts et les structures. Je dis à Claude (ou similaire) ce que je veux construire, et il génère l'implémentation. Mon travail est l'architecture et l'intégration, pas la syntaxe.

**Cela signifie** : Si vous pouvez décrire clairement ce que vous voulez, vous pouvez le construire.

### 2. Open Source Partout
Tous les outils que j'utilise sont gratuits et open source :
- XenServer pour la virtualisation
- Docker Swarm pour l'orchestration de conteneurs
- PostgreSQL pour les bases de données
- Gitea pour les workflows Git
- Prometheus/Grafana pour le monitoring

**Cela signifie** : Zéro coût de licence, contrôle total, et une énorme communauté pour le support.

### 3. Tout Automatiser
Les processus manuels ne passent pas à l'échelle et vous les oublierez. Mon infrastructure utilise :
- Workflows GitOps (push config → déploiement automatique)
- Cloud-init pour le provisioning de VM
- Automation par webhooks pour CI/CD
- Orchestration de conteneurs pour l'auto-guérison

**Cela signifie** : Une fois configuré, le système tourne tout seul. Vous maintenez l'infrastructure sous forme de code, pas en cliquant dans des interfaces.

## Le Parcours : Ce Que J'ai Vraiment Construit

Laissez-moi vous guider à travers l'évolution, parce que ça n'a pas été linéaire :

### Phase 1 : Les Fondations (Mois 0-2)
**J'ai commencé avec** : Configuration XenServer de base, apprentissage des concepts de virtualisation

**Ce que j'ai appris** : Il vous faut une couche de base solide avant quoi que ce soit de fancy. J'ai passé du temps à comprendre :
- Le bonding réseau pour la haute disponibilité
- La gestion du stockage
- Les templates de VM et le provisioning

**Piège débutant que j'ai évité** : Essayer de tout faire d'un coup. Maîtrisez une couche avant d'ajouter la suivante.

### Phase 2 : Orchestration de Conteneurs (Mois 2-3)
**J'ai construit** : Cluster Docker Swarm avec déploiement automatique

**Ce que ça vous apporte** : Déployer de nouveaux services en secondes, pas en heures. Les services redémarrent automatiquement s'ils plantent.

**Le moment "aha"** : Quand j'ai poussé du code sur Git et l'ai vu se déployer automatiquement en production sans toucher un terminal. C'est là que j'ai compris.

### Phase 3 : Workflow GitOps (Mois 3-4)
**J'ai construit** : Intégration Gitea avec des datasources cloud-init personnalisées qui interrogent PostgreSQL

**Ce que ça permet** :
- Écrire une config YAML décrivant une VM
- La pusher sur Git
- La VM se crée et se configure automatiquement
- Toute l'infrastructure devient reproductible

**Pourquoi c'est important** : Votre homelab devient du code. La reprise après sinistre, c'est juste re-exécuter votre repo Git.

### Phase 4 : Threat Intelligence (Mois 4-6)
**J'ai construit** : La plateforme de threat intelligence proprement dite avec :
- Monitoring par bot Telegram avec capacités OSINT
- Reconnaissance d'Entités Nommées (NER) multilingue
- Extraction d'entités et mapping de relations
- Algorithmes de scoring de buzz
- Intégration avec Maltego, TheHive, MISP
- Mapping du framework MITRE ATT&CK

**La percée** : Réaliser que la threat intelligence, c'est du pattern matching à l'échelle. Le ML aide, mais l'architecture intelligente et le streaming de données comptent davantage.

## L'Architecture (Simplifiée)

Voici comment les pièces s'assemblent sans vous submerger :

```
[Canaux Telegram] 
    ↓ (flux de messages)
[Infrastructure Bot Telegram]
    ↓ (texte brut + métadonnées)
[Traitement NER Multilingue]
    ↓ (entités identifiées)
[Extraction d'Entités & Scoring]
    ↓ (scores de menace)
[Base de Données PostgreSQL]
    ↓ (requêtes pour analyse)
[Système d'Alerte] → [Moi !]
```

Chaque boîte est un microservice dans Docker. Ils communiquent via des files de messages et des API. Si l'un plante, les autres continuent de tourner.

## Technologies Clés Expliquées (Pour Débutants)

**XenServer** : Imaginez avoir plusieurs ordinateurs à l'intérieur d'un seul ordinateur physique. Chaque "machine virtuelle" agit indépendamment.

**Docker Swarm** : Gère les conteneurs (mini-environnements légers). Si vous déployez 5 conteneurs, Swarm les répartit sur vos serveurs et les redémarre s'ils meurent.

**PostgreSQL** : Une base de données. Elle stocke toutes les données structurées (entités, scores de menace, relations).

**Gitea** : Comme GitHub, mais vous l'hébergez vous-même. Votre code et vos configs vivent ici.

**Cloud-init** : Automatise la configuration de VM. Au lieu de cliquer dans des installeurs, vous décrivez ce que vous voulez dans un fichier.

**NER (Named Entity Recognition)** : ML qui trouve des entités dans le texte. Il repère "Microsoft" dans un message et sait que c'est une organisation, pas juste un mot.

## Conseils Pratiques Si Vous Débutez

### Commencez Petit, Pensez Grand
N'essayez pas de tout construire d'un coup. J'ai commencé avec :
1. Une VM qui fait tourner Docker
2. Un service simple (un bot Telegram)
3. Une base de données
4. Puis j'ai progressivement ajouté orchestration, monitoring, automation

### Adoptez la Configuration Plutôt que le Code
Écrivez des configs YAML qui décrivent ce que vous voulez. Laissez des outils comme Docker Compose et cloud-init gérer l'implémentation.

### Construisez en Production dès le Premier Jour
N'ayez pas un "environnement d'apprentissage" et un "environnement de production". Construisez en niveau production dès le début :
- Utilisez l'orchestration de conteneurs
- Mettez en place du monitoring
- Implémentez du logging
- Concevez pour la défaillance

Vous apprendrez de meilleures pratiques et n'aurez pas à tout reconstruire plus tard.

### Utilisez les Assistants IA de Façon Agressive
J'utilise Claude pour :
- Générer des applications FastAPI
- Écrire des configs Docker
- Créer des schémas de base de données
- Débugger des problèmes
- Expliquer des concepts que je ne comprends pas

Ce n'est pas tricher - c'est travailler intelligemment.

### Concentrez-vous sur l'Intégration, Pas l'Implémentation
Votre valeur n'est pas d'écrire du Python - c'est de concevoir des systèmes qui résolvent des problèmes. Laissez l'IA gérer la syntaxe. Vous gérez l'architecture.

## La Plateforme de Threat Intelligence : Plongée Profonde

Puisque c'est la partie cool, laissez-moi détailler comment fonctionne la partie ML/intelligence :

### 1. Ingestion de Données
Les bots Telegram surveillent les canaux et capturent :
- Texte du message
- Horodatage
- Info de l'expéditeur
- Métadonnées du canal

Cela stream dans une file de messages pour traitement.

### 2. Traitement Multilingue
Les messages peuvent être en russe, anglais, français, ou mixtes. Le pipeline NER :
- Détecte la langue
- Applique le modèle NER approprié
- Extrait les entités (organisations, personnes, lieux, IPs, domaines)

**Pourquoi le multilingue compte** : Les hacktivistes opèrent souvent en russe ou utilisent des langues mixtes pour éviter la détection.

### 3. Extraction d'Entités & Scoring
Pour chaque entité (comme "Entreprise X"), le système :
- Vérifie si elle est française (géolocalisation + analyse de domaine)
- Compte les mentions sur des fenêtres de temps
- Analyse le sentiment et les mots-clés de menace
- Calcule un "score de buzz"

Score de buzz élevé = quelque chose se passe.

### 4. Corrélation de Menaces
Le système mappe les entités à :
- Infrastructure connue (via outils OSINT comme Shodan, VirusTotal)
- Patterns d'attaque historiques
- Techniques MITRE ATT&CK

Cela construit un graphe de menaces montrant les relations.

### 5. Alertes
Quand les patterns indiquent un risque élevé :
- Le score dépasse un seuil
- Plusieurs canaux mentionnent la même cible
- Des mots-clés de menace apparaissent dans le contexte

→ L'alerte se déclenche avec les preuves à l'appui.

## Intégration OSINT : Le Rendre Plus Intelligent

Le bot Telegram a des capacités OSINT intégrées :

**Analyse d'IP** : Requêtes VirusTotal, AbuseIPDB, Shodan pour la réputation et les données historiques

**Intelligence de Domaine** : DNS passif, WHOIS, analyse de certificats

**Enrollment Blockchain** : Vérification d'utilisateurs via systèmes basés blockchain (pour contrôle d'accès)

**Mapping de Framework** : Identification automatique des techniques MITRE ATT&CK

Cela transforme les données brutes en intelligence actionnable.

## Ce Que Je Ferais Différemment ?

**Commencer avec un meilleur monitoring** : J'ai ajouté Prometheus/Grafana tardivement. J'aurais aimé le construire dès le premier jour. Vous ne pouvez pas débugger ce que vous ne pouvez pas voir.

**Documenter au fur et à mesure** : Je reconstruis certaines connaissances parce que je n'ai pas documenté les décisions. Écrivez POURQUOI vous avez choisi quelque chose, pas juste QUOI.

**Design réseau dès le début** : J'ai dû refactoriser le réseau plusieurs fois. Planifiez vos sous-réseaux, VLANs, et règles de firewall avant de déployer des services.

**Tester la reprise après sinistre tôt** : J'ai construit un système incroyable... puis réalisé que je n'avais pas testé la restauration depuis les backups. Testez vos modes de défaillance.

## Ressources Qui M'ont Vraiment Aidé

**Pour apprendre l'infrastructure** :
- The Phoenix Project (livre) - a changé ma façon de penser les systèmes
- Documentation XenServer - étonnamment lisible
- Docs Docker Swarm - plus courtes que Kubernetes, plus faciles pour commencer

**Pour la threat intelligence** :
- Framework MITRE ATT&CK - gratuit, complet
- Documentation MISP Project - partage de menaces open source
- TheHive Project - plateforme de réponse aux incidents

**Pour les compétences pratiques** :
- Claude (évidemment) - pour génération de code et explications
- Repos GitHub de projets similaires - apprenez des implémentations réelles
- Chaînes YouTube sur les setups homelab

## La Réalité des Coûts

**Hardware** : J'ai commencé avec du matériel serveur plus ancien (~500$ d'occasion)
**Software** : 0$ (tout en open source)
**Cloud** : J'ai de l'infrastructure AWS, mais le homelab est auto-hébergé
**Temps** : Significatif, mais compressé en utilisant l'assistance IA

Vous pouvez commencer plus petit - un ordinateur de bureau décent ou un serveur d'occasion suffit.

## Réflexions Finales : Vous Pouvez le Faire

Le domaine de la cybersécurité semble parfois protégé par la complexité et le jargon. Mais voici la vérité : **si vous pouvez décrire clairement un problème, vous pouvez construire une solution**.

Il y a six mois :
- Je ne savais pas ce qu'était Docker Swarm
- Je n'avais jamais écrit d'app FastAPI
- Je ne pouvais pas expliquer ce que NER signifiait
- Je n'avais jamais déployé une VM programmatiquement

Aujourd'hui je gère une plateforme de threat intelligence de niveau production.

La différence n'est pas que je suis devenu un génie - c'est que j'ai :
1. Décomposé de gros problèmes en petites étapes
2. Utilisé l'IA pour gérer les détails d'implémentation
3. Mis l'accent sur les outils open source
4. Automatisé sans relâche
5. Construit en public (même quand c'était le bazar)

Votre plateforme de threat intelligence pourrait être différente de la mienne. Peut-être que vous vous souciez de menaces différentes, utilisez des sources de données différentes, ou avez une infrastructure différente. C'est parfait - construisez ce qui compte pour vous.

Les outils sont gratuits. La connaissance est accessible. Les assistants IA sont prêts à aider.

Commencez avec une VM. Déployez un service. Automatisez une chose.

Dans six mois, vous écrirez votre propre post "parcours d'un débutant".

---

**Suite de cette série** : Je détaillerai l'architecture technique avec des exemples de code, des configs Docker, et l'implémentation réelle du bot Telegram. Mais d'abord, je veux vous entendre : quelle partie vous intéresse le plus ?

#ThreatIntelligence  #CyberSecurity  #MachineLearning  #ML #OSINT #InfoSec

*Contactez-moi sur https://t.me/+oppPK07e5S00Y2Y8 avec vos questions, ou suivez-moi pendant que je documente les plongées* techniques.*

* voit nota
nota : ce post est genere par Claude, et Claude peut faire de erreurs.(MDR)
