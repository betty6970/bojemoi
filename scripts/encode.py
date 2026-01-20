#!/usr/bin/env python3
# -*- coding: iso-8859-15 -*-
"""
Solutions pour résoudre l'erreur d'encodage Python:
"Non-UTF-8 code starting with '\xf0' in file"
"""

import os
import sys
import chardet

def detect_file_encoding(file_path):
    """Détecte l'encodage d'un fichier."""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result
    except Exception as e:
        return {'encoding': None, 'confidence': 0, 'error': str(e)}

def fix_encoding_declaration(file_path, target_encoding='utf-8'):
    """Ajoute la déclaration d'encodage en début de fichier."""
    try:
        # Lire le fichier avec l'encodage détecté
        encoding_info = detect_file_encoding(file_path)
        detected_encoding = encoding_info.get('encoding', 'utf-8')
        
        print(f"Encodage détecté: {detected_encoding} (confiance: {encoding_info.get('confidence', 0):.2f})")
        
        # Lire le contenu
        with open(file_path, 'r', encoding=detected_encoding, errors='replace') as f:
            lines = f.readlines()
        
        # Vérifier si la déclaration d'encodage existe déjà
        has_encoding_declaration = False
        for i, line in enumerate(lines[:3]):  # Les 3 premières lignes
            if 'coding' in line or 'encoding' in line:
                has_encoding_declaration = True
                break
        
        # Ajouter la déclaration si elle n'existe pas
        if not has_encoding_declaration:
            # Trouver où insérer la déclaration
            insert_line = 0
            if lines and lines[0].startswith('#!'):  # Shebang présent
                insert_line = 1
            
            encoding_declaration = f'# -*- coding: {target_encoding} -*-\n'
            lines.insert(insert_line, encoding_declaration)
            
            # Réécrire le fichier
            with open(file_path, 'w', encoding=target_encoding, errors='replace') as f:
                f.writelines(lines)
            
            print(f"✅ Déclaration d'encodage ajoutée: {target_encoding}")
        else:
            print("ℹ️ Déclaration d'encodage déjà présente")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

def clean_non_utf8_chars(file_path, output_path=None):
    """Nettoie les caractères non-UTF-8 d'un fichier."""
    if output_path is None:
        output_path = file_path + '.cleaned'
    
    try:
        # Détecter l'encodage
        encoding_info = detect_file_encoding(file_path)
        detected_encoding = encoding_info.get('encoding', 'latin1')
        
        # Lire avec l'encodage détecté
        with open(file_path, 'r', encoding=detected_encoding, errors='replace') as f:
            content = f.read()
        
        # Nettoyer les caractères problématiques
        # Remplacer les caractères de remplacement
        content = content.replace('\ufffd', '?')  # Caractère de remplacement Unicode
        
        # Écrire en UTF-8 propre
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('#!/usr/bin/env python3\n')
            f.write('# -*- coding: utf-8 -*-\n')
            if not content.startswith('#'):
                f.write('\n')
            f.write(content)
        
        print(f"✅ Fichier nettoyé sauvegardé: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Erreur nettoyage: {e}")
        return None

def convert_file_encoding(input_path, output_path, source_encoding, target_encoding='utf-8'):
    """Convertit l'encodage d'un fichier."""
    try:
        # Lire avec l'encodage source
        with open(input_path, 'r', encoding=source_encoding, errors='replace') as f:
            content = f.read()
        
        # Ajouter les déclarations d'encodage appropriées
        lines = content.split('\n')
        
        # Construire le nouveau contenu
        new_lines = []
        
        # Garder le shebang s'il existe
        if lines and lines[0].startswith('#!'):
            new_lines.append(lines[0])
            lines = lines[1:]
        else:
            new_lines.append('#!/usr/bin/env python3')
        
        # Ajouter déclaration d'encodage
        new_lines.append(f'# -*- coding: {target_encoding} -*-')
        
        # Ajouter le reste du contenu
        new_lines.extend(lines)
        
        # Écrire avec le nouvel encodage
        with open(output_path, 'w', encoding=target_encoding) as f:
            f.write('\n'.join(new_lines))
        
        print(f"✅ Fichier converti: {source_encoding} → {target_encoding}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur conversion: {e}")
        return False

def analyze_encoding_problem(file_path):
    """Analyse détaillée du problème d'encodage."""
    print(f"� Analyse du fichier: {file_path}")
    print("-" * 50)
    
    # 1. Informations sur le fichier
    try:
        stat_info = os.stat(file_path)
        print(f"Taille: {stat_info.st_size} bytes")
        print(f"Permissions: {oct(stat_info.st_mode)[-3:]}")
    except Exception as e:
        print(f"❌ Impossible de lire les stats: {e}")
        return
    
    # 2. Détection d'encodage
    encoding_info = detect_file_encoding(file_path)
    print(f"Encodage détecté: {encoding_info}")
    
    # 3. Vérifier les premières lignes
    try:
        with open(file_path, 'rb') as f:
            first_bytes = f.read(1000)
            print(f"Premiers bytes (hex): {first_bytes[:50].hex()}")
            
        # Essayer de lire comme texte
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()[:10]
            print(f"Premières lignes:")
            for i, line in enumerate(lines, 1):
                print(f"  {i:3d}: {repr(line)}")
                
    except Exception as e:
        print(f"❌ Erreur lecture: {e}")
    
    # 4. Localiser ligne 436 spécifiquement
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            if len(lines) >= 436:
                print(f"\nLigne 436 problématique:")
                print(f"  Contenu: {repr(lines[435])}")  # Index 435 = ligne 436
                print(f"  Bytes: {lines[435].encode('utf-8', errors='replace').hex()}")
            else:
                print(f"❌ Fichier a seulement {len(lines)} lignes")
                
    except Exception as e:
        print(f"❌ Erreur analyse ligne 436: {e}")

def quick_fix(file_path):
    """Solution rapide pour corriger le fichier."""
    print(f"� Correction rapide de: {file_path}")
    
    backup_path = file_path + '.backup'
    
    try:
        # 1. Faire une sauvegarde
        with open(file_path, 'rb') as src:
            with open(backup_path, 'wb') as dst:
                dst.write(src.read())
        print(f"� Sauvegarde créée: {backup_path}")
        
        # 2. Nettoyer et corriger
        cleaned_path = clean_non_utf8_chars(file_path)
        
        if cleaned_path:
            # 3. Remplacer l'original
            import shutil
            shutil.move(cleaned_path, file_path)
            print(f"✅ Fichier corrigé et remplacé")
        
    except Exception as e:
        print(f"❌ Erreur correction: {e}")

# Script principal pour diagnostic et correction
if __name__ == '__main__':
    # Remplacez par le chemin de votre fichier
    problematic_file = '/opt/bojemoi/titi'
    
    if len(sys.argv) > 1:
        problematic_file = sys.argv[1]
    
    print("=== Diagnostic et Correction Encodage Python ===\n")
    
    # Vérifier que le fichier existe
    if not os.path.exists(problematic_file):
        print(f"❌ Fichier non trouvé: {problematic_file}")
        print("Usage: python script.py /chemin/vers/fichier.py")
        sys.exit(1)
    
    # 1. Analyser le problème
    analyze_encoding_problem(problematic_file)
    
    print(f"\n" + "="*50)
    
    # 2. Proposer la correction
    response = input("Voulez-vous corriger automatiquement ce fichier? (o/N): ")
    
    if response.lower() in ['o', 'oui', 'y', 'yes']:
        quick_fix(problematic_file)
    else:
        print("\n� Actions manuelles possibles:")
        print("1. Ajouter en début de fichier:")
        print("   # -*- coding: utf-8 -*-")
        print("\n2. Ou utiliser:")
        print("   # coding: utf-8")
        print("\n3. Pour nettoyer manuellement:")
        print(f"   python3 -c \"")
        print(f"import chardet")
        print(f"with open('{problematic_file}', 'rb') as f:")
        print(f"    print(chardet.detect(f.read()))\"")
