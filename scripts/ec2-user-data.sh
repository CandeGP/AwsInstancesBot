#!/bin/bash
set -Eeuo pipefail

exec > >(tee /var/log/aws-instances-bot-bootstrap.log | logger -t aws-instances-bot-bootstrap -s 2>/dev/console) 2>&1

export DEBIAN_FRONTEND=noninteractive
GAME_DIR="/home/steam/zomboid"
DATA_DIR="/home/steam/zomboid-data"
STEAMCMD_DIR="/home/steam/steamcmd"
ENV_FILE="${GAME_DIR}/server.env"

apt-get update
apt-get install -y \
	ca-certificates \
	curl \
	file \
	gzip \
	lib32gcc-s1 \
	lib32stdc++6 \
	openjdk-17-jre-headless \
	openssl \
	tar \
	unzip \
	util-linux

if ! id steam >/dev/null 2>&1; then
	useradd --create-home --shell /bin/bash steam
fi

install -d -o steam -g steam "${STEAMCMD_DIR}" "${GAME_DIR}" \
	"${DATA_DIR}/Saves" "${DATA_DIR}/Mods" "${DATA_DIR}/logs"

if [[ ! -x "${STEAMCMD_DIR}/steamcmd.sh" ]]; then
	runuser -u steam -- bash -c \
		"cd '${STEAMCMD_DIR}' && curl -fsSL 'https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz' | tar -xzf -"
fi

for attempt in 1 2 3; do
	if runuser -u steam -- "${STEAMCMD_DIR}/steamcmd.sh" \
		+force_install_dir "${GAME_DIR}" \
		+login anonymous \
		+app_update 380870 validate \
		+quit; then
		break
	fi

	if [[ "${attempt}" -eq 3 ]]; then
		echo "SteamCMD could not install Project Zomboid dedicated server after 3 attempts."
		exit 1
	fi
	echo "SteamCMD installation attempt ${attempt} failed; retrying in 30 seconds."
	sleep 30
done

if [[ ! -x "${GAME_DIR}/ProjectZomboid64" ]]; then
	echo "Project Zomboid server binary was not installed at ${GAME_DIR}/ProjectZomboid64."
	exit 1
fi
chmod +x "${GAME_DIR}/ProjectZomboid64"

unzip -p "${GAME_DIR}/java/projectzomboid.jar" \
	org/sqlite/native/Linux/x86_64/libsqlitejdbc.so \
	> "${GAME_DIR}/linux64/libsqlitejdbc.so"
chmod 755 "${GAME_DIR}/linux64/libsqlitejdbc.so"

sed -i \
	-e 's#"java/\."#"/home/steam/zomboid/java/."#' \
	-e 's#"java/projectzomboid\.jar"#"/home/steam/zomboid/java/projectzomboid.jar"#' \
	-e 's#-Djava\.library\.path=linux64/#-Djava.library.path=/home/steam/zomboid/linux64/#' \
	-e 's/-Xmx8g/-Xmx1536m/' \
	"${GAME_DIR}/ProjectZomboid64.json"

umask 077
if [[ ! -f "${ENV_FILE}" ]]; then
	admin_password="$(openssl rand -hex 24)"
	cat > "${ENV_FILE}" <<EOF
SERVER_NAME=servertest
ADMIN_PASSWORD=${admin_password}
GAME_PASSWORD=
MAX_PLAYERS=20
PORT=16261
EOF
	chown steam:steam "${ENV_FILE}"
fi

cat > "${GAME_DIR}/start_server.sh" <<'EOF'
#!/bin/bash
set -Eeuo pipefail

GAME_DIR="/home/steam/zomboid"
DATA_DIR="/home/steam/zomboid-data"

source "${GAME_DIR}/server.env"
mkdir -p "${DATA_DIR}/Saves" "${DATA_DIR}/Mods" "${DATA_DIR}/logs"
chown -R steam:steam "${DATA_DIR}"
cd "${GAME_DIR}"
export LD_LIBRARY_PATH="${GAME_DIR}:${GAME_DIR}/linux64:${GAME_DIR}/linux32:${LD_LIBRARY_PATH:-}"
export PATH="/usr/lib/jvm/java-17-openjdk-amd64/bin:${PATH}"

exec "${GAME_DIR}/start-server.sh" \
	-server \
	-servername "${SERVER_NAME}" \
	-adminpassword "${ADMIN_PASSWORD}" \
	-password "${GAME_PASSWORD}" \
	-port "${PORT}" \
	-maxplayers "${MAX_PLAYERS}" \
	-cachedir "${DATA_DIR}" \
	-logdir "${DATA_DIR}/logs" \
	-modfolders "${DATA_DIR}/Mods" \
	2>&1 | tee -a "${DATA_DIR}/logs/zomboid_$(date +%Y%m%d).log"
EOF

chmod 750 "${GAME_DIR}/start_server.sh"
chown steam:steam "${GAME_DIR}/start_server.sh" "${GAME_DIR}/ProjectZomboid64"

cat > /etc/systemd/system/zomboid.service <<'EOF'
[Unit]
Description=Project Zomboid Dedicated Server
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=steam
Group=steam
WorkingDirectory=/home/steam/zomboid
EnvironmentFile=/home/steam/zomboid/server.env
Environment="LD_LIBRARY_PATH=/home/steam/zomboid:/home/steam/zomboid/linux64:/home/steam/zomboid/linux32"
Environment="PATH=/usr/lib/jvm/java-17-openjdk-amd64/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/steam/zomboid/start_server.sh
Restart=on-failure
RestartSec=15
LimitNOFILE=65536
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/home/steam/zomboid /home/steam/zomboid-data
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now zomboid.service

mkdir -p /opt/aws-instances-bot
cat > /opt/aws-instances-bot/README <<'EOF'
EC2 bootstrap completed with Project Zomboid installed.
Service: zomboid.service
Logs: journalctl -u zomboid.service
Game data: /home/steam/zomboid-data
EOF

systemctl enable amazon-ssm-agent || true
systemctl start amazon-ssm-agent || true

echo "Project Zomboid bootstrap completed successfully."
