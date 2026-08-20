#!/usr/bin/env bash
#
# SessionStart-Hook: meldet, wie viele Commits der ausgecheckte Stand hinter
# origin/<default-branch> liegt.
#
# GRUND
#   Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
#   Ursache nicht im Diff stand - die fehlenden Commits waren jeweils genau
#   die, die das Gate einfuehrten, an dem der Branch scheiterte. Die Pruefung
#   kostet eine Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.
#
# OBERSTE REGEL: NIEMALS BLOCKIEREN
#   Kein Netz, kein Remote, kein origin/HEAD, detached HEAD, flatterndes DNS,
#   fehlende Credentials - jeder dieser Faelle geht still durch: exit 0, keine
#   Ausgabe. Ein Hook, der bei Netzproblemen die Arbeit anhaelt, wird nach dem
#   zweiten Mal abgeschaltet und schuetzt danach gar nichts.
#
#   Darum bewusst KEIN `set -e`: ein fehlschlagendes git-Kommando darf den Hook
#   nicht abbrechen, sondern muss in den stillen Ausstieg laufen. Der EXIT-Trap
#   erzwingt zusaetzlich den Rueckgabewert 0, auch bei einem Fehler, den dieses
#   Skript nicht vorhergesehen hat.
#
# AUSGABE
#   Nur wenn tatsaechlich Commits fehlen. Bei 0 schweigt der Hook.

set -u
trap 'exit 0' EXIT

# Sekunden, die eine Netzoperation hoechstens dauern darf.
NET_TIMEOUT=5

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# --- Netzoperationen hart begrenzen -----------------------------------------
# Alle Ausgaben nach /dev/null: ein Hintergrundprozess, der die stdout-Pipe des
# Hooks offen haelt, wuerde den Sessionstart genau so haengen lassen wie ein
# haengendes fetch.
with_timeout() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "${NET_TIMEOUT}s" "$@" >/dev/null 2>&1
    return $?
  fi

  # Fallback ohne coreutils-timeout: macOS liefert `timeout` nicht mit, dort
  # laeuft also genau dieser Zweig - selbst pollen.
  #
  # `set -m` gibt dem Hintergrundjob eine eigene Prozessgruppe (pgid == pid),
  # damit der Kill unten die ganze Gruppe trifft. Ohne das ueberlebt die
  # Verwandtschaft: `git fetch` startet Kindprozesse (git-remote-https, ssh),
  # und ein Kill nur auf die pid laesst die weiterlaufen - gemessen, nicht
  # vermutet. Sie halten die stdout-Pipe des Hooks zwar nicht offen (die
  # Umlenkung nach /dev/null wird vererbt), koennen aber eine
  # FETCH_HEAD.lock hinterlassen, an der das naechste fetch scheitert. Der
  # Hook schweigt dann - und ein stiller Hook ist genau der Zustand, vor dem
  # er warnen soll.
  set -m
  "$@" >/dev/null 2>&1 &
  local pid=$! waited=0 limit=$((NET_TIMEOUT * 10))
  set +m
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$waited" -ge "$limit" ]; then
      # Erst die Gruppe, dann ersatzweise die pid allein, falls das Anlegen
      # der Gruppe nicht geklappt hat.
      kill -9 -"$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
      wait "$pid" 2>/dev/null
      return 124
    fi
    sleep 0.1
    waited=$((waited + 1))
  done
  wait "$pid" 2>/dev/null
  return $?
}

# --- Vorbedingungen ----------------------------------------------------------
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || exit 0   # leeres Repo
git remote get-url origin >/dev/null 2>&1 || exit 0             # kein Remote

# Auf "compact" nicht erneut ins Netz: der Klon ist derselbe wie beim Start.
if [ ! -t 0 ]; then
  payload=$(cat 2>/dev/null)
  case "$payload" in
    *'"source"'*'"compact"'*) exit 0 ;;
  esac
fi

# Niemals interaktiv nachfragen - ein Passwort-Prompt haengt ohne Timeout.
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes -o ConnectTimeout=${NET_TIMEOUT}"
export GIT_ASKPASS=/bin/true
export GCM_INTERACTIVE=Never

# --- Default-Branch ermitteln, nicht annehmen --------------------------------
# "main" zu raten hat schon einmal einen Branch 15 Commits alt werden lassen:
# im Portfolio heissen mehrere Repos ihren Default-Branch "master".
read_origin_head() {
  git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null
}

default_branch=$(read_origin_head)
if [ -z "$default_branch" ]; then
  # Remote fragen. `set-head --auto` schreibt refs/remotes/origin/HEAD, es muss
  # also keine Ausgabe eingesammelt werden - der Wert wird danach lokal gelesen.
  with_timeout git remote set-head origin --auto || exit 0
  default_branch=$(read_origin_head)
fi
default_branch=${default_branch#origin/}
[ -n "$default_branch" ] || exit 0

# --- Abstand messen ----------------------------------------------------------
with_timeout git fetch origin "$default_branch" || exit 0

# FETCH_HEAD, nicht refs/remotes/...: FETCH_HEAD wird von diesem fetch garantiert
# frisch geschrieben. Ein Vergleich gegen eine Referenz, die das fetch je nach
# git-Version gar nicht anfasst, koennte einen alten Stand melden.
behind=$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)
case "$behind" in
  ''|*[!0-9]*) exit 0 ;;   # kein zaehlbares Ergebnis -> schweigen
  0)           exit 0 ;;   # aktuell -> schweigen
esac

# --- Nur jetzt wird geredet --------------------------------------------------
if [ "$behind" -eq 1 ]; then
  commit_word="Commit"
else
  commit_word="Commits"
fi

head_label=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ -z "$head_label" ] || [ "$head_label" = "HEAD" ]; then
  head_label="detached HEAD ($(git rev-parse --short HEAD 2>/dev/null))"
fi

cat <<EOF
[Klon-Aktualitaet] $head_label liegt $behind $commit_word hinter origin/$default_branch.

Vor der Arbeit aktualisieren:
    git fetch origin $default_branch && git merge origin/$default_branch

Grund: ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff
steht - es fehlen typischerweise genau die Commits, die das Gate einfuehren,
an dem der Branch dann scheitert.
EOF

exit 0
