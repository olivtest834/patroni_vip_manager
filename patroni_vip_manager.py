#!/usr/bin/env python3
#
# Description: Add or remove Virtual IP according to the Patroni role
#
# Required packages:
# - python3-pyyaml
# - python3-requests
#=======================================================================
# 2025-11-29        Olivier GAMACHE         First release
# 2026-01-20        Olivier GAMACHE         Some updates
#=======================================================================

import warnings
warnings.filterwarnings("ignore")

import requests
import json
import yaml
from pathlib import Path
import psutil
import subprocess
import time

import urllib3
urllib3.disable_warnings()


script_dir = str(Path(__file__).parent)
cfg_file = script_dir +'/patroni_vip_manager.json'



########## Main ##########
if __name__ == "__main__":

    # Parameters
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", required=False, action='store_true')
    args = parser.parse_args()

    # Load Config
    print("Loading config file ...")
    try:
        with open(cfg_file, 'r') as f:
            cfg = json.load(f)
        print(json.dumps(cfg, indent=4))
    except Exception as error:
        print(error)
        exit(1)


    # Load Patroni Config
    print("\nLoading patroni config file")
    try:
        with open(cfg["patroni_cfg_file"], 'r') as f:
            patroni_cfg = yaml.safe_load(f)
        patroni_url = 'http://' +patroni_cfg['restapi']['listen']
        print(patroni_url)
    except Exception as error:
        print(error)
        exit(1)


    print("\nStart of the loop")
    while True:
    
        try:
            response = requests.get(patroni_url, verify=False)
            role = response.json()['role']
        except Exception as e:
            print("Cannot retrieve role from " +patroni_url)
            print(e)
            role = None

        if args.debug == True:
            print("Role: " +role)
    

        # init values
        vips_to_add = []
        vips_to_del = []


        if role == "primary":
            vips_to_add.append({
                "role":"primary",
                "interface":cfg["vips"]["primary"]["interface"],
                "ip": cfg["vips"]["primary"]["ip"]
            })
            if "replica" in cfg["vips"]:
                vips_to_del.append({
                    "role":"replica",
                    "interface":cfg["vips"]["replica"]["interface"],
                    "ip": cfg["vips"]["replica"]["ip"]
                })
        elif role == "replica":
            if "replica" in cfg["vips"]:
                vips_to_add.append({
                    "role":"replica",
                    "interface":cfg["vips"]["replica"]["interface"],
                    "ip": cfg["vips"]["replica"]["ip"]
                })
            vips_to_del.append({
                "role":"primary",
                "interface": cfg["vips"]["primary"]["interface"],
                "ip": cfg["vips"]["primary"]["ip"]
            })
        else:
            vips_to_del.append({
                "role":"primary",
                "interface": cfg["vips"]["primary"]["interface"],
                "ip": cfg["vips"]["primary"]["ip"]
            })
            if "replica" in cfg["vips"]:
                vips_to_del.append({
                    "role":"replica",
                    "interface":cfg["vips"]["replica"]["interface"],
                    "ip": cfg["vips"]["replica"]["ip"]
                })
    
        if args.debug == True:
            print("VIPs to add if not exists:", json.dumps(vips_to_add, indent=4))
            print("VIPs to delete if exists:", json.dumps(vips_to_del, indent=4))
    
    
        interfaces = psutil.net_if_addrs()
    


        # Add VIP
        for vip_to_add in vips_to_add:
            vip_interface = vip_to_add["interface"]
            vip_ip = vip_to_add["ip"]
            vip_found = False

            for if_ip in interfaces[vip_interface]:
                if if_ip.address == vip_ip:
                    if args.debug == True:
                        print("OK, vip already configured with IP", vip_ip)
                    vip_found = True
        
            if vip_found == False:
                print(f"Add IP address {vip_ip} to {vip_interface} ...")
                cmd = ["ip", "addr", "add", f"{vip_ip}/24", "dev", vip_interface]
                try:
                    subprocess.run(cmd, check=True)
                    print("IP address added")
                except subprocess.CalledProcessError as e:
                    print("Error :", e)
    


        # Del VIP
        for vip_to_del in vips_to_del:
            vip_interface = vip_to_del["interface"]
            vip_ip = vip_to_del["ip"]
            vip_found = False

            for if_ip in interfaces[vip_interface]:
                if if_ip.address == vip_ip:
                    print("Interface already configured with IP {vip_ip}, ip need to be deleted")
                    vip_found = True
        
            if vip_found == True:
                print(f"Remove IP address {vip_ip} from {vip_interface} ...")
                cmd = ["ip", "addr", "del", f"{vip_ip}/24", "dev", vip_interface]
                try:
                    subprocess.run(cmd, check=True)
                    print("IP address removed")
                except subprocess.CalledProcessError as e:
                    print("Error :", e)
    

        time.sleep(int(cfg["wait"]))

