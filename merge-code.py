#python merge-code.py --tree --tree-file arborescence.txt

import os
import argparse

# Mode d'exclusion (original)
EXCLUDED_DIRS = {".gitignore","__pycache__", ".git","venv","skillbase.egg-info","logs","docs","pids",".qodo"}
EXCLUDED_EXTENSIONS = {".md",".pdf", ".log", ".pid", ".gitignore",".egg-info", ".bak"}
EXCLUDE_ALL = False  # Nouvelle option pour exclure tout par défaut

# Mode d'inclusion (nouveau)
INCLUDED_DIRS = {""}  # Ensemble des dossiers à inclure par défaut
INCLUDED_EXTENSIONS = {".py", ".js", ".html", ".css", ".sql", ".json"}  # Extensions courantes de code

def is_text_file(filepath):
    """ Vérifie si un fichier est lisible en UTF-8 (exclut les binaires) """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read(1024)  # Lire une petite partie du fichier pour tester
        return True
    except UnicodeDecodeError:
        return False

def merge_code_to_txt(source_dir, output_file, mode="exclude", generate_tree=False):
    tree_structure = []
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Compteurs pour les statistiques
        files_included = 0
        files_excluded = 0
        
        for root, dirs, files in os.walk(source_dir):
            relative_path = os.path.relpath(root, source_dir)
            dir_name = os.path.basename(root)
            
            # Filtrer les dossiers selon le mode
            if mode == "exclude":
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            else:  # mode == "include"
                if INCLUDED_DIRS:
                    # Construire le chemin relatif complet pour la vérification
                    if relative_path == '.':
                        rel_path_for_check = ''
                    else:
                        rel_path_for_check = relative_path
                    
                    # Si au moins un dossier est spécifié, ne garder que les dossiers qui:
                    # 1. Sont directement dans la liste d'inclusion
                    # 2. Ont un parent qui est dans la liste d'inclusion
                    # 3. Sont parents d'un dossier dans la liste d'inclusion
                    keep_dirs = []
                    for d in dirs:
                        # Construire le chemin complet pour ce dossier
                        if rel_path_for_check:
                            current_path = f"{rel_path_for_check}/{d}"
                        else:
                            current_path = d
                        
                        # Règle 1: Le dossier lui-même est dans la liste
                        should_keep = current_path in INCLUDED_DIRS or d in INCLUDED_DIRS
                        
                        # Règle 2: Un parent du dossier est dans la liste
                        if not should_keep:
                            for included_dir in INCLUDED_DIRS:
                                # Si le dossier courant est contenu dans un dossier inclus
                                if rel_path_for_check.startswith(included_dir):
                                    should_keep = True
                                    break
                        
                        # Règle 3: Le dossier est parent d'un dossier inclus
                        if not should_keep:
                            for included_dir in INCLUDED_DIRS:
                                # Si un dossier inclus commence par le chemin du dossier courant
                                if included_dir.startswith(current_path + '/') or included_dir == current_path:
                                    should_keep = True
                                    break
                        
                        if should_keep:
                            keep_dirs.append(d)
                    
                    dirs[:] = keep_dirs
            
            for file in files:
                file_path = os.path.join(root, file)
                _, extension = os.path.splitext(file)
                
                # Vérifier si le fichier doit être inclus selon le mode
                if mode == "exclude":
                    # Si EXCLUDE_ALL est actif, tout exclure sauf si explicitement inclus
                    if EXCLUDE_ALL:
                        # Vérifier d'abord si ce fichier est dans un dossier explicitement inclus
                        is_in_included_dir = False
                        if INCLUDED_DIRS:
                            for included_dir in INCLUDED_DIRS:
                                if relative_path == included_dir or relative_path.startswith(included_dir + '/'):
                                    is_in_included_dir = True
                                    break
                        
                        # Ensuite vérifier l'extension
                        has_included_ext = extension.lower() in INCLUDED_EXTENSIONS
                        
                        if not (is_in_included_dir and has_included_ext):
                            print(f"Ignoré (exclude_all) : {file_path}")
                            files_excluded += 1
                            continue
                    # Sinon, appliquer la logique normale d'exclusion
                    elif extension.lower() in EXCLUDED_EXTENSIONS or not is_text_file(file_path):
                        print(f"Ignoré : {file_path}")
                        files_excluded += 1
                        continue
                else:  # mode == "include"
                    if INCLUDED_EXTENSIONS and extension.lower() not in INCLUDED_EXTENSIONS:
                        print(f"Ignoré : {file_path}")
                        files_excluded += 1
                        continue
                    if not is_text_file(file_path):
                        print(f"Ignoré (binaire) : {file_path}")
                        files_excluded += 1
                        continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(f"\n# --- {file_path} ---\n\n")
                        outfile.write(infile.read() + '\n')
                        print(f"Fusionné : {file_path}")
                        files_included += 1
                        
                        # Ajouter au tree_structure si demandé
                        if generate_tree:
                            rel_path = os.path.relpath(file_path, source_dir)
                            tree_structure.append(rel_path)
                except Exception as e:
                    print(f"Erreur lors de la lecture de {file_path}: {e}")
                    files_excluded += 1

def main():
    parser = argparse.ArgumentParser(description='Fusionner des fichiers de code dans un seul fichier texte')
    parser.add_argument('--source', type=str, default="./", help='Répertoire source')
    parser.add_argument('--output', type=str, default="merged_code.txt", help='Fichier de sortie')
    parser.add_argument('--mode', type=str, choices=['include', 'exclude'], default='exclude', 
                        help='Mode de sélection: exclude (par défaut, exclut les répertoires/extensions spécifiés) ou include (inclut uniquement les répertoires/extensions spécifiés)')
    parser.add_argument('--dirs', type=str, nargs='*', help='Répertoires à inclure ou exclure (selon le mode). Format: chemin/relatif/au/dossier ou nom_dossier pour dossiers à la racine')
    parser.add_argument('--extensions', type=str, nargs='*', help='Extensions à inclure ou exclure (selon le mode). Par exemple: py js html')
    parser.add_argument('--exclude-all', action='store_true', help='Exclure tout par défaut, et inclure uniquement ce qui est spécifié avec --dirs et --extensions')
    parser.add_argument('--tree', action='store_true', help='Générer une arborescence des fichiers fusionnés à la fin du fichier de sortie')
    parser.add_argument('--tree-file', type=str, help='Générer une arborescence des fichiers fusionnés dans un fichier séparé')
    
    args = parser.parse_args()
    
    # Mise à jour des ensembles selon les arguments
    global INCLUDED_DIRS, INCLUDED_EXTENSIONS
    global EXCLUDED_DIRS, EXCLUDED_EXTENSIONS
    global EXCLUDE_ALL
    
    # Option pour tout exclure par défaut
    if args.exclude_all:
        EXCLUDE_ALL = True
        
    if args.mode == 'include':
        if args.dirs:
            INCLUDED_DIRS = set(args.dirs)
        if args.extensions:
            INCLUDED_EXTENSIONS = set(args.extensions)
    else:  # mode == 'exclude'
        if args.dirs:
            EXCLUDED_DIRS = set(args.dirs)
        if args.extensions:
            EXCLUDED_EXTENSIONS = set(args.extensions)
        # Si on utilise exclude_all, on a besoin des dirs/extensions à inclure même en mode exclude
        if EXCLUDE_ALL:
            if args.dirs:
                INCLUDED_DIRS = set(args.dirs)
            if args.extensions:
                INCLUDED_EXTENSIONS = set(args.extensions)
    
    # Normaliser les extensions pour s'assurer qu'elles commencent par un point
    if INCLUDED_EXTENSIONS:
        INCLUDED_EXTENSIONS = {ext if ext.startswith('.') else '.' + ext for ext in INCLUDED_EXTENSIONS}
    if EXCLUDED_EXTENSIONS:
        EXCLUDED_EXTENSIONS = {ext if ext.startswith('.') else '.' + ext for ext in EXCLUDED_EXTENSIONS}
    
    print(f"Mode: {args.mode}")
    if EXCLUDE_ALL:
        print("Mode exclude-all: tous les fichiers sont exclus par défaut")
        print(f"Dossiers spécifiquement inclus: {INCLUDED_DIRS}")
        print(f"Extensions spécifiquement incluses: {INCLUDED_EXTENSIONS}")
    elif args.mode == 'include':
        if INCLUDED_DIRS:
            print(f"Dossiers inclus: {INCLUDED_DIRS}")
        else:
            print("Aucun dossier spécifiquement inclus, parcours de tous les dossiers (sauf exclus)")
        print(f"Extensions incluses: {INCLUDED_EXTENSIONS}")
    else:
        print(f"Dossiers exclus: {EXCLUDED_DIRS}")
        print(f"Extensions exclues: {EXCLUDED_EXTENSIONS}")
    
    # Normaliser les chemins des dossiers inclus
    if INCLUDED_DIRS:
        # Remplacer les backslashes par des forward slashes pour uniformité
        INCLUDED_DIRS = {dir_path.replace('\\', '/') for dir_path in INCLUDED_DIRS}
        # Supprimer les slashes au début et à la fin
        INCLUDED_DIRS = {dir_path.strip('/') for dir_path in INCLUDED_DIRS}
        print(f"Dossiers inclus (normalisés): {INCLUDED_DIRS}")
    
    merge_code_to_txt(args.source, args.output, args.mode, args.tree)
    
    # Si une arborescence séparée est demandée, la générer
    if args.tree_file:
        try:
            # Réutiliser la fonction merge_code mais en mode "dry run" (sans écrire le contenu des fichiers)
            # en créant une fonction helper qui maintient les mêmes décisions d'inclusion/exclusion
            def write_tree_only(src_dir, tree_file):
                files_list = []
                for root, dirs, files in os.walk(src_dir):
                    relative_path = os.path.relpath(root, src_dir)
                    
                    # Appliquer les mêmes filtres que dans la fonction principale
                    if args.mode == "exclude":
                        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                    elif INCLUDED_DIRS:
                        # Filtrer les dossiers selon les règles d'inclusion
                        keep_dirs = []
                        for d in dirs:
                            if relative_path == '.':
                                rel_path_for_check = ''
                            else:
                                rel_path_for_check = relative_path
                                
                            if rel_path_for_check:
                                current_path = f"{rel_path_for_check}/{d}"
                            else:
                                current_path = d
                            
                            # Appliquer les mêmes règles d'inclusion que dans la fonction principale
                            should_keep = current_path in INCLUDED_DIRS or d in INCLUDED_DIRS
                            if not should_keep:
                                for included_dir in INCLUDED_DIRS:
                                    if rel_path_for_check.startswith(included_dir):
                                        should_keep = True
                                        break
                            if not should_keep:
                                for included_dir in INCLUDED_DIRS:
                                    if included_dir.startswith(current_path + '/') or included_dir == current_path:
                                        should_keep = True
                                        break
                            
                            if should_keep:
                                keep_dirs.append(d)
                        
                        dirs[:] = keep_dirs
                    
                    # Pour chaque fichier, vérifier s'il serait inclus
                    for file in files:
                        file_path = os.path.join(root, file)
                        _, extension = os.path.splitext(file)
                        
                        # Appliquer les mêmes règles que dans la fonction principale
                        include_file = True
                        if args.mode == "exclude":
                            if EXCLUDE_ALL:
                                is_in_included_dir = False
                                if INCLUDED_DIRS:
                                    for included_dir in INCLUDED_DIRS:
                                        if relative_path == included_dir or relative_path.startswith(included_dir + '/'):
                                            is_in_included_dir = True
                                            break
                                
                                has_included_ext = extension.lower() in INCLUDED_EXTENSIONS
                                include_file = is_in_included_dir and has_included_ext
                            else:
                                include_file = not (extension.lower() in EXCLUDED_EXTENSIONS or not is_text_file(file_path))
                        else:  # mode == "include"
                            include_file = (not INCLUDED_EXTENSIONS or extension.lower() in INCLUDED_EXTENSIONS) and is_text_file(file_path)
                        
                        if include_file:
                            rel_path = os.path.relpath(file_path, src_dir)
                            files_list.append(rel_path)
                
                # Écrire l'arborescence dans un fichier séparé
                with open(tree_file, 'w', encoding='utf-8') as tree_outfile:
                    tree_outfile.write("# ARBORESCENCE DES FICHIERS FUSIONNÉS\n\n")
                    
                    # Trier pour une meilleure lisibilité
                    files_list.sort()
                    
                    # Générer une arborescence graphique
                    current_dirs = []
                    for path in files_list:
                        parts = path.split(os.sep)
                        filename = parts[-1]
                        dirs = parts[:-1]
                        
                        # Déterminer les niveaux de dossiers et les préfixes appropriés
                        for i, dir_name in enumerate(dirs):
                            if i >= len(current_dirs):
                                prefix = "    " * i
                                if i > 0:
                                    prefix = prefix[:-4] + "├── "
                                tree_outfile.write(f"{prefix}{dir_name}/\n")
                                current_dirs.append(dir_name)
                            elif current_dirs[i] != dir_name:
                                prefix = "    " * i
                                if i > 0:
                                    prefix = prefix[:-4] + "├── "
                                tree_outfile.write(f"{prefix}{dir_name}/\n")
                                current_dirs[i] = dir_name
                                current_dirs = current_dirs[:i+1]
                        
                        # Écrire le fichier
                        prefix = "    " * len(dirs)
                        if len(dirs) > 0:
                            prefix = prefix[:-4] + "└── "
                        tree_outfile.write(f"{prefix}{filename}\n")
                
                print(f"Arborescence générée dans {tree_file}")
            
            write_tree_only(args.source, args.tree_file)
        except Exception as e:
            print(f"Erreur lors de la génération de l'arborescence séparée : {e}")
    
    print(f"✅ Fusion terminée. Résultat dans {args.output}")

if __name__ == "__main__":
    main()