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

Données enregistrées localement (`localStorage`) par défaut. Pour partager les données entre plusieurs utilisateurs, voir « Activer la base partagée » ci-dessous.

---

## 🔐 Accès protégé par code

Au chargement, l'application demande un code d'accès. Modifier la liste dans `config.js` :

```js
accessCodes: ["GREENTECH2026", "EYA-CONSULT"]
```

Les codes par défaut sont à changer avant tout partage public.

---

## 🌐 Publier en ligne (GitHub Pages)

1. Repo GitHub → **Settings** → **Pages**
2. Source : branche `claude/consultant-tracking-app-Y00GB`, dossier `/ (root)` → Save
3. L'app sera live à `https://<utilisateur>.github.io/<repo>/`
4. Partager l'URL + le code d'accès aux utilisateurs

---

## 🔄 Activer la base partagée (Firebase — optionnel)

Sans config Firebase, chaque utilisateur a ses données isolées. Pour partager :

1. Créer un projet sur https://console.firebase.google.com
2. Dans le projet : **Ajouter une application Web** → copier l'objet `firebaseConfig`
3. Activer **Firestore Database** (mode test pour démarrer)
4. Activer **Authentication** → onglet **Sign-in method** → activer **Anonymous**
5. Coller la config dans `config.js` sous `firebase: { ... }`
6. Pousser sur GitHub

Tous les utilisateurs avec le code d'accès partagent désormais le même espace de travail (un document Firestore identifié par `workspaceId`).

### 👑 Mode Admin vs 👁️ Visiteur

L'app reconnaît 2 niveaux de codes définis dans `config.js` :
- `adminCodes` → toi : lecture **+** modification
- `viewerCodes` → tout le monde : **lecture seule** (tous les boutons et champs sont désactivés)

**⚠️ Important** : La protection côté navigateur peut être contournée par un utilisateur technique. Pour une **vraie** protection serveur, appliquer les règles Firestore ci-dessous, qui n'autorisent l'écriture qu'aux clients dont l'UID figure dans la liste blanche.

### Règles Firestore — lecture publique authentifiée, écriture admin uniquement

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /workspaces/{workspaceId} {
      allow read: if request.auth != null;
      // Remplacer "TON_UID_ANONYME" par ton UID Firebase (visible dans
      // l'onglet Authentication > Users après ta 1ère connexion admin)
      allow write: if request.auth != null
                   && request.auth.uid in ["TON_UID_ANONYME"];
    }
  }
}
```

**Procédure** :
1. Te connecter une 1ère fois avec ton code admin → Firebase crée ton UID
2. Console Firebase → Authentication → Users → copier ton UID
3. Coller cet UID dans la règle ci-dessus → Publier
4. Désormais seul ton appareil peut écrire ; tous les autres lisent uniquement
