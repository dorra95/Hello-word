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
  // CODE ADMIN — réservé à toi (lecture + modification)
  adminCodes: [
    "ADMIN-2026"
  ],

  // CODES VISITEURS — à partager (lecture seule)
  viewerCodes: [
    "GREENTECH2026"
  ],

  // (compat ancien champ — ignoré si adminCodes/viewerCodes sont définis)
  accessCodes: [],

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
    apiKey: "AIzaSyAh4TyGRujoVZOlc8QIed4IHXE34ROpGSE",
    authDomain: "suivi-greentech.firebaseapp.com",
    projectId: "suivi-greentech",
    storageBucket: "suivi-greentech.firebasestorage.app",
    messagingSenderId: "851017030075",
    appId: "1:851017030075:web:3c4db297284ced1d34cc9e"
  },

  // Identifiant de l'espace de travail partagé (document Firestore)
  workspaceId: "consultant-greentech-tunisie"
};
