import os
import subprocess

def decouper_video(chemin_video, dossier_sortie, duree_chunk_secondes=60):
    """
    Découpe une vidéo lourde en plusieurs morceaux (chunks) d'une durée fixe
    en utilisant directement FFmpeg pour des performances maximales.
    """
    if not os.path.exists(dossier_sortie):
        os.makedirs(dossier_sortie)
        print(f"[+] Création du dossier pour les morceaux : {dossier_sortie}")

    print(f"[+] Début du découpage de la vidéo : {chemin_video}")
    
    # Commande FFmpeg magique pour découper sans réencoder (ultra rapide)
    # %03d_chunk.mp4 générera 000_chunk.mp4, 001_chunk.mp4, etc.
    motif_sortie = os.path.join(dossier_sortie, "%03d_chunk.mp4")
    
    commande = [
        'ffmpeg',
        '-i', chemin_video,
        '-c', 'copy', # 'copy' permet de copier les flux sans réencoder (vitesse maximale)
        '-map', '0',
        '-segment_time', str(duree_chunk_secondes),
        '-f', 'segment',
        '-reset_timestamps', '1',
        motif_sortie
    ]
    
    try:
        # Exécution de la commande système FFmpeg
        subprocess.run(commande, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        
        morceaux_generes = sorted(os.listdir(dossier_sortie))
        print(f"[✓] Découpage terminé ! {len(morceaux_generes)} morceaux générés dans '{dossier_sortie}'.")
        return morceaux_generes
    except subprocess.CalledProcessError as e:
        print(f"[X] Erreur lors du découpage avec FFmpeg : {e.stderr.decode()}")
        return []

# --- ZONE DE TEST ---
if __name__ == "__main__":
    # Teste avec une petite vidéo de plus d'une minute si tu as
    fichier_test = "ma_video_test.mp4"
    dossier_chunks = "chunks_video"
    
    if os.path.exists(fichier_test):
        # On découpe en morceaux de 30 secondes pour le test
        decouper_video(fichier_test, dossier_chunks, duree_chunk_secondes=30)
    else:
        print(f"[!] Rappel : Place une vidéo '{fichier_test}' dans le dossier pour tester.")