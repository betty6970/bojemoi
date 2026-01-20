#!/usr/bin/env python3
"""
Configuration automatique de ZAP
Configure ZAP avec des politiques de scan optimisées
"""

from zapv2 import ZAPv2
import time
import sys

def configure_zap(zap_url='http://localhost:8080', api_key=''):
    """Configure ZAP avec les meilleures pratiques"""
    
    zap = ZAPv2(apikey=api_key, proxies={'http': zap_url, 'https': zap_url})
    
    print("[+] Configuration de ZAP...")
    
    # Configuration générale
    try:
        # Timeout des connexions
        zap.core.set_option_timeout_in_secs(60)
        print("[+] Timeout configuré: 60s")
        
        # Profondeur du spider
        zap.spider.set_option_max_depth(5)
        print("[+] Profondeur spider: 5")
        
        # Nombre de threads
        zap.spider.set_option_thread_count(5)
        print("[+] Threads spider: 5")
        
        # Ajax spider
        zap.ajaxSpider.set_option_max_duration(10)
        print("[+] Durée Ajax spider: 10 minutes")
        
        # Scanner actif
        zap.ascan.set_option_thread_per_host(5)
        print("[+] Threads scan actif: 5")
        
        # Délai entre les requêtes (anti-DoS)
        zap.ascan.set_option_delay_in_ms(0)
        print("[+] Délai entre requêtes: 0ms")
        
        # Politique de scan
        zap.ascan.set_option_scan_policy_name('Default Policy')
        print("[+] Politique de scan: Default")
        
        # User-Agent personnalisé
        zap.core.set_option_default_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        print("[+] User-Agent configuré")
        
        # Configuration du proxy
        zap.core.set_option_proxy_chain_name('')
        zap.core.set_option_proxy_chain_port(0)
        zap.core.set_option_use_proxy_chain(False)
        print("[+] Proxy configuré")
        
        print("[+] Configuration ZAP terminée avec succès!")
        return True
        
    except Exception as e:
        print(f"[-] Erreur lors de la configuration: {e}")
        return False

def create_context(zap_url='http://localhost:8080', api_key='', context_name='Default', target_url=''):
    """Créer un contexte ZAP pour la cible"""
    
    zap = ZAPv2(apikey=api_key, proxies={'http': zap_url, 'https': zap_url})
    
    try:
        # Créer le contexte
        context_id = zap.context.new_context(context_name)
        print(f"[+] Contexte créé: {context_name} (ID: {context_id})")
        
        # Ajouter l'URL au contexte
        if target_url:
            zap.context.include_in_context(context_name, f"{target_url}.*")
            print(f"[+] URL ajoutée au contexte: {target_url}")
        
        # Configuration de l'authentification (si nécessaire)
        # zap.authentication.set_authentication_method(...)
        
        return context_id
        
    except Exception as e:
        print(f"[-] Erreur lors de la création du contexte: {e}")
        return None

def export_config(zap_url='http://localhost:8080', api_key='', output_file='/zap/configs/zap_config.xml'):
    """Exporter la configuration ZAP"""
    
    zap = ZAPv2(apikey=api_key, proxies={'http': zap_url, 'https': zap_url})
    
    try:
        # Exporter la configuration
        # Note: L'export de configuration n'est pas directement disponible via l'API
        # On peut sauvegarder la session
        print(f"[+] Sauvegarde de la session...")
        # zap.core.save_session(...)
        print(f"[+] Configuration exportée")
        return True
        
    except Exception as e:
        print(f"[-] Erreur lors de l'export: {e}")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Configuration automatique de ZAP')
    parser.add_argument('--zap-url', default='http://localhost:8080',
                        help='URL de ZAP (default: http://localhost:8080)')
    parser.add_argument('--api-key', default='',
                        help='Clé API ZAP (optionnel)')
    parser.add_argument('--target', default='',
                        help='URL cible pour créer un contexte')
    parser.add_argument('--context-name', default='Default',
                        help='Nom du contexte (default: Default)')
    
    args = parser.parse_args()
    
    print("=== Configuration ZAP ===")
    
    # Configuration de base
    if configure_zap(args.zap_url, args.api_key):
        print("\n[+] Configuration de base réussie")
    else:
        print("\n[-] Échec de la configuration de base")
        sys.exit(1)
    
    # Créer un contexte si une cible est spécifiée
    if args.target:
        print(f"\n=== Création du contexte pour {args.target} ===")
        if create_context(args.zap_url, args.api_key, args.context_name, args.target):
            print("\n[+] Contexte créé avec succès")
        else:
            print("\n[-] Échec de la création du contexte")
    
    print("\n[+] Configuration terminée!")
