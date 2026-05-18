# Suivi Mission Consultant S&E — Initiative GreenTech Tunisie

Application web (HTML/CSS/JS pur, données en `localStorage`) pour suivre la mission de la consultante en Suivi & Évaluation, conformément au contrat signé le 04/03/2026 et à l'Avenant n°1 (CDC / Greenov'i).

## Lancer

Ouvrir `index.html` dans un navigateur, ou servir le dossier :

```
python3 -m http.server
```

## Fonctionnalités

- **Tableau de bord** : KPIs (montant total, mensualité, mensualités payées/restantes, jours travaillés du mois, congés restants), résumé mensuel calculé, prochaines échéances.
- **Calendrier / Jours** : marquer chaque jour (présence, ½ journée, congé, autorisation, férié, absent), description des tâches/livrables associés.
- **Livrables** : titre, description, dates prévue/livrée, statut, validation par le coordinateur, lien (Drive, etc.).
- **Tâches** : à faire / en cours / terminées, priorité, échéance, filtres.
- **Congés & Autorisations** : demandes, période, motif, statut, quota.
- **Décaissements** : génération auto de l'échéancier (19 mensualités de 5 300,000 DT TTC), validation livrables → date paiement attendue (+15 jours), montant perçu, n° reçu, statut.
- **Paramètres** : initialisés avec les valeurs de l'Avenant n°1, export/import JSON, reset.

## Données pré-remplies (Avenant n°1)

| Champ | Valeur |
|---|---|
| Consultante | Eya TBORSKI MANAI |
| Client | Caisse des Dépôts et Consignations |
| Projet | Initiative GreenTech Tunisie — Greenov'i (Expertise France / UE) |
| Montant total | 100 700,000 DT TTC |
| Mensualité | 5 300,000 DT TTC |
| Durée | 19 mois à partir du 04/03/2026 |
| Délai paiement | 15 jours après validation des livrables |

## Stockage

Données enregistrées localement (`localStorage`). Utilisez **Exporter JSON** pour sauvegarder et **Importer JSON** pour restaurer.
