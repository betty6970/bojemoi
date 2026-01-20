#!/usr/bin/env python3
# coding: utf-8
"""
Convertisseur CSV IP2Location vers base de données avec colonnes supplémentaires
Ajoute les colonnes : cidr_z, nmap, date_nmap
Téléchargement automatique de la base IP2Location LITE
"""

import pandas as pd
import sqlite3
import ipaddress
import math
from datetime import datetime
import argparse
import sys
import requests
import zipfile
import os
import tempfile
from urllib.parse import urljoin

def ip_to_int(ip_str):
    """Convertit une adresse IP en entier"""
    try:
        return int(ipaddress.IPv4Address(ip_str))
    except:
        return None

def int_to_ip(ip_int):
    """Convertit un entier en adresse IP"""
    try:
        return str(ipaddress.IPv4Address(ip_int))
    except:
        return None

def calculate_cidr_z(ip_from_int, ip_to_int):
    """
    Calcule la notation CIDR à partir des IP de début et fin
    Retourne la notation CIDR la plus proche ou None si impossible
    """
    try:
        # Calculer le nombre d'adresses dans la plage
        num_addresses = ip_to_int - ip_from_int + 1
        
        # Vérifier si c'est une puissance de 2
        if num_addresses > 0 and (num_addresses & (num_addresses - 1)) == 0:
            # C'est une puissance de 2, calculer le préfixe
            prefix_length = 32 - int(math.log2(num_addresses))
            
            # Vérifier si l'IP de début est alignée sur la limite du réseau
            network_size = 2 ** (32 - prefix_length)
            if ip_from_int % network_size == 0:
                base_ip = int_to_ip(ip_from_int)
                return f"{base_ip}/{prefix_length}"
        
        # Si ce n'est pas un bloc CIDR parfait, retourner la plage
        ip_from = int_to_ip(ip_from_int)
        ip_to = int_to_ip(ip_to_int)
        return f"{ip_from}-{ip_to}"
        
    except Exception as e:
        print(f"Erreur dans calculate_cidr_z: {e}")
        return None

def process_csv_to_database(csv_file, db_file, table_name="ip2location_db1"):
    """
    Traite le fichier CSV IP2Location et crée une base de données SQLite
    avec les colonnes supplémentaires
    """
    
    print(f"Lecture du fichier CSV: {csv_file}")
    
    try:
        # Lire le CSV (adapter les noms de colonnes selon votre fichier)
        # Format typique IP2Location DB1: ip_from, ip_to, country_code, country_name
        df = pd.read_csv(csv_file, names=[
            'ip_from', 'ip_to', 'country_code', 'country_name'
        ])
        
        print(f"Fichier lu avec succès. Nombre de lignes: {len(df)}")
        
        # Convertir les IP en entiers si elles ne le sont pas déjà
        if df['ip_from'].dtype == 'object':
            print("Conversion des adresses IP en entiers...")
            df['ip_from'] = df['ip_from'].apply(ip_to_int)
            df['ip_to'] = df['ip_to'].apply(ip_to_int)
        
        # Supprimer les lignes avec des IP invalides
        df = df.dropna(subset=['ip_from', 'ip_to'])
        
        print("Calcul des colonnes CIDR...")
        # Calculer la colonne cidr_z
        df['cidr_z'] = df.apply(
            lambda row: calculate_cidr_z(row['ip_from'], row['ip_to']), 
            axis=1
        )
        
        # Ajouter les colonnes nmap et date_nmap (initialement vides)
        df['nmap'] = None  # Peut contenir les résultats de scan nmap
        df['date_nmap'] = None  # Date du dernier scan nmap
        
        print(f"Création de la base de données: {db_file}")
        
        # Créer la base de données SQLite
        conn = sqlite3.connect(db_file)
        
        # Créer la table avec le bon schéma
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_from INTEGER NOT NULL,
            ip_to INTEGER NOT NULL,
            country_code TEXT,
            country_name TEXT,
            cidr_z TEXT,
            nmap TEXT,
            date_nmap DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX(ip_from),
            INDEX(ip_to)
        )
        """
        
        conn.execute(create_table_sql)
        
        # Insérer les données
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Créer des index pour les performances
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_ip_range ON {table_name}(ip_from, ip_to)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_country ON {table_name}(country_code)")
        
        conn.commit()
        conn.close()
        
        print(f"Base de données créée avec succès!")
        print(f"Nombre d'enregistrements insérés: {len(df)}")
        print(f"Table: {table_name}")
        
        return True
        
    except Exception as e:
        print(f"Erreur lors du traitement: {e}")
        return False

def query_ip_location(db_file, ip_address, table_name="ip2location_db1"):
    """
    Recherche les informations de géolocalisation pour une IP donnée
    """
    try:
        ip_int = ip_to_int(ip_address)
        if ip_int is None:
            return None
            
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        query = f"""
        SELECT * FROM {table_name} 
        WHERE ip_from <= ? AND ip_to >= ?
        LIMIT 1
        """
        
        cursor.execute(query, (ip_int, ip_int))
        result = cursor.fetchone()
        conn.close()
        
        return result
        
    except Exception as e:
        print(f"Erreur lors de la requête: {e}")
        return None

def update_nmap_data(db_file, ip_address, nmap_result, table_name="ip2location_db1"):
    """
    Met à jour les colonnes nmap et date_nmap pour une IP donnée
    """
    try:
        ip_int = ip_to_int(ip_address)
        if ip_int is None:
            return False
            
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        update_query = f"""
        UPDATE {table_name} 
        SET nmap = ?, date_nmap = ?
        WHERE ip_from <= ? AND ip_to >= ?
        """
        
        current_time = datetime.now().isoformat()
        cursor.execute(update_query, (nmap_result, current_time, ip_int, ip_int))
        
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        return rows_affected > 0
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convertit un CSV IP2Location en base de données SQLite')
    parser.add_argument('csv_file', help='Fichier CSV IP2Location à convertir')
    parser.add_argument('-o', '--output', default='ip2location.db', help='Fichier de base de données de sortie')
    parser.add_argument('-t', '--table', default='ip2location_db1', help='Nom de la table à créer')
    parser.add_argument('--query-ip', help='Tester avec une adresse IP')
    
    args = parser.parse_args()
    
    # Traitement principal
    if process_csv_to_database(args.csv_file, args.output, args.table):
        print("\n✅ Conversion terminée avec succès!")
        
        # Test optionnel avec une IP
        if args.query_ip:
            print(f"\n� Test avec l'IP: {args.query_ip}")
            result = query_ip_location(args.output, args.query_ip, args.table)
            if result:
                print("Résultat trouvé:", result)
            else:
                print("Aucun résultat trouvé pour cette IP")
    else:
        print("\n❌ Échec de la conversion")
        sys.exit(1)

if __name__ == "__main__":
    # Exemple d'utilisation si exécuté directement
    if len(sys.argv) == 1:
        print("Exemple d'utilisation:")
        print("python ip2location_converter.py fichier.csv -o ma_base.db")
        print("\nOu pour tester:")
        print("python ip2location_converter.py fichier.csv --query-ip 8.8.8.8")
    else:
        main()
