param(
    [string]$HostName = "",
    [int]$Port = 0,
    [string]$User = "",
    [string]$RemoteRoot = "",
    [ValidateSet("auto", "backend", "middleware", "system", "health")]
    [string]$Mode = "auto",
    [int]$Lines = 200,
    [switch]$NoFollow
)

$ErrorActionPreference = "Stop"

function Get-ConfigValue {
    param(
        [string]$Value,
        [string]$EnvName,
        [string]$DefaultValue
    )

    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        return $Value
    }

    $envValue = [Environment]::GetEnvironmentVariable($EnvName)
    if (-not [string]::IsNullOrWhiteSpace($envValue)) {
        return $envValue
    }

    return $DefaultValue
}

$HostName = Get-ConfigValue $HostName "RIVERMIND_SSH_HOST" "sh01-ssh.gpuhome.cc"
$User = Get-ConfigValue $User "RIVERMIND_SSH_USER" "root"
$RemoteRoot = Get-ConfigValue $RemoteRoot "RIVERMIND_REMOTE_ROOT" "/root/rivermind-data"

if ($Port -le 0) {
    $portFromEnv = [Environment]::GetEnvironmentVariable("RIVERMIND_SSH_PORT")
    if ([string]::IsNullOrWhiteSpace($portFromEnv)) {
        $Port = 30087
    } else {
        $Port = [int]$portFromEnv
    }
}

if ($Lines -lt 20) {
    $Lines = 20
}

$followFlag = "1"
if ($NoFollow) {
    $followFlag = "0"
}

$sshTarget = "$User@$HostName"
$sshArgs = @(
    "-o", "ServerAliveInterval=20",
    "-o", "ServerAliveCountMax=3",
    "-o", "ConnectTimeout=10",
    "-p", "$Port",
    $sshTarget,
    "bash -s -- '$Mode' '$Lines' '$RemoteRoot' '$followFlag'"
)

# Remote script only reads logs and process metadata.
$remoteScript = @'
set -euo pipefail

MODE="${1:-auto}"
LINES="${2:-200}"
REMOTE_ROOT="${3:-/root/rivermind-data}"
FOLLOW="${4:-1}"

echo "[watch] server: $(hostname)  time: $(date '+%F %T')"
echo "[watch] mode: ${MODE}  lines: ${LINES}  data_root: ${REMOTE_ROOT}"
echo

tail_file() {
  local file="$1"
  echo "[watch] log file: ${file}"
  if [ "${FOLLOW}" = "1" ]; then
    tail -n "${LINES}" -F "${file}"
  else
    tail -n "${LINES}" "${file}"
  fi
}

docker_follow() {
  local pattern="$1"
  local names
  names="$(docker ps --format '{{.Names}}' 2>/dev/null | grep -Ei "${pattern}" || true)"
  if [ -z "${names}" ]; then
    return 1
  fi

  echo "[watch] docker containers:"
  echo "${names}" | sed 's/^/  - /'
  echo

  if [ "${FOLLOW}" = "1" ]; then
    docker logs --tail "${LINES}" -f ${names}
  else
    docker logs --tail "${LINES}" ${names}
  fi
}

journal_follow() {
  local pattern="$1"
  local unit
  unit="$(systemctl list-units --type=service --all --no-legend 2>/dev/null | awk '{print $1}' | grep -Ei "${pattern}" | head -1 || true)"
  if [ -z "${unit}" ]; then
    return 1
  fi

  echo "[watch] systemd service: ${unit}"
  echo

  if [ "${FOLLOW}" = "1" ]; then
    journalctl -u "${unit}" -n "${LINES}" -f --no-pager
  else
    journalctl -u "${unit}" -n "${LINES}" --no-pager
  fi
}

file_follow() {
  local pattern="$1"
  local file
  file="$(find "${REMOTE_ROOT}" /var/log -maxdepth 5 -type f \( -name '*.log' -o -name '*.out' \) 2>/dev/null \
    | grep -Ei "${pattern}" \
    | sort \
    | tail -1 || true)"
  if [ -z "${file}" ]; then
    return 1
  fi
  tail_file "${file}"
}

backend_file_follow() {
  local file
  file="$(find "${REMOTE_ROOT}" /var/log -maxdepth 6 -type f \( -name '*.log' -o -name '*.out' \) 2>/dev/null \
    | grep -Ei 'backend|api|uvicorn|gunicorn|fastapi|travel-agent' \
    | grep -Evi 'middleware|postgres|postgresql|elastic|elasticsearch|redis|chroma|mcp|amap|localtunnel|tunnel|lt' \
    | sort \
    | tail -1 || true)"
  if [ -z "${file}" ]; then
    return 1
  fi
  tail_file "${file}"
}

show_health() {
  echo "[watch] process overview"
  ps -eo pid,ppid,etime,cmd --sort=-etime \
    | grep -Ei 'uvicorn|gunicorn|python|localtunnel|lt --port|travel-agent|docker|postgres|elastic|redis' \
    | grep -v grep \
    | head -80 || true
  echo

  echo "[watch] docker overview"
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true
  echo

  echo "[watch] related systemd services"
  systemctl list-units --type=service --all --no-pager 2>/dev/null \
    | grep -Ei 'travel|river|agent|postgres|elastic|redis|nginx|tunnel|localtunnel' || true
}

case "${MODE}" in
  health)
    show_health
    exit 0
    ;;
  backend)
    docker_follow 'backend|api|uvicorn|gunicorn|fastapi|travel-agent-backend' \
      || journal_follow 'backend|api|uvicorn|gunicorn|fastapi|travel-agent-backend' \
      || backend_file_follow
    ;;
  middleware)
    docker_follow 'postgres|postgresql|elastic|elasticsearch|redis|chroma|mcp|amap' \
      || journal_follow 'postgres|postgresql|elastic|elasticsearch|redis|chroma|mcp|amap' \
      || file_follow 'postgres|postgresql|elastic|elasticsearch|redis|chroma|mcp|amap'
    ;;
  system)
    journal_follow 'nginx|tunnel|localtunnel|frp|caddy|docker' \
      || docker_follow 'nginx|tunnel|localtunnel|frp|caddy' \
      || file_follow 'nginx|tunnel|localtunnel|frp|caddy|system'
    ;;
  auto)
    docker_follow 'backend|api|uvicorn|gunicorn|fastapi|travel-agent-backend' \
      || journal_follow 'backend|api|uvicorn|gunicorn|fastapi|travel-agent-backend' \
      || backend_file_follow \
      || docker_follow 'postgres|postgresql|elastic|elasticsearch|redis|chroma|mcp|amap' \
      || journal_follow 'postgres|postgresql|elastic|elasticsearch|redis|chroma|mcp|amap' \
      || file_follow 'postgres|postgresql|elastic|elasticsearch|redis|chroma|mcp|amap'
    ;;
esac

status=$?
if [ "${status}" -ne 0 ]; then
  echo "[watch] no log source was detected automatically; run -Mode health first."
fi
exit "${status}"
'@

Write-Host "[watch] connect $sshTarget : $Port"
Write-Host "[watch] stop live logs with Ctrl + C"
Write-Host ""

$remoteScript | & ssh @sshArgs
