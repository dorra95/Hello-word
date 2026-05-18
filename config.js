// ============================================================
// CONFIGURATION — modifier ce fichier UNIQUEMENT
// ============================================================
//
// 1) CODES D'ACCÈS
//    Liste des codes valides pour ouvrir l'application.
//    Tous les utilisateurs ayant un de ces codes peuvent se connecter.
//    Changez ces valeurs avant le déploiement.
//
window.APP_CONFIG = {
  accessCodes: [
    "GREENTECH2026",   // code principal — à partager
    "EYA-CONSULT"      // code secondaire
  ],

  // 2) FIREBASE (optionnel — pour partager les données entre utilisateurs)
  //    Si vide, les données restent locales (localStorage).
  //
  //    Pour activer la synchro partagée :
  //    a) Créer un projet sur https://console.firebase.google.com
  //    b) Ajouter une app Web → copier la config Firebase
  //    c) Activer Firestore Database (mode test)
  //    d) Activer Authentication → Anonymous
  //    e) Coller la config ci-dessous
  //
  firebase: {
    // apiKey: "AIza...",
    // authDomain: "xxx.firebaseapp.com",
    // projectId: "xxx",
    // storageBucket: "xxx.appspot.com",
    // messagingSenderId: "...",
    // appId: "..."
  },

  // Identifiant de l'espace de travail partagé (document Firestore)
  workspaceId: "consultant-greentech-tunisie"
};
