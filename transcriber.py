import os
import librosa

# --- CONFIGURATION STRICTE DES DOSSIERS ---
os.environ["HF_HOME"] = os.path.join(os.getcwd(), "modeles_ia")

from transformers import pipeline

# On charge le modèle UNE SEULE FOIS ici globalement
print("[+] Chargement initial du modèle d'IA Whisper (une seule fois)...")
generateur_texte = pipeline(
    "automatic-speech-recognition", 
    model="openai/whisper-base",
    chunk_length_s=30
)

def transcrire_chunk(chemin_video_chunk):
    """
    Transcrit proprement un morceau vidéo en utilisant le modèle déjà chargé.
    """
    # Extraction audio via librosa
    audio, taux_echantillonnage = librosa.load(chemin_video_chunk, sr=16000)
    
    # Transcription directe sans recharger le pipeline
    resultat = generateur_texte(
        audio, 
        generate_kwargs={
            "language": "french", 
            "task": "transcribe",
            "no_repeat_ngram_size": 2
        }
    )
    
    return resultat["text"].strip()

# --- AUTOMATISATION GLOBALE ---
if __name__ == "__main__":
    dossier_chunks = "chunks_video"
    fichier_sortie = "transcription_totale.txt"
    
    if not os.path.exists(dossier_chunks):
        print(f"[!] Erreur : Le dossier '{dossier_chunks}' n'existe pas.")
        exit()
        
    liste_morceaux = [f for f in os.listdir(dossier_chunks) if f.endswith(".mp4")]
    liste_morceaux.sort()
    
    if not liste_morceaux:
        print(f"[!] Aucun fichier vidéo trouvé.")
        exit()
        
    print(f"[===] Début de la transcription rapide de {len(liste_morceaux)} morceaux [===]")
    
    with open(fichier_sortie, "w", encoding="utf-8") as f_txt:
        for i, nom_fichier in enumerate(liste_morceaux):
            chemin_complet = os.path.join(dossier_chunks, nom_fichier)
            print(f"Avancement : {i+1}/{len(liste_morceaux)} ({nom_fichier})", end="\r")
            
            try:
                texte_chunk = transcrire_chunk(chemin_complet)
                
                # Nettoyage rapide des hallucinations
                hallucinations = ["Sous-titres réalisés par l'Ontario", "Sous-titres réalisés", "Ontario"]
                for hal in hallucinations:
                    texte_chunk = texte_chunk.replace(hal, "")
                
                texte_chunk = texte_chunk.strip()
                
                if texte_chunk:
                    f_txt.write(f"[{nom_fichier}] : {texte_chunk}\n")
                    
            except Exception as e:
                print(f"\n[!] Erreur sur {nom_fichier} : {e}")
                
    print(f"\n[===] TOUT EST TERMINÉ ! Résultat dans '{fichier_sortie}' [===]")