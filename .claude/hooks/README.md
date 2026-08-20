# SessionStart-Hook: Klon-Aktualität

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<default-branch>` liegt.

Registriert in `.claude/settings.json` unter `hooks.SessionStart`. Der Grund
steht hier und nicht dort, weil `settings.json` striktes JSON ist und keine
Kommentare trägt.

## Warum

Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte. Die Prüfung kostet eine
Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.

Damit ist die Prüfung aus `CLAUDE.md` («Vor der Arbeit») automatisiert: sie
läuft, ohne dass jemand daran denken muss.

## Verhalten

| Situation | Verhalten |
| --- | --- |
| Stand ist aktuell (0 Commits) | schweigt |
| Stand liegt zurück | meldet Anzahl, Default-Branch und den Update-Befehl |
| Kein Netz, DNS flattert, `origin` nicht erreichbar | still, `exit 0` |
| Kein Git-Repo, kein Remote, leeres Repo | still, `exit 0` |
| Detached HEAD | wird gemessen und mit Kurz-SHA benannt |
| `source: compact` | übersprungen — der Klon ist derselbe wie beim Start |

## Die drei Zusicherungen

**1. Der Hook blockiert die Session niemals.** Kein `set -e` (ein
fehlschlagendes `git` soll in den stillen Ausstieg laufen, nicht abbrechen),
dazu `trap 'exit 0' EXIT` als Netz für alles, was dieses Skript nicht
vorhergesehen hat. Ein Hook, der bei Netzproblemen die Arbeit anhält, wird
nach dem zweiten Mal abgeschaltet und schützt danach gar nichts.

**2. Netzoperationen sind hart begrenzt.** `NET_TIMEOUT=5` Sekunden pro
Aufruf, umgesetzt über `timeout(1)`; wo es das nicht gibt, pollt
`with_timeout` den Hintergrundprozess selbst und killt ihn. Zusätzlich
`timeout: 15` in `settings.json` als Backstop auf Harness-Ebene.

Der Fallback ist nicht der Sonderfall: macOS liefert `timeout` nicht mit, dort
läuft also genau dieser Zweig. Er killt die **Prozessgruppe**, nicht nur die
pid — `git fetch` startet Kindprozesse (`git-remote-https`, `ssh`), die einen
Kill auf die pid allein überleben. Gemessen mit einem `git`, das im `fetch`
hängt: `timeout(1)`-Pfad 0 Waisen, Fallback-Pfad vor dem Fix 1 Waise, danach
0. Die stdout-Pipe halten sie nicht offen (die Umlenkung nach `/dev/null` wird
vererbt), sie können aber eine `FETCH_HEAD.lock` hinterlassen, an der das
nächste `fetch` scheitert — und der Hook schweigt bei jedem Fehler. Ein
stiller Hook ist genau der Zustand, vor dem er warnen soll.

Zwei Fallen, die beide zum Hänger führen und darum beide entschärft sind:

- Ein Passwort- oder Passphrase-Prompt wartet ohne Timeout ewig. Deshalb
  `GIT_TERMINAL_PROMPT=0`, `GIT_ASKPASS`, `ssh -o BatchMode=yes`.
- Ein Hintergrundprozess, der die stdout-Pipe des Hooks offen hält, lässt den
  Sessionstart genauso hängen wie ein hängendes `fetch` — auch dann, wenn der
  Hook selbst schon zurückgekehrt ist. Deshalb gehen in `with_timeout` alle
  Ausgaben nach `/dev/null`, und der Abstand wird über `FETCH_HEAD` (eine
  Datei) statt über eingesammelte Ausgabe gemessen.

**3. Der Default-Branch wird ermittelt, nicht angenommen.** Zuerst lokal
`refs/remotes/origin/HEAD`, sonst `git remote set-head origin --auto` (mit
Timeout) und danach erneut lokal lesen. Fällt beides aus, schweigt der Hook,
statt auf `main` zu raten: Im Portfolio heissen `openlex-mcp`,
`swiss-courts-mcp` und `swisstopo-mcp` ihren Default-Branch `master`, und
genau diese Annahme hat schon einmal einen Branch 15 Commits alt werden
lassen.

`set-head --auto` schreibt die Referenz selbst, deshalb muss keine Ausgabe
eingesammelt werden — der Wert wird anschliessend lokal gelesen. Das hält
Punkt 2 ein.

## Testen

```bash
CLAUDE_PROJECT_DIR="$PWD" ./.claude/hooks/session-start.sh </dev/null; echo "exit=$?"
```

Erwartung auf aktuellem Stand: keine Ausgabe, `exit=0`.

Gegenprobe — künstlich zurückfallen und prüfen, dass der Hook anschlägt:

```bash
git checkout -q --detach HEAD~3
CLAUDE_PROJECT_DIR="$PWD" ./.claude/hooks/session-start.sh </dev/null; echo "exit=$?"
git checkout -q -
```

Gegenprobe zur Nicht-Blockier-Zusicherung — ein Remote, der nirgendwohin
führt, muss still und schnell durchgehen:

```bash
git -c remote.origin.url=https://192.0.2.1/nope.git \
  ... # bzw. in einem Wegwerf-Klon: git remote set-url origin https://192.0.2.1/nope.git
time (CLAUDE_PROJECT_DIR="$PWD" ./.claude/hooks/session-start.sh </dev/null; echo "exit=$?")
```

Erwartung: keine Ausgabe, `exit=0`, deutlich unter 15 Sekunden.

Gegenprobe zum Prozessgruppen-Kill — ein `git`, das im `fetch` hängt, und ein
`PATH` ohne `timeout(1)`, damit der Fallback läuft:

```bash
waisen() { ps -eo comm=,args= | awk '$1 ~ /(^|\/)sleep$/ && /3117/ {n++} END {print n+0}'; }
d=$(mktemp -d); real=$(command -v git)
printf '#!/usr/bin/env bash\ncase "$1" in fetch) sleep 3117;; esac\nexec %s "$@"\n' "$real" > "$d/git"
chmod +x "$d/git"
for b in bash sed cat sleep kill env; do ln -s "$(command -v $b)" "$d/$b"; done
PATH="$d" CLAUDE_PROJECT_DIR="$PWD" ./.claude/hooks/session-start.sh </dev/null
sleep 1; [ "$(waisen)" -eq 0 ] && echo "OK: keine Waise" || echo "FEHLER: Waise"
```

Erwartung: Rückkehr nach ~5 s, danach `OK: keine Waise`.

**Nicht `pgrep -f 'sleep 3117'` benutzen.** `-f` matcht die ganze
Kommandozeile, und die Zeile, die den Test *startet*, enthält das Muster
selbst — der Aufruf findet also die eigene Shell und meldet eine Waise, die es
nicht gibt. Genau das ist hier einmal passiert und hätte den Fix beinahe als
wirkungslos erscheinen lassen. Darum `comm` prüfen, nicht `args`. Aus
demselben Grund ist `pkill -f` beim Aufräumen gefährlich: es erschiesst die
eigene Shell.

Gegenprobe zur Gegenprobe — das Rezept muss anschlagen, wenn der Fix fehlt:
`set -m` auskommentieren, `kill -9 -"$pid"` auf `kill -9 "$pid"` zurücksetzen,
Lauf wiederholen. Erwartung: `FEHLER: Waise`. Ohne diesen Schritt wäre nicht
gezeigt, dass der Test überhaupt etwas prüft.

## Reichweite

Der Hook ist nicht auf `$CLAUDE_CODE_REMOTE` eingeschränkt. Er installiert
nichts, verändert den Arbeitsbaum nicht und ist ausserhalb des
Zurückliegens stumm — und ein veralteter Klon entsteht lokal genauso wie in
einer Websession. Er wirkt für alle erst, sobald er auf `main` gemergt ist.
