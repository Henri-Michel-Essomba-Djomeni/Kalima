/**
 * Upload robuste avec reprise sur coupure réseau.
 *
 * Découpe le fichier en morceaux de TAILLE_MORCEAU octets et les envoie
 * un par un. Si un envoi échoue (coupure réseau), on retente plusieurs
 * fois avant d'abandonner ; si l'utilisateur relance manuellement plus
 * tard avec le même fichier, l'empreinte identique permet au serveur de
 * dire "j'ai déjà reçu X octets", et on reprend à partir de là au lieu
 * de tout renvoyer.
 *
 * Dépend de fetchAuth(url, options), déjà défini ailleurs dans le
 * frontend de Kalima.
 */

const TAILLE_MORCEAU = 2 * 1024 * 1024; // 2 Mo par morceau
const TENTATIVES_MAX_PAR_MORCEAU = 5;

function calculerEmpreinte(fichier) {
  // Identifiant stable pour un même fichier, sans avoir à le hasher
  // entièrement (trop lent pour de grosses vidéos côté navigateur).
  return `${fichier.name}_${fichier.size}_${fichier.lastModified}`;
}

function attendre(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Envoie `fichier` avec reprise automatique.
 * `onProgression(fraction)` est appelé régulièrement avec une valeur de 0 à 1.
 * Retourne { empreinte, taille_totale } à passer ensuite à /api/traduire.
 */
async function envoyerAvecReprise(fichier, onProgression) {
  const empreinte = calculerEmpreinte(fichier);

  const resInit = await fetchAuth("/api/upload/initialiser", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      empreinte,
      nom_fichier: fichier.name,
      taille_totale: fichier.size,
    }),
  });
  if (!resInit.ok) throw new Error("Impossible de démarrer l'envoi.");
  let { octets_recus } = await resInit.json();

  if (onProgression) onProgression(octets_recus / fichier.size);

  while (octets_recus < fichier.size) {
    const morceau = fichier.slice(octets_recus, octets_recus + TAILLE_MORCEAU);
    let tentative = 0;
    let succes = false;

    while (!succes && tentative < TENTATIVES_MAX_PAR_MORCEAU) {
      try {
        const res = await fetchAuth(
          `/api/upload/morceau/${empreinte}?offset=${octets_recus}`,
          { method: "POST", body: morceau }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        octets_recus = data.octets_recus;
        succes = true;
      } catch (err) {
        tentative += 1;
        if (tentative >= TENTATIVES_MAX_PAR_MORCEAU) {
          throw new Error(
            "Connexion instable : l'envoi s'est arrêté. Relance -- il reprendra où il en était."
          );
        }
        // Attente croissante avant de retenter (coupure réseau temporaire)
        await attendre(1000 * tentative);
      }
    }

    if (onProgression) onProgression(octets_recus / fichier.size);
  }

  return { empreinte, taille_totale: fichier.size };
}
