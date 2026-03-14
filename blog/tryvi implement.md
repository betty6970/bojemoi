Charite bine ordonnée commence par soi-meme.
implementation de tryvi dans Gitea pour les sources et les images.
Réponse Claude
 
Here is Claude's plan:                                                                                                               
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Plan: Intégration Trivy dans Gitea Actions             

 Contexte

 Le projet /opt/bojemoi contient 30+ Dockerfiles et 10 stack YAMLs sans scan de sécurité
 automatisé côté Gitea. Trivy sera ajouté en CI/CD Gitea Actions pour détecter les
 misconfigurations (Dockerfiles, stacks) et les secrets exposés dans le code.

 Le runner Gitea tourne sur Lightsail (916 MB RAM) — on évite le téléchargement de la base
 de vulnérabilités (~300 MB) et on se concentre sur misconfig + secret qui fonctionnent
 sans DB et sont les plus utiles pour un repo infra.

 ---
 Fichier à créer

 /opt/bojemoi/.gitea/workflows/trivy.yml

 name: Trivy Security Scan

 on:
   push:
     branches: [main]
   pull_request:

 jobs:
   trivy:
     runs-on: ubuntu-latest
     container:
       image: aquasec/trivy:latest

     steps:
       - name: Clone repo
         run: |
           git clone --depth 1 --branch "${GITHUB_REF_NAME:-main}" \
             "http://gitea:3000/${GITHUB_REPOSITORY}.git" /workspace

       - name: Scan — misconfigurations (Dockerfiles + stack YAMLs)
         run: |
           trivy config \
             --severity HIGH,CRITICAL \
             --exit-code 0 \
             /workspace
         continue-on-error: true

       - name: Scan — secrets exposés
         run: |
           trivy fs \
             --scanners secret \
             --exit-code 0 \
             /workspace
         continue-on-error: true

 Pattern identique au workflow Hugo existant (blog-repo/.gitea/workflows/hugo-deploy.yml) :
 - runs-on: ubuntu-latest + container: image:
 - git clone manuel (pas actions/checkout)
 - http://gitea:3000/ comme URL interne Gitea

 ---
 Ce que Trivy scannera

 ┌─────────┬─────────────────────────────────┬────────────────────────────────────────────────────────────┐
 │ Scanner │             Cibles              │                           Valeur                           │
 ├─────────┼─────────────────────────────────┼────────────────────────────────────────────────────────────┤
 │ config  │ 30+ Dockerfiles, 10 stack YAMLs │ Misconfigs IaC (USER root, ports exposés, capabilities...) │
 ├─────────┼─────────────────────────────────┼────────────────────────────────────────────────────────────┤
 │ secret  │ Tout le repo                    │ API keys, tokens, mots de passe hardcodés                  │
 └─────────┴─────────────────────────────────┴────────────────────────────────────────────────────────────┘

 --exit-code 0 → advisory mode, ne bloque pas les déploiements au démarrage.
 Peut passer à --exit-code 1 une fois le bruit de base géré.

 ---
 Étapes d'implémentation

 1. Créer le répertoire .gitea/workflows/ dans /opt/bojemoi
 2. Écrire le fichier trivy.yml
 3. Committer et pusher sur Gitea (main)
 4. Vérifier le résultat du job dans l'interface Gitea

 ---
 Vérification

 - Interface Gitea → repo → Actions → vérifier que le job trivy se lance et termine
 - Les logs affichent les findings (misconfigs + secrets)
 - Aucun blocage de pipeline (exit-code 0)
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

 Claude has written up a plan and is ready to execute. Would you like to proceed?

