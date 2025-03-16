# SkillLab Human Review System

Ce module fournit une interface de révision humaine pour les documents traités par le pipeline SkillLab. Il permet d'identifier, d'examiner et de corriger les documents qui ont été signalés lors du processus d'extraction.

## Fonctionnalités

- **Système de file d'attente** : Gestion des documents qui nécessitent une révision
- **Interface Web** : Interface Streamlit pour la visualisation et la correction des données
- **Dashboard** : Statistiques et informations sur les performances du pipeline
- **CLI** : Interface en ligne de commande pour accéder rapidement aux statistiques

## Architecture

Le système de révision est composé des éléments suivants :

- `app.py` : Application Streamlit pour l'interface web
- `db_manager.py` : Gestionnaire de base de données pour le suivi des documents
- `cli.py` : Interface en ligne de commande pour la gestion des révisions

## Installation

Le système de révision est installé automatiquement lors de l'installation du package SkillLab. Si vous n'avez pas encore installé les dépendances requises, exécutez :

```bash
# Depuis la racine du projet
bash install.sh
```

## Utilisation

### Interface Web

Pour lancer l'interface web de révision :

```bash
skilllab review
# ou
skilllab review web
```

L'interface web est accessible à l'adresse http://localhost:8501 et offre les fonctionnalités suivantes :

1. **Dashboard** : Statistiques générales sur le pipeline et les documents à réviser
2. **File d'attente de révision** : Liste des documents signalés pour révision
3. **Interface de correction** : Visualisation et édition des documents signalés

### Interface CLI

Pour afficher l'état actuel de la file d'attente de révision :

```bash
skilllab review status
```

Pour lister les documents signalés pour révision :

```bash
skilllab review list
```

Pour filtrer par type de problème :

```bash
skilllab review list --filter low_ocr_confidence
```

## Critères de révision

Les documents sont automatiquement signalés pour révision dans les cas suivants :

1. **Faible confiance d'OCR** : Score de confiance OCR inférieur à 75%
2. **Champs critiques manquants** : Absence de nom, email ou téléphone
3. **Problèmes de validation JSON** : Échec de la validation du schéma
4. **Corrections multiples** : Document ayant nécessité plus de 3 tentatives de correction automatique

## Workflow de révision

1. Les documents sont automatiquement signalés lors du traitement
2. Les documents signalés apparaissent dans la file d'attente de révision
3. L'opérateur peut examiner chaque document via l'interface web
4. L'opérateur peut approuver, rejeter ou corriger manuellement les données
5. Les corrections sont enregistrées pour améliorer le traitement futur

## Intégration avec le pipeline

Le système de révision est intégré au pipeline principal via :

1. **Monitoring** : Les métriques de révision sont affichées dans le tableau de bord de monitoring
2. **Boucle de retour** : Les corrections manuelles sont utilisées pour améliorer l'extraction future
3. **CLI unifié** : Accès via la commande `skilllab review`

## Structure de la base de données

Le système de révision utilise une base de données SQLite avec les tables suivantes :

- `documents` : Informations sur les documents traités
- `document_issues` : Problèmes identifiés pour chaque document
- `review_feedback` : Retours des révisions humaines
- `field_corrections` : Corrections spécifiques apportées aux champs

## Personnalisation

Pour personnaliser l'interface de révision, vous pouvez modifier :

- `app.py` : Pour modifier l'interface utilisateur Streamlit
- Les seuils de confiance dans `db_manager.py` pour ajuster les critères de signalement