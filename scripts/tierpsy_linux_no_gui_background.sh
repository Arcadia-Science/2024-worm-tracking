#!/bin/bash

local_folder_to_mount="$HOME/github/2024-worm-tracking"
network_folder_to_mount=""

# Check if Docker service is active, start or restart if necessary
if ! systemctl is-active --quiet docker; then
    echo "Docker service is not active. Trying to start Docker..."
    sudo systemctl start docker
    # Wait a bit and check if the service is up
    sleep 5
    if ! systemctl is-active --quiet docker; then
        echo "Failed to start Docker. Please check the service status manually."
        exit 1
    fi	
else
    echo "Docker is already running."
fi

# Create array of arguments for docker run.
docker_arguments=(-d --rm)
docker_arguments+=(--name my_tierpsy_container)
docker_arguments+=(--sysctl net.ipv4.tcp_keepalive_intvl=30)
docker_arguments+=(--sysctl net.ipv4.tcp_keepalive_probes=5)
docker_arguments+=(--sysctl net.ipv4.tcp_keepalive_time=100)
docker_arguments+=(--hostname tierpsydocker)

# if local folder not empty, add to array
if [[ ! -z "$local_folder_to_mount" ]]; then
    docker_arguments+=(-v "${local_folder_to_mount}:/DATA/local_drive")
fi

# if network folder is not empty, add to array
if [[ ! -z "$network_folder_to_mount" ]]; then
    docker_arguments+=(-v "${network_folder_to_mount}:/DATA/network_drive")
fi

# launch using the parameters in the array
docker run "${docker_arguments[@]}" arcadiascience/tierpsy-tracker-no-gui:fc691a090d8a tail -f /dev/null
