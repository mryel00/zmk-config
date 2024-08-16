#!/usr/bin/env python3

import asyncio
import shutil
import yaml
import os

# MARK: CONFIGURATION
ZEPHYR_VERSION="3.5"
MULTITHREAD="true"

OUTPUT_DIR="/mnt/d/Programming_Projects/Cloned_Projects/zmk-config/firmware_build"
LOG_DIR="/tmp"

HOME = os.environ['HOME']
HOST_ZMK_DIR=HOME+"/zmk"
HOST_MODULES_DIR=HOME+"/zmk-modules"
HOST_CONFIG_DIR="/mnt/d/Programming_Projects/Cloned_Projects/zmk-config"

DOCKER_ZMK_DIR="/workspace/zmk"
DOCKER_MODULES_DIR="/workspace/zmk-modules"
DOCKER_CONFIG_DIR="/workspace/zmk-config"

DOCKER_IMG=f"zmkfirmware/zmk-dev-arm:{ZEPHYR_VERSION}"
DOCKER_BIN="podman"

build_config = None

with open(HOST_CONFIG_DIR+"/build.yaml", "r") as stream:
    try:
        build_config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

west_config = None

with open(HOST_CONFIG_DIR+"/config/west.yml", "r") as stream:
    try:
        west_config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

DOCKER_CMD=f'{DOCKER_BIN} run --rm ' \
    f'--mount type=bind,source={HOST_ZMK_DIR},target={DOCKER_ZMK_DIR} ' \
    f'--mount type=bind,source={HOST_MODULES_DIR},target={DOCKER_MODULES_DIR},readonly ' \
    f'--mount type=bind,source={HOST_CONFIG_DIR},target={DOCKER_CONFIG_DIR},readonly ' \
    f'--mount type=volume,source=zmk-root-user-{ZEPHYR_VERSION},target=/root ' \
    f'--mount type=volume,source=zmk-zephyr-{ZEPHYR_VERSION},target={DOCKER_ZMK_DIR}/zephyr ' \
    f'--mount type=volume,source=zmk-zephyr-modules-{ZEPHYR_VERSION},target={DOCKER_ZMK_DIR}/modules ' \
    f'--mount type=volume,source=zmk-zephyr-tools-{ZEPHYR_VERSION},target={DOCKER_ZMK_DIR}/tools'

DOCKER_PREFIX=f"{DOCKER_CMD} -w {DOCKER_ZMK_DIR}/app {DOCKER_IMG}"
SUFFIX=f"{ZEPHYR_VERSION}_docker"
CONFIG_DIR=f"{DOCKER_CONFIG_DIR}/config"

# TODO: Translate to python
# if [[ -f config/combos.dtsi ]]; then
#     # update maximum combos per key
#     count=$(
#         tail -n +10 config/combos.dtsi |
#             grep -Eo '[LR][TMBH][0-9]' |
#             sort | uniq -c | sort -nr |
#             awk 'NR==1{print $1}'
#     )
#     sed -Ei "/CONFIG_ZMK_COMBO_MAX_COMBOS_PER_KEY/s/=.+/=$count/" config/*.conf
#     echo "Setting MAX_COMBOS_PER_KEY to $count"

#     # update maximum keys per combo
#     count=$(
#         tail -n +10 config/combos.dtsi |
#             grep -o -n '[LR][TMBH][0-9]' |
#             cut -d : -f 1 | uniq -c | sort -nr |
#             awk 'NR==1{print $1}'
#     )
#     sed -Ei "/CONFIG_ZMK_COMBO_MAX_KEYS_PER_COMBO/s/=.+/=$count/" config/*.conf
#     echo "Setting MAX_KEYS_PER_COMBO to $count"
# fi

# MARK: BUILD FIRMWARE

async def compile_board(board: str, shield: str, modules: str):
    BUILD_DIR=f"{board}_{shield.replace(' ','_')}_{SUFFIX}"
    LOGFILE=f"{LOG_DIR}/zmk_build_{board}_{shield.replace(' ','_')}.log"
    print(f"Building {board} with shield {shield}...")
    # print(f'{DOCKER_PREFIX} west build -p -d "build/{BUILD_DIR}" -b {board} -- -DZMK_CONFIG="{CONFIG_DIR}" -Wno-dev -DSHIELD="{shield}" -DCONFIG_BUILD_OUTPUT_UF2=y > "{LOGFILE}" 2>&1')
    p = await asyncio.create_subprocess_shell(f'{DOCKER_PREFIX} west build -p -d "build/{BUILD_DIR}" -b {board} ' \
        f'-- -DZMK_CONFIG="{CONFIG_DIR}" -Wno-dev -DSHIELD="{shield}" -DCONFIG_BUILD_OUTPUT_UF2=y > "{LOGFILE}" 2>&1')
    await p.wait()
    await asyncio.sleep(2)
    shutil.move(f"{HOST_ZMK_DIR}/app/build/{BUILD_DIR}/zephyr/zmk.uf2", f"{OUTPUT_DIR}/{shield.replace(' ','_')}-{board}-zmk.uf2")
    print(f"Building {board} with shield {shield}... Done!")

async def main():
    tasks = []
    for build in build_config["include"]:
        tasks.append(asyncio.create_task(compile_board(build["board"], build["shield"], '')))
    await asyncio.wait(tasks) 

loop = asyncio.get_event_loop() 
loop.run_until_complete(main()) 
loop.close() 
