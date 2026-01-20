# Guide de contribution

Merci de votre intérêt pour contribuer à Faraday Security Stack!

## 🤝 Comment contribuer

### Signaler un bug

1. Vérifiez que le bug n'a pas déjà été signalé
2. Ouvrez une issue avec le template "Bug Report"
3. Incluez:
   - Description détaillée du problème
   - Étapes pour reproduire
   - Comportement attendu vs actuel
   - Version de Docker et Docker Compose
   - Logs pertinents

### Proposer une amélioration

1. Ouvrez une issue avec le template "Feature Request"
2. Décrivez clairement la fonctionnalité souhaitée
3. Expliquez le cas d'usage
4. Si possible, proposez une implémentation

### Soumettre un Pull Request

1. Fork le projet
2. Créez une branche pour votre fonctionnalité:
   ```bash
   git checkout -b feature/ma-fonctionnalite
   ```
3. Commitez vos changements:
   ```bash
   git commit -m "feat: ajout de ma fonctionnalité"
   ```
4. Pushez vers votre fork:
   ```bash
   git push origin feature/ma-fonctionnalite
   ```
5. Ouvrez un Pull Request

## 📋 Standards de code

### Scripts Bash

- Utilisez `set -e` en début de script
- Commentez les sections complexes
- Utilisez des fonctions pour la réutilisation
- Gérez les erreurs proprement
- Utilisez des noms de variables explicites

### Scripts Python

- Suivez PEP 8
- Utilisez des docstrings
- Gérez les exceptions
- Ajoutez des logs informatifs
- Testez votre code

### Docker

- Optimisez les layers
- Utilisez des images officielles
- Nettoyez les fichiers temporaires
- Documentez les variables d'environnement
- Suivez les best practices de sécurité

## 🧪 Tests

Avant de soumettre un PR:

```bash
# Exécutez les tests
./test.sh

# Vérifiez que tous les services démarrent
make up
make status

# Testez vos modifications
```

## 📝 Convention de commit

Utilisez des messages de commit clairs:

- `feat:` Nouvelle fonctionnalité
- `fix:` Correction de bug
- `docs:` Documentation
- `style:` Formatage
- `refactor:` Refactoring
- `test:` Tests
- `chore:` Maintenance

Exemple:
```
feat: ajout du support pour Nessus
fix: correction de l'import ZAP
docs: mise à jour du README
```

## 🔐 Sécurité

Si vous découvrez une vulnérabilité de sécurité:

1. **NE PAS** ouvrir une issue publique
2. Contactez les mainteneurs directement
3. Fournissez les détails de la vulnérabilité
4. Attendez une réponse avant de divulguer

## 📄 Licence

En contribuant, vous acceptez que vos contributions soient sous la même licence que le projet.

## 💬 Questions

Pour toute question, n'hésitez pas à:
- Ouvrir une discussion
- Contacter les mainteneurs
- Consulter la documentation

Merci pour votre contribution! 🎉
