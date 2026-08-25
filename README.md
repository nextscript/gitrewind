<p align="center"><img src="https://github.com/nextscript/gitrewind/raw/refs/heads/main/GitRewind_icon_animated.svg" width="350" height="350"></p>

# GitRewind

**GitRewind** ist ein grafisches Rollback-Tool für GitHub-Repositories. Es hilft dabei, einen fehlerhaften Commit rückgängig zu machen, indem der lokale `main`-Branch gezielt auf einen früheren, funktionierenden Commit zurückgesetzt und anschließend mit `--force-with-lease` zu GitHub übertragen wird.

> **Wichtig:** GitRewind verändert die Commit-Historie des Ziel-Branches. Nutze das Tool nur, wenn du verstehst, dass ein Rollback auf `main` neuere Commits aus der sichtbaren Branch-Historie entfernen kann.

---
<details>
<summary><h2>1. Was ist GitRewind?</h2></summary>

GitRewind ist eine Desktop-Anwendung mit grafischer Oberfläche für Git-Rollbacks.

Das Tool verbindet sich über einen GitHub Personal Access Token mit deinem GitHub-Konto, lädt deine Repositories sowie deren Commit-Historie und erlaubt dir anschließend, einen früheren Commit als neuen Stand von `main` festzulegen.

Der grundlegende Ablauf ist:

```text
GitHub anmelden
    ↓
Repository auswählen
    ↓
Commit-Historie laden
    ↓
guten Ziel-Commit auswählen
    ↓
kaputten/problematischen Commit auswählen
    ↓
lokales Backup anlegen
    ↓
main lokal auf Ziel-Commit setzen
    ↓
Remote-Stand aktualisieren
    ↓
git push --force-with-lease
```

GitRewind nutzt bewusst `--force-with-lease` statt eines blinden `--force`, damit ein Push abgelehnt wird, wenn sich der Remote-Branch unerwartet verändert hat.

---
</details>
<details>
    
<summary><h2>2. Für was braucht man das Tool?</h2></summary>


GitRewind ist für Situationen gedacht, in denen ein neuer Commit ein Repository beschädigt hat und du schnell auf einen vorherigen funktionierenden Zustand zurück möchtest.

Typische Beispiele:

- Ein neuer Commit verursacht Fehler oder Abstürze.
- Eine größere Änderung soll vollständig zurückgenommen werden.
- `main` soll wieder exakt auf einen bekannten funktionierenden Commit zeigen.
- Du möchtest den Rollback ohne manuelle Git-Kommandos durchführen.
- Du möchtest vor dem Rollback automatisch einen lokalen Backup-Branch behalten.

Das Tool ist **kein Ersatz für normale Reverts**. Wenn du die Historie nicht umschreiben möchtest oder mehrere Personen gleichzeitig an demselben Branch arbeiten, ist ein normaler `git revert` häufig die sicherere Lösung.

---
</details>
<details>
<summary><h2>3. Wie funktioniert GitRewind?</h2></summary>

### GitHub-Verbindung

Nach dem Start meldest du dich mit einem GitHub Personal Access Token an.

GitRewind verwendet die GitHub API unter anderem zum:

- Prüfen des Tokens
- Laden der Repository-Liste
- Laden der Commit-Historie
- Prüfen der Repository-Berechtigungen

Die Commit-Historie wird über die GitHub API geladen. Die aktuelle Anwendung lädt dabei bis zu **500 Commits**.

### Lokaler Rollback

Nach Auswahl des Ziel-Commits führt GitRewind sinngemäß folgende Schritte aus:

```bash
git fetch
git branch backup-before-rollback-<COMMIT>
git checkout -B main <ZIEL-COMMIT>
```

Existiert der lokale Repository-Ordner noch nicht, wird das Repository vorher geklont.

### Push zu GitHub

Vor dem eigentlichen Push wird der aktuelle Remote-Stand erneut geladen.

Danach wird `main` mit einem geschützten Force-Push aktualisiert:

```bash
git push --force-with-lease ...
```

`--force-with-lease` ist sicherer als ein einfacher `--force`, weil Git dabei prüft, ob der erwartete Remote-Stand noch aktuell ist.

### Backup

Vor dem Rollback wird lokal ein Backup-Branch erzeugt:

```text
backup-before-rollback-<PROBLEM-COMMIT>
```

Existiert dieser Branch bereits, wird das vorhandene Backup beibehalten.

---
</details>
<details>
<summary><h2>4. Was braucht man, um GitRewind nutzen zu können?</h2></summary>

### Allgemeine Voraussetzungen

Du brauchst:

- einen GitHub-Account
- Zugriff auf mindestens ein GitHub-Repository
- einen GitHub Personal Access Token
- Git auf dem Rechner
- eine Internetverbindung zu GitHub
- Python 3.10 oder neuer
- PyQt6

Python 3.10 oder neuer ist erforderlich, weil der Code moderne Python-Typnotation wie `Path | None` verwendet.

### Python-Abhängigkeiten

Installiere mindestens:

```bash
pip install PyQt6
```

Unter macOS und Linux wird zusätzlich das Python-Paket `keyring` für den sicheren System-Schlüsselspeicher verwendet:

```bash
pip install keyring
```

Unter Linux wird für Secret Service typischerweise zusätzlich benötigt:

```bash
pip install secretstorage
```

GitRewind verwendet dabei **keinen selbst erzeugten Verschlüsselungsschlüssel neben der Anwendung**.

Git muss separat installiert und über die Kommandozeile erreichbar sein:

```bash
git --version
```

Wenn dieser Befehl funktioniert, kann GitRewind Git normalerweise ebenfalls finden.

---
</details>
<details>
<summary><h2>5. Was muss ich beim GitHub API Token beachten?</h2></summary>

GitHub nennt diese Zugangsdaten **Personal Access Tokens (PAT)**.

Für GitRewind ist ein **Fine-Grained Personal Access Token** empfehlenswert, weil du damit den Zugriff auf bestimmte Repositories und Berechtigungen begrenzen kannst.

### Empfohlene Fine-Grained-Einstellungen

Unter:

```text
GitHub
→ Settings
→ Developer settings
→ Personal access tokens
→ Fine-grained tokens
```

solltest du Folgendes einstellen:

### Repository access

Am sichersten:

```text
Only select repositories
```

und danach nur die Repositories auswählen, die GitRewind tatsächlich verwalten darf.

### Repository permissions

Für den normalen Betrieb:

| Berechtigung | Einstellung |
|---|---|
| Metadata | Read |
| Contents | Read and write |

`Metadata: Read` wird für Repository-Metadaten und Repository-Abfragen benötigt. `Contents: Read and write` ist die entscheidende Berechtigung für Schreiboperationen auf Repository-Inhalte bzw. Git-Referenzen. [GitHub, Permissions required for fine-grained personal access tokens, https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens]

### Workflow-Dateien

Wenn der zurückgesetzte Stand Änderungen unter:

```text
.github/workflows/
```

betrifft, kann zusätzlich folgende Berechtigung erforderlich sein:

```text
Workflows: Read and write
```

GitHub behandelt Workflow-bezogene Schreiboperationen gesondert. [GitHub, Permissions required for fine-grained personal access tokens, https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens]

### Nicht benötigte Rechte

GitRewind braucht für seinen normalen Zweck keine pauschalen Schreibrechte auf:

- Actions
- Issues
- Discussions
- Deployments
- Secrets
- Administration
- Codespaces
- Dependabot
- Pages
- Repository Hooks

Vergib grundsätzlich nur die Berechtigungen, die wirklich benötigt werden.

### Branch Protection und Rulesets

Auch mit einem korrekt berechtigten Token kann GitHub den Rollback blockieren, wenn `main` durch eine Branch Protection oder ein Ruleset gegen Force-Pushes geschützt ist.

In diesem Fall musst du die Repository-Regeln prüfen:

```text
Repository
→ Settings
→ Rules
→ Rulesets
```

bzw.:

```text
Repository
→ Settings
→ Branches
```

GitRewind deaktiviert solche Schutzmechanismen nicht automatisch.

---
</details>
<details>
<summary><h2>6. Auf welchen Betriebssystemen kann GitRewind laufen?</h2></summary>

Der Python-/PyQt6-Code ist grundsätzlich für folgende Desktop-Systeme ausgelegt:

- Windows
- Linux
- macOS

### Windows

Windows ist die derzeit am besten integrierte Plattform, insbesondere bei der Speicherung des GitHub-Tokens.

### Linux

Linux funktioniert, wenn folgende Komponenten vorhanden sind:

- Python
- PyQt6
- Git
- `cryptography`

Je nach Desktop-Umgebung können zusätzliche Qt-Systempakete erforderlich sein.

### macOS

macOS benötigt ebenfalls:

- Python
- PyQt6
- Git
- `cryptography`

---
</details>
<details>
<summary><h2>7. Wie sicher ist es, meinen GitHub API Key dort einzugeben?</h2></summary>

### Kurzfassung

GitRewind speichert den GitHub Personal Access Token plattformspezifisch im sicheren Schlüsselspeicher des Betriebssystems:

| Betriebssystem | Speicherung |
|---|---|
| Windows | Windows DPAPI |
| macOS | Apple Keychain über `keyring` |
| Linux | Secret Service / KWallet über `keyring` |

Der GitHub-Token wird auf macOS und Linux **nicht zusammen mit einem eigenen Verschlüsselungsschlüssel neben GitRewind gespeichert**.

---

### Windows – DPAPI

Unter Windows verwendet GitRewind die Windows Data Protection API (**DPAPI**) über `CryptProtectData`.

DPAPI schützt die gespeicherten Daten über den Windows-Benutzerkontext. Die verschlüsselten Daten können normalerweise nicht einfach auf einen anderen Benutzer oder Rechner kopiert und dort entschlüsselt werden.

[Microsoft, CryptProtectData function, https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata]

GitRewind speichert dabei nur die von DPAPI geschützten Daten lokal.

---

### macOS – Apple Keychain

Unter macOS wird der GitHub-Token über das Python-Paket `keyring` im **Apple Keychain** gespeichert.

Der eigentliche Token liegt dadurch nicht als Klartext und auch nicht zusammen mit einem eigenen Entschlüsselungsschlüssel im GitRewind-Ordner.

Apple Keychain ist der vom Betriebssystem vorgesehene geschützte Speicher für Passwörter, Tokens und andere Zugangsdaten.

[Apple, Keychain Services, https://developer.apple.com/documentation/security/keychain-services]

Eine eventuell von GitRewind angelegte lokale Metadaten-Datei enthält **nicht den GitHub-Token selbst**, sondern nur Informationen, die benötigt werden, um den gespeicherten Eintrag wiederzufinden.

---

### Linux – Secret Service / KWallet

Unter Linux verwendet GitRewind ebenfalls `keyring`.

Je nach Desktop-Umgebung wird der Token dadurch beispielsweise gespeichert in:

- GNOME Keyring / Secret Service
- KDE KWallet
- einem anderen kompatiblen sicheren Keyring-Backend

Der eigentliche Token wird **nicht als normale Datei im GitRewind-Verzeichnis gespeichert**.

Für Secret Service kann zusätzlich benötigt werden:

```bash
pip install secretstorage
```

Auf einem typischen Linux-Desktop muss außerdem ein funktionierender Secret-Service bzw. Keyring verfügbar sein.

Wenn kein sicherer Keyring verfügbar ist, soll GitRewind den Token **nicht auf einen unsicheren Datei-Fallback zurückstufen**. Stattdessen wird die Speicherung abgelehnt und eine Fehlermeldung angezeigt.

---

### Keine `git_rewind.key` mehr für den normalen Betrieb

Die frühere Variante verwendete auf Linux/macOS einen lokalen Fernet-Schlüssel:

```text
git_rewind.key
```

Diese Lösung ist nicht mehr die vorgesehene Speicherung.

In der aktuellen sicheren Architektur gilt:

```text
Windows → DPAPI
macOS   → Apple Keychain
Linux   → Secret Service / KWallet
```

Damit befindet sich auf macOS/Linux kein eigener Schlüssel neben der Anwendung, mit dem sich der Token direkt entschlüsseln ließe.

---

### Wie sicher ist das?

Für eine lokale Desktop-Anwendung ist diese Architektur sinnvoll und deutlich besser als:

```text
Token verschlüsseln
+
Entschlüsselungsschlüssel im selben App-Ordner speichern
```

Der Schutz ist dennoch nicht absolut.

Kein lokaler Schlüsselspeicher kann einen Token zuverlässig schützen, wenn:

- dein Benutzerkonto bereits vollständig kompromittiert wurde
- Malware unter deinem Benutzerkonto läuft
- ein Angreifer Administrator- bzw. Root-Zugriff auf das laufende System besitzt
- ein Angreifer Zugriff auf deinen entsperrten Benutzer-Schlüsselspeicher erhält

Deshalb sollte der GitHub-Token zusätzlich immer nach dem **Least-Privilege-Prinzip** erstellt werden.

Empfohlen:

```text
Repository access:
nur die Repositories auswählen, die GitRewind wirklich benötigt

Repository permissions:
Metadata → Read
Contents → Read and write
```

---

### Weitere Schutzmaßnahmen in GitRewind

GitRewind versucht zusätzlich:

- GitHub-Tokens aus Protokollausgaben zu maskieren
- den Token nicht dauerhaft in der Git-Remote-URL (`.git/config`) zu speichern
- den Token nur für authentifizierte GitHub-Aufrufe zu verwenden
- auf Linux/macOS keinen unsicheren Datei-Fallback zu verwenden
- den Token beim Abmelden aus dem sicheren Schlüsselspeicher zu entfernen

Trotzdem gilt:

> Ein GitHub Personal Access Token ist ein Zugangsschlüssel. Veröffentliche ihn niemals in einem Repository, Screenshot, Log oder Chat.

---
</details>
<details>
<summary><h2>8. Wie benutze ich GitRewind?</h2></summary>

### Schritt 1 – Voraussetzungen installieren

Prüfe zuerst Git:

```bash
git --version
```

Installiere danach die Python-Abhängigkeiten:

```bash
pip install PyQt6
```

Unter macOS/Linux zusätzlich:

```bash
pip install keyring
```

Unter Linux für Secret Service typischerweise zusätzlich:

```bash
pip install secretstorage
```

---

### Schritt 2 – GitHub Token erstellen

Öffne in GitHub:

```text
Settings
→ Developer settings
→ Personal access tokens
→ Fine-grained tokens
```

Erstelle einen neuen Token.

Empfohlene Einstellungen:

```text
Repository access:
Only select repositories
→ gewünschte Repositories auswählen

Repository permissions:
Metadata → Read
Contents → Read and write
```

---

### Schritt 3 – GitRewind starten

Starte:

```bash
python git_rewind_gui.py
```

---

### Schritt 4 – Bei GitHub anmelden

1. GitHub-Token in GitRewind einfügen.
2. **„Überprüfen & speichern“** drücken.
3. GitRewind prüft den Token.
4. Bei erfolgreicher Anmeldung wird der Token lokal verschlüsselt gespeichert.

---

### Schritt 5 – Repository auswählen

Wähle im Repository-Dropdown das Repository aus, das zurückgesetzt werden soll.

GitRewind lädt anschließend:

- Repository-Informationen
- Push-Berechtigungen
- Commit-Historie

---

### Schritt 6 – Ziel-Commit auswählen

Unter:

```text
Ziel-Commit (gut)
```

wählst du den Commit aus, auf den das Repository zurückgesetzt werden soll.

Beispiel:

```text
A = funktionierender Commit
B = fehlerhafter Commit
```

Dann:

```text
Ziel-Commit = A
```

---

### Schritt 7 – Problem-Commit auswählen

Unter:

```text
Problem-Commit (kaputt)
```

wählst du den Commit aus, der den fehlerhaften Stand repräsentiert.

Dieser Commit wird unter anderem für den Namen des lokalen Backup-Branches verwendet.

---

### Schritt 8 – Optional: Parameter prüfen

Drücke:

```text
Parameter prüfen
```

GitRewind kontrolliert unter anderem:

- GitHub-Login
- Repository
- Ziel-Commit
- Problem-Commit
- grundlegende Push-Berechtigung

---

### Schritt 9 – Rollback starten

Drücke:

```text
Rollback starten
```

GitRewind führt den Rollback aus.

Dabei wird:

1. Git geprüft.
2. Das Repository bei Bedarf geklont.
3. Der aktuelle GitHub-Stand geladen.
4. Ein lokaler Backup-Branch angelegt.
5. `main` auf den Ziel-Commit gesetzt.
6. Der Remote-Stand erneut geprüft.
7. `main` mit `--force-with-lease` zu GitHub übertragen.

---

### Schritt 10 – Ergebnis prüfen

Nach erfolgreichem Abschluss solltest du auf GitHub kontrollieren, ob `main` jetzt auf den gewünschten Commit zeigt.

Kontrolliere zusätzlich lokal:

```bash
git log --oneline -10
```

---

## Wichtige Hinweise

### Kein automatisches `git pull`

Wenn Git meldet:

```text
Your branch is behind 'origin/main'
```

ist das während eines Rollbacks nicht automatisch ein Fehler.

Ein `git pull` würde den Commit, den du gerade entfernen möchtest, unter Umständen wieder einbinden.

### Force-Push verändert Branch-Historie

Der Rollback setzt `main` direkt auf einen früheren Commit.

Das bedeutet, dass neuere Commits danach nicht mehr Teil der normalen `main`-Historie sind.

### Zusammenarbeit mit anderen

Wenn mehrere Personen gleichzeitig am Repository arbeiten, solltest du den Rollback vorher abstimmen.

Andere lokale Klone können nach einem History-Rewrite von `main` nicht mehr zum neuen Remote-Verlauf passen.

### Backup bleibt lokal

Der von GitRewind erzeugte Backup-Branch ist ein lokaler Sicherheitsanker. Prüfe ihn, bevor du lokale Repository-Daten löschst.

---

## Fehlerbehebung

### HTTP 403 / Permission denied

Beispiel:

```text
Permission to OWNER/REPO.git denied
HTTP 403
```

Prüfe:

```text
Fine-Grained Token
→ Repository access
→ Repository ausgewählt

Repository permissions
→ Contents
→ Read and write
```

---

### Token ungültig

Bei:

```text
401
Bad credentials
Authentication failed
```

Token in GitHub prüfen bzw. neu erzeugen und in GitRewind erneut anmelden.

---

### Force-Push wird blockiert

Bei Meldungen wie:

```text
GH006
GH013
protected branch
repository rule violations
```

prüfe die Branch Protection bzw. GitHub Rulesets.

---

### Git wurde nicht gefunden

Prüfe:

```bash
git --version
```

Wenn der Befehl nicht funktioniert, Git installieren und GitRewind danach erneut starten.

---

## Sicherheitsempfehlung

Für GitRewind solltest du einen **eigenen Fine-Grained Token nur für dieses Tool** verwenden.

Empfohlen:

```text
Repository access:
nur benötigte Repositories

Permissions:
Metadata → Read
Contents → Read and write
```

Je weniger Rechte der Token besitzt, desto geringer ist der mögliche Schaden, falls er kompromittiert wird.

---
</details>
