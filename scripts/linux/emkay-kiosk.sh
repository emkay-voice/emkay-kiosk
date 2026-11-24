#!/usr/bin/env bash
# Emkay Kiosk helper for Linux – https://github.com/emkay-voice/emkay-kiosk
#
# Gives Emkay a fixed screen on a Linux machine (old laptop, mini PC, Raspberry Pi).
# Two ways:
#   --desktop    (default) Emkay starts full screen when you log in to your own desktop.
#   --dedicated  The machine becomes an Emkay: it boots straight into Emkay (cage + greetd),
#                with its own 'emkay' user. This replaces the login screen.
#
# Both make Chromium allow Emkay's microphone and sound without asking, and – where
# PipeWire/WirePlumber is used – make USB microphones and speakers win over HDMI and jack.
#
# Supported: Debian 12+ and Raspberry Pi OS, Fedora, Arch, openSUSE. Ubuntu's Chromium is a
# snap, which this helper can't configure yet (see docs/linux.md).
#
# Usage: sudo ./emkay-kiosk.sh [--url URL] [--desktop | --dedicated] [--user NAME]
#                              [--yes] [--dry-run] [--uninstall]
set -euo pipefail

VERSION="0.1.0"
URL="https://app.emkay.ai"
MODE="desktop"
USER_NAME=""
ASSUME_YES=0
DRY=0
ACTION="install"
LOG="/var/log/emkay-kiosk.log"
STATE="/var/lib/emkay-kiosk"
POLICY="/etc/chromium/policies/managed/emkay.json"
WP_CONF="/etc/wireplumber/wireplumber.conf.d/51-emkay-usb.conf"   # WirePlumber 0.5+
WP_LUA="/etc/wireplumber/main.lua.d/51-emkay-usb.lua"             # WirePlumber 0.4
AUTOSTART_NAME="emkay-kiosk.desktop"

# ---------- output: quiet, one line per step; details go to the log ----------
if [ -t 1 ]; then C=$'\e[36m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; D=$'\e[90m'; N=$'\e[0m'; else C=; G=; Y=; R=; D=; N=; fi
step() { printf '  %s●%s %s\n' "$C" "$N" "$*"; }
done_() { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
note() { printf '    %s%s%s\n' "$D" "$*" "$N"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }
die() { printf '  %s✗%s %s\n' "$R" "$N" "$*" >&2; exit 1; }

usage() {
  sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# Runs a command, or only shows it in --dry-run. Output goes to the log.
run() {
  if [ "$DRY" = 1 ]; then note "would run: $*"; return 0; fi
  echo "+ $*" >>"$LOG"
  "$@" >>"$LOG" 2>&1
}

# Writes stdin to a file (creating its folder), or only shows it in --dry-run.
write_file() {
  local path="$1" content
  content="$(cat)"
  if [ "$DRY" = 1 ]; then note "would write $path:"; printf '%s\n' "$content" | sed 's/^/        /'; return 0; fi
  mkdir -p "$(dirname "$path")"
  printf '%s\n' "$content" >"$path"
  echo "+ wrote $path" >>"$LOG"
}

remove_file() {
  [ -e "$1" ] || return 0
  if [ "$DRY" = 1 ]; then note "would remove $1"; return 0; fi
  rm -f "$1"; echo "+ removed $1" >>"$LOG"
}

# ---------- arguments ----------
while [ $# -gt 0 ]; do
  case "$1" in
    --url) URL="${2:?--url needs an address}"; shift ;;
    --desktop) MODE="desktop" ;;
    --dedicated) MODE="dedicated" ;;
    --user) USER_NAME="${2:?--user needs a name}"; shift ;;
    --yes|-y) ASSUME_YES=1 ;;
    --dry-run) DRY=1 ;;
    --uninstall) ACTION="uninstall" ;;
    --version) echo "emkay-kiosk $VERSION"; exit 0 ;;
    -h|--help) usage ;;
    *) die "Unknown option: $1 (see --help)" ;;
  esac
  shift
done

case "$URL" in http://*|https://*) ;; *) die "The address must start with https:// (got: $URL)" ;; esac
# Chromium's policies want the origin (scheme://host[:port]), not a full address.
ORIGIN="$(printf '%s' "$URL" | sed -E 's#^(https?://[^/]+).*#\1#')"

if [ "$DRY" = 0 ] && [ "$(id -u)" != 0 ]; then
  die "Please run with sudo (or try --dry-run first to see what would happen)."
fi
if [ "$DRY" = 1 ]; then LOG="/dev/null"; fi

# ---------- distribution ----------
FAMILY=""
detect_family() {
  [ -r /etc/os-release ] || die "Can't tell which Linux this is (no /etc/os-release)."
  # shellcheck disable=SC1091
  . /etc/os-release
  local ids=" ${ID:-} ${ID_LIKE:-} "
  case "$ids" in
    *" fedora "*|*" rhel "*) FAMILY="fedora" ;;
    *" arch "*) FAMILY="arch" ;;
    *" suse "*|*" opensuse "*|*opensuse-*) FAMILY="suse" ;;
    *" debian "*|*" ubuntu "*|*" raspbian "*) FAMILY="debian" ;;
    *) die "${PRETTY_NAME:-This Linux} isn't supported yet. Supported: Debian, Raspberry Pi OS, Fedora, Arch, openSUSE." ;;
  esac
  OS_NAME="${PRETTY_NAME:-$ID}"
}

APT_UPDATED=0
pkg_install() {
  case "$FAMILY" in
    debian)
      if [ "$APT_UPDATED" = 0 ]; then run apt-get update; APT_UPDATED=1; fi
      run env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$@" ;;
    fedora) run dnf install -y "$@" ;;
    arch) run pacman -S --needed --noconfirm "$@" ;;
    suse) run zypper -n install "$@" ;;
  esac
}

# ---------- the browser ----------
BROWSER=""
find_browser() {
  local b
  for b in chromium chromium-browser; do
    if command -v "$b" >/dev/null 2>&1; then
      # A snap Chromium ignores /etc/chromium policies.
      case "$(readlink -f "$(command -v "$b")")" in /snap/*) continue ;; esac
      BROWSER="$(command -v "$b")"; return 0
    fi
  done
  return 1
}

ensure_browser() {
  step "Chromium"
  if ! find_browser; then
    if [ "$FAMILY" = debian ] && [ "$APT_UPDATED" = 0 ]; then run apt-get update; APT_UPDATED=1; fi
    if [ "$FAMILY" = debian ] && apt-cache show chromium 2>/dev/null | grep -qi 'snap'; then
      die "This system only offers Chromium as a snap, which this helper can't set up yet. See docs/linux.md."
    fi
    pkg_install chromium
    if [ "$DRY" = 1 ]; then BROWSER="/usr/bin/chromium"; else find_browser || die "Chromium was installed but not found. See $LOG."; fi
  fi
  done_ "Chromium: $BROWSER"
}

browser_command() {
  # --password-store=basic: no keyring prompt on a machine that logs in by itself.
  printf '%s --kiosk --no-first-run --noerrdialogs --disable-session-crashed-bubble --password-store=basic --autoplay-policy=no-user-gesture-required --ozone-platform-hint=auto %s' \
    "$BROWSER" "$URL"
}

allow_mic_and_sound() {
  step "Letting Emkay use the microphone and play sound without asking"
  write_file "$POLICY" <<EOF
{
  "AudioCaptureAllowedUrls": ["$ORIGIN"],
  "AutoplayAllowlist": ["$ORIGIN"]
}
EOF
  done_ "Chromium allows the microphone and sound for $ORIGIN"
}

# ---------- sound ----------
ensure_sound() {
  step "Sound"
  if command -v pipewire >/dev/null 2>&1 || command -v pulseaudio >/dev/null 2>&1; then
    done_ "Sound server already in place"
  else
    case "$FAMILY" in
      debian|arch) pkg_install pipewire pipewire-pulse wireplumber ;;
      fedora|suse) pkg_install pipewire pipewire-pulseaudio wireplumber ;;
    esac
    done_ "PipeWire installed"
  fi

  if ! command -v wireplumber >/dev/null 2>&1; then
    note "No WirePlumber here, so the USB rule is skipped. Set the default microphone in the sound settings."
    return 0
  fi
  local v
  v="$(wireplumber --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)"
  case "$v" in
    0.4)
      write_file "$WP_LUA" <<'EOF'
-- Emkay Kiosk: USB microphones and speakers win over HDMI and jack.
table.insert(alsa_monitor.rules, {
  matches = {
    { { "node.name", "matches", "alsa_input.usb-*" } },
    { { "node.name", "matches", "alsa_output.usb-*" } },
  },
  apply_properties = { ["priority.session"] = 2000, ["priority.driver"] = 2000 },
})
EOF
      ;;
    *)
      write_file "$WP_CONF" <<'EOF'
# Emkay Kiosk: USB microphones and speakers win over HDMI and jack.
monitor.alsa.rules = [
  {
    matches = [
      { node.name = "~alsa_input.usb-.*" }
      { node.name = "~alsa_output.usb-.*" }
    ]
    actions = {
      update-props = {
        priority.session = 2000
        priority.driver = 2000
      }
    }
  }
]
EOF
      ;;
  esac
  done_ "USB microphones and speakers come first (WirePlumber ${v:-?})"
}

# ---------- desktop mode ----------
install_desktop() {
  local u="${USER_NAME:-${SUDO_USER:-${USER:-}}}" home
  [ -n "$u" ] && [ "$u" != root ] || die "Which user's desktop? Run with sudo from your own account, or add --user NAME."
  home="$(getent passwd "$u" | cut -d: -f6)"
  [ -n "$home" ] || die "No user called $u."
  step "Starting Emkay full screen when $u logs in"
  write_file "$home/.config/autostart/$AUTOSTART_NAME" <<EOF
[Desktop Entry]
Type=Application
Name=Emkay
Comment=Emkay full screen (emkay-kiosk)
Exec=$(browser_command)
X-GNOME-Autostart-enabled=true
EOF
  if [ "$DRY" = 0 ]; then chown -R "$u:" "$home/.config/autostart"; fi
  done_ "Emkay starts at login (press Alt+F4 to close it)"
}

# ---------- dedicated mode ----------
install_dedicated() {
  local u="${USER_NAME:-emkay}" g groups=""
  if [ "$ASSUME_YES" = 0 ] && [ "$DRY" = 0 ]; then
    warn "Dedicated mode replaces this machine's login screen: it will boot straight into Emkay."
    read -r -p "    Continue? [y/N] " a
    case "$a" in y|Y|yes|YES) ;; *) die "Nothing changed." ;; esac
  fi

  step "A user for Emkay ($u)"
  if ! getent passwd "$u" >/dev/null; then
    for g in audio video render input; do getent group "$g" >/dev/null && groups="${groups:+$groups,}$g"; done
    run useradd -m -s /bin/bash ${groups:+-G "$groups"} "$u"
    run passwd -l "$u"
  fi
  done_ "User $u (no password; nobody logs in as it by hand)"

  step "Kiosk shell (cage) and autologin (greetd)"
  pkg_install cage greetd
  done_ "cage and greetd installed"

  step "Booting straight into Emkay"
  if [ "$DRY" = 0 ]; then
    mkdir -p "$STATE"
    echo dedicated >"$STATE/mode"
    echo "$u" >"$STATE/user"
    systemctl get-default >"$STATE/default-target" 2>/dev/null || true
    if [ -L /etc/systemd/system/display-manager.service ]; then
      basename "$(readlink -f /etc/systemd/system/display-manager.service)" >"$STATE/display-manager"
    fi
    if [ -f /etc/greetd/config.toml ] && [ ! -f "$STATE/greetd-config.toml" ]; then
      cp /etc/greetd/config.toml "$STATE/greetd-config.toml"
    fi
  fi
  write_file /etc/greetd/config.toml <<EOF
# Written by emkay-kiosk – boots straight into Emkay. Undo with: emkay-kiosk.sh --uninstall
[terminal]
vt = 7

[default_session]
command = "cage -s -- $(browser_command)"
user = "$u"
EOF
  if [ -f "$STATE/display-manager" ] || [ "$DRY" = 1 ]; then
    run systemctl disable display-manager.service || true
  fi
  run systemctl enable greetd.service
  run systemctl set-default graphical.target
  done_ "Emkay starts at boot – restart the machine to begin"
}

# ---------- uninstall ----------
uninstall() {
  step "Removing Emkay Kiosk"
  remove_file "$POLICY"
  remove_file "$WP_CONF"
  remove_file "$WP_LUA"
  local f
  for f in /home/*/.config/autostart/"$AUTOSTART_NAME" /root/.config/autostart/"$AUTOSTART_NAME"; do
    remove_file "$f"
  done
  if [ -f "$STATE/mode" ]; then
    run systemctl disable greetd.service || true
    if [ -f "$STATE/greetd-config.toml" ]; then
      run cp "$STATE/greetd-config.toml" /etc/greetd/config.toml
    else
      remove_file /etc/greetd/config.toml
    fi
    if [ -f "$STATE/display-manager" ]; then
      run systemctl enable "$(cat "$STATE/display-manager")" || true
    fi
    if [ -f "$STATE/default-target" ]; then
      run systemctl set-default "$(cat "$STATE/default-target")" || true
    fi
    note "The user $(cat "$STATE/user" 2>/dev/null || echo emkay) and Emkay's data were kept. Remove them with: sudo userdel -r <user>"
  fi
  if [ "$DRY" = 1 ]; then note "would remove $STATE"; else rm -rf "$STATE"; fi
  done_ "Emkay Kiosk removed – restart to get the old login back"
}

# ---------- main ----------
echo
printf '  E M K A Y   K I O S K   %s%s%s\n' "$D" "$VERSION" "$N"
if [ "$DRY" = 1 ]; then printf '  %sdry run – nothing is changed%s\n' "$Y" "$N"; fi
echo
if [ "$ACTION" = uninstall ]; then
  uninstall
  exit 0
fi

detect_family
note "$OS_NAME · $MODE mode · $URL"
if [ "$DRY" = 0 ]; then : >>"$LOG"; fi
ensure_browser
allow_mic_and_sound
ensure_sound
if [ "$MODE" = dedicated ]; then install_dedicated; else install_desktop; fi
echo
if [ "$DRY" = 0 ]; then note "Details: $LOG"; echo; fi
