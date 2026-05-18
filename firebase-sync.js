// Firebase sync (optional). Loads only if config is provided.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAuth, signInAnonymously, onAuthStateChanged }
  from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";
import { getFirestore, doc, onSnapshot, setDoc }
  from "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js";

const cfg = (window.APP_CONFIG && window.APP_CONFIG.firebase) || {};
const hasConfig = cfg.apiKey && cfg.projectId;

window.SYNC = {
  enabled: hasConfig,
  ready: false,
  remoteWrite: null,    // function(data)
  onRemoteChange: null  // assignable callback
};

if (!hasConfig) {
  console.info("[sync] Firebase non configuré — mode localStorage");
} else {
  try {
    const app = initializeApp(cfg);
    const auth = getAuth(app);
    const db = getFirestore(app);
    const workspaceId = (window.APP_CONFIG && window.APP_CONFIG.workspaceId) || "default";
    const docRef = doc(db, "workspaces", workspaceId);

    let suppressNext = false;

    window.SYNC.remoteWrite = async (data) => {
      try {
        suppressNext = true;
        await setDoc(docRef, { data, updatedAt: Date.now() }, { merge: true });
      } catch (e) { console.error("[sync] write failed", e); }
    };

    await signInAnonymously(auth);
    onAuthStateChanged(auth, (user) => {
      if (!user) return;
      onSnapshot(docRef, (snap) => {
        if (suppressNext) { suppressNext = false; return; }
        const remote = snap.data();
        if (remote && remote.data && typeof window.SYNC.onRemoteChange === "function") {
          window.SYNC.onRemoteChange(remote.data);
        }
      });
      window.SYNC.ready = true;
      document.dispatchEvent(new CustomEvent("sync-ready"));
    });
  } catch (e) {
    console.error("[sync] init failed", e);
    window.SYNC.enabled = false;
  }
}
