# OSINT Report — progruzspb.ru / 5.8.8.23
**Date** : 2026-02-22
**Analyste** : Bojemoi Lab
**Cible initiale** : IP `5.8.8.23` → domaine `progruzspb.ru`

---

## 1. IP 5.8.8.23

| Champ | Valeur |
|---|---|
| ASN | AS34665 — Petersburg Internet Network Ltd. (PIN DC) |
| Localisation | Saint-Pétersbourg, Russie |
| PTR | Aucun |
| Bloc | 5.8.8.0/24 |
| OS | Ubuntu 24.04 LTS |
| Ports ouverts | 22 (OpenSSH 9.6p1), 80/443 (nginx 1.24.0) |
| Tag Shodan | `eol-product` |
| CVEs | CVE-2025-23419 (nginx TLS), CVE-2023-44487 (HTTP/2 Rapid Reset) |
| Wayback Machine | Aucun snapshot sur l'IP directement |

### Historique IP
| Hostname | Période |
|---|---|
| `megahost1111.secureservercloud.net` | 2019-08 → 2020-02 |
| `progruzspb.ru` | 2025-09 → présent |

### Threat Intel IP
- 1 malware OTX (2021) : `ALF:PUA:Win32/Coinminer.MK!MTB` — hash `1bef44a9745600e9dca3f425a00ccdac13437523fee7291e4af01c1556ffbb55` → attribuable à l'ancien tenant `megahost1111`
- Fichier `.rar` distribué sur port **182** en 2018 (tenant précédent)
- IP actuellement whitelistée OTX, non blacklistée CleanTalk

---

## 2. Domaine progruzspb.ru

### Enregistrement
| Champ | Valeur |
|---|---|
| Créé | 2025-08-02 |
| Expire | 2026-08-02 |
| Registrar | PIN-RU (= même entité que l'hébergeur AS34665) |
| Registrant | "Private Person" — statut **UNVERIFIED** |
| Nameservers | may.ns.cloudflare.com, mike.ns.cloudflare.com |

### DNS
- Cloudflare DNS uniquement — **proxy désactivé**, IP origine exposée
- Aucun MX, SPF, DKIM, DMARC → domaine **spoofable**
- Aucun AAAA (pas d'IPv6)

### TLS (crt.sh — 18 certificats)
- Let's Encrypt : `progruzspb.ru` + `www.progruzspb.ru`
- Google Trust Services : `*.progruzspb.ru` + `progruzspb.ru` (via Cloudflare Universal SSL)
- Premier cert : 2025-08-04 (J+2 après enregistrement)
- Cert actuel valide jusqu'au 2026-05-06

### Site Web
| Champ | Valeur |
|---|---|
| Titre | "Gruzoperevozki" (transport de fret) |
| Langue | Russe |
| Type | Site statique 3 pages (index, service, we) |
| Stack | nginx, HTML/CSS/JS vanilla, WOW.js, Animate.css |
| Fonts | Google Fonts (Lato, Noto Sans, Open Sans, Roboto) |
| Analytics | **Aucune** (ni GA, ni Yandex Metrika) |
| Last-Modified | **2025-08-07** — jamais mis à jour depuis |
| robots.txt | 404 |
| sitemap.xml | 404 |

### Wayback Machine
| Date | Status |
|---|---|
| 2025-08-30 | 200 OK |
| 2025-10-27 | warc/revisit (inchangé) |
| 2026-01-23 | 200 OK |

### Threat Intel domaine
- OTX : 0 pulse, clean
- URLhaus : non indexé
- Non blacklisté

---

## 3. Contacts & Attribution

| Canal | Valeur | Notes |
|---|---|---|
| Téléphone | +7 914 231-82-61 | Préfixe **Extrême-Orient russe** — incohérent avec SPb |
| Telegram | @ProGruzspb | Compte personnel, nom affiché : **"Nik"** |
| WhatsApp | +79142318261 | Même numéro |
| Email (HTML commenté) | `gruzoperevozki@gmail.com` | Présent dans source mais désactivé |

---

## 4. Holehe — gruzoperevozki@gmail.com

- 121 sites vérifiés
- Résultat majoritairement `[x]` (rate limit) — non concluant
- Confirmés **absents** (`[-]`) : mail.ru, ok.ru, rambler.ru, twitter.com, amazon.com, adobe.com
- **Notable** : absent sur les plateformes russes majeures (mail.ru, ok.ru) → email probablement créé pour ce projet uniquement

---

## 5. GHunt — gruzoperevozki@gmail.com

- GHunt v2.3.3 installé
- **Non exécuté** : nécessite authentification Google (cookies `__Secure-1PSID` / `__Secure-1PSIDTS`)
- En attente de credentials pour compléter l'analyse

---

## 6. Signaux suspects (synthèse)

| Signal | Niveau |
|---|---|
| Registrar = Hébergeur (PIN-RU) | Moyen |
| Statut UNVERIFIED au registre .RU | Moyen |
| Numéro +7 914 (Extrême-Orient) pour business "SPb" | Moyen |
| Site jamais mis à jour depuis création (6 mois) | Faible |
| Aucune analytics, aucun SEO de base | Faible |
| Email Gmail commenté dans le HTML | Faible |
| Historique IP : coinminer 2021, .rar port 182 (2018) | Faible (ancien tenant) |
| Cloudflare proxy désactivé — IP exposée | Faible (mauvaise pratique) |
| Opérateur Telegram "Nik" — profil vide | Faible |

**Conclusion provisoire** : site vitrine à très faible activité, possiblement fictif ou abandonné. Pas de marqueur actif de malveillance sur le domaine actuel. L'historique de l'IP appartient à des tenants précédents.

---

## 7. Pistes non explorées

- [ ] GHunt sur `gruzoperevozki@gmail.com` (nécessite auth Google)
- [ ] OSINT téléphone +7 914 231-82-61 (GetContact, TrueCaller)
- [ ] Analyse Telegram @ProGruzspb (contenu privé, nécessite compte)
- [ ] Scan ports non-standard sur 5.8.8.23 (port 182 historique)
- [ ] Voisins /24 — 212 hôtes en base msf à croiser
- [ ] HaveIBeenPwned sur `gruzoperevozki@gmail.com`
- [ ] Hash malware `1bef44a9...` → VirusTotal / Hybrid Analysis
